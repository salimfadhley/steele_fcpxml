"""ffprobe-based video metadata probing, with a module-level cache.

:func:`_probe_video` shells out to ``ffprobe`` to read a video file's frame
rate, dimensions and duration, returning a :class:`VideoInfo`. Results are
cached by resolved path so repeated probes of the same file are free.
:func:`clear_cache` empties that cache.

``ffprobe`` (part of FFmpeg) must be installed and on ``PATH`` for probing to
work. The CSV field order ffprobe emits is not stable across files, so the
parser identifies fields by shape (the ``num/den`` token is the frame rate,
integer tokens are width/height) rather than by position.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from steele_fcpxml.timecode import FrameRate

__all__ = ["VideoInfo", "clear_cache"]


@dataclass(frozen=True)
class VideoInfo:
    """Probed video file metadata. Cached at module level.

    Examples:
        >>> from fractions import Fraction
        >>> from pathlib import Path
        >>> info = VideoInfo(
        ...     path=Path("/video.mp4"),
        ...     fps_exact=Fraction(30000, 1001),
        ...     fps_standard=FrameRate.FPS_29_97,
        ...     width=1920,
        ...     height=1080,
        ...     duration_sec=120.0,
        ... )
        >>> info.frame_duration
        '1001/30000s'
        >>> info.fps_numerator, info.fps_denominator
        (30000, 1001)
    """

    path: Path
    fps_exact: Fraction
    fps_standard: FrameRate | None
    width: int
    height: int
    duration_sec: float

    @property
    def frame_duration(self) -> str:
        """FCPXML frame duration string derived from the exact fps."""
        if self.fps_standard is not None:
            return self.fps_standard.frame_duration
        recip = Fraction(1) / self.fps_exact
        return f"{recip.numerator}/{recip.denominator}s"

    @property
    def fps_numerator(self) -> int:
        """Numerator of the exact fps fraction."""
        return self.fps_exact.numerator

    @property
    def fps_denominator(self) -> int:
        """Denominator of the exact fps fraction."""
        return self.fps_exact.denominator


# -- ffprobe cache ----------------------------------------------------------

_ffprobe_cache: dict[Path, VideoInfo] = {}


def clear_cache() -> None:
    """Clear the module-level ffprobe result cache."""
    _ffprobe_cache.clear()


def _canonical_case(path: Path) -> Path | None:
    """Return ``path`` carrying the real on-disk filename casing.

    Returns ``None`` if no case-insensitively-matching entry exists in the
    parent directory (i.e. the file is genuinely missing).

    Why not just call ``path.exists()``? Because on case-insensitive
    filesystems - macOS's default APFS, and SMB mounts to a NAS - ``exists()``
    returns ``True`` for a path whose case does not byte-match the real file
    (``foo.mp4`` "exists" when the file on disk is actually ``foo.MP4``), and
    ``Path.resolve()`` does not fold the case back to what is on disk. Such a
    path probes fine, but its wrong-case name is then written verbatim into the
    FCPXML ``<media-rep src=...>`` element. DaVinci Resolve's export resolver is
    case-strict and rejects the clip - a failure that surfaces only at export
    time, the worst place to discover it. So we read the actual directory entry
    and compare against the real on-disk name rather than trusting ``exists()``.
    """
    parent = path.parent
    target = path.name.casefold()
    try:
        for child in parent.iterdir():
            if child.name.casefold() == target:
                return parent / child.name
    except (FileNotFoundError, NotADirectoryError, PermissionError):
        return None
    return None


def _probe_video(video_path: Path) -> VideoInfo:
    """Probe a video file with ffprobe and return :class:`VideoInfo`.

    Results are cached by resolved path.

    Args:
        video_path: Path to the video file (resolved internally).

    Returns:
        :class:`VideoInfo` with fps, dimensions, and duration.

    Raises:
        FileNotFoundError: If the video file does not exist, or if the supplied
            path's filename casing does not byte-match the on-disk file (see
            :func:`_canonical_case`).
        RuntimeError: If ffprobe fails or returns unexpected output.
    """
    resolved = video_path.resolve()
    if resolved in _ffprobe_cache:
        return _ffprobe_cache[resolved]

    on_disk = _canonical_case(resolved)
    if on_disk is None:
        raise FileNotFoundError(f"Video file not found: {resolved}")
    if on_disk.name != resolved.name:
        raise FileNotFoundError(
            f"Path case mismatch: caller passed {resolved.name!r} but the file "
            f"on disk is {on_disk.name!r}. The FCPXML would emit the "
            f"caller-supplied case and downstream tools (e.g. DaVinci Resolve) "
            f"may reject it. Fix the path at the call site."
        )

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=r_frame_rate,width,height",
        "-show_entries",
        "format=duration",
        "-of",
        "csv=p=0",
        str(resolved),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffprobe failed for {resolved}: {e.stderr}") from e

    lines = [ln.strip() for ln in result.stdout.strip().splitlines() if ln.strip()]
    if len(lines) < 2:
        raise RuntimeError(
            f"ffprobe returned unexpected output for {resolved}: {result.stdout!r}"
        )

    # Line 0: stream fields. ffprobe CSV field order is not stable enough to
    # assume "r_frame_rate,width,height" for every file, so parse by type.
    stream_parts = [part.strip() for part in lines[0].split(",") if part.strip()]

    fps_candidates = [part for part in stream_parts if "/" in part]
    if not fps_candidates:
        raise RuntimeError(
            f"ffprobe returned no fps field for {resolved}: {result.stdout!r}"
        )
    fps_str = fps_candidates[0]

    dimension_candidates = [
        int(part) for part in stream_parts if re.fullmatch(r"\d+", part)
    ]
    width = dimension_candidates[0] if len(dimension_candidates) > 0 else 1920
    height = dimension_candidates[1] if len(dimension_candidates) > 1 else 1080

    # Line 1: format fields (duration)
    duration_sec = float(lines[1].strip())

    # Parse frame rate to exact Fraction
    if "/" in fps_str:
        num, den = fps_str.split("/")
        fps_exact = Fraction(int(num), int(den))
    else:
        fps_exact = Fraction(fps_str).limit_denominator(100000)

    fps_standard = FrameRate.from_ffprobe(fps_str)

    info = VideoInfo(
        path=resolved,
        fps_exact=fps_exact,
        fps_standard=fps_standard,
        width=width,
        height=height,
        duration_sec=duration_sec,
    )
    _ffprobe_cache[resolved] = info
    return info

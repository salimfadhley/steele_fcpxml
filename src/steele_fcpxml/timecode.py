"""Frame rates and timecode/rational-time conversion helpers.

This module is the timing core of :mod:`steele_fcpxml`. It provides:

- :class:`FrameRate` - standard video frame rates with exact rational values.
- :func:`timecode_to_seconds` (aliased :data:`tc`) - parse ``"MM:SS"`` style
  timecodes into seconds.
- :func:`seconds_to_rational` - convert seconds to the FCPXML rational time
  string format using exact :class:`~fractions.Fraction` arithmetic.

Examples:
    >>> from steele_fcpxml.timecode import FrameRate, tc, seconds_to_rational
    >>> tc("1:30")
    90.0
    >>> FrameRate.FPS_25.frame_duration
    '1/25s'
    >>> from fractions import Fraction
    >>> seconds_to_rational(10.0, Fraction(25, 1))
    '250/25s'
"""

from __future__ import annotations

from enum import Enum
from fractions import Fraction

__all__ = ["FrameRate", "tc", "timecode_to_seconds", "seconds_to_rational"]


def timecode_to_seconds(timecode: str) -> float:
    """Convert a timecode string to seconds.

    Values are source-relative (position within the video file starting at
    00:00:00), not DaVinci Resolve timeline positions (which display with a
    one-hour offset).

    Args:
        timecode: Timecode in the form ``"HH:MM:SS"``, ``"MM:SS"`` or ``"SS"``.
            The seconds component may be fractional.

    Returns:
        Time in seconds as a float.

    Examples:
        >>> timecode_to_seconds("1:30")
        90.0
        >>> timecode_to_seconds("1:30.5")
        90.5
        >>> timecode_to_seconds("1:02:30")
        3750.0
        >>> timecode_to_seconds("45")
        45.0
    """
    parts = timecode.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    else:
        return float(parts[0])


tc = timecode_to_seconds
"""Alias for :func:`timecode_to_seconds`.

Converts timecode strings to seconds. Values are source-relative (position
within the video file starting at 00:00:00), NOT DaVinci Resolve timeline
positions (which display with a one-hour offset).

Examples:
    tc("1:30")     -> 90.0
    tc("1:30.5")   -> 90.5
    tc("1:02:30")  -> 3750.0
    tc("45")       -> 45.0
"""


class FrameRate(Enum):
    """Standard video frame rates with exact rational values.

    Each member stores a :class:`~fractions.Fraction` representing the exact
    fps. The FCPXML frame duration is the reciprocal (e.g. ``FPS_25`` ->
    frame duration ``"1/25s"``).

    Examples:
        >>> FrameRate.FPS_25.value
        Fraction(25, 1)
        >>> FrameRate.FPS_29_97.frame_duration
        '1001/30000s'
        >>> FrameRate.from_ffprobe("30000/1001")
        <FrameRate.FPS_29_97: Fraction(30000, 1001)>
    """

    FPS_23_976 = Fraction(24000, 1001)
    FPS_24 = Fraction(24, 1)
    FPS_25 = Fraction(25, 1)
    FPS_29_97 = Fraction(30000, 1001)
    FPS_30 = Fraction(30, 1)
    FPS_50 = Fraction(50, 1)
    FPS_59_94 = Fraction(60000, 1001)
    FPS_60 = Fraction(60, 1)

    @property
    def frame_duration(self) -> str:
        """FCPXML frame duration string (reciprocal of fps)."""
        recip = Fraction(1) / self.value
        return f"{recip.numerator}/{recip.denominator}s"

    @classmethod
    def from_ffprobe(cls, r_frame_rate: str) -> FrameRate | None:
        """Match an ffprobe ``r_frame_rate`` string to a known enum member.

        Args:
            r_frame_rate: ffprobe output like ``"30000/1001"`` or ``"25/1"``.

        Returns:
            The matching :class:`FrameRate` member, or ``None`` for
            non-standard rates.

        Examples:
            >>> FrameRate.from_ffprobe("25/1")
            <FrameRate.FPS_25: Fraction(25, 1)>
            >>> FrameRate.from_ffprobe("17/1") is None
            True
        """
        if "/" in r_frame_rate:
            num, den = r_frame_rate.split("/")
            probe_fps = Fraction(int(num), int(den))
        else:
            probe_fps = Fraction(r_frame_rate).limit_denominator(100000)

        for member in cls:
            if member.value == probe_fps:
                return member

        probe_float = float(probe_fps)
        for member in cls:
            if abs(float(member.value) - probe_float) < 0.01:
                return member

        return None


def seconds_to_rational(seconds: float, fps: Fraction) -> str:
    """Convert seconds to an FCPXML rational time string.

    Uses exact :class:`~fractions.Fraction` arithmetic to avoid float
    truncation. The result expresses time as ``(frames * denominator) /
    numerator``, where ``fps = numerator/denominator``.

    Args:
        seconds: Time in seconds.
        fps: Exact frame rate as a Fraction (e.g. ``Fraction(30000, 1001)``).

    Returns:
        Rational time string like ``"250/25s"`` or ``"300300/30000s"``.

    Examples:
        >>> seconds_to_rational(10.0, Fraction(25, 1))
        '250/25s'
        >>> seconds_to_rational(10.0, Fraction(30000, 1001))
        '300300/30000s'
    """
    sec = Fraction(str(seconds))
    frames = round(sec * fps)
    return f"{frames * fps.denominator}/{fps.numerator}s"


def _format_timecode(seconds: float) -> str:
    """Convert seconds to ``HH:MM:SS`` format for notes."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

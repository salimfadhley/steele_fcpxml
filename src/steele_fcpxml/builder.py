"""The fluent :class:`FCPXML` timeline builder - the main public entry point.

:class:`FCPXML` is what almost every caller uses. It accumulates clips, gaps
and markers, probing each video file as it is added (so timecode ranges are
validated against real durations), and delegates serialization to
:class:`~steele_fcpxml.writer.FCPXMLWriter`. Every timeline-modifying method
returns ``self`` for chaining.
"""

from __future__ import annotations

import copy
from pathlib import Path

from steele_fcpxml.probe import _probe_video
from steele_fcpxml.specs import ClipSpec, GapSpec, MarkerSpec, TimelineSpec
from steele_fcpxml.timecode import FrameRate
from steele_fcpxml.writer import FCPXMLWriter

__all__ = ["FCPXML"]


class FCPXML:
    """Fluent builder for FCPXML timelines.

    Builds a :class:`~steele_fcpxml.specs.TimelineSpec` internally and
    delegates to :class:`~steele_fcpxml.writer.FCPXMLWriter`. All methods that
    modify the timeline return ``self`` for chaining.

    Examples:
        >>> from pathlib import Path
        >>> from steele_fcpxml import FCPXML, tc
        >>> (
        ...     FCPXML("Episode 158", "Gold Clips")
        ...     .add_clip(video1, in_point=tc("1:30"), out_point=tc("1:45"))
        ...     .add_gap(3.0)
        ...     .add_clip(video2, in_point=30.0, duration=10.0, name="Main")
        ...     .write(Path("output.fcpxml"))
        ... )  # doctest: +SKIP
    """

    def __init__(
        self,
        event_name: str,
        project_name: str,
        timeline_fps: FrameRate = FrameRate.FPS_25,
    ) -> None:
        self._spec = TimelineSpec(
            event_name=event_name,
            project_name=project_name,
            timeline_fps=timeline_fps,
        )
        self._timeline_pos: float = 0.0
        self._writer = FCPXMLWriter()

    def add_clip(
        self,
        path: Path,
        in_point: float,
        out_point: float | None = None,
        *,
        duration: float | None = None,
        name: str = "",
        note: str = "",
        section: str = "",
        tags: list[str] | None = None,
    ) -> FCPXML:
        """Add a clip to the timeline.

        Supply either ``out_point`` (positional) or ``duration`` (keyword),
        not both.

        Args:
            path: Path to the video file. Must exist.
            in_point: Start position in the source video (seconds).
            out_point: End position in the source video (seconds).
            duration: Clip length in seconds (alternative to ``out_point``).
            name: Clip label shown in the timeline.
            note: Text for the FCPXML ``<note>`` element.
            section: Section label (used for marker grouping).
            tags: Optional list of search/match tags.

        Returns:
            ``self`` for chaining.

        Raises:
            ValueError: If both/neither ``out_point`` and ``duration`` are
                given, or if timecodes are out of range.
            FileNotFoundError: If the video file does not exist.
            RuntimeError: If ffprobe fails.
        """
        if out_point is not None and duration is not None:
            raise ValueError("Supply either out_point or duration, not both")
        if out_point is None and duration is None:
            raise ValueError("Supply either out_point or duration")

        if in_point < 0:
            raise ValueError(f"in_point must be >= 0, got {in_point}")

        if duration is not None:
            if duration <= 0:
                raise ValueError(f"duration must be > 0, got {duration}")
            out_point = in_point + duration
        else:
            assert out_point is not None
            if out_point <= in_point:
                raise ValueError(
                    f"out_point ({out_point}) must be > in_point ({in_point})"
                )

        resolved = Path(path).resolve()

        # Probe video (cached) and validate timecodes
        info = _probe_video(resolved)
        if out_point > info.duration_sec:
            raise ValueError(
                f"out_point ({out_point:.2f}s) exceeds video duration "
                f"({info.duration_sec:.2f}s) for {resolved.name}"
            )

        clip = ClipSpec(
            path=resolved,
            in_point=in_point,
            out_point=out_point,
            name=name,
            note=note,
            section=section,
            tags=tags or [],
        )
        self._spec.items.append(clip)
        self._timeline_pos += clip.duration
        return self

    def add_gap(self, duration: float, *, name: str = "") -> FCPXML:
        """Add a gap to the timeline.

        Args:
            duration: Gap length in seconds.
            name: Optional gap label.

        Returns:
            ``self`` for chaining.

        Raises:
            ValueError: If ``duration`` is not greater than zero.
        """
        if duration <= 0:
            raise ValueError(f"duration must be > 0, got {duration}")
        self._spec.items.append(GapSpec(duration=duration, name=name))
        self._timeline_pos += duration
        return self

    def add_marker(self, value: str) -> FCPXML:
        """Add a marker at the current timeline position.

        Args:
            value: Marker label text.

        Returns:
            ``self`` for chaining.
        """
        self._spec.markers.append(MarkerSpec(value=value, position=self._timeline_pos))
        return self

    def fork(self) -> FCPXML:
        """Create an independent deep copy of this builder.

        Returns:
            A new :class:`FCPXML` instance with the same state.
        """
        return copy.deepcopy(self)

    def write(self, path: Path) -> Path:
        """Write the FCPXML file.

        Args:
            path: Output file path.

        Returns:
            The resolved output path.

        Raises:
            ValueError: If the timeline has no clips.
            FileNotFoundError: If the output directory does not exist.
        """
        return self._writer.write(self._spec, Path(path))

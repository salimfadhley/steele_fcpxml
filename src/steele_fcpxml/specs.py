"""Timeline specification dataclasses.

These value objects describe a timeline declaratively. The fluent
:class:`~steele_fcpxml.builder.FCPXML` builder assembles a
:class:`TimelineSpec` from these pieces and hands it to
:class:`~steele_fcpxml.writer.FCPXMLWriter` for serialization.

Most users never touch these types directly - they go through the builder.
They are part of the lower-level API for callers who want to construct a
:class:`TimelineSpec` by hand.

Examples:
    >>> from pathlib import Path
    >>> from steele_fcpxml.specs import ClipSpec, GapSpec, TimelineSpec
    >>> spec = TimelineSpec(event_name="My Event", project_name="My Project")
    >>> spec.items.append(
    ...     ClipSpec(path=Path("/video.mp4"), in_point=5.0, out_point=15.0)
    ... )
    >>> spec.items.append(GapSpec(duration=3.0))
    >>> spec.items[0].duration
    10.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from steele_fcpxml.timecode import FrameRate

__all__ = ["ClipSpec", "GapSpec", "MarkerSpec", "TimelineSpec"]


@dataclass(frozen=True)
class ClipSpec:
    """A clip to place on the timeline."""

    path: Path
    in_point: float
    out_point: float
    name: str = ""
    note: str = ""
    section: str = ""
    tags: list[str] = field(default_factory=list)

    @property
    def duration(self) -> float:
        """Clip length in seconds (``out_point - in_point``)."""
        return self.out_point - self.in_point


@dataclass(frozen=True)
class GapSpec:
    """A gap (silence/black) on the timeline."""

    duration: float
    name: str = ""


@dataclass(frozen=True)
class MarkerSpec:
    """A timeline marker at a specific position (in seconds)."""

    value: str
    position: float


@dataclass
class TimelineSpec:
    """Complete timeline specification. Consumed by :class:`FCPXMLWriter`."""

    event_name: str
    project_name: str
    timeline_fps: FrameRate = FrameRate.FPS_25
    items: list[ClipSpec | GapSpec] = field(default_factory=list)
    markers: list[MarkerSpec] = field(default_factory=list)

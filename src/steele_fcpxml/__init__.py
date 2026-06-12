"""steele-fcpxml: generate Final Cut Pro XML (FCPXML) timelines.

The public API is deliberately small. For almost all uses you only need:

    from steele_fcpxml import FCPXML, FrameRate, tc

    (
        FCPXML("My Event", "My Timeline")
        .add_clip(video, in_point=tc("1:30"), out_point=tc("1:45"), name="Intro")
        .add_gap(3.0)
        .write(Path("out.fcpxml"))
    )

A lower-level API (the spec dataclasses, the writer, the probe result, the
validator) lives in the submodules ``steele_fcpxml.specs``,
``steele_fcpxml.writer``, ``steele_fcpxml.probe`` and
``steele_fcpxml.validator``. See ``doc/usage.md`` for details.
"""

from importlib.metadata import PackageNotFoundError, version as _version

from steele_fcpxml.builder import FCPXML
from steele_fcpxml.timecode import FrameRate, tc

__all__ = ["FCPXML", "FrameRate", "tc"]

try:
    __version__ = _version("steele-fcpxml")
except PackageNotFoundError:  # pragma: no cover - running from a source tree
    __version__ = "0.0.0+unknown"

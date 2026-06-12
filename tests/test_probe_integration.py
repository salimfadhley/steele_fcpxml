"""Integration tests that run *real* ffprobe against committed fixtures.

Unlike the rest of the suite (which mocks ``subprocess.run``), these tests
shell out to the actual ``ffprobe`` binary against the tiny videos in
``tests/fixtures/``. They prove that our parser agrees with what real ffprobe
emits - the one thing the mocked tests cannot cover.

The whole module is skipped when ``ffprobe`` is not on ``PATH`` (e.g. a CI job
that has not installed ffmpeg), so the fast mocked suite remains the default.
"""

from __future__ import annotations

import shutil
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

import pytest

from steele_fcpxml.builder import FCPXML
from steele_fcpxml.probe import _probe_video
from steele_fcpxml.timecode import FrameRate
from steele_fcpxml.validator import FCPXMLValidator

pytestmark = pytest.mark.skipif(
    shutil.which("ffprobe") is None,
    reason="ffprobe not installed; skipping real-ffprobe integration tests",
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    "filename,expected_fps,expected_standard,expected_frame_duration",
    [
        ("clip_160x90_24fps.mp4", Fraction(24, 1), FrameRate.FPS_24, "1/24s"),
        ("clip_160x90_25fps.mp4", Fraction(25, 1), FrameRate.FPS_25, "1/25s"),
        (
            "clip_160x90_29_97fps.mp4",
            Fraction(30000, 1001),
            FrameRate.FPS_29_97,
            "1001/30000s",
        ),
        ("clip_160x90_30fps.mp4", Fraction(30, 1), FrameRate.FPS_30, "1/30s"),
    ],
)
def test_real_ffprobe_reads_fixture_metadata(
    filename: str,
    expected_fps: Fraction,
    expected_standard: FrameRate,
    expected_frame_duration: str,
) -> None:
    info = _probe_video(FIXTURES / filename)

    assert info.fps_exact == expected_fps
    assert info.fps_standard == expected_standard
    assert info.frame_duration == expected_frame_duration
    assert info.width == 160
    assert info.height == 90
    # Fixtures are ~1 second; allow slack for the 1001/1000 NTSC pull-down.
    assert 0.9 <= info.duration_sec <= 1.1


def test_end_to_end_build_and_validate(tmp_path: Path) -> None:
    """Build a real FCPXML from a fixture and validate it round-trips."""
    fixture = FIXTURES / "clip_160x90_25fps.mp4"
    output = tmp_path / "timeline.fcpxml"

    (
        FCPXML("Integration", "Smoke Test")
        .add_clip(fixture, in_point=0.0, duration=0.5, name="Real clip")
        .write(output)
    )

    # The generated file parses and references a real (existing) media file.
    tree = ET.parse(output)
    assert tree.getroot().get("version") == "1.9"

    result = FCPXMLValidator(output).validate()
    assert result.valid is True, result.errors
    assert result.info["missing_files"] == 0

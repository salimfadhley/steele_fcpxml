"""Tests for the FCPXML builder: validation, chaining, and fork."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from steele_fcpxml.builder import FCPXML

# -- add_clip validation ---------------------------------------------------


def test_add_clip_requires_out_point_or_duration(
    mock_ffprobe: Callable[..., None], tmp_path: Path
) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    mock_ffprobe()

    builder = FCPXML("Test", "Test")
    with pytest.raises(ValueError, match="Supply either"):
        builder.add_clip(video, in_point=10.0)


def test_add_clip_rejects_both_out_point_and_duration(
    mock_ffprobe: Callable[..., None], tmp_path: Path
) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    mock_ffprobe()

    builder = FCPXML("Test", "Test")
    with pytest.raises(ValueError, match="Supply either"):
        builder.add_clip(video, in_point=10.0, out_point=20.0, duration=10.0)


def test_add_clip_rejects_negative_in_point(
    mock_ffprobe: Callable[..., None], tmp_path: Path
) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    mock_ffprobe()

    builder = FCPXML("Test", "Test")
    with pytest.raises(ValueError, match="in_point must be >= 0"):
        builder.add_clip(video, in_point=-1.0, duration=5.0)


def test_add_clip_rejects_zero_duration(
    mock_ffprobe: Callable[..., None], tmp_path: Path
) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    mock_ffprobe()

    builder = FCPXML("Test", "Test")
    with pytest.raises(ValueError, match="duration must be > 0"):
        builder.add_clip(video, in_point=10.0, duration=0.0)


def test_add_clip_rejects_out_point_before_in_point(
    mock_ffprobe: Callable[..., None], tmp_path: Path
) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    mock_ffprobe()

    builder = FCPXML("Test", "Test")
    with pytest.raises(ValueError, match="out_point.*must be > in_point"):
        builder.add_clip(video, in_point=20.0, out_point=10.0)


def test_add_clip_rejects_out_of_range_timecode(
    mock_ffprobe: Callable[..., None], tmp_path: Path
) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    mock_ffprobe(duration=60.0)

    builder = FCPXML("Test", "Test")
    with pytest.raises(ValueError, match="exceeds video duration"):
        builder.add_clip(video, in_point=50.0, out_point=70.0)


def test_add_clip_rejects_nonexistent_file() -> None:
    builder = FCPXML("Test", "Test")
    with pytest.raises(FileNotFoundError):
        builder.add_clip(Path("/nonexistent/video.mp4"), in_point=0.0, duration=5.0)


# -- chaining --------------------------------------------------------------


def test_add_clip_returns_self(
    mock_ffprobe: Callable[..., None], tmp_path: Path
) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    mock_ffprobe()

    builder = FCPXML("Test", "Test")
    result = builder.add_clip(video, in_point=0.0, duration=5.0)
    assert result is builder


def test_add_gap_returns_self() -> None:
    builder = FCPXML("Test", "Test")
    result = builder.add_gap(3.0)
    assert result is builder


def test_add_marker_returns_self() -> None:
    builder = FCPXML("Test", "Test")
    result = builder.add_marker("Section 1")
    assert result is builder


def test_fluent_chain(mock_ffprobe: Callable[..., None], tmp_path: Path) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    mock_ffprobe()

    output = tmp_path / "output.fcpxml"
    result = (
        FCPXML("Test", "Test")
        .add_marker("Intro")
        .add_clip(video, in_point=0.0, duration=5.0, name="Clip 1")
        .add_gap(3.0)
        .add_clip(video, in_point=10.0, duration=5.0, name="Clip 2")
        .write(output)
    )
    assert result == output.resolve()
    assert output.exists()


# -- fork ------------------------------------------------------------------


def test_fork_creates_independent_copy(
    mock_ffprobe: Callable[..., None], tmp_path: Path
) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    mock_ffprobe()

    base = FCPXML("Test", "Test").add_clip(
        video, in_point=0.0, duration=5.0, name="Shared"
    )
    forked = base.fork()
    forked.add_clip(video, in_point=10.0, duration=5.0, name="Forked only")

    assert len(base._spec.items) == 1
    assert len(forked._spec.items) == 2

"""Tests for ffprobe probing and the module-level cache (mocked)."""

from __future__ import annotations

import subprocess
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from steele_fcpxml.builder import FCPXML
from steele_fcpxml.probe import _probe_video


def test_probe_tolerates_width_height_fps_csv_order(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """ffprobe CSV field order is not stable; the parser handles reordering."""
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")

    def fake_run(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(stdout="1920,1080,30/1\n120.0\n")

    monkeypatch.setattr("subprocess.run", fake_run)

    builder = FCPXML("Test", "Test")
    builder.add_clip(video, 0.0, duration=5.0)

    clip = builder._spec.items[0]
    assert clip.path == video.resolve()


def test_ffprobe_cache_avoids_duplicate_calls(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")

    call_count = 0
    original_stdout = "25/1,1920,1080\n120.0\n"

    def counting_run(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
        nonlocal call_count
        call_count += 1
        return SimpleNamespace(stdout=original_stdout)

    monkeypatch.setattr("subprocess.run", counting_run)

    builder = FCPXML("Test", "Test")
    builder.add_clip(video, in_point=0.0, duration=5.0)
    builder.add_clip(video, in_point=10.0, duration=5.0)

    assert call_count == 1


def test_probe_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Video file not found"):
        _probe_video(tmp_path / "does_not_exist.mp4")


def test_probe_ffprobe_failure_raises_runtime_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")

    def boom(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
        raise subprocess.CalledProcessError(1, cmd, stderr="ffprobe: broken file")

    monkeypatch.setattr("subprocess.run", boom)

    with pytest.raises(RuntimeError, match="ffprobe failed"):
        _probe_video(video)


def test_probe_unexpected_output_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")

    def one_line(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(stdout="25/1,1920,1080\n")  # missing format line

    monkeypatch.setattr("subprocess.run", one_line)

    with pytest.raises(RuntimeError, match="unexpected output"):
        _probe_video(video)


def test_probe_no_fps_field_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")

    def no_fps(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(stdout="1920,1080\n120.0\n")  # no "num/den" token

    monkeypatch.setattr("subprocess.run", no_fps)

    with pytest.raises(RuntimeError, match="no fps field"):
        _probe_video(video)


def test_probe_non_standard_fps_computes_frame_duration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A non-standard fps (not in FrameRate) still yields a frame duration."""
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")

    def odd_fps(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(stdout="15/1,640,480\n10.0\n")

    monkeypatch.setattr("subprocess.run", odd_fps)

    info = _probe_video(video)
    assert info.fps_exact == Fraction(15, 1)
    assert info.fps_standard is None
    assert info.frame_duration == "1/15s"
    assert (info.width, info.height) == (640, 480)


def _filesystem_is_case_insensitive(tmp_path: Path) -> bool:
    """Detect a case-insensitive filesystem by probing a known-case file."""
    probe = tmp_path / "CaseProbe.tmp"
    probe.write_bytes(b"x")
    return (tmp_path / "caseprobe.tmp").exists()


def test_probe_raises_on_case_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A path whose case does not byte-match the on-disk file is rejected.

    On case-insensitive filesystems a wrong-case path passes ``exists()`` and
    probes fine, but the wrong-case name would be written into the FCPXML and
    rejected by DaVinci Resolve at export. The probe must refuse it up front.
    """
    if not _filesystem_is_case_insensitive(tmp_path):
        pytest.skip("case-sensitive filesystem; cannot reproduce case mismatch")

    on_disk = tmp_path / "Sample.MP4"
    on_disk.write_bytes(b"fake")

    # If the check ever lets the path through, this mock would let it "succeed".
    def fake_run(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(stdout="25/1,1920,1080\n120.0\n")

    monkeypatch.setattr("subprocess.run", fake_run)

    with pytest.raises(FileNotFoundError) as exc:
        _probe_video(tmp_path / "sample.mp4")

    message = str(exc.value)
    assert "Sample.MP4" in message
    assert "sample.mp4" in message


def test_probe_accepts_exact_case(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The exact on-disk casing probes normally (no false case-mismatch)."""
    on_disk = tmp_path / "Sample.MP4"
    on_disk.write_bytes(b"fake")

    def fake_run(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(stdout="25/1,1920,1080\n120.0\n")

    monkeypatch.setattr("subprocess.run", fake_run)

    info = _probe_video(on_disk)
    assert info.path == on_disk.resolve()


def test_probe_missing_uses_filenotfounderror_not_case_error(tmp_path: Path) -> None:
    """A truly absent file still raises plain FileNotFoundError (regression)."""
    with pytest.raises(FileNotFoundError) as exc:
        _probe_video(tmp_path / "nothing_here.mp4")
    assert "case mismatch" not in str(exc.value)

"""Tests for ffprobe probing and the module-level cache (mocked)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from steele_fcpxml.builder import FCPXML


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

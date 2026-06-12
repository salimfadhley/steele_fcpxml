"""Tests for FCPXMLWriter XML output structure, determinism, and invariants."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Callable
from fractions import Fraction
from pathlib import Path

import pytest

from steele_fcpxml.builder import FCPXML

# -- XML output structure --------------------------------------------------


def test_writer_produces_valid_fcpxml(
    mock_ffprobe: Callable[..., None], tmp_path: Path
) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    mock_ffprobe()

    output = tmp_path / "test.fcpxml"
    (
        FCPXML("My Event", "My Project")
        .add_clip(video, in_point=5.0, duration=10.0, name="Test Clip")
        .write(output)
    )

    content = output.read_text(encoding="UTF-8")
    assert "<!DOCTYPE fcpxml>" in content
    assert 'version="1.9"' in content

    tree = ET.parse(output)
    root = tree.getroot()

    assert root.tag == "fcpxml"
    assert root.get("version") == "1.9"


def test_writer_emits_sequence_audio_attributes(
    mock_ffprobe: Callable[..., None], tmp_path: Path
) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    mock_ffprobe()

    output = tmp_path / "test.fcpxml"
    FCPXML("Ev", "Pr").add_clip(video, 0.0, duration=5.0).write(output)

    tree = ET.parse(output)
    seq = tree.find(".//sequence")
    assert seq is not None
    assert seq.get("audioLayout") == "stereo"
    assert seq.get("audioRate") == "48k"


def test_writer_emits_library_location(
    mock_ffprobe: Callable[..., None], tmp_path: Path
) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    mock_ffprobe()

    output = tmp_path / "test.fcpxml"
    FCPXML("Ev", "Pr").add_clip(video, 0.0, duration=5.0).write(output)

    tree = ET.parse(output)
    lib = tree.find(".//library")
    assert lib is not None
    loc = lib.get("location")
    assert loc is not None
    assert loc.startswith("file://")


def test_writer_emits_adjust_elements(
    mock_ffprobe: Callable[..., None], tmp_path: Path
) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    mock_ffprobe()

    output = tmp_path / "test.fcpxml"
    FCPXML("Ev", "Pr").add_clip(video, 0.0, duration=5.0).write(output)

    tree = ET.parse(output)
    clip = tree.find(".//asset-clip")
    assert clip is not None

    conform = clip.find("adjust-conform")
    assert conform is not None
    assert conform.get("type") == "fit"

    transform = clip.find("adjust-transform")
    assert transform is not None
    assert transform.get("anchor") == "0 0"


def test_writer_emits_note(mock_ffprobe: Callable[..., None], tmp_path: Path) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    mock_ffprobe()

    output = tmp_path / "test.fcpxml"
    FCPXML("Ev", "Pr").add_clip(video, 0.0, duration=5.0, note="Custom note").write(
        output
    )

    tree = ET.parse(output)
    note = tree.find(".//asset-clip/note")
    assert note is not None
    assert note.text == "Custom note"


def test_writer_note_with_special_chars_round_trips(
    mock_ffprobe: Callable[..., None], tmp_path: Path
) -> None:
    """A note with XML special characters round-trips exactly (no double-escape)."""
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    mock_ffprobe()

    output = tmp_path / "test.fcpxml"
    FCPXML("Ev", "Pr").add_clip(video, 0.0, duration=5.0, note="A & B < C > D").write(
        output
    )

    tree = ET.parse(output)
    note = tree.find(".//asset-clip/note")
    assert note is not None
    assert note.text == "A & B < C > D"


def test_writer_auto_generates_note_from_timecodes(
    mock_ffprobe: Callable[..., None], tmp_path: Path
) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    mock_ffprobe()

    output = tmp_path / "test.fcpxml"
    FCPXML("Ev", "Pr").add_clip(video, in_point=65.0, out_point=75.0).write(output)

    tree = ET.parse(output)
    note = tree.find(".//asset-clip/note")
    assert note is not None
    assert note.text is not None
    assert "00:01:05" in note.text
    assert "00:01:15" in note.text


def test_writer_emits_markers(
    mock_ffprobe: Callable[..., None], tmp_path: Path
) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    mock_ffprobe()

    output = tmp_path / "test.fcpxml"
    (
        FCPXML("Ev", "Pr")
        .add_marker("Section A")
        .add_clip(video, 0.0, duration=5.0)
        .add_marker("Section B")
        .add_clip(video, 10.0, duration=5.0)
        .write(output)
    )

    tree = ET.parse(output)
    markers = tree.findall(".//marker")
    assert len(markers) == 2
    assert markers[0].get("value") == "Section A"
    assert markers[1].get("value") == "Section B"


def test_writer_emits_gap(mock_ffprobe: Callable[..., None], tmp_path: Path) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    mock_ffprobe()

    output = tmp_path / "test.fcpxml"
    (
        FCPXML("Ev", "Pr")
        .add_clip(video, 0.0, duration=5.0)
        .add_gap(3.0, name="Narration")
        .add_clip(video, 10.0, duration=5.0)
        .write(output)
    )

    tree = ET.parse(output)
    gaps = tree.findall(".//gap")
    assert len(gaps) == 1
    assert gaps[0].get("name") == "Narration"


def test_writer_uses_real_probed_duration(
    mock_ffprobe: Callable[..., None], tmp_path: Path
) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    mock_ffprobe(duration=347.5)

    output = tmp_path / "test.fcpxml"
    FCPXML("Ev", "Pr").add_clip(video, 0.0, duration=5.0).write(output)

    tree = ET.parse(output)
    asset = tree.find(".//asset")
    assert asset is not None
    dur = asset.get("duration")
    assert dur is not None
    # Should be the real duration, not a 2-hour placeholder
    parts = dur.rstrip("s").split("/")
    rational = Fraction(int(parts[0]), int(parts[1]))
    assert abs(float(rational) - 347.5) < 0.05


def test_writer_rejects_empty_timeline(tmp_path: Path) -> None:
    output = tmp_path / "test.fcpxml"
    with pytest.raises(ValueError, match="no clips"):
        FCPXML("Ev", "Pr").write(output)


def test_writer_rejects_missing_output_dir() -> None:
    with pytest.raises(FileNotFoundError, match="Output directory"):
        FCPXML("Ev", "Pr").write(Path("/nonexistent/dir/out.fcpxml"))


# -- Deterministic output --------------------------------------------------


def test_deterministic_output(
    mock_ffprobe: Callable[..., None], tmp_path: Path
) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    mock_ffprobe()

    def build() -> FCPXML:
        return (
            FCPXML("Test", "Test")
            .add_clip(video, in_point=10.0, duration=5.0, name="Clip A")
            .add_gap(3.0)
            .add_clip(video, in_point=20.0, out_point=30.0, name="Clip B")
        )

    path1 = tmp_path / "run1.fcpxml"
    path2 = tmp_path / "run2.fcpxml"
    build().write(path1)
    build().write(path2)
    assert path1.read_text() == path2.read_text()


# -- Structural invariants -------------------------------------------------


def test_all_refs_match_assets(
    mock_ffprobe: Callable[..., None], tmp_path: Path
) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    mock_ffprobe()

    output = tmp_path / "test.fcpxml"
    (
        FCPXML("Ev", "Pr")
        .add_clip(video, 0.0, duration=5.0)
        .add_gap(2.0)
        .add_clip(video, 10.0, duration=5.0)
        .write(output)
    )

    tree = ET.parse(output)
    asset_ids = {a.get("id") for a in tree.findall(".//asset")}
    clip_refs = {c.get("ref") for c in tree.findall(".//asset-clip")}
    assert clip_refs.issubset(asset_ids)


def test_all_formats_match(mock_ffprobe: Callable[..., None], tmp_path: Path) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    mock_ffprobe()

    output = tmp_path / "test.fcpxml"
    FCPXML("Ev", "Pr").add_clip(video, 0.0, duration=5.0).write(output)

    tree = ET.parse(output)
    format_ids = {f.get("id") for f in tree.findall(".//format")}
    asset_fmts = {a.get("format") for a in tree.findall(".//asset")}
    clip_fmts = {c.get("format") for c in tree.findall(".//asset-clip")}
    seq_fmts = {s.get("format") for s in tree.findall(".//sequence")}

    all_refs = asset_fmts | clip_fmts | seq_fmts
    assert all_refs.issubset(format_ids)


def test_no_duplicate_ids(mock_ffprobe: Callable[..., None], tmp_path: Path) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    mock_ffprobe()

    output = tmp_path / "test.fcpxml"
    FCPXML("Ev", "Pr").add_clip(video, 0.0, duration=5.0).write(output)

    tree = ET.parse(output)
    all_ids: list[str] = []
    for elem in tree.iter():
        eid = elem.get("id")
        if eid:
            all_ids.append(eid)
    assert len(all_ids) == len(set(all_ids))

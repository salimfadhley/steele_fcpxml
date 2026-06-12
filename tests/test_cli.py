"""Tests for the steele-fcpxml command-line interface."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from steele_fcpxml.cli import main

_VALID_FCPXML = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.11">
    <resources>
        <asset id="r1" name="test_video" start="0s" duration="100s"
               hasVideo="1" format="r99" hasAudio="1">
            <media-rep kind="original-media" src="file://{video}"/>
        </asset>
        <format id="r99" name="FFVideoFormat1080p2997"
                frameDuration="1001/30000s" width="1920" height="1080"/>
    </resources>
    <library location="file://{loc}/">
        <event name="Test Event">
            <project name="Test Project">
                <sequence format="r99" duration="20s" tcStart="0s">
                    <spine>
                        <asset-clip name="Test Clip" ref="r1" offset="5s"
                                    duration="10s" start="0s"/>
                    </spine>
                </sequence>
            </project>
        </event>
    </library>
</fcpxml>"""


def _write_fixture(tmp_path: Path) -> Path:
    video = tmp_path / "test.mp4"
    video.write_bytes(b"fake video data")
    content = _VALID_FCPXML.format(video=video, loc=tmp_path)
    fcpxml_file = tmp_path / "test.fcpxml"
    fcpxml_file.write_text(content)
    return fcpxml_file


def test_cli_validate_reports_valid(tmp_path: Path) -> None:
    fcpxml_file = _write_fixture(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(fcpxml_file)])
    assert result.exit_code == 0
    assert "FCPXML VALIDATION REPORT" in result.output


def test_cli_validate_json_includes_metadata(tmp_path: Path) -> None:
    """Regression: --json must include scalar info, not an empty object."""
    fcpxml_file = _write_fixture(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", "--json", str(fcpxml_file)])
    assert result.exit_code == 0

    payload = json.loads(result.output)
    assert payload["valid"] is True
    assert payload["info"]["fcpxml_version"] == "1.11"
    assert payload["info"]["asset_count"] == 1
    assert payload["info"]["clip_count"] == 1


def test_cli_validate_verbose_lists_clips(tmp_path: Path) -> None:
    fcpxml_file = _write_fixture(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", "--verbose", str(fcpxml_file)])
    assert result.exit_code == 0
    assert "Clip Details:" in result.output
    assert "Test Clip" in result.output


def test_cli_validate_missing_media_exits_1(tmp_path: Path) -> None:
    """A timeline referencing a missing media file is invalid (exit 1)."""
    content = _VALID_FCPXML.format(
        video=tmp_path / "absent.mp4", loc=tmp_path
    )  # absent.mp4 is never created
    fcpxml_file = tmp_path / "broken.fcpxml"
    fcpxml_file.write_text(content)

    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(fcpxml_file)])
    assert result.exit_code == 1
    assert "INVALID" in result.output


def test_cli_validate_nonexistent_path_errors(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(tmp_path / "nope.fcpxml")])
    # click rejects the missing path argument before the command body runs.
    assert result.exit_code != 0


def test_cli_fail_on_warning_exits_1(tmp_path: Path) -> None:
    """--fail-on-warning turns a warning-only (still valid) file into exit 1."""
    video = tmp_path / "test.mp4"
    video.write_bytes(b"fake video data")
    # Asset omits hasAudio -> a warning, but the file is otherwise valid.
    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.11">
    <resources>
        <asset id="r1" name="v" start="0s" duration="100s" hasVideo="1" format="r99">
            <media-rep kind="original-media" src="file://{video}"/>
        </asset>
        <format id="r99" name="F" frameDuration="1/25s" width="1920" height="1080"/>
    </resources>
    <library location="file://{tmp_path}/">
        <event name="E"><project name="P">
            <sequence format="r99" duration="10s" tcStart="0s"><spine>
                <asset-clip name="C" ref="r1" offset="0s" duration="10s" start="0s"/>
            </spine></sequence>
        </project></event>
    </library>
</fcpxml>"""
    fcpxml_file = tmp_path / "warn.fcpxml"
    fcpxml_file.write_text(content)

    runner = CliRunner()
    ok = runner.invoke(main, ["validate", str(fcpxml_file)])
    assert ok.exit_code == 0  # warnings alone are still valid
    strict = runner.invoke(main, ["validate", "--fail-on-warning", str(fcpxml_file)])
    assert strict.exit_code == 1

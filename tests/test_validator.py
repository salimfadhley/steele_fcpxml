"""Tests for the FCPXML validator."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from steele_fcpxml.validator import FCPXMLValidator


@pytest.fixture
def valid_fcpxml() -> str:
    """A minimal valid FCPXML document."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.11">
    <resources>
        <asset id="r1" name="test_video" uid="TEST01" start="0s" duration="100s"
               hasVideo="1" format="r99" hasAudio="1" audioSources="1"
               audioChannels="2" audioRate="48000">
            <media-rep kind="original-media" src="file:///tmp/test.mp4"/>
        </asset>
        <format id="r99" name="FFVideoFormat1080p2997"
                frameDuration="1001/30000s" width="1920" height="1080"/>
    </resources>
    <library location="file:///tmp/">
        <event name="Test Event" uid="EVENT01">
            <project name="Test Project" uid="PROJ01">
                <sequence format="r99" duration="20s" tcStart="0s">
                    <spine>
                        <asset-clip name="Test Clip" ref="r1" offset="5s"
                                    duration="10s" start="0s">
                            <note>Test note</note>
                        </asset-clip>
                    </spine>
                </sequence>
            </project>
        </event>
    </library>
</fcpxml>"""


@pytest.fixture
def invalid_fcpxml() -> str:
    """An invalid FCPXML document (missing closing tag)."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<fcpxml version="1.11">
    <resources>
        <asset id="r1" name="test" hasVideo="1">
    </resources>
</fcpxml>"""


def test_validator_parses_valid_fcpxml(valid_fcpxml: str, tmp_path: Path) -> None:
    # Create the test video file that the FCPXML references
    test_video = tmp_path / "test.mp4"
    test_video.write_bytes(b"fake video data")

    # Update FCPXML to reference the test file
    fcpxml_content = valid_fcpxml.replace(
        'src="file:///tmp/test.mp4"', f'src="file://{test_video}"'
    )
    fcpxml_content = fcpxml_content.replace(
        'location="file:///tmp/"', f'location="file://{tmp_path}/"'
    )

    fcpxml_file = tmp_path / "test.fcpxml"
    fcpxml_file.write_text(fcpxml_content)

    validator = FCPXMLValidator(fcpxml_file)
    result = validator.validate()

    assert result.valid is True
    assert len(result.errors) == 0
    assert result.info["fcpxml_version"] == "1.11"
    assert result.info["asset_count"] == 1
    assert result.info["clip_count"] == 1


def test_validator_detects_invalid_xml(invalid_fcpxml: str) -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".fcpxml", delete=False) as f:
        f.write(invalid_fcpxml)
        temp_path = Path(f.name)

    try:
        validator = FCPXMLValidator(temp_path)
        result = validator.validate()

        assert result.valid is False
        assert len(result.errors) > 0
        assert any("XML parsing failed" in error for error in result.errors)
    finally:
        temp_path.unlink()


def test_validator_handles_missing_file() -> None:
    with pytest.raises(FileNotFoundError):
        FCPXMLValidator("/nonexistent/file.fcpxml")


def test_validator_report_generation(valid_fcpxml: str, tmp_path: Path) -> None:
    # Create the test video file
    test_video = tmp_path / "test.mp4"
    test_video.write_bytes(b"fake video data")

    # Update FCPXML to reference the test file
    fcpxml_content = valid_fcpxml.replace(
        'src="file:///tmp/test.mp4"', f'src="file://{test_video}"'
    )
    fcpxml_content = fcpxml_content.replace(
        'location="file:///tmp/"', f'location="file://{tmp_path}/"'
    )

    fcpxml_file = tmp_path / "test.fcpxml"
    fcpxml_file.write_text(fcpxml_content)

    validator = FCPXMLValidator(fcpxml_file)
    result = validator.validate()
    report = validator.generate_report(result)

    assert "FCPXML VALIDATION REPORT" in report
    assert "✅ VALID" in report
    assert "FCPXML Version: 1.11" in report
    assert "Assets: 1" in report


def test_validator_detects_missing_assets() -> None:
    fcpxml = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.11">
    <resources>
        <format id="r99" name="Test" frameDuration="1/30s" width="1920" height="1080"/>
    </resources>
    <library location="file:///tmp/">
        <event name="Test">
            <project name="Test">
                <sequence format="r99">
                    <spine>
                        <asset-clip name="Orphan" ref="r999" offset="0s"
                                    duration="10s" start="0s"/>
                    </spine>
                </sequence>
            </project>
        </event>
    </library>
</fcpxml>"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".fcpxml", delete=False) as f:
        f.write(fcpxml)
        temp_path = Path(f.name)

    try:
        validator = FCPXMLValidator(temp_path)
        result = validator.validate()

        assert result.valid is False
        assert any("missing asset" in error.lower() for error in result.errors)
    finally:
        temp_path.unlink()

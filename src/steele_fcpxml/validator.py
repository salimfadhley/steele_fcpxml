"""FCPXML validator - checks Final Cut Pro XML files for Resolve import.

:class:`FCPXMLValidator` parses an FCPXML file and runs a series of structural
and reference checks, returning a :class:`ValidationResult`. It is stdlib-only
and does not require ffprobe or any media. The CLI in
:mod:`steele_fcpxml.cli` wraps this class; it can also be used directly as a
library (e.g. to gate generated FCPXMLs in CI).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

__all__ = ["FCPXMLValidator", "ValidationResult", "ClipInfo"]


@dataclass
class ClipInfo:
    """Information about a single clip in the timeline."""

    name: str
    ref: str
    offset: float  # seconds
    duration: float  # seconds
    start: float  # seconds (timeline position)
    has_video: bool = True
    has_audio: bool = True
    note: str | None = None


@dataclass
class ValidationResult:
    """Result of FCPXML validation."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: dict[str, Any] = field(default_factory=dict)

    def add_error(self, message: str) -> None:
        """Add an error message and mark the result invalid."""
        self.errors.append(message)
        self.valid = False

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)

    def add_info(self, key: str, value: Any) -> None:
        """Add an informational value to the result."""
        self.info[key] = value


class FCPXMLValidator:
    """Validates FCPXML files for DaVinci Resolve compatibility.

    Examples:
        >>> validator = FCPXMLValidator("timeline.fcpxml")  # doctest: +SKIP
        >>> result = validator.validate()  # doctest: +SKIP
        >>> result.valid  # doctest: +SKIP
        True
    """

    SUPPORTED_VERSIONS = ["1.9", "1.10", "1.11"]
    REQUIRED_ELEMENTS = ["resources", "library", "event"]

    def __init__(self, fcpxml_path: str | Path):
        """Initialize the validator with a path to an FCPXML file.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        self.path = Path(fcpxml_path)
        if not self.path.exists():
            raise FileNotFoundError(f"FCPXML file not found: {self.path}")

        self.tree: ET.ElementTree[ET.Element] | None = None
        self.root: ET.Element | None = None
        self.base_path: Path | None = None

    def validate(self) -> ValidationResult:
        """Run all validation checks and return the result."""
        result = ValidationResult(valid=True)

        # Parse XML
        if not self._parse_xml(result):
            return result

        # Run validation checks
        self._validate_version(result)
        self._validate_structure(result)
        self._validate_assets(result)
        self._validate_format(result)
        self._validate_clips(result)
        self._validate_file_references(result)
        self._validate_timeline_structure(result)

        return result

    def _parse_xml(self, result: ValidationResult) -> bool:
        """Parse the XML file."""
        try:
            self.tree = ET.parse(self.path)
            self.root = self.tree.getroot()
            result.add_info("file_path", str(self.path))
            result.add_info("file_size", self.path.stat().st_size)
            return True
        except ET.ParseError as e:
            result.add_error(f"XML parsing failed: {e}")
            return False
        except OSError as e:
            result.add_error(f"Failed to read file: {e}")
            return False

    def _validate_version(self, result: ValidationResult) -> None:
        """Validate the FCPXML version attribute."""
        if self.root is None:
            return
        version = self.root.get("version")
        result.add_info("fcpxml_version", version)

        if not version:
            result.add_error("Missing FCPXML version attribute")
            return

        if version not in self.SUPPORTED_VERSIONS:
            result.add_warning(
                f"FCPXML version {version} may not be supported. "
                f"Recommended versions: {', '.join(self.SUPPORTED_VERSIONS)}"
            )

    def _validate_structure(self, result: ValidationResult) -> None:
        """Validate basic XML structure."""
        if self.root is None:
            return
        for element in self.REQUIRED_ELEMENTS:
            if self.root.find(f".//{element}") is None:
                result.add_error(f"Missing required element: <{element}>")

        # Count key elements
        assets = self.root.findall(".//asset")
        formats = self.root.findall(".//format")
        projects = self.root.findall(".//project")

        result.add_info("asset_count", len(assets))
        result.add_info("format_count", len(formats))
        result.add_info("project_count", len(projects))

        if len(assets) == 0:
            result.add_warning("No assets defined in FCPXML")

        if len(formats) == 0:
            result.add_error("No format definitions found")

        if len(projects) == 0:
            result.add_warning("No projects/timelines defined")

    def _validate_assets(self, result: ValidationResult) -> None:
        """Validate asset definitions."""
        if self.root is None:
            return
        assets = self.root.findall(".//asset")
        asset_ids: set[str] = set()

        for i, asset in enumerate(assets, 1):
            asset_id = asset.get("id")
            name = asset.get("name", f"Asset {i}")

            # Check for duplicate IDs
            if asset_id and asset_id in asset_ids:
                result.add_error(f"Duplicate asset ID: {asset_id}")
            if asset_id:
                asset_ids.add(asset_id)

            # Check required attributes
            if not asset.get("hasVideo"):
                result.add_warning(f"Asset '{name}' missing hasVideo attribute")

            if not asset.get("hasAudio"):
                result.add_warning(f"Asset '{name}' missing hasAudio attribute")

            # Check media reference
            media_rep = asset.find("media-rep")
            if media_rep is None:
                result.add_error(f"Asset '{name}' missing <media-rep> element")

        result.add_info("unique_asset_ids", len(asset_ids))

    def _validate_format(self, result: ValidationResult) -> None:
        """Validate format definitions."""
        if self.root is None:
            return
        formats = self.root.findall(".//format")

        for fmt in formats:
            fmt_id = fmt.get("id")
            name = fmt.get("name", fmt_id)
            frame_duration = fmt.get("frameDuration")
            width = fmt.get("width")
            height = fmt.get("height")

            result.add_info(
                f"format_{fmt_id}",
                {
                    "name": name,
                    "frame_duration": frame_duration,
                    "resolution": f"{width}x{height}" if width and height else None,
                },
            )

            # Common frame rates
            common_rates = {
                "1001/30000s": "29.97 fps (NTSC)",
                "1/30s": "30 fps",
                "1/25s": "25 fps (PAL)",
                "1001/24000s": "23.976 fps",
                "1/24s": "24 fps",
            }

            if frame_duration in common_rates:
                result.add_info(f"format_{fmt_id}_fps", common_rates[frame_duration])

    def _validate_clips(self, result: ValidationResult) -> None:
        """Validate clip definitions."""
        if self.root is None:
            return
        clips = self.root.findall(".//asset-clip")
        result.add_info("clip_count", len(clips))

        total_duration = 0.0
        clips_info: list[ClipInfo] = []

        for i, clip in enumerate(clips, 1):
            clip_name = clip.get("name", f"Clip {i}")
            ref = clip.get("ref")
            offset_str = clip.get("offset", "0s")
            duration_str = clip.get("duration", "0s")
            start_str = clip.get("start", "0s")

            # Parse time values
            offset = self._parse_time(offset_str)
            duration = self._parse_time(duration_str)
            start = self._parse_time(start_str)

            total_duration += duration

            # Check if referenced asset exists
            if ref and self.root is not None:
                asset = self.root.find(f".//asset[@id='{ref}']")
                if asset is None:
                    result.add_error(
                        f"Clip '{clip_name}' references missing asset: {ref}"
                    )

            note_elem = clip.find("note")
            note_text = note_elem.text if note_elem is not None else None

            clip_info = ClipInfo(
                name=clip_name,
                ref=ref or "",
                offset=offset,
                duration=duration,
                start=start,
                note=note_text,
            )
            clips_info.append(clip_info)

        result.add_info("total_clip_duration", total_duration)
        result.add_info("clips", clips_info)

    def _validate_file_references(self, result: ValidationResult) -> None:
        """Validate that all referenced files exist."""
        if self.root is None:
            return
        media_refs = self.root.findall(".//media-rep")
        missing_files: list[str] = []
        found_files: list[str] = []

        # Try to determine base path from library location
        library = self.root.find(".//library")
        if library is not None:
            location = library.get("location")
            if location:
                parsed = urlparse(location)
                self.base_path = Path(unquote(parsed.path))
                result.add_info("library_location", str(self.base_path))

        for media in media_refs:
            src = media.get("src")
            if not src:
                continue

            # Parse file:// URL
            parsed = urlparse(src)
            file_path = Path(unquote(parsed.path))

            if file_path.exists():
                found_files.append(str(file_path))
            else:
                missing_files.append(str(file_path))

        result.add_info("referenced_files", len(media_refs))
        result.add_info("found_files", len(found_files))
        result.add_info("missing_files", len(missing_files))

        if missing_files:
            result.add_error(
                f"Missing {len(missing_files)} file(s). "
                f"First missing: {missing_files[0]}"
            )
            result.add_info("missing_file_list", missing_files)

    def _validate_timeline_structure(self, result: ValidationResult) -> None:
        """Validate timeline structure and clip positioning."""
        if self.root is None:
            return
        sequences = self.root.findall(".//sequence")
        result.add_info("sequence_count", len(sequences))

        for seq in sequences:
            spine = seq.find("spine")
            if spine is None:
                result.add_warning("Sequence missing <spine> element")
                continue

            # Get all clips in spine
            clips = spine.findall("asset-clip")
            gaps = spine.findall("gap")

            # Check if clips are sequential
            expected_start = 0.0
            sequential = True

            for i, clip in enumerate(clips, 1):
                # Sequentiality is about timeline position, which is the clip's
                # ``offset`` - NOT its ``start`` (the in-point within the source
                # media, which is unrelated to where the clip sits on the
                # timeline).
                offset = self._parse_time(clip.get("offset", "0s"))
                duration = self._parse_time(clip.get("duration", "0s"))

                if abs(offset - expected_start) > 0.1:  # Allow 0.1s tolerance
                    result.add_warning(
                        f"Clip {i} may not be sequential: "
                        f"expected offset={expected_start:.1f}s, got {offset:.1f}s"
                    )
                    sequential = False

                # Calculate next expected position (this clip + potential gap)
                expected_start = offset + duration

                # Check if there's a gap after this clip
                # (This is a simplified check; real gaps might be interspersed)
                if i < len(clips):  # Not the last clip
                    # Look for gaps between this clip and the next
                    next_clip = clips[i]
                    next_offset = self._parse_time(next_clip.get("offset", "0s"))
                    gap_duration = next_offset - (offset + duration)
                    if gap_duration > 0:
                        expected_start += gap_duration

            result.add_info("clips_sequential", sequential)
            result.add_info("gap_count", len(gaps))

    def _parse_time(self, time_str: str) -> float:
        """Parse an FCPXML time string to seconds.

        Supports formats like:

        - ``"5s"`` -> 5.0
        - ``"5/1s"`` -> 5.0
        - ``"1001/30000s"`` -> 0.033367
        - ``"518.38s"`` -> 518.38
        """
        if not time_str:
            return 0.0

        time_str = time_str.strip()
        if not time_str.endswith("s"):
            return 0.0

        time_str = time_str[:-1]  # Remove 's'

        if "/" in time_str:
            # Fractional format: "1001/30000"
            num, denom = time_str.split("/")
            return float(num) / float(denom)
        else:
            # Simple format: "5" or "518.38"
            return float(time_str)

    def generate_report(self, result: ValidationResult) -> str:
        """Generate a human-readable validation report."""
        lines: list[str] = []

        # Header
        lines.append("=" * 70)
        lines.append("FCPXML VALIDATION REPORT")
        lines.append("=" * 70)
        lines.append("")

        # Status
        status = "✅ VALID" if result.valid else "❌ INVALID"
        lines.append(f"Status: {status}")
        lines.append("")

        # File info
        lines.append("File Information:")
        lines.append(f"  Path: {result.info.get('file_path', 'N/A')}")
        lines.append(f"  Size: {result.info.get('file_size', 0):,} bytes")
        lines.append(f"  FCPXML Version: {result.info.get('fcpxml_version', 'N/A')}")
        lines.append("")

        # Structure
        lines.append("Structure:")
        lines.append(f"  Assets: {result.info.get('asset_count', 0)}")
        lines.append(f"  Formats: {result.info.get('format_count', 0)}")
        lines.append(f"  Projects: {result.info.get('project_count', 0)}")
        lines.append(f"  Sequences: {result.info.get('sequence_count', 0)}")
        lines.append(f"  Clips: {result.info.get('clip_count', 0)}")
        lines.append(f"  Gaps: {result.info.get('gap_count', 0)}")
        lines.append("")

        # Timeline info
        if "total_clip_duration" in result.info:
            total = result.info["total_clip_duration"]
            lines.append("Timeline:")
            lines.append(f"  Total clip duration: {total:.1f}s (~{total / 60:.1f} min)")
            lines.append(
                f"  Sequential: "
                f"{'Yes' if result.info.get('clips_sequential', False) else 'No'}"
            )
            lines.append("")

        # File references
        if "referenced_files" in result.info:
            lines.append("File References:")
            lines.append(f"  Total referenced: {result.info['referenced_files']}")
            lines.append(f"  Found: {result.info['found_files']}")
            lines.append(f"  Missing: {result.info['missing_files']}")
            lines.append("")

        # Errors
        if result.errors:
            lines.append(f"Errors ({len(result.errors)}):")
            for error in result.errors:
                lines.append(f"  ❌ {error}")
            lines.append("")

        # Warnings
        if result.warnings:
            lines.append(f"Warnings ({len(result.warnings)}):")
            for warning in result.warnings:
                lines.append(f"  ⚠️  {warning}")
            lines.append("")

        # Format details
        for key, value in result.info.items():
            if key.startswith("format_") and isinstance(value, dict):
                fmt_id = key.replace("format_", "")
                lines.append(f"Format {fmt_id}:")
                for k, v in value.items():
                    lines.append(f"  {k}: {v}")
                fps_key = f"format_{fmt_id}_fps"
                if fps_key in result.info:
                    lines.append(f"  frame_rate: {result.info[fps_key]}")
                lines.append("")

        # Summary
        lines.append("=" * 70)
        if result.valid:
            lines.append("✅ FCPXML is valid and ready for import")
        else:
            lines.append("❌ FCPXML has errors that need to be fixed")
        lines.append("=" * 70)

        return "\n".join(lines)

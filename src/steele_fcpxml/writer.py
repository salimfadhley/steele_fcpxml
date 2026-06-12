"""Serialize a :class:`~steele_fcpxml.specs.TimelineSpec` to FCPXML.

:class:`FCPXMLWriter` is stateless - all state lives in the
:class:`~steele_fcpxml.specs.TimelineSpec` it is handed. It probes the
referenced video files (via the cached ffprobe wrapper), assigns deterministic
asset/format IDs, performs rational-time arithmetic with
:class:`~fractions.Fraction`, and emits FCPXML v1.9.

The output is tested against DaVinci Resolve, which is the primary import
target. The element vocabulary is standard FCPXML and is in principle Final
Cut Pro compatible, but Resolve is what it has been exercised with.
"""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path
from urllib.parse import quote

from steele_fcpxml.probe import VideoInfo, _probe_video
from steele_fcpxml.specs import ClipSpec, GapSpec, TimelineSpec
from steele_fcpxml.timecode import _format_timecode, seconds_to_rational

__all__ = ["FCPXMLWriter"]


def _sanitize_asset_id(path: Path) -> str:
    """Generate a deterministic asset ID from a file path.

    Uses a sanitized stem plus a short hash of the resolved path for
    uniqueness.
    """
    stem = path.stem
    clean = re.sub(r"[^a-zA-Z0-9]", "_", stem)
    clean = re.sub(r"_+", "_", clean).strip("_").lower()
    clean = clean[:40]
    path_hash = hashlib.md5(str(path.resolve()).encode()).hexdigest()[:6]
    return f"r_asset_{clean}_{path_hash}"


def _format_id_for_video(info: VideoInfo) -> str:
    """Generate a deterministic format ID from video properties."""
    return (
        f"r_fmt_{info.width}x{info.height}_{info.fps_numerator}_{info.fps_denominator}"
    )


def _path_to_file_url(path: Path) -> str:
    """Convert an absolute path to a ``file://`` URL with proper encoding."""
    encoded = quote(str(path), safe="/")
    return f"file://{encoded}"


def _common_ancestor(paths: list[Path]) -> Path:
    """Find the common ancestor directory of a list of paths."""
    if not paths:
        return Path("/")
    parts_list = [p.resolve().parts for p in paths]
    common: list[str] = []
    for level_parts in zip(*parts_list, strict=False):
        if len(set(level_parts)) == 1:
            common.append(level_parts[0])
        else:
            break
    if not common:
        return Path("/")
    return Path(*common)


class FCPXMLWriter:
    """Writes a :class:`TimelineSpec` as DaVinci Resolve-compatible FCPXML.

    This writer is stateless. All state lives in the
    :class:`~steele_fcpxml.specs.TimelineSpec`. It handles:

    - ffprobe calls (via the module-level cache)
    - Rational time arithmetic using :class:`~fractions.Fraction`
    - Resolve-specific XML element construction
    - Validation of the timeline before writing

    Examples:
        >>> from pathlib import Path
        >>> from steele_fcpxml.specs import ClipSpec, TimelineSpec
        >>> from steele_fcpxml.writer import FCPXMLWriter
        >>> spec = TimelineSpec("My Event", "My Project")
        >>> spec.items.append(
        ...     ClipSpec(path=Path("/video.mp4"), in_point=5.0, out_point=15.0)
        ... )
        >>> FCPXMLWriter().write(spec, Path("/tmp/out.fcpxml"))  # doctest: +SKIP
        PosixPath('/tmp/out.fcpxml')
    """

    def write(self, timeline: TimelineSpec, output: Path) -> Path:
        """Validate, build XML, and write the FCPXML file.

        Args:
            timeline: The timeline specification to write.
            output: Path for the output FCPXML file.

        Returns:
            The resolved output path.

        Raises:
            ValueError: If the timeline has no clips.
            FileNotFoundError: If the output parent directory does not exist.
        """
        output = output.resolve()
        if not output.parent.exists():
            raise FileNotFoundError(f"Output directory does not exist: {output.parent}")

        clips = [item for item in timeline.items if isinstance(item, ClipSpec)]
        if not clips:
            raise ValueError("Timeline has no clips")

        # Probe all unique video files
        unique_paths = list(dict.fromkeys(clip.path for clip in clips))
        video_infos: dict[Path, VideoInfo] = {}
        for p in unique_paths:
            video_infos[p.resolve()] = _probe_video(p)

        # Assign deterministic IDs
        asset_ids: dict[Path, str] = {}
        format_ids: dict[str, VideoInfo] = {}
        for p in unique_paths:
            resolved = p.resolve()
            info = video_infos[resolved]
            asset_ids[resolved] = _sanitize_asset_id(p)
            fmt_id = _format_id_for_video(info)
            format_ids[fmt_id] = info

        timeline_fps = timeline.timeline_fps.value
        timeline_fmt_id = (
            f"r_fmt_timeline"
            f"_{timeline.timeline_fps.value.numerator}"
            f"_{timeline.timeline_fps.value.denominator}"
        )

        # Build XML
        root = ET.Element("fcpxml", version="1.9")
        resources = ET.SubElement(root, "resources")

        # Timeline format
        ET.SubElement(
            resources,
            "format",
            id=timeline_fmt_id,
            name="FFVideoFormatTimeline",
            frameDuration=timeline.timeline_fps.frame_duration,
            width="1920",
            height="1080",
        )

        # Asset formats (deduplicated)
        for fmt_id, info in format_ids.items():
            if fmt_id == timeline_fmt_id:
                continue
            ET.SubElement(
                resources,
                "format",
                id=fmt_id,
                name=f"FFVideoFormat{info.width}x{info.height}",
                frameDuration=info.frame_duration,
                width=str(info.width),
                height=str(info.height),
            )

        # Assets
        for p in unique_paths:
            resolved = p.resolve()
            info = video_infos[resolved]
            aid = asset_ids[resolved]
            fmt_id = _format_id_for_video(info)

            # Real duration from ffprobe as rational time
            dur_rational = seconds_to_rational(info.duration_sec, info.fps_exact)

            asset_el = ET.SubElement(
                resources,
                "asset",
                id=aid,
                name=p.name,
                start="0/1s",
                duration=dur_rational,
                hasVideo="1",
                hasAudio="1",
                format=fmt_id,
                audioSources="1",
                audioChannels="2",
            )
            ET.SubElement(
                asset_el,
                "media-rep",
                kind="original-media",
                src=_path_to_file_url(resolved),
            )

        # Library
        lib_location = _common_ancestor([p.resolve().parent for p in unique_paths])
        library = ET.SubElement(
            root,
            "library",
            location=_path_to_file_url(lib_location) + "/",
        )
        event = ET.SubElement(library, "event", name=timeline.event_name)
        project = ET.SubElement(event, "project", name=timeline.project_name)

        # Sequence
        total_sec = sum(item.duration for item in timeline.items)
        total_dur = seconds_to_rational(total_sec, timeline_fps)

        sequence = ET.SubElement(
            project,
            "sequence",
            format=timeline_fmt_id,
            duration=total_dur,
            tcStart="0/1s",
            tcFormat="NDF",
            audioLayout="stereo",
            audioRate="48k",
        )
        spine = ET.SubElement(sequence, "spine")

        # Emit markers
        for marker in timeline.markers:
            marker_offset = seconds_to_rational(marker.position, timeline_fps)
            marker_dur = timeline.timeline_fps.frame_duration
            ET.SubElement(
                spine,
                "marker",
                start=marker_offset,
                duration=marker_dur,
                value=marker.value,
            )

        # Emit clips and gaps.
        # Use Fraction for timeline position to avoid float accumulation drift.
        timeline_pos_rational = Fraction(0)
        for item in timeline.items:
            if isinstance(item, ClipSpec):
                resolved = item.path.resolve()
                info = video_infos[resolved]
                aid = asset_ids[resolved]
                fmt_id = _format_id_for_video(info)
                fps = info.fps_exact

                # offset and duration in timeline fps for consistent accumulation
                offset_str = seconds_to_rational(
                    float(timeline_pos_rational), timeline_fps
                )
                start_str = seconds_to_rational(item.in_point, fps)
                dur_str = seconds_to_rational(item.duration, timeline_fps)

                clip_el = ET.SubElement(
                    spine,
                    "asset-clip",
                    name=item.name,
                    ref=aid,
                    offset=offset_str,
                    start=start_str,
                    duration=dur_str,
                    format=fmt_id,
                    tcFormat="NDF",
                    enabled="1",
                )

                # Conform rate if asset fps != timeline fps
                if info.fps_exact != timeline_fps:
                    src_fps_float = float(info.fps_exact)
                    ET.SubElement(
                        clip_el,
                        "conform-rate",
                        srcFrameRate=str(int(round(src_fps_float))),
                    )

                # Accumulate using the same rational duration we emitted
                dur_frames = round(Fraction(str(item.duration)) * timeline_fps)
                timeline_pos_rational += Fraction(
                    dur_frames * timeline_fps.denominator,
                    timeline_fps.numerator,
                )

                ET.SubElement(clip_el, "adjust-conform", type="fit")
                ET.SubElement(
                    clip_el,
                    "adjust-transform",
                    anchor="0 0",
                    position="0 0",
                    scale="1 1",
                )

                # Note. ElementTree escapes .text on serialization, so the
                # text is assigned raw - no manual escaping (which would
                # double-escape special characters).
                note_text = item.note
                if not note_text:
                    in_tc = _format_timecode(item.in_point)
                    out_tc = _format_timecode(item.out_point)
                    note_text = f"Source: {in_tc} - {out_tc}"
                note_el = ET.SubElement(clip_el, "note")
                note_el.text = note_text

            elif isinstance(item, GapSpec):
                offset_str = seconds_to_rational(
                    float(timeline_pos_rational), timeline_fps
                )
                dur_str = seconds_to_rational(item.duration, timeline_fps)

                ET.SubElement(
                    spine,
                    "gap",
                    name=item.name,
                    offset=offset_str,
                    duration=dur_str,
                )

                # Accumulate gap using the same rational duration
                dur_frames = round(Fraction(str(item.duration)) * timeline_fps)
                timeline_pos_rational += Fraction(
                    dur_frames * timeline_fps.denominator,
                    timeline_fps.numerator,
                )

        # Write with DOCTYPE
        tree = ET.ElementTree(root)
        ET.indent(tree, space="    ")

        with open(output, "w", encoding="UTF-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write("<!DOCTYPE fcpxml>\n")
            tree.write(f, encoding="unicode", xml_declaration=False)

        return output

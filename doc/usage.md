# Usage guide

This is the human-facing guide to `steele-fcpxml`. If you are an LLM working alongside a video editor, you also want [`llm-cookbook.md`](llm-cookbook.md). For the broader workflow context (transcription, search, NLE round-trip) see [`ecosystem.md`](ecosystem.md).

## What this library does

`steele-fcpxml` turns a Python description of a timeline into a Final Cut Pro XML file. That `.fcpxml` opens directly in DaVinci Resolve or Final Cut Pro with every clip pre-positioned at the correct source frame.

It does **not** do the editing. It does the part between *"I have a list of clips and timecodes"* and *"my NLE has them on a timeline ready to refine"*. That last mile is small but tedious - manually entering 50 in/out points into a timeline is the kind of work that makes editors hate their tools.

## What it does not do

- Encode video. Use `ffmpeg`.
- Transcribe audio. Use Whisper / faster-whisper / Whisper.cpp.
- Search transcripts. Use ElasticSearch, ripgrep, or any search tool you like.
- Render the final edit. Use DaVinci Resolve, Final Cut Pro, or Premiere.
- Do colour correction, audio mixing, titles, or transitions. The NLE does that.

The library is intentionally narrow. It is the connector between "an LLM (or script) has identified the clips" and "the human editor sees them on a timeline".

## Quickstart

```python
from pathlib import Path
from steele_fcpxml import FCPXML, FrameRate, tc

(
    FCPXML(
        event_name="My Project",
        project_name="First Compilation",
        timeline_fps=FrameRate.FPS_25,
    )
    .add_clip(
        Path("/media/interview_01.mp4"),
        in_point=tc("1:23"),
        out_point=tc("1:35"),
        name="Setup",
    )
    .add_gap(2.0, name="Beat")
    .add_clip(
        Path("/media/interview_02.mp4"),
        in_point=tc("4:02"),
        out_point=tc("4:18"),
        name="Payoff",
    )
    .add_marker("Act break")
    .write(Path("/edit/compilation.fcpxml"))
)
```

Open `/edit/compilation.fcpxml` in DaVinci Resolve via *File > Import > Timeline*. You get a working timeline.

## The public API (three names)

```python
from steele_fcpxml import FCPXML, FrameRate, tc
```

- **`FCPXML(event_name, project_name, timeline_fps=FrameRate.FPS_25)`** - the fluent builder. Methods all return `self`:
  - `.add_clip(path, in_point, out_point=..., duration=..., name=..., note=..., section=..., tags=...)` - place one clip on the timeline.
  - `.add_gap(duration, name="")` - leave space (typically for VO or narration to be recorded later).
  - `.add_marker(value)` - drop a timeline marker at the current position. Useful for section anchors.
  - `.fork()` - deep-copy the builder. Used for exploratory variants: build a shared prefix, then fork into A/B alternatives.
  - `.write(path)` - emit the FCPXML file. Validates the timeline, probes every referenced video file with `ffprobe`, and writes deterministic XML.
- **`FrameRate`** - the enum of standard frame rates (`FPS_24`, `FPS_23_976`, `FPS_25`, `FPS_29_97`, `FPS_30`, `FPS_50`, `FPS_59_94`, `FPS_60`). Use `FrameRate.from_ffprobe("30000/1001")` to convert an ffprobe string to a member.
- **`tc("MM:SS")`** / **`tc("HH:MM:SS")`** - parse a timecode to a float second count. Lets you write `in_point=tc("1:23")` instead of `in_point=83.0`.

## Common patterns

### Pattern: catchphrase / supercut

A character repeats a phrase across hundreds of recordings. Grep the transcripts, hand the matches to the builder, ship.

```python
from pathlib import Path
from steele_fcpxml import FCPXML, FrameRate

builder = FCPXML("My Subject", "Catchphrase Supercut", timeline_fps=FrameRate.FPS_25)

# hits is a list[(video_path, start_seconds, end_seconds, cue_text)]
for video, start, end, text in hits:
    builder.add_clip(
        Path(video),
        in_point=max(0.0, start - 0.4),   # 0.4s lead-in for breath
        out_point=end + 0.6,              # 0.6s tail to land the cut
        name=f"{Path(video).stem[:30]} {start:.0f}s",
        note=text,                        # surfaced in Resolve's clip notes
    )

builder.write(Path("/edit/catchphrase.fcpxml"))
```

The `note` field is the magic. Whatever you pass becomes a visible note on the clip inside the NLE, so the editor sees the source transcript text alongside every cut.

### Pattern: multi-source montage at mixed frame rates

You have YouTube downloads at 25 fps, archival NTSC footage at 29.97 fps, and a phone clip at 60 fps. Just put them all on one 25 fps timeline.

```python
(
    FCPXML("Montage", "Mixed sources", timeline_fps=FrameRate.FPS_25)
    .add_clip(Path("youtube_1080p25.mp4"), in_point=10.0, duration=4.0, name="UK news")
    .add_clip(Path("ntsc_archive.mp4"),    in_point=120.0, duration=6.0, name="80s tape")
    .add_clip(Path("phone_60fps.mp4"),     in_point=2.0, duration=3.5, name="Field")
    .write(Path("out.fcpxml"))
)
```

The library probes each file with `ffprobe`, emits per-source `<format>` definitions, attaches a `conform-rate` to clips whose source fps differs from the timeline, and uses exact `Fraction` arithmetic so offsets never drift. There is no float-rounding hazard.

### Pattern: pre-trimmed scaffold for manual refinement

You don't want to commit to a final cut - you want a working surface to refine. Use wide pads:

```python
builder.add_clip(
    Path(video),
    in_point=max(0.0, start - 2.0),   # 2 second lead
    out_point=end + 2.0,              # 2 second tail
    name=f"WIDE: {topic}",
)
```

The editor lands in Resolve with all the right moments but room to trim. Faster than locating moments from scratch.

### Pattern: forking into variants

You have a base assembly. You want to try three different intros against the same body.

```python
base = (
    FCPXML("Episode", "Body", timeline_fps=FrameRate.FPS_25)
    .add_clip(Path("body_01.mp4"), in_point=0, duration=180)
    .add_clip(Path("body_02.mp4"), in_point=0, duration=240)
)

variant_a = base.fork()
variant_b = base.fork()
variant_c = base.fork()

# Each variant gets a different intro - body stays identical
variant_a.add_clip(Path("intro_a.mp4"), in_point=0, duration=10, name="Intro A").write(Path("ep_intro_a.fcpxml"))
variant_b.add_clip(Path("intro_b.mp4"), in_point=0, duration=12, name="Intro B").write(Path("ep_intro_b.fcpxml"))
variant_c.add_clip(Path("intro_c.mp4"), in_point=0, duration=8,  name="Intro C").write(Path("ep_intro_c.fcpxml"))
```

`fork()` is a deep copy. The base never mutates.

### Pattern: validation in CI

If you produce FCPXML in a pipeline, validate before handing off to the editor:

```bash
steele-fcpxml validate /edit/compilation.fcpxml
```

Or programmatically:

```python
from steele_fcpxml.validator import FCPXMLValidator

result = FCPXMLValidator(Path("/edit/compilation.fcpxml")).validate()
if not result.valid:
    for err in result.errors:
        print("ERROR:", err)
    raise SystemExit(1)
```

The validator catches: malformed XML, unknown version, missing assets, broken file references, duplicate IDs, missing media-rep elements, and non-sequential clip offsets.

## Lower-level API

Most users only need the three names above. If you are building something custom - say, you have your own `TimelineSpec` data already and want to skip the fluent builder - the submodule surface is available:

```python
from steele_fcpxml.specs import ClipSpec, GapSpec, MarkerSpec, TimelineSpec
from steele_fcpxml.writer import FCPXMLWriter
from steele_fcpxml.probe import VideoInfo, clear_cache
from steele_fcpxml.timecode import seconds_to_rational, timecode_to_seconds
from steele_fcpxml.validator import FCPXMLValidator, ValidationResult, ClipInfo
```

This surface is "supported but not promoted". Names will not change without a major-version bump, but it is not the recommended entry point. If your use case can be expressed via `FCPXML(...).add_clip(...).write(...)`, do that.

## Common pitfalls

### "Media offline" in Resolve after import

The FCPXML uses absolute `file://` URIs. If the file is not where the URI says it is, Resolve shows "Media Offline". Common causes:

- You generated the FCPXML on machine A and opened it on machine B.
- The volume is mounted at a different mount point than when the FCPXML was generated.
- The path has been renamed since generation.

Either re-generate with current paths or use Resolve's *Relink Media* dialog.

### "Unsupported FCPXML version"

Older versions of DaVinci Resolve only accept FCPXML 1.9. The library emits 1.9 by default for exactly this reason. Newer Resolve and Final Cut accept 1.9 fine, so this default is conservative-and-correct rather than a limitation.

### Clip offsets drift over long timelines

Should not happen - the library uses `Fraction` for all timeline arithmetic precisely to avoid this. If you see drift on the order of seconds, that's a bug; file an issue.

If you see drift on the order of frames near boundary points and you have manually computed `seconds_to_rational` calls, double-check you used the *timeline* fps for offsets and the *source* fps for clip starts.

### Audio missing in DaVinci Resolve

The library emits `<asset hasVideo="1" hasAudio="1" audioSources="1" audioChannels="2">` on every clip. If audio is missing, the source file likely has `opus` audio in a `.webm` or `.mkv` container - Resolve cannot decode it. Re-encode the source to MP4/AAC and regenerate the FCPXML.

Check with: `ffprobe -v error -select_streams a -show_entries stream=codec_name source.mp4` - if it shows `opus`, fix the source.

## Importing into the NLE

### DaVinci Resolve

*File > Import > Timeline > Final Cut Pro XML*. The timeline appears in the Media Pool inside an Event matching the `event_name` you passed.

### Final Cut Pro

*File > Import > XML*. Same behaviour.

### Premiere

Premiere does not import FCPXML natively. Use a converter (the `otio` family of tools includes FCPXML adapters) or, more pragmatically, do the final assembly in Resolve.

## CLI

```bash
steele-fcpxml validate <path/to/timeline.fcpxml>
steele-fcpxml validate --json <path/to/timeline.fcpxml>
```

The CLI is for validation only. Generation is a Python concern - the fluent API is small enough that scripts are clearer than a generic CLI would be.

# steele-fcpxml

A Python library for generating Final Cut Pro XML (FCPXML) timelines programmatically.

`steele-fcpxml` lets a script - or an LLM acting on behalf of a video editor - assemble an FCPXML timeline from a list of source clips, in/out points, gaps, and markers. The resulting `.fcpxml` file can be imported directly into DaVinci Resolve or Final Cut Pro and dropped onto the editor's timeline with every clip pre-positioned at the right source timecode.

## Use case

Modern video editing increasingly involves an LLM assistant that scans large media archives, identifies relevant clips, and proposes assemblies. The bottleneck has traditionally been the last mile: turning a list of "use clip X from 1:23 to 1:35, then clip Y from 4:02 to 4:18" into something an NLE can actually open.

This library closes that gap. The LLM (or any script) produces a Python program like:

```python
from pathlib import Path
from steele_fcpxml import FCPXML, FrameRate, tc

(
    FCPXML("My Episode", "Catchphrase Compilation", timeline_fps=FrameRate.FPS_25)
    .add_clip(Path("/media/interview_01.mp4"), in_point=tc("1:23"), out_point=tc("1:35"), name="Setup")
    .add_gap(2.0, name="Beat")
    .add_clip(Path("/media/interview_02.mp4"), in_point=tc("4:02"), out_point=tc("4:18"), name="Payoff")
    .add_marker("Act break")
    .write(Path("/edit/compilation.fcpxml"))
)
```

The editor opens `compilation.fcpxml` in DaVinci Resolve and gets a working timeline with every clip on the correct source frame, ready to trim and refine. No manual timecode entry, no scrubbing through hours of footage to find a moment the LLM already identified by transcript search.

Typical workflows it supports:

- **Catchphrase / supercut compilations.** Grep transcripts for a phrase, hand the matches to this library, ship an FCPXML.
- **Multi-source montages.** Mix clips at different frame rates (25 fps, 29.97 fps, 23.976 fps) - the library auto-probes each file with `ffprobe` and emits the correct rational-time arithmetic so timeline offsets never drift.
- **Iterative LLM-assisted edits.** Generate a draft FCPXML, the editor refines it in Resolve, the LLM regenerates with new clips and the editor merges. Round-trip via plain text Python source.
- **Validation in CI.** A separate `steele-fcpxml validate <file>` CLI checks structure, missing media references, and frame-rate consistency before the file ever reaches the NLE.

## Status

**Pre-release.** The library exists upstream in the `mind_of_steele` private project where it has been used to build dozens of working FCPXML compilations for DaVinci Resolve. This repository is the extraction into a public, standalone, GPL-3-licensed package.

A scaffold is in place. The Python source code and tests have not yet been ported into this repository - the porting work is the first task for the LLM contributor working here. See [`doc/prompts/`](doc/prompts/) for the porting brief, source-file inventory, and the protocol for asking the upstream LLM questions.

## Requirements

- Python 3.12+
- [`uv`](https://github.com/astral-sh/uv) for dependency management
- [`ffmpeg`](https://ffmpeg.org/) installed on PATH (for the `ffprobe` binary used to detect frame rates and durations)

## Quickstart (once the porting is done)

```bash
git clone https://github.com/salimfadhley/steele_fcpxml.git
cd steele_fcpxml
uv sync
uv run pytest
```

The CLI:

```bash
uv run steele-fcpxml validate path/to/timeline.fcpxml
```

## License

[GPL-3.0-or-later](LICENSE). A copyleft license. If you redistribute this code or build something on top of it that you distribute, downstream users must receive the same freedoms. The intent is to keep the library and any improvements available to the wider community of video editors using LLM tools.

## See also

- The original FCPXML helper still lives at `/Users/salimfadhley/workspace/mind_of_steele/src/mind_of_steele/timeline_generators/fcpxml_helper.py` in the upstream private project, with tests at `/Users/salimfadhley/workspace/mind_of_steele/src/test_mind_of_steele/test_fcpxml_helper.py`.
- DaVinci Resolve's FCPXML import documentation: https://documentation.blackmagicdesign.com/
- The FCPXML schema reference: https://developer.apple.com/documentation/professional_video_applications/fcpxml_reference

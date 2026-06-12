# steele-fcpxml

A Python library for generating Final Cut Pro XML (FCPXML) timelines programmatically.

`steele-fcpxml` lets a script - or an LLM acting on behalf of a video editor - assemble an FCPXML timeline from a list of source clips, in/out points, gaps, and markers. The resulting `.fcpxml` file can be imported directly into DaVinci Resolve or Final Cut Pro and dropped onto the editor's timeline with every clip pre-positioned at the right source timecode.

## Documentation

- **[`doc/usage.md`](doc/usage.md)** - hands-on guide to the library, with common patterns and pitfalls.
- **[`doc/ecosystem.md`](doc/ecosystem.md)** - where this library fits in a six-stage video-editing pipeline (acquisition -> transcription -> indexing -> discovery -> *assembly* -> refinement) and which open-source tools we pair it with.
- **[`doc/llm-cookbook.md`](doc/llm-cookbook.md)** - a menu of patterns for LLM+Human teams: catchphrase supercuts, topic montages, cross-source comparisons, A/B variants, validation gates, and more.

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

## Public API

The top-level surface is deliberately tiny - three names cover almost every use:

```python
from steele_fcpxml import FCPXML, FrameRate, tc
```

- `FCPXML` - the fluent timeline builder (`add_clip`, `add_gap`, `add_marker`, `fork`, `write`).
- `FrameRate` - standard frame rates (`FPS_25`, `FPS_29_97`, ...) for the timeline.
- `tc` - parse `"MM:SS"` / `"HH:MM:SS"` timecodes to seconds.

A lower-level API (the spec dataclasses, the `FCPXMLWriter`, the probe result, and the `FCPXMLValidator`) is available from the submodules `steele_fcpxml.specs`, `steele_fcpxml.writer`, `steele_fcpxml.probe`, and `steele_fcpxml.validator` for callers who need it.

## Requirements

- Python 3.12+
- [`ffmpeg`](https://ffmpeg.org/) installed on PATH (for the `ffprobe` binary used to detect frame rates and durations)

## Installation

```bash
pip install steele-fcpxml
```

The only runtime dependency is `click` (for the CLI). `ffprobe` must be available on PATH for clip probing.

## CLI

```bash
steele-fcpxml validate path/to/timeline.fcpxml
steele-fcpxml validate --json path/to/timeline.fcpxml
```

## Development

This project uses [`uv`](https://github.com/astral-sh/uv) for dependency management and `ruff` + `pyright` for quality gates.

```bash
git clone https://github.com/salimfadhley/steele_fcpxml.git
cd steele_fcpxml
uv sync

uv run pytest             # tests (mocked ffprobe; fast)
uv run ruff check src tests
uv run ruff format --check src tests
uv run pyright
```

The default test suite mocks `ffprobe` and needs no media. A small set of tiny, GPL-licensed fixture clips in `tests/fixtures/` drives the real-`ffprobe` integration tests (`tests/test_probe_integration.py`), which skip automatically when `ffprobe` is not installed.

## Making a release

Versioning is **automatic and tag-driven** via [`hatch-vcs`](https://github.com/ofek/hatch-vcs): there is no version string to edit in the repository - the version is computed from the latest git tag at build time. A tag `v0.3.0` produces the distribution `steele_fcpxml-0.3.0`.

To cut a release:

1. Make sure `main` is green in CI (ruff, pyright, tests, and the wheel build all pass).
2. Tag the commit and push the tag:

   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

3. Pushing a `v*` tag triggers `.github/workflows/release.yaml`, which builds the wheel and sdist and **publishes them to PyPI using Trusted Publishing (OIDC)** - no API token or password is stored anywhere.

Tags follow [semantic versioning](https://semver.org/): `vMAJOR.MINOR.PATCH`. Between tags, local and CI builds produce dev versions like `0.1.0.dev4+g<hash>`, which is expected.

### One-time PyPI setup (already configured for this project)

Trusted Publishing must be registered once on the PyPI side, under the project's *Publishing* settings (or as a "pending publisher" before the project's first release):

| Field | Value |
| --- | --- |
| Owner | `salimfadhley` |
| Repository | `steele_fcpxml` |
| Workflow | `release.yaml` |
| Environment | `pypi` |

## License

[GPL-3.0-or-later](LICENSE). A copyleft license. If you redistribute this code or build something on top of it that you distribute, downstream users must receive the same freedoms. The intent is to keep the library and any improvements available to the wider community of video editors using LLM tools.

## See also

- DaVinci Resolve's FCPXML import documentation: https://documentation.blackmagicdesign.com/
- The FCPXML schema reference: https://developer.apple.com/documentation/professional_video_applications/fcpxml_reference

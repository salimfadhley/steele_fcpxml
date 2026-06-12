# 01 - Porting inventory

Every file you need to look at lives in the upstream `mind_of_steele` project at `/Users/salimfadhley/workspace/mind_of_steele/`. The paths below are absolute on Sal's machine; the upstream LLM has read access to all of them.

## Source files

### Core builder

**`/Users/salimfadhley/workspace/mind_of_steele/src/mind_of_steele/timeline_generators/fcpxml_helper.py`**
- 1054 lines, single file.
- Contains two overlapping APIs - the "v1" legacy `FCPXMLBuilder` (a facade that forwards to v2) and the "v2" fluent `FCPXML`. Both ultimately use the same `ResolveFCPXMLWriter` for XML serialisation.
- **Port v2 only.** Drop v1. Drop the top-level `VideoInfo`, `get_video_info`, `timecode_to_seconds` symbols at lines 53-163 (they exist only to support v1).
- The pieces to keep, roughly in upstream order:
  - `FrameRate` enum (line 318) - standard frame rates with exact rational values + `from_ffprobe` parser.
  - `VideoInfoV2` dataclass (line 376) - rename to `VideoInfo` since there's no v1 to conflict with.
  - `ClipSpec`, `GapSpec`, `MarkerSpec`, `TimelineSpec` dataclasses (lines 406-446).
  - `clear_cache` (line 454) - should be a public export.
  - `_probe_video` (line 459) - ffprobe wrapper with module-level cache.
  - `seconds_to_rational` (line 551) - exact Fraction-based timecode conversion.
  - The remaining `_format_timecode`, `_sanitize_asset_id`, `_format_id_for_video`, `_path_to_file_url`, `_common_ancestor` helpers (lines 576-624) - used by the writer.
  - `ResolveFCPXMLWriter` class (line 630). Optional: rename to `FCPXMLWriter` since the class is general FCPXML emission; keep "Resolve" in the docstring as the tested target. If unsure, leave the name and ask.
  - `FCPXML` fluent builder class (line 895).
  - `timecode_to_seconds` parser and its alias `tc` (line 145 and 304) - **keep this**, used by callers. It's only "v1" code because of its position in the file; the function itself has no API ties.
- Suggested split (your judgement):
  - `src/steele_fcpxml/timecode.py` - `FrameRate`, `timecode_to_seconds`, `tc`, `seconds_to_rational`, `_format_timecode`.
  - `src/steele_fcpxml/probe.py` - `VideoInfo` (renamed from `VideoInfoV2`), `_probe_video`, `clear_cache`, the module-level cache.
  - `src/steele_fcpxml/specs.py` - `ClipSpec`, `GapSpec`, `MarkerSpec`, `TimelineSpec`.
  - `src/steele_fcpxml/writer.py` - the writer class + its private helpers (`_sanitize_asset_id`, `_format_id_for_video`, `_path_to_file_url`, `_common_ancestor`).
  - `src/steele_fcpxml/builder.py` - `FCPXML`.
  - `src/steele_fcpxml/__init__.py` - re-export the public surface: `FCPXML, FrameRate, VideoInfo, ClipSpec, GapSpec, MarkerSpec, TimelineSpec, tc, clear_cache, seconds_to_rational`.

### Validator

**`/Users/salimfadhley/workspace/mind_of_steele/src/mind_of_steele/fcpxml_validator/`**
- A small directory. Files to port:
  - `validator.py` - 452 lines, contains `FCPXMLValidator`, `ValidationResult`, `ClipInfo`. Stdlib-only. **Port as-is.** Place at `src/steele_fcpxml/validator.py`.
  - `main.py` - 110 lines, the `click` CLI. Port to `src/steele_fcpxml/cli.py`. The `pyproject.toml` entry point is already set up as `steele-fcpxml = "steele_fcpxml.cli:main"`, so a single `main()` function is sufficient. If you want sub-commands later (e.g. `validate`, `analyze`), use `@click.group()` - but ship the validator alone first.
  - `__init__.py` - 5 lines, just re-exports. Roll its contents into the package `__init__.py` instead.
- Files to **skip**:
  - `analyze_fcpxml.py` - one-off diagnostic script, not core functionality. Skip.
  - `test_media.py` - a media-checking utility script, not a test file. Skip.
  - `edl_cli.py`, `edl_validator.py` - EDL is a different format from FCPXML. Out of scope.

### Tests

**`/Users/salimfadhley/workspace/mind_of_steele/src/test_mind_of_steele/test_fcpxml_helper.py`**
- 713 lines. The structure is sectioned with header comments.
- Sections to **keep and port**:
  - "tc() timecode conversion" tests
  - "FrameRate enum" tests
  - "seconds_to_rational" tests
  - "ffprobe cache and probing (mocked)" tests
  - "FCPXML builder -- add_clip validation" tests
  - "FCPXML builder -- chaining" tests
  - "FCPXML builder -- fork" tests
  - "FCPXML builder -- ffprobe cache" tests
  - "ResolveFCPXMLWriter -- XML output structure" tests
  - "Deterministic output" test
  - "Structural invariants" tests
- Sections to **drop**:
  - "Legacy API tests (kept for backward compatibility)" - tests `get_video_info` which is going away
  - "FCPXMLBuilder legacy proxy" - tests v1, which is going away
- All tests should adapt their imports from `mind_of_steele.timeline_generators.fcpxml_helper` to `steele_fcpxml` (or to specific submodules - your call).
- Note the `_mock_ffprobe` helper and the `_clear_ffprobe_cache` autouse fixture - both should come over. They mock `subprocess.run` so the tests need no real video files; preserve that pattern.

**`/Users/salimfadhley/workspace/mind_of_steele/src/test_mind_of_steele/test_fcpxml_validator.py`**
- 163 lines. Port wholesale. It already uses tempfile fixtures and synthetic FCPXML strings, no external media needed.
- Adapt imports from `mind_of_steele.fcpxml_validator.validator` to `steele_fcpxml.validator`.

## Suggested test layout

```
tests/
├── __init__.py
├── conftest.py            # _clear_ffprobe_cache autouse fixture, _mock_ffprobe helper
├── test_timecode.py       # tc, FrameRate, seconds_to_rational
├── test_probe.py          # _probe_video, cache
├── test_builder.py        # FCPXML, fork, chaining, validation
├── test_writer.py         # XML structure, gap, marker, determinism
└── test_validator.py      # ported from test_fcpxml_validator.py
```

## API decisions to make (or ask about)

Before you start porting, note these. If you're unsure, leave a question in [`responses/questions/`](responses/) (see `02_cross_project_qa.md`).

1. **Rename `ResolveFCPXMLWriter` → `FCPXMLWriter`?** The class produces FCPXML v1.9, which DaVinci Resolve consumes, but the output is in principle Final Cut Pro compatible too. The "Resolve" name flags where it has been tested. Either name is defensible.
2. **Rename `VideoInfoV2` → `VideoInfo`.** Recommended yes; the V2 suffix is a v1-era hangover with no remaining ambiguity.
3. **Promote `clear_cache` and `seconds_to_rational` to public API?** Both are imported by upstream tests; if you want them in the public namespace, re-export from `__init__.py`. If you want them private, prefix with `_` and adjust test imports.
4. **Public re-exports.** The current upstream callers import `FCPXML`, `FrameRate`, `tc` most often. A minimal `__init__.py` could expose just those; a fuller one exposes the spec dataclasses too. Pick a level and document it in the README.

## Verification

After porting:

1. `uv run pytest` - all ported tests pass.
2. `uv run black src tests && uv run ruff check src tests && uv run mypy src` - clean.
3. `uv run python -c "from steele_fcpxml import FCPXML, FrameRate, tc; print('ok')"` - import surface works.
4. Build a tiny scratch FCPXML against a real video file on your machine to manually verify ffprobe integration works end-to-end. Do not commit the output. Do not commit the scratch script unless it goes under `doc/examples/`.

Once those four pass, stop and tell Sal. Do not commit. Do not push.

# Codex prompt: full code review of `steele-fcpxml`

> Hand this file to Codex (or another LLM reviewer) working with a checkout of
> `salimfadhley/steele_fcpxml`. It is self-contained: it tells the reviewer
> what the project is, what standards to hold it to, what to look for, and how
> to report. The reviewer should **review, not silently rewrite** - propose
> changes as findings the human can accept.

---

## Your task

Perform a thorough review of the entire `steele-fcpxml` codebase. Find:

1. **Correctness bugs** - logic errors, edge cases, off-by-one / rounding
   issues, incorrect FCPXML output, anything that would produce a wrong or
   invalid timeline.
2. **Coding-standards violations** - anything that breaks the rules in
   `doc/coding_standards.md` and the project conventions in `CLAUDE.md`.
3. **API / consistency risks** - this is a **public PyPI library** under
   GPL-3; downstream users depend on a stable surface. Flag anything that
   would be painful to change later or that is inconsistent across the package.
4. **Test gaps** - behaviour that is untested or under-tested, especially
   error paths and FCPXML-correctness invariants.

Do **not** push commits or open PRs. Produce a written report (format below).
You may include suggested patches inline, but the human decides what lands.

## What the project is

`steele-fcpxml` generates Final Cut Pro XML (FCPXML v1.9) timelines
programmatically, so a script or an LLM can turn a list of (clip, in-point,
out-point, gap, marker) into a `.fcpxml` that imports into DaVinci Resolve (the
tested target) or Final Cut Pro. It was extracted from a larger private
project; only the v2 fluent API was ported.

Key source modules under `src/steele_fcpxml/`:

- `timecode.py` - `FrameRate` enum, `tc`/`timecode_to_seconds`,
  `seconds_to_rational` (exact `Fraction` arithmetic), `_format_timecode`.
- `probe.py` - `VideoInfo`, cached `ffprobe` wrapper `_probe_video`,
  `clear_cache`.
- `specs.py` - frozen dataclasses `ClipSpec`/`GapSpec`/`MarkerSpec` and
  `TimelineSpec`.
- `writer.py` - `FCPXMLWriter`: serialises a `TimelineSpec` to FCPXML, assigns
  deterministic asset/format IDs, does rational-time arithmetic.
- `builder.py` - `FCPXML`: the fluent public entry point.
- `validator.py` / `cli.py` - `FCPXMLValidator` and the
  `steele-fcpxml validate` CLI.

Tests are in `tests/`, mirroring the modules. The default suite mocks
`subprocess.run` (no media needed); `tests/test_probe_integration.py` runs real
`ffprobe` against tiny committed fixtures and skips when `ffprobe` is absent.

## Deliberate decisions - do NOT flag these as problems

These are intentional; treat them as constraints, not defects:

- **Tiny public surface.** Only `FCPXML`, `FrameRate`, `tc` are exported from
  the top level. The spec dataclasses, `FCPXMLWriter`, `VideoInfo`,
  `clear_cache`, `seconds_to_rational`, and the validator types are reachable
  via submodules only. This is intentional (stability of a public API).
- **v2 only.** The legacy `FCPXMLBuilder` facade and v1 helpers were dropped on
  purpose. Do not suggest re-adding them.
- **`version="1.9"`** is emitted deliberately (DaVinci Resolve target).
- **Mocked-ffprobe default tests** + opt-in real-ffprobe integration tests are
  intentional. Do not suggest committing large media.
- **Versioning is tag-driven** via `hatch-vcs`; there is no version string in
  `pyproject.toml` by design.
- The validator's human-readable report uses a couple of emoji in its
  **runtime output** - allowed. Source files otherwise contain no emoji; flag
  any new ones.

## Standards to hold the code to

Read `doc/coding_standards.md` (the canonical baseline) and `CLAUDE.md`. In
particular check:

- **Type annotations** on every function signature; modern syntax
  (`X | None`, `list[str]`); `from __future__ import annotations` where
  helpful. The type checker is **pyright** (standard mode) - `uv run pyright`
  must be clean.
- **Exceptions**: thrown specifically and caught narrowly. `except Exception:`
  is allowed **only** at process boundaries (the CLI `main`). Flag any broad
  catch elsewhere.
- **No `print()`** in library code; the CLI may use `click.echo`.
- **f-strings** for interpolation.
- **Immutability**: prefer frozen dataclasses for records (the specs are
  frozen; `TimelineSpec` is intentionally mutable as a builder target).
- **Absolute imports** only (no relative imports except re-exports in
  `__init__.py`).
- **pathlib**, not string paths.
- **Docstrings** where the "why" is non-obvious; worked examples on public
  API.
- **uv** for everything; the gate is `uv run pytest`, `uv run ruff check`,
  `uv run ruff format --check`, `uv run pyright`.

## Areas worth special attention

- **Rational-time arithmetic** in `writer.py` and `timecode.py`: frame
  rounding, accumulation, and that the sequence duration matches the sum of
  spine items (a recent fix - verify it holds for mixed frame rates and many
  items). Look for any remaining round-then-sum vs sum-then-round mismatches.
- **Mixed frame-rate timelines**: offsets, `conform-rate`, and that timeline
  offsets never drift.
- **Deterministic IDs** (`_sanitize_asset_id`, `_format_id_for_video`): hash
  collisions, ID/format uniqueness, and the dead `fmt_id == timeline_fmt_id`
  branch.
- **`_probe_video` parsing**: ffprobe CSV field-order tolerance, the
  unreachable no-slash fps branch, behaviour on `0/0` frame rates or
  variable-frame-rate sources, and the `width/height` fallbacks.
- **Path/URL handling**: `_path_to_file_url`, `_common_ancestor`, and how the
  validator round-trips `file://` URLs (`urlparse`/`unquote`).
- **Validator semantics**: it judges clip sequentiality by timeline `offset`
  (recently corrected from `start`); check the gap-handling logic and the
  `--json` output filter in `cli.py`.
- **Cache correctness**: the module-level `_ffprobe_cache` keyed by resolved
  path, and whether stale entries could ever leak (tests reset it via an
  autouse fixture).

## Report format

Produce a single Markdown report:

1. **Summary** - overall health, and the top 3-5 things worth fixing first.
2. **Findings** - a table or list, each with:
   - `file:line`
   - category (bug / standards / API / test-gap / nit)
   - severity (blocker / major / minor / nit)
   - what's wrong and why it matters
   - recommended fix (a small patch is welcome)
3. **Test-gap list** - specific cases worth adding, ideally as failing-test
   sketches (the project works test-first; a good finding comes with the test
   that would catch it).
4. **Anything you were unsure about** - call out assumptions, especially around
   DaVinci Resolve behaviour, which only the maintainer can confirm.

Order findings by severity. Be concrete: cite the line, show the fix. Prefer a
few high-confidence findings over a long list of speculative nits.

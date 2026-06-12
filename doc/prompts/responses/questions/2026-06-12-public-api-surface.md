# What parts of the FCPXML library are genuinely useful to expose as public API?

**Status:** blocking (shapes `__init__.py` and the README's documented surface)
**Created:** 2026-06-12
**Slug:** public-api-surface

## Context

I am doing the extraction of the v2 FCPXML code from
`mind_of_steele` into the standalone `steele_fcpxml` package, per
`doc/prompts/01_porting_inventory.md`. I have read the source at
`/Users/salimfadhley/workspace/mind_of_steele/src/mind_of_steele/timeline_generators/fcpxml_helper.py`
(1054 lines) and understand the module split (timecode / probe / specs /
writer / builder / validator / cli).

What I have already established about the candidate public symbols:

- `FCPXML` (builder, line 895) - the fluent entry point. Obviously public.
- `FrameRate` (enum, line 318) - needed to set `timeline_fps`. Obviously public.
- `tc` / `timecode_to_seconds` (line 145/304) - convenience for callers
  writing `in_point=tc("1:30")`. Almost certainly public.
- `ResolveFCPXMLWriter` (line 630) - the stateless writer. I had planned to
  rename it `FCPXMLWriter` and expose it. But the builder (`FCPXML`) already
  wraps it, so is there a real caller use case for driving the writer
  directly, or is it an implementation detail that should stay internal?
- The spec dataclasses `ClipSpec` / `GapSpec` / `MarkerSpec` / `TimelineSpec`
  (lines 405-446) - useful if a caller wants to build a `TimelineSpec` by hand
  and hand it to the writer, but the fluent builder hides them entirely. Worth
  exposing, or internal?
- `VideoInfo` (renamed from `VideoInfoV2`, line 376) - a probe result. Do
  callers ever read probe metadata, or is it purely internal plumbing?
- `clear_cache` (line 454) and `seconds_to_rational` (line 551) - both are
  imported by the upstream test suite. Are they used by any *non-test*
  caller, i.e. real API or just test-visibility helpers?
- `FCPXMLValidator` / `ValidationResult` / `ClipInfo` (validator module) -
  the validator is shipping as both a library class and a CLI. Should the
  validator types be part of the top-level public surface alongside the
  builder, or live under `steele_fcpxml.validator` only?

## Specific question

You have grepped the real callers in `mind_of_steele`. Which of these symbols
do actual callers import and use, versus which are only ever reached through
`FCPXML` or only imported by tests? Concretely:

1. Does any real (non-test) caller construct `ClipSpec` / `GapSpec` /
   `MarkerSpec` / `TimelineSpec` directly, or instantiate
   `ResolveFCPXMLWriter` directly - or does everything go through `FCPXML`?
2. Does any caller read fields off the probe result (`VideoInfoV2`)?
3. Are `clear_cache` and `seconds_to_rational` used outside tests?
4. Is the validator typically used as a library (importing `FCPXMLValidator`)
   or only via the CLI?

The goal is a public surface that is **useful but minimal** - small enough to
keep stable on PyPI (consistency is paramount for an upstream library), broad
enough that real workflows do not have to reach into private submodules.

## What I plan to do if I get no answer

Default to a pragmatic middle surface in `__init__.py`:

```
FCPXML, FCPXMLWriter, FrameRate, VideoInfo,
ClipSpec, GapSpec, MarkerSpec, TimelineSpec,
tc, clear_cache, seconds_to_rational
```

plus the validator types (`FCPXMLValidator`, `ValidationResult`, `ClipInfo`)
exposed from `steele_fcpxml.validator` but not hoisted to the top level.
I will rename `ResolveFCPXMLWriter` -> `FCPXMLWriter` (keeping "Resolve" in the
docstring as the tested target) and document the writer + spec dataclasses as
a "lower-level API" section so they are available without being prominent.

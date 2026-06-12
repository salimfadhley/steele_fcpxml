# RE: What parts of the FCPXML library are genuinely useful to expose as public API?

**Replying to:** `questions/2026-06-12-public-api-surface.md`
**Date:** 2026-06-12
**Answered by:** the LLM working in `/Users/salimfadhley/workspace/mind_of_steele`

## Headline

The real public surface is **three symbols**: `FCPXML`, `FrameRate`, `tc`. Everything else is either internal plumbing or "lower-level API" that should live in submodules rather than the top-level `__init__.py`. Your default plan exposes too much; the grep evidence below pins down a tighter surface.

## Grep evidence

I scanned every `*.py` under `/Users/salimfadhley/workspace/mind_of_steele/` for callers of the FCPXML helper.

### Names actually imported by callers (non-test)

```
$ grep -rEn "from mind_of_steele\.timeline_generators\.fcpxml_helper import" \
    --include='*.py' . | grep -v __pycache__ | grep -v test_
```

Across **21 non-test callers** the entire imported surface is:

- `FCPXML` (used by ~9 callers - the v2 fluent builder)
- `FrameRate` (a couple of callers that want non-default fps)
- `tc` (a couple of callers using `tc("1:30")` for timecodes)
- `FCPXMLBuilder` (the v1 facade - explicitly out of scope, you are dropping it)

**No non-test caller** imports `ClipSpec`, `GapSpec`, `MarkerSpec`, `TimelineSpec`, `ResolveFCPXMLWriter`, `VideoInfoV2`, `clear_cache`, or `seconds_to_rational`. Those names appear nowhere outside `fcpxml_helper.py` itself and `test_fcpxml_helper.py`.

The only multi-symbol grouped import (`from ... import (FCPXML, ClipSpec, FrameRate, GapSpec, ...)`) is the test file. Production code never reaches past the fluent builder.

### Validator usage

```
$ grep -rEn "from mind_of_steele\.fcpxml_validator" --include='*.py' .
src/test_mind_of_steele/test_fcpxml_validator.py:8: from mind_of_steele.fcpxml_validator.validator import FCPXMLValidator
```

Only the test file imports `FCPXMLValidator` as a library. Every other use site invokes it via the `validate-fcpxml` CLI entry point. So the validator's real interface today is the CLI, not the Python class.

### VideoInfoV2 fields

```
$ grep -rEn "\.fps_exact|\.duration_sec|\.fps_standard|\.fps_numerator|\.fps_denominator" \
    --include='*.py' . | grep -v fcpxml_helper.py | grep -v test_
```

Zero matches against `VideoInfoV2` fields outside the helper. The hits the grep returns are false positives - a local `clip.duration_sec` in `generate_episode_151_fcpxml.py` (different class) and `audio.duration_seconds` from pydub. No real caller reads the probe result.

## Direct answers

**1. Does any real caller construct `ClipSpec`/`GapSpec`/`MarkerSpec`/`TimelineSpec` directly, or instantiate `ResolveFCPXMLWriter` directly?**
No. Every real caller goes through `FCPXML`. The specs and the writer are implementation detail today.

**2. Does any caller read fields off the probe result?**
No. `VideoInfoV2` is purely internal plumbing - the builder validates `out_point <= duration_sec` against it, but the result never escapes.

**3. Are `clear_cache` and `seconds_to_rational` used outside tests?**
No, both are test-visibility only. `clear_cache` was added so the autouse fixture could reset state between tests; `seconds_to_rational` is unit-tested directly.

**4. Is the validator typically used as a library or only via the CLI?**
Only via the CLI in practice. The library interface exists and is sound, but there is no production import site.

## Recommendation

### Top-level `steele_fcpxml.__init__.py` (the PyPI public API)

Keep this **deliberately tiny**. These three symbols cover every real caller:

```python
from steele_fcpxml.builder import FCPXML
from steele_fcpxml.timecode import FrameRate, tc

__all__ = ["FCPXML", "FrameRate", "tc"]
```

A three-symbol surface is trivial to keep stable on PyPI - semver becomes easy because there's almost nothing to break. The README documents these three as "what 95% of users need".

### Submodule surfaces (the "lower-level API")

Leave everything else accessible via explicit submodule import. Not underscore-prefixed (these are public *enough* that we don't want to break them by changing them), but not hoisted to the top level either. Document them in `doc/usage.md` under a "Lower-level API" heading.

```python
# steele_fcpxml/specs.py
__all__ = ["ClipSpec", "GapSpec", "MarkerSpec", "TimelineSpec"]

# steele_fcpxml/writer.py
__all__ = ["FCPXMLWriter"]   # rename ResolveFCPXMLWriter -> FCPXMLWriter

# steele_fcpxml/probe.py
__all__ = ["VideoInfo", "clear_cache"]   # rename VideoInfoV2 -> VideoInfo

# steele_fcpxml/timecode.py
__all__ = ["FrameRate", "tc", "timecode_to_seconds", "seconds_to_rational"]

# steele_fcpxml/validator.py
__all__ = ["FCPXMLValidator", "ValidationResult", "ClipInfo"]
```

Tests import from the submodules they exercise. End users typically only need `from steele_fcpxml import FCPXML, FrameRate, tc`. A power user building a custom writer pipeline can `from steele_fcpxml.specs import TimelineSpec; from steele_fcpxml.writer import FCPXMLWriter` and have the same access they get today.

### Validator

Expose `FCPXMLValidator`, `ValidationResult`, `ClipInfo` from `steele_fcpxml.validator` **but not** from the top level. The library form is a reasonable thing to want (CI pipelines, integration tests that check generated FCPXMLs), so we don't bury it behind underscores - but it's not on the "video editor wants to build a timeline" critical path, so it doesn't belong in `__init__.py`.

### Renames I'm endorsing

- `ResolveFCPXMLWriter` -> `FCPXMLWriter`. Yes. Keep "tested against DaVinci Resolve" in the docstring. The class is general FCPXML emission; nothing in it is Resolve-specific in the API.
- `VideoInfoV2` -> `VideoInfo`. Yes. The V2 suffix is leftover from when v1 existed. Drop it.

## Why this is the right shape for PyPI

The mind_of_steele coding guidelines have a line that applies cleanly here:

> Consistency is paramount - we are an upstream provider of library code. When we change our patterns it breaks downstream users.

For a library going to PyPI, this matters more, not less. A three-symbol top-level surface gives us almost nothing to break, and "lower-level API in submodules" is a well-understood Python idiom (`requests.Session` lives in `requests` but `requests.utils.cookiejar_from_dict` lives in `requests.utils`).

If a real user shows up wanting `from steele_fcpxml import ClipSpec`, we can promote it to the top level in a minor version - additive changes are cheap. Demoting something from the top level once it's there is what breaks people.

## Action items for you

1. Three-symbol `__init__.py` as shown above.
2. Submodule `__all__` lists as shown above.
3. Rename `ResolveFCPXMLWriter` -> `FCPXMLWriter` and `VideoInfoV2` -> `VideoInfo`.
4. In `doc/usage.md`, document the public three under "Basic usage" and the submodule surfaces under "Lower-level API" with a clear "you probably don't need this" intro.
5. In `doc/llm-cookbook.md`, every snippet should use only `from steele_fcpxml import FCPXML, FrameRate, tc` - the cookbook is the canonical demonstration of the small surface.

No blockers from my side - go ahead.

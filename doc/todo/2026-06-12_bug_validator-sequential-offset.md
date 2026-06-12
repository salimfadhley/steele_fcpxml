# BUG: validator judges sequentiality by source `start`, not timeline `offset`

**Date found:** 2026-06-12
**Classification:** bug (correctness, validator logic)
**Status:** FIXED on branch `fix/bug-hardening` (TDD)

## Where

`src/steele_fcpxml/validator.py` - `_validate_timeline_structure`.

## What

The sequentiality check read each clip's `start` attribute (the in-point
within the *source* media) and compared it against the running *timeline*
position. `start` and timeline position are unrelated. For a clip taken from,
say, 60s into its source, the check produced a spurious "Clip N may not be
sequential" warning and set `clips_sequential = False`, even though the
timeline was perfectly contiguous. (A gap-compensation branch masked the bug
only when source in-points happened to be monotonically increasing.)

The correct attribute for timeline position is `offset`.

## Fix

Use `offset` (and the next clip's `offset`) throughout the check instead of
`start`.

## Test

`tests/test_validator.py::test_validator_sequential_uses_timeline_offset_not_source_start`
- builds a contiguous timeline whose clips come from non-monotonic source
in-points (60s, 10s, 90s) and asserts `clips_sequential` is True with no
sequential warnings.

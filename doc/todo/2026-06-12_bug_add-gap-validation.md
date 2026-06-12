# BUG: add_gap accepts zero/negative durations

**Date found:** 2026-06-12
**Classification:** bug (missing input validation)
**Status:** FIXED on branch `fix/bug-hardening` (TDD)

## Where

`src/steele_fcpxml/builder.py` - `FCPXML.add_gap`.

## What

`add_clip` validates its duration (`> 0`), but `add_gap` did not. A call like
`add_gap(0.0)` or `add_gap(-5.0)` was accepted, producing a degenerate or
negative-length gap and a malformed timeline, with no error to the caller.

## Fix

Validate `duration > 0` in `add_gap`, raising
`ValueError("duration must be > 0, got ...")` to match `add_clip`.

## Tests

`tests/test_builder.py::test_add_gap_rejects_zero_duration`,
`tests/test_builder.py::test_add_gap_rejects_negative_duration`.

# BUG: sequence duration drifts a frame from the spine content

**Date found:** 2026-06-12
**Classification:** bug (correctness, rounding)
**Status:** FIXED on branch `fix/bug-hardening` (TDD)

## Where

`src/steele_fcpxml/writer.py` - the `# Sequence` block.

## What

The sequence `duration` was computed as `seconds_to_rational(sum_of_item_seconds)`
(sum-then-round), while each spine item's duration is rounded to whole frames
independently (round-then-sum). With fractional-second durations these
disagree. Example: two 0.5s clips at 25 fps each round to 12 frames
(`round(12.5) -> 12`), so the spine holds 24 frames but the sequence claimed
25 (1.0s) - a one-frame phantom tail on the timeline.

## Fix

Compute the sequence total from the same per-item frame rounding the spine
uses: `total_frames = sum(round(item.duration * fps))`, then emit
`{total_frames * den}/{num}s`.

## Test

`tests/test_writer.py::test_sequence_duration_matches_spine_content` -
asserts the sequence duration equals the summed spine item durations.

# BUG: CLI `--json` always emits an empty `info` object

**Date found:** 2026-06-12
**Classification:** bug (correctness, dead filter condition)
**Status:** awaiting upstream decision (default: fix)
**Upstream question:** `doc/prompts/responses/questions/2026-06-12-cli-json-info-empty.md`

## Where

Upstream source:
`/Users/salimfadhley/workspace/mind_of_steele/src/mind_of_steele/fcpxml_validator/main.py`
lines 60-73 (will land in `src/steele_fcpxml/cli.py`).

## What

The `--json` branch filters info values with
`if not isinstance(v, (list, object))`. Every value is an instance of
`object`, so the condition is always False and the `info` dict is always
emitted empty. None of the real validation metadata (version, asset/clip
counts, format details) ever reaches the JSON output. Intended behaviour was
presumably to exclude only the non-serializable lists (e.g. `clips` list of
`ClipInfo`).

## Fix (planned default)

Include scalar info values (str / int / float / bool / None) and exclude the
non-serializable lists. Add a test asserting `--json` output contains
`fcpxml_version` and the count fields.

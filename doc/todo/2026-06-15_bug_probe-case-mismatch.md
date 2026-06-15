# BUG: probe accepts wrong-case paths, breaking Resolve export

**Date found:** 2026-06-15 (reported by upstream `mind_of_steele` LLM)
**Classification:** bug (correctness, production export failure)
**Status:** FIXED on branch `fix/probe-case-mismatch` (TDD), strict mode
**Question:** `doc/prompts/responses/questions/2026-06-15-probe-case-mismatch-strict.md`

## What

On case-insensitive filesystems (macOS APFS default, SMB/NAS mounts),
`Path.exists()` returns True for a path whose case does not byte-match the
real file, and `Path.resolve()` does not fold case. A wrong-case path
(`foo.mp4` for an on-disk `foo.MP4`) therefore probed fine and was written
verbatim into `<media-rep src=...>`. DaVinci Resolve's export resolver is
case-strict and rejected the clip - the clip *played* in the editor but could
not be *exported*.

## Fix

`src/steele_fcpxml/probe.py`: new `_canonical_case()` reads the parent
directory and returns the real on-disk name (with a comment explaining why
`exists()` is insufficient). `_probe_video` now raises `FileNotFoundError`
(strict, no auto-correct, no warning) when the supplied filename casing does
not byte-match disk, naming both casings so the caller can fix the call site.
A genuinely missing file still raises plain `FileNotFoundError`.

## Tests

`tests/test_probe.py`:
- `test_probe_raises_on_case_mismatch` (skips on case-sensitive FS)
- `test_probe_accepts_exact_case`
- `test_probe_missing_uses_filenotfounderror_not_case_error`

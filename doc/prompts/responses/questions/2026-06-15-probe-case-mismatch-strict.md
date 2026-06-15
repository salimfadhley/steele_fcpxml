# Probe accepts wrong-case paths and emits them into the FCPXML - raise instead

**Status:** library bug confirmed in production. Fix endorsed by the upstream
user. Mode: **strict (raise)**, no auto-correct, no warn-and-continue.
**Created:** 2026-06-15
**Slug:** probe-case-mismatch-strict

## Context

A real timeline produced by the upstream caller
(`mind_of_steele/scripts/build_mark_steele_catchphrases.py`) failed to export
in DaVinci Resolve. Resolve reported, per clip:

```
Unable to export timeline video clip because it is not associated with
valid or supported source media: 13100022-001 Alec Defty 1:49
```

Initial guess was a codec issue. It is not. Root cause is a **path case
mismatch** that the library never detected:

- Files on disk: `13100022-001 Alec Defty.MP4` (uppercase extension - they
  are camera-original Sony files).
- Path passed to `FCPXML.add_clip(...)`: `.../13100022-001 Alec Defty.mp4`
  (lowercase). The caller used a hard-coded list of lowercase extensions
  (`(".mp4", ".m4v", ".mov", ".mkv", ".webm")`) and trusted `Path.exists()`
  to vet the candidate. On macOS APFS and on the SMB mount to the Synology
  NAS, `exists()` is case-insensitive at the `open(2)` layer, so the
  lowercase candidate "exists" as far as Python can tell.
- Resulting FCPXML `<media-rep src="...%20Alec%20Defty.mp4" />` (lowercase).
- Resolve's FCPXML importer parses the URI before passing it to the OS and
  does NOT fold case; or its export pipeline uses a stricter resolver than
  its preview pipeline. Either way, the clip plays in the editor but cannot
  be exported.

The library is doing exactly what the spec says and producing a
syntactically valid FCPXML. The bug is that it allowed a path through that
does not byte-match the on-disk filename, and that mismatch only manifests
at NLE-export time, which is the worst possible place to discover it.

## Where in the code

`src/steele_fcpxml/probe.py` lines 84-104 (`_probe_video`). The relevant
sequence:

```python
resolved = video_path.resolve()
if resolved in _ffprobe_cache:
    return _ffprobe_cache[resolved]

if not resolved.exists():
    raise FileNotFoundError(f"Video file not found: {resolved}")

# ... ffprobe is then run on resolved
```

All three of `resolve()`, `exists()`, and the subsequent `ffprobe` succeed
silently for a wrong-case path on macOS/SMB. `Path.resolve()` does NOT
canonicalize case on case-insensitive filesystems; it returns whatever case
the caller passed, just made absolute.

The wrong-case `Path` is then stored on the resulting `VideoInfo` and
propagated to `writer.py`, which writes it into the `<media-rep src=...>`
element verbatim (URL-encoded).

## Specific change requested

Add a strict case check inside `_probe_video` before ffprobing. Roughly:

```python
def _canonical_case(path: Path) -> Path | None:
    """Return path with on-disk casing, or None if no case-folded match exists."""
    parent = path.parent
    target = path.name.casefold()
    try:
        for child in parent.iterdir():
            if child.name.casefold() == target:
                return parent / child.name
    except (FileNotFoundError, NotADirectoryError, PermissionError):
        return None
    return None


def _probe_video(video_path: Path) -> VideoInfo:
    resolved = video_path.resolve()
    if resolved in _ffprobe_cache:
        return _ffprobe_cache[resolved]

    on_disk = _canonical_case(resolved)
    if on_disk is None:
        raise FileNotFoundError(f"Video file not found: {resolved}")
    if on_disk.name != resolved.name:
        raise FileNotFoundError(
            f"Path case mismatch: caller passed {resolved.name!r} but the "
            f"file on disk is {on_disk.name!r}. The FCPXML would emit the "
            f"caller-supplied case and downstream tools (e.g. DaVinci Resolve) "
            f"may reject it. Fix the path at the call site."
        )

    # ... rest of probe unchanged, ffprobing `resolved` (now known to match disk)
```

Key behaviour to preserve:

- `FileNotFoundError` (not a new exception type, not a warning) - matches the
  user's stated preference for strict failure. The library's contract becomes
  "the path you give me must byte-match disk; if it doesn't, I refuse."
- The error message must name both the supplied case AND the on-disk case,
  so the caller can fix their code immediately without re-running probe
  manually.
- The check must be a no-op on case-sensitive filesystems (Linux, macOS APFS
  case-sensitive variant): if the caller passes `foo.MP4` and that exact
  name is in the directory listing, `casefold()` matches and `on_disk.name
  == resolved.name`, so we proceed normally. No platform-specific code.
- Do not auto-correct. The user explicitly rejected silent fix-up. The point
  of strict mode is that callers fix their code, not that the library covers
  for them.

Cache behaviour: do NOT cache on `FileNotFoundError`. The current code caches
only successful probes (line 169), so this is already correct - just make
sure the new error path does not insert into `_ffprobe_cache`.

## Tests to add

In `tests/test_probe.py` (or wherever probe tests live):

1. **`test_probe_raises_on_case_mismatch`** - create a real fixture file in a
   `tmp_path` with a known case (e.g. `Sample.MP4`). Call `_probe_video`
   with the lowercase variant (`sample.mp4`). Assert it raises
   `FileNotFoundError` and that the message contains both `'Sample.MP4'`
   and `'sample.mp4'`. Mark `pytest.mark.skipif` if the test filesystem is
   case-sensitive (detect by writing one file and checking whether a
   different-case `.exists()` returns True).

2. **`test_probe_accepts_exact_case`** - same fixture, call with exact
   on-disk case. Assert probe succeeds (will need ffprobe mocked or a real
   tiny fixture in `tests/fixtures/`).

3. **`test_probe_raises_filenotfounderror_when_missing`** - regression for the
   existing behaviour. A path whose case-folded name does not match
   anything in the parent directory should still raise `FileNotFoundError`,
   not the new "case mismatch" error.

The first test is the load-bearing one; if the directory scan finds nothing
matching case-folded (file truly missing) the new code must still raise
`FileNotFoundError` for backward compatibility.

## What I plan to do if I get no answer

Implement exactly as specified above. The user has explicitly endorsed
strict mode in conversation:

> 3, this is a library bug. Strict error handling will be less of a hassle
> in the long run.

So I will not wait for further sign-off. The only reason I'm filing this as
a question rather than just making the change is that I want you (the
upstream LLM) to know the production incident this fixes, in case anything
else in the broader pipeline also needs touching.

## Out of scope

- Fixing the upstream caller's bug in
  `build_mark_steele_catchphrases.py:138-150`. That is a separate fix in
  `mind_of_steele` and the upstream LLM is handling it.
- Adding case-folding tolerance for *path components above the filename*
  (e.g. `foo/Bar/baz.mp4` vs `foo/bar/baz.mp4` directory case). The
  observed bug is filename-only; broaden if you find evidence the directory
  parts can also mismatch in practice.
- Auto-correction. The user explicitly rejected this.
- Logging or warnings. The user explicitly rejected non-fatal modes.

## Cross-reference

- Upstream conversation log: 2026-06-15.
- Affected FCPXML: `/Volumes/Home/research/flerfs/mark_steele/fcpxml/gateshead_council.fcpxml`.
- Affected source folder: `/Volumes/Home/research/flerfs/mark_steele/alec_defty_mark_steele_interview/`.
- All Alec Defty `.MP4` files in that folder are camera-original Sony pro-camera
  recordings with PCM audio + timecode data track. Those characteristics are
  red herrings for the bug under report - the case mismatch alone is sufficient
  to break export, regardless of codec.

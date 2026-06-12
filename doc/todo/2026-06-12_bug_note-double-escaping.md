# BUG: Writer double-escapes clip `<note>` text

**Date found:** 2026-06-12
**Classification:** bug (correctness, latent - not caught by existing tests)
**Status:** awaiting upstream decision (default: fix)
**Upstream question:** `doc/prompts/responses/questions/2026-06-12-note-double-escaping.md`

## Where

Upstream source:
`/Users/salimfadhley/workspace/mind_of_steele/src/mind_of_steele/timeline_generators/fcpxml_helper.py`
lines 846-857 (will land in `src/steele_fcpxml/writer.py`).

## What

The writer manually XML-escapes the note text (`&` -> `&amp;`, `<` -> `&lt;`,
`>` -> `&gt;`) and then assigns the result to an ElementTree element's
`.text`. ElementTree escapes `.text` again on serialization, so a note
containing `Tom & Jerry` is written as `Tom &amp;amp; Jerry` and displays in
Resolve as the literal `Tom &amp; Jerry`.

Not caught by tests because every note under test is plain ASCII with no
special characters.

## Fix (planned default)

Remove the manual `.replace()` escaping and let ElementTree handle escaping.
Add a regression test that a note containing `A & B < C > D` round-trips
exactly. Changes real output only for notes with special characters.

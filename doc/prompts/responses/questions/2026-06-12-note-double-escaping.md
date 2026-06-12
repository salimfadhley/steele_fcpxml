# Writer double-escapes clip <note> text - port the bug or fix it?

**Status:** blocking the writer port (I need to choose faithful-port vs fix)
**Created:** 2026-06-12
**Slug:** note-double-escaping

## Context

Porting the writer from
`/Users/salimfadhley/workspace/mind_of_steele/src/mind_of_steele/timeline_generators/fcpxml_helper.py`.

At lines 846-857 the writer manually XML-escapes the clip note text and then
assigns it to an ElementTree element's `.text`:

```python
escaped = (
    note_text.replace("&", "&amp;")
    .replace("<", "&lt;")
    .replace(">", "&gt;")
)
note_el = ET.SubElement(clip_el, "note")
note_el.text = escaped
```

The problem: ElementTree **also** escapes special characters when it
serializes `.text`. So a note containing `Tom & Jerry` is first turned into
`Tom &amp; Jerry` by the manual `.replace()`, and then ET escapes the `&` in
`&amp;` again on write, producing `Tom &amp;amp; Jerry` in the file. DaVinci
Resolve would display the literal text `Tom &amp; Jerry`, not `Tom & Jerry`.
The same double-escaping hits `<` and `>`.

The existing tests never catch this because every note under test uses plain
text with no `&`, `<`, or `>` (`test_writer_emits_note` uses "Custom note";
`test_writer_auto_generates_note_from_timecodes` uses timecodes). The
auto-generated `Source: HH:MM:SS - HH:MM:SS` notes also never contain special
characters, so in normal operation the bug is invisible.

## Specific question

Two things only you can answer from production history:

1. Do any real timelines you have generated pass a `note=` (or clip `name`)
   containing `&`, `<`, or `>`? If notes were always plain ASCII timecode
   strings, this bug has never actually fired and fixing it is risk-free.
2. Was the manual `.replace()` escaping added deliberately to work around some
   ElementTree or Resolve quirk (e.g. a Resolve version that did *not*
   auto-escape, or a path where the text was written raw rather than via ET)?
   I want to be sure I'm not removing a workaround that mattered.

## What I plan to do if I get no answer

Remove the manual `.replace()` escaping and let ElementTree handle escaping
(the correct, idiomatic behaviour), since ET already escapes `.text` on
serialization. I will add a regression test that a note containing
`A & B < C > D` round-trips to exactly `A & B < C > D` when re-parsed. This
changes output only for notes containing special characters - which, if your
answer to (1) is "always plain text", means no real timeline output changes.

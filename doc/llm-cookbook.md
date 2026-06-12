# LLM cookbook

This document is for the LLM working alongside a video editor. It is a menu of workflow patterns - each one a way to combine *search* (which LLMs are good at) with *assembly* (which this library does) and *refinement* (which the human editor does in their NLE).

For background on the pipeline these patterns sit inside, see [`ecosystem.md`](ecosystem.md). For the library API, see [`usage.md`](usage.md).

The patterns are sized from "trivial" to "ambitious". Pick one. Mix several. They are not orthogonal - real workflows usually combine three or four.

## The shape of every pattern

The user gives you a research request in natural language. You produce a Python script that calls this library. The script is the deliverable - not text, not a list, not a description. **A file the editor can run.**

```python
from pathlib import Path
from steele_fcpxml import FCPXML, FrameRate, tc

builder = FCPXML("<project>", "<descriptive-name>", timeline_fps=FrameRate.FPS_25)
# ... add_clip calls ...
builder.write(Path("<output>.fcpxml"))
```

Everything else is variation.

## Pattern A: catchphrase supercut

**When:** the user wants every instance of a specific phrase across an archive.

**User asks:** *"Build me a compilation of every time figure X says 'make no mistake about it'."*

**You do:**

1. Search the transcript index (ElasticSearch, sqlite-fts, grep, whatever the project uses) for the phrase.
2. For each hit, look up the source video file and the `start`/`end` timestamps of the matching cue.
3. Pad each clip wider than the cue itself - 0.4s head, 0.6s tail by convention.
4. Emit the FCPXML.

```python
for video_path, start, end, cue_text in search_results:
    builder.add_clip(
        Path(video_path),
        in_point=max(0.0, start - 0.4),
        out_point=end + 0.6,
        name=f"{Path(video_path).stem[:40]} {int(start//60)}:{int(start%60):02d}",
        note=cue_text,
    )
```

**Tip:** if the phrase has variants ("make no mistake", "make no mistakes about it"), match the union and dedup overlapping cues from the same source. The user will be more pleased with 60 quality hits than 200 hits where half are duplicates.

## Pattern B: topic montage

**When:** the user wants every appearance of a *topic*, not a specific phrase. Multiple search terms point at the same idea.

**User asks:** *"Find me every time anybody discusses subject X across the archive."*

**You do:**

1. Brainstorm related phrasings of the topic. *"vaccines"* might also be *"the jab"*, *"the shot"*, *"the vax"*.
2. Run each search; merge the hits; deduplicate by `(video_path, ±5 seconds of overlap)`.
3. Optionally, hand the deduplicated candidate list back to the user before building, e.g. *"I found 142 candidates across 38 videos - shall I assemble all of them, or filter by channel first?"*
4. Build the FCPXML.

**Tip:** add a `section=` label on each clip indicating which subtopic it matched (`section="jab"`, `section="vaccine schedule"`) - useful for the editor when they want to group clips by sub-theme.

## Pattern C: cross-source comparison

**When:** the user wants to juxtapose two or more sources on the same topic.

**User asks:** *"Werner says X about banks creating money. Goldberg says Y about the same thing. Find me clips of each, alternating, so the contrast is visible."*

**You do:**

1. Search Werner's content for hits on the topic. Pull the strongest 4-6.
2. Search Goldberg's content. Pull the strongest 4-6.
3. Interleave them on the timeline.
4. Add markers between sections so the editor can find the structural breaks.

```python
builder.add_marker("Werner block 1")
for video, start, end, cue in werner_hits[:3]:
    builder.add_clip(...)

builder.add_marker("Goldberg block 1")
for video, start, end, cue in goldberg_hits[:3]:
    builder.add_clip(...)

builder.add_marker("Werner block 2")
# ...
```

**Tip:** the editor will probably want to add narration between the blocks - leave a `add_gap(3.0, name="Narration")` between sections so there is a working hole.

## Pattern D: pre-trimmed scaffold

**When:** the user wants a *starting surface*, not a final cut. They expect to trim aggressively in the NLE.

**User asks:** *"Give me a working timeline of the best moments from this 3-hour interview."*

**You do:**

1. Pick 20-30 moments rather than trying to find the perfect 8.
2. Pad each clip *wider* than usual - 2 seconds lead and tail rather than 0.4 / 0.6.
3. Name them with rich context so the editor can navigate quickly.

```python
builder.add_clip(
    Path(interview),
    in_point=max(0.0, start - 2.0),
    out_point=end + 2.0,
    name=f"WIDE {start:.0f}s :: {topic_tag}",
    note=cue_text,
)
```

**Tip:** errors here are forgiven - the editor will trim. Bias toward including a clip and letting them delete it, rather than excluding and forcing them to re-search.

## Pattern E: b-roll selection around narration

**When:** the editor has a narration track and needs visual coverage for specific moments.

**User asks:** *"At 0:15 I'm talking about cars; at 0:32 I'm talking about Glastonbury; find me b-roll for each."*

**You do:**

1. Search the archive for moments matching each visual topic.
2. Pick the best 3-5 candidates per topic.
3. Place them on the timeline at the narration anchor positions, with markers so the editor sees which clip is meant for which moment.

```python
builder.add_marker("0:15 - cars")
for clip in car_brolls[:5]:
    builder.add_clip(..., name=f"BROLL-CAR {clip.stem[:30]}")

builder.add_marker("0:32 - Glastonbury")
for clip in glasto_brolls[:5]:
    builder.add_clip(..., name=f"BROLL-GLASTO {clip.stem[:30]}")
```

**Tip:** the editor will pick *one* per group and delete the rest. Make the `name` prefixes consistent so the editor can find them all in the NLE bin search.

## Pattern F: iterative refinement (Round 1 / Round 2)

**When:** the first attempt produces too many clips, or the wrong ones. Treat the FCPXML as a draft.

**User asks (Round 1):** *"Build me a compilation of X."*

**You do:** make the FCPXML, hand it over.

**User comes back:** *"Too many - just the first 30 seconds of each is enough."* Or: *"Drop everything from before 2025."* Or: *"Only this channel."*

**You do (Round 2):** rerun the same script with the filter applied. New FCPXML.

```python
# Round 2 example: limit each clip to first 30s, drop pre-2025
filtered = [
    (v, s, min(e, s + 30.0), t)
    for (v, s, e, t) in search_results
    if path_year(v) >= 2025
]
```

**Tip:** keep the search and the assembly in two cleanly separated functions. Round 2 only changes the filter step. The editor never opens the Python - but you can iterate the file in seconds without changing the rest of the pipeline.

## Pattern G: validation gate

**When:** you are producing FCPXMLs in a pipeline or CI job. You want to catch broken output before the editor opens it.

**You do:**

```python
from steele_fcpxml.validator import FCPXMLValidator

out = builder.write(Path("/edit/compilation.fcpxml"))
result = FCPXMLValidator(out).validate()
if not result.valid:
    raise RuntimeError(f"Generated FCPXML failed validation: {result.errors}")
```

Or, in shell:

```bash
steele-fcpxml validate /edit/compilation.fcpxml || exit 1
```

**Tip:** the validator catches missing media references - which means it tells you when the editor's machine *cannot reach the source files*. Saves a frustrated "media offline" message in the NLE.

## Pattern H: A/B variants from a shared base

**When:** the user wants to test two intros against the same body, or two endings against the same setup.

**You do:**

```python
base = build_body()           # FCPXML with body clips
intro_a = base.fork()
intro_b = base.fork()

intro_a.add_clip(intro_clip_a, ...).write(Path("ep_intro_a.fcpxml"))
intro_b.add_clip(intro_clip_b, ...).write(Path("ep_intro_b.fcpxml"))
```

`fork()` is a deep copy. The base never mutates - safe to make any number of variants.

**Tip:** name the output files in a way that survives sorting. `ep_2026-06-12_intro_a.fcpxml` beats `intro_a.fcpxml` once the editor has 30 of them.

## Pattern I: catchphrase atlas (multi-target)

**When:** the user wants to see one person's "voice signature" by compiling several catchphrases at once.

**You do:**

1. Pre-compute the catchphrase list (an n-gram analysis against a background corpus typically surfaces the over-represented phrases).
2. For each catchphrase, build a separate FCPXML.
3. Hand the editor a directory of FCPXMLs - they import the ones they want.

```python
for phrase, needles in catchphrases.items():
    cues = search_for_phrase(needles)
    builder = FCPXML("Subject X", phrase, timeline_fps=FrameRate.FPS_25)
    for video, s, e, t in cues:
        builder.add_clip(Path(video), in_point=s-0.4, out_point=e+0.6, name=..., note=t)
    builder.write(out_dir / f"{slugify(phrase)}.fcpxml")
```

This was the original use case for the library. It scales to dozens of compilations in seconds.

## Pattern J: timeline annotation pass

**When:** the editor has *already cut* a sequence and wants you to annotate it with research notes.

**You do:** generate a *parallel* FCPXML at the same length as theirs, but with markers at the moments of interest. The editor imports it as a second track for reference.

```python
builder = FCPXML("Episode 162", "Annotations", timeline_fps=FrameRate.FPS_25)
# Tiny invisible "gap" clips of the right length, with markers at key points
for offset, note in annotations:
    builder.add_gap(offset - previous_offset)
    builder.add_marker(note)
    previous_offset = offset
builder.write(out)
```

**Tip:** this pattern is less common than the others but extremely useful for fact-checking - you give the editor a marked-up reference track they can scrub through.

## Things to avoid

- **Don't commit to a final cut.** Your output is a *starting surface*. The editor knows what they want better than you do; your job is to save them research time, not to make creative decisions.
- **Don't strip context from the `note` field.** The editor wants to know *why* this clip is here. Put the matching transcript text in the note. Add the section / topic tag in the name. Make the timeline self-documenting.
- **Don't generate huge timelines silently.** If your search returns 800 hits, tell the human before building - ask whether they want all 800 or a sample.
- **Don't pad too tight.** 0.4 / 0.6 lead / tail is the conservative default. The editor can always trim; they cannot easily *extend* a clip past where you cut it.
- **Don't shell out to the NLE.** Stop at the FCPXML file. The editor opens it themselves. Auto-launching DaVinci is a footgun across different setups.

## A reasonable default skeleton

When in doubt, this is a defensible starting template:

```python
"""Generate <description> as an FCPXML for the editor.

Usage:
    uv run python <this_file>.py
Output:
    <output_path>
"""
from pathlib import Path
from steele_fcpxml import FCPXML, FrameRate

SEARCH_RESULTS = [
    # (video_path, start_seconds, end_seconds, cue_text)
    # populated by your discovery step
]

HEAD_PAD = 0.4
TAIL_PAD = 0.6
TIMELINE_FPS = FrameRate.FPS_25

OUTPUT = Path("/edit/<descriptive_name>.fcpxml")


def main() -> None:
    builder = FCPXML(
        event_name="<project>",
        project_name="<descriptive>",
        timeline_fps=TIMELINE_FPS,
    )
    for video, start, end, cue in SEARCH_RESULTS:
        builder.add_clip(
            Path(video),
            in_point=max(0.0, start - HEAD_PAD),
            out_point=end + TAIL_PAD,
            name=f"{Path(video).stem[:40]} {int(start//60)}:{int(start%60):02d}",
            note=cue,
        )
    out = builder.write(OUTPUT)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
```

Hand the editor *this* and the search results as data, and they can re-run it with any filter or padding they want without your involvement.

## Want a new pattern?

If you find yourself doing something repeatable that is not in this list, write it up as a new section and add it to this file. The patterns above are not the universe - they are the ones our team has found valuable. Yours will be different.

# Ecosystem: where this library fits

`steele-fcpxml` is one stage in a longer pipeline. This document explains the pipeline, the open-source tools we use at each stage, and why the FCPXML generation stage exists at all.

## The problem

A modern long-form video editor sits on top of an archive that no human can search by hand.

A working figure for context: the project that gave birth to this library has **4,600+ archived YouTube videos**, around **2 TB**, **133 million words of transcript text**. The editor's day job is to make essays *about* this archive. A typical research request from the editor sounds like:

- "Show me every time figure X claims that vaccines cause autism."
- "Build me a compilation of every appearance of phrase Y across these three channels."
- "Find me all the moments where person Z mentions topic W, and put them on a timeline."
- "Anybody discuss subject X across the archive - assemble what you find."

The editor's NLE (DaVinci Resolve, in our case) is brilliant at *refining* a timeline but useless at *discovering* clips. The transcript and search tools are brilliant at finding moments but useless at the last-mile handoff to the NLE.

## The pipeline

```
 [1] Acquisition   [2] Transcription   [3] Indexing   [4] Discovery   [5] Assembly   [6] Refinement
 ──────────────    ────────────────    ────────────   ─────────────   ─────────────  ────────────────
   yt-dlp           Whisper /            ElasticSearch    LLM +          THIS          DaVinci Resolve
   ffmpeg           faster-whisper       (or sqlite-fts,  search          LIBRARY       Final Cut Pro
   camera ingest    Whisper.cpp          ripgrep, etc.)   tools                         Premiere
```

Each stage is independent. Each can be replaced. The only contract is the data shape that flows between them. This is what makes the system robust against tool churn - if `faster-whisper` becomes the better choice next year, you swap stage 2 without touching the others.

### Stage 1: acquisition

Source files arrive on a NAS. For our archive:

- **`yt-dlp`** for YouTube, Facebook reels, BitChute, Rumble. Always download mp4+m4a (AAC audio) - Resolve cannot decode `opus`.
- **`ffmpeg`** for format conversion when something arrives in webm/mkv with opus audio.
- Hard links into curated "collection" directories. No copies. The 2 TB archive lives once on disk; topical collections are zero-cost views.

This stage produces files on disk and not much else.

### Stage 2: transcription

Every video file gets a sidecar `.en.srt` and (in our flavour) a `.summary.txt` from an LLM.

- **`whisper.cpp`** / **`faster-whisper`** for the transcript - both are open, fast, and run locally.
- **GPT / Claude** to produce a structured summary alongside the raw transcript, including extracted topics, people mentioned, and key claims.

We use OpenAI's API for the summarisation step because it produces consistent structured JSON for thousands of files. You could do this entirely locally with a sufficiently large open-weights model.

After this stage, every video has timecoded text. That is the key unlock: the editor can now query *moments*, not files.

### Stage 3: indexing

A 4,600-video transcript pile is too big to grep usefully. We use **ElasticSearch** because it gives us:

- Full-text search across transcripts, summaries, titles, and metadata in one query.
- Field-aware queries (`summary.individuals.name: "Werner"`).
- Highlighting (snippets with the matching phrase in context).
- Aggregations (how many videos mention X by channel, by year).

For a smaller archive you can absolutely use **`sqlite-fts5`** or even `ripgrep` over the raw `.srt` files. The stage's *contract* is "given a query, return a list of `(video_path, start_seconds, end_seconds, cue_text)` matches". The implementation under that contract can swap.

### Stage 4: discovery

This is where an LLM does the work of a research assistant:

- The editor asks in natural language: *"Build me an FCPXML of every time the Mark Steele archive uses the phrase 'make no mistake about it'."*
- The LLM translates that to an ElasticSearch query, runs it, and gets back a list of matching cues with timestamps.
- The LLM may iterate - too many results, narrow by channel; too few, broaden the phrase; the editor sees a candidate list before any clips are cut.

This stage is *cheap and iterative*. The LLM can ask the editor "I found 230 matches across 14 channels - do you want all of them, or the 80 from the main channel only?" without committing to anything.

### Stage 5: assembly - **the gap this library fills**

This is the stage the rest of the ecosystem leaves unsolved.

Discovery produces a list of "the clip is here, between these timestamps". The NLE wants a timeline file with clips at those timestamps. The gap between those two representations is the *last mile* - and it has historically been filled by the human editor manually typing in/out points for every clip, 50, 100, 200 times.

`steele-fcpxml` is the bridge. The LLM (or any glue script) produces:

```python
from pathlib import Path
from steele_fcpxml import FCPXML, FrameRate

builder = FCPXML("Mark Steele", "make no mistake supercut", timeline_fps=FrameRate.FPS_25)
for video, start, end, cue in es_results:
    builder.add_clip(
        Path(video), in_point=start - 0.4, out_point=end + 0.6,
        name=f"{Path(video).stem[:30]} {start:.0f}s",
        note=cue,
    )
builder.write(Path("/edit/make_no_mistake.fcpxml"))
```

That `.fcpxml` opens in DaVinci with 80 pre-positioned clips. The editor never typed a timecode.

This is what we mean by "automate the tedious work and leave the creative work to the human". The LLM finds, this library assembles, the human edits.

### Stage 6: refinement

DaVinci Resolve / Final Cut Pro / Premiere does what it has always done well: cut, colour, mix, title. The pre-positioned clips from stage 5 are the *starting point*, not the answer. The editor lands in their NLE with a working timeline and can immediately:

- Trim around each cut (the library adds 0.4s lead / 0.6s tail by convention - the editor tightens or relaxes as they go).
- Reorder clips.
- Delete the ones that don't work.
- Layer music, narration, b-roll.

If the editor finds the assembly was wrong - "actually I wanted hits from this *other* channel" - they go back to the LLM, regenerate, re-import. Round-trip via Python source. The discovery query is just text in a script.

## Why the FCPXML stage matters

Without this library, the workflow breaks down in one of two ways:

1. **The editor does it manually.** 80 clips × 30 seconds per clip to find and trim = 40 minutes of clerical work *before* any creative decisions. The editor's flow is destroyed.
2. **The LLM hands over plain text.** "Use clip A from 1:23 to 1:35, then clip B from 4:02 to 4:18, ..." - the editor opens it in a text editor, opens the NLE, types every number in. Worse than option 1.

The bridge has to be a *file the NLE opens*. That file is FCPXML. The library exists because the alternative is awful.

## Patterns across our setup

A few patterns repeat in our use of this stack. They are likely useful in any setup that follows the same six-stage pipeline.

### The transcript is the source of truth for discovery

Everything searchable lives in transcript-shaped text: `.en.srt` for cues, summaries for high-level claims, ES for fast retrieval. Video metadata (titles, channels) goes in too, but the moment-by-moment data is text.

### Hard links, never copies

The base archive is huge (2 TB+). Topical collections live as hard links into a flat tree:

```
research/
  flerfs/                    <- the full archive
  conspiracy_theories/
    banking/
      01_werner_uk_radio.mp4 <- hard link, not a copy
      02_goldberg_clip.mp4   <- hard link
```

Hard links survive across SMB-mounted filesystems where symbolic links do not. `ls -lah` shows a link count of `2` when the link is in place.

### Pad clips wider than your final cut

In `add_clip` we pass `in_point - 0.4, out_point + 0.6` rather than the exact match boundaries. Reasons:

- Whisper timestamps are accurate to about half a second.
- Cuts on the exact boundary feel rushed.
- The editor can always trim *in*, never *out*.

The default values are conventions - tune per project.

### Notes carry the source transcript text

We pass the matching cue text into `note=` on every clip. In DaVinci, that text shows in the clip inspector. The editor sees *why the LLM picked this clip* and can sanity-check before cutting.

### Validate FCPXML in CI

Generated `.fcpxml` files go through `steele-fcpxml validate` before being committed or handed to the editor. Catches missing media references, malformed structure, version drift. Five-second check, saves a "Media Offline" surprise in Resolve.

## Open-source neighbours

The library plays well with:

- **`yt-dlp`** (acquisition) - https://github.com/yt-dlp/yt-dlp
- **`ffmpeg`** / **`ffprobe`** (encoding, frame-rate detection) - https://ffmpeg.org/. This library shells out to `ffprobe` at every clip add.
- **`whisper.cpp`** / **`faster-whisper`** (transcription) - https://github.com/ggerganov/whisper.cpp / https://github.com/SYSTRAN/faster-whisper
- **ElasticSearch** (indexing) - https://www.elastic.co/. Apache-licensed core via OpenSearch.
- **DaVinci Resolve** (refinement) - free version is sufficient; the FCPXML import is identical to the paid Studio version.
- **OpenTimelineIO** (alternative timeline format with FCPXML adapters) - https://opentimelineio.readthedocs.io/. Useful when you need to inter-operate with other formats.

The library is GPL-3-or-later, deliberately copyleft, on the theory that improvements to the bridge-between-LLM-and-NLE should flow back to the community.

## What to read next

- [`usage.md`](usage.md) - hands-on guide to the library API itself.
- [`llm-cookbook.md`](llm-cookbook.md) - menu of LLM+Human workflow patterns inspired by this ecosystem.

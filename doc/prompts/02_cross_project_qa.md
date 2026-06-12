# 02 - Cross-project Q&A protocol

You will hit questions the upstream code cannot answer on its own:

- Why does the writer set `audioLayout="stereo"` unconditionally?
- Was the v1 facade ever needed by callers we should worry about, or is dropping it definitely safe?
- Has anyone tested this with FCPXML v1.10 or v1.11, or is `version="1.9"` load-bearing for Resolve compatibility?
- Why does `_common_ancestor` exist - what does the library location attribute actually need to point to?

These are exactly the questions where the upstream LLM has context that doesn't live in any file. Use the protocol below to ask.

## The protocol

### 1. Where you write

Put each question as a self-contained Markdown file under:

```
doc/prompts/responses/questions/YYYY-MM-DD-<slug>.md
```

Examples:
- `2026-06-12-resolve-fcpxml-version-lock.md`
- `2026-06-12-stereo-audio-default.md`
- `2026-06-12-rename-resolve-writer.md`

One question (or one tightly-related cluster) per file. Don't batch ten unrelated questions into one mega-file - it makes routing slow and the answers harder to find later.

### 2. Where you read replies

Answers come back in:

```
doc/prompts/responses/answers/YYYY-MM-DD-<slug>.md
```

Same slug as the question. So `2026-06-12-resolve-fcpxml-version-lock.md` in `questions/` is answered by `2026-06-12-resolve-fcpxml-version-lock.md` in `answers/`. This makes pairing them trivial.

### 3. How to alert the human

The upstream LLM does not poll your repository. After you write a question file, tell Sal:

> "I've left a question for the upstream LLM at `doc/prompts/responses/questions/2026-06-12-stereo-audio-default.md`."

Sal will hand the question to the upstream session. The reply lands as a new file in `doc/prompts/responses/answers/` (Sal will commit or paste it in).

If you have multiple questions you can write them all, then send Sal one message listing all the filenames at once.

## How to write a good question

The upstream LLM has full context on `mind_of_steele` but does not have your in-progress port loaded in its head. So make each question stand on its own. Specifically:

- **Cite by absolute path and line number.** "Why does `fcpxml_helper.py:765` set `audioLayout='stereo'` always, regardless of source?" - not "in the writer, the audio attribute is hardcoded".
- **State what you've already established.** "I have ported the writer module. The `audioLayout="stereo"` attribute on the `<sequence>` element appears to be unconditional. I checked git log and could not find when it was added."
- **State the decision you need.** "Should the new package emit `audioLayout` based on probed source audio channels, or preserve the hardcoded stereo default?"
- **Note the blocker level.** "Blocking the writer port" vs. "Curious, not blocking" - so the upstream LLM knows whether to answer in detail or in one line.

A good question template:

```markdown
# <one-line headline question>

**Status:** blocking / curious / cleanup
**Created:** YYYY-MM-DD
**Slug:** <same as filename>

## Context

What I'm working on, what I've already established, where I'm stuck.

## Specific question

The thing I need answered, phrased so the upstream LLM can answer it without
re-reading the whole codebase.

## What I plan to do if I get no answer

So the upstream LLM knows the default - they only need to reply if they
want to override it.
```

The "what I'll do if I get no answer" line is the most valuable - it means questions never block you. If the answer never comes, you've already declared your default; proceed with that.

## Things the upstream LLM is good at answering

- "Why was X done this way?" - design history.
- "Is Y still used anywhere in the upstream codebase?" - they can grep `mind_of_steele/`.
- "Does any current upstream caller depend on Z behaviour?" - they can grep callers.
- "What does DaVinci Resolve do when this attribute is missing?" - they have observed Resolve behaviour over many real FCPXML files.

## Things the upstream LLM is NOT good at answering

- "How should this code be structured?" - that's your call. You're the one looking at it now.
- "Is this Python idiomatic?" - again, your call.
- "What should the package be named?" - check with Sal directly.
- General Python language questions - just answer from your own knowledge.

The upstream LLM is the historian and the production-context oracle. Don't use it as a code reviewer or a generic Python assistant.

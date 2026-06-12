# CLAUDE.md

This file is for the LLM working in the `steele_fcpxml` repository.

## What this project is

`steele-fcpxml` is a standalone Python library for generating Final Cut Pro XML (FCPXML) timelines. It is being extracted from a larger private project, `mind_of_steele`, where the FCPXML code grew up as one module among many.

This is the **public, GPL-3 copyleft** version. The goal is a small, focused package on PyPI that video editors (and the LLMs that work alongside them) can pip-install without pulling in any of `mind_of_steele`'s domain-specific scaffolding.

## Current state

The repository is a fresh scaffold. The source code and tests are **not yet copied in** - that is the first job. See [`doc/prompts/`](doc/prompts/) for the porting brief and the inventory of source files in the upstream project.

## How to work here

- **Python 3.12+.** Set in `pyproject.toml`.
- **Package manager:** `uv`. Always `uv run <cmd>`, `uv add <pkg>`, `uv sync`. Never `pip install` or `poetry`. The dev dependencies (`pytest`, `black`, `ruff`, `mypy`) are in the `dev` group.
- **Source layout:** `src/steele_fcpxml/` (importable as `steele_fcpxml`). Tests in `tests/`.
- **License:** GPL-3-or-later. Every new source file should be okay with that. Don't add code with incompatible licenses.
- **Style:** PEP 8, type hints on public functions and on non-trivial variables, f-strings, `pathlib.Path` (never bare strings for paths), `click` for any CLI work, absolute imports only.
- **No emojis in source files.** The validator's human-readable report uses a couple in its output, which is fine because it's runtime output, not source. Don't add new ones.
- **No git commits without the human's explicit say-so.** This is a strong project rule, mirrored from `mind_of_steele`. Make the changes, run the tests, then stop and ask.

## How to ask the upstream LLM questions

The LLM working in `mind_of_steele` (the source project) has the full context of how this code was used, what edge cases it handles, and why certain decisions were made. If you hit a question that the local files cannot answer:

1. Write your question as a markdown file in `doc/prompts/responses/questions/`. Use a clear filename: `YYYY-MM-DD-<short-slug>.md`.
2. Make the question self-contained. Cite specific file paths and line numbers in the upstream project where relevant.
3. Tell the human (Sal) you have left a question, and which file. They will route it to the upstream LLM.
4. The reply will land in `doc/prompts/responses/answers/` with the same slug.

See [`doc/prompts/02_cross_project_qa.md`](doc/prompts/02_cross_project_qa.md) for the full protocol, including how to phrase questions that the upstream LLM can answer without re-reading huge swathes of context.

## Common operations

```bash
# Setup (once)
uv sync

# Run tests
uv run pytest

# Format
uv run black src tests

# Lint
uv run ruff check src tests

# Type check
uv run mypy src

# Try the CLI (after the CLI module exists)
uv run steele-fcpxml validate <file.fcpxml>
```

## What not to do

- Don't depend on anything from `mind_of_steele`. The whole point of the extraction is that this is self-contained.
- Don't reach across to `/Volumes/Home/...` or any path on the upstream user's machine. The code should work for anyone who pip-installs the package.
- Don't add a second FCPXML API. The upstream code carried a legacy `FCPXMLBuilder` facade alongside the newer `FCPXML` fluent builder. Drop the legacy facade. Only port the v2 (`FCPXML`) API. The upstream LLM can confirm which classes that includes - see the porting brief.
- Keep the default test suite media-free. The unit tests must work with synthetic / mocked `ffprobe` output (mirror the pattern in `tests/conftest.py`) so they run fast and need no binaries. A small set of tiny, copyright-cleared, GPL-licensed fixture clips lives in `tests/fixtures/` for the *real*-`ffprobe` integration tests (`tests/test_probe_integration.py`), which skip automatically when `ffprobe` is absent. Don't add large media, and don't make the core suite depend on real video files.
- Don't pin runtime deps tighter than necessary. `click>=8.1` is the only runtime dep needed; nothing else from the upstream project should follow this code over.

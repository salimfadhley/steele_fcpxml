# 00 - Orientation: read this first

You are an LLM working in the `steele_fcpxml` repository. This file orients you on what's already done, what's left to do, and the overall shape of the work.

## Why we are doing this

The FCPXML timeline-generator code grew up inside a private project (`mind_of_steele`) where it has earned its keep building dozens of working DaVinci Resolve timelines from automated transcript searches. The code itself is small, stdlib-only at its core, and useful well beyond the show it was written for - any video editor working with an LLM assistant can use it to bridge the gap between "the LLM has identified the clips" and "the timeline is open in my NLE ready to refine".

The goal of this project is to **take that useful function and make it available to the public.**

Concretely, that means:

1. **Extract the code cleanly.** No upstream coupling, no domain leakage. A user pip-installs `steele-fcpxml` and gets a focused FCPXML builder, nothing else.
2. **Build a wheel on GitHub Actions.** Every push runs the test suite; tagged releases build a `.whl` and `.tar.gz` as workflow artifacts. The CI pipeline is itself an artifact of the project - it shows future contributors how to add or modify the build.
3. **Publish to PyPI** once the API has settled. The package name `steele-fcpxml` is already declared in `pyproject.toml`. Publication will use the standard PyPI trusted-publisher flow from GitHub Actions (no API tokens in the repo).
4. **Document the library for both humans and LLMs.** A video editor opening the README should learn what the package does and how to call it. An LLM working inside the package's user's project should be able to read the same documentation and synthesise correct Python source for the editor's exact compilation request. That dual audience shapes the docs: prose explanations of the use case, but also explicit input/output examples that an LLM can pattern-match against.

The license is **GPL-3-or-later**. Anyone who distributes a derivative must give downstream users the same freedoms. The library is small enough that this rarely bites real users (most callers will be Python scripts that import it - mere aggregation, not derivative work), but anyone embedding the code into a closed-source product will need to think about it. That is the intended chilling effect: keep improvements flowing back to the wider community of LLM-assisted editors.

## Who set this up

The scaffold (directory structure, `pyproject.toml`, `README.md`, `CLAUDE.md`, `LICENSE`, this prompt set) was set up by **the LLM working in the upstream `mind_of_steele` project**. 

The upstream project is here: /Users/salimfadhley/workspace/mind_of_steele

That LLM has full context on:

- How the FCPXML code grew up - which classes are load-bearing, which are vestigial, which edge cases matter
- Why specific design choices were made (e.g. Fraction-based timing, deterministic asset IDs, the v1 vs v2 split)
- What's been tested in production over months of real video editing for the upstream show
- Where the failure modes are (DaVinci Resolve quirks, ffprobe CSV column ordering, mixed frame rates)

That LLM is your point of contact. The protocol for asking it questions is in [`02_cross_project_qa.md`](02_cross_project_qa.md) - read that file before you go looking for context the local repository cannot provide.

## What's already in place

```
steele_fcpxml/
├── README.md              user-facing description + use case
├── CLAUDE.md              conventions for you, the LLM working here
├── LICENSE                GPL-3.0 full text
├── pyproject.toml         python>=3.12, uv-managed, click runtime dep, dev deps for pytest/black/ruff/mypy
├── .gitignore             standard Python + uv
├── src/steele_fcpxml/
│   └── __init__.py        empty placeholder
├── tests/
│   └── __init__.py        empty placeholder
└── doc/
    ├── prompts/
    │   ├── 00_orientation.md       this file
    │   ├── 01_porting_inventory.md sources to port + decisions to make
    │   ├── 02_cross_project_qa.md  how to ask the upstream LLM questions
    │   └── responses/              your Q&A workspace
    └── examples/                   examples go here (none yet)
```

You will add (these do not exist yet, you create them):

- `src/steele_fcpxml/*.py` - the ported source modules
- `tests/test_*.py` and `tests/conftest.py` - the ported tests
- `.github/workflows/ci.yml` - run tests, formatters, linters on every push
- `.github/workflows/release.yml` (or a job in ci.yml) - build wheels on tagged pushes
- `doc/usage.md` - human-oriented how-to with worked examples
- `doc/llm-cookbook.md` - copy-pasteable snippets for LLMs assisting video editors
- An expanded `README.md` quickstart referencing the new docs

`uv sync` will create a working venv with the dev tools, but `uv run pytest` will report no tests collected until you have ported things.

## What you need to do

In order:

1. **Read [`01_porting_inventory.md`](01_porting_inventory.md)** to see the exact list of source files in the upstream project, with absolute paths and notes on what to keep / drop / rename.
2. **Port the source code** from `mind_of_steele` into `src/steele_fcpxml/`. Split the monolithic upstream `fcpxml_helper.py` into logical submodules - the inventory file suggests a layout but you have judgement on the final shape.
3. **Port the tests** from `mind_of_steele` into `tests/`. Adapt imports. Drop tests for any code you decided not to port (e.g. the legacy v1 facade).
4. **Run the test suite.** `uv run pytest`. Iterate until green.
5. **Wire up the CLI entry point.** `pyproject.toml` already declares `steele-fcpxml = "steele_fcpxml.cli:main"`. After porting the validator CLI, `uv run steele-fcpxml validate <file>` should work.
6. **Sanity check the format.** Run `uv run black src tests`, `uv run ruff check src tests`, `uv run mypy src`. Fix what they flag.
7. **Add GitHub Actions CI.** A `.github/workflows/ci.yml` that, on every push and pull request, runs `uv sync`, `uv run pytest`, `uv run black --check`, `uv run ruff check`, and `uv run mypy`. The matrix should cover the supported Python versions (start with 3.12 and 3.13). Cache `~/.cache/uv` for speed.
8. **Add a wheel-build workflow.** A `.github/workflows/release.yml` (or extend `ci.yml`) that, on a tagged push (`v*`), runs `uv build` to produce `.whl` and `.tar.gz`, and uploads them as workflow artifacts. Do *not* publish to PyPI yet - that's a later step Sal will gate.
9. **Write documentation for both humans and LLMs.** Expand the README with a quickstart, an annotated example, and a short list of "common LLM prompts" that show how an editor's LLM should phrase requests to the library. Add `doc/usage.md` for the long-form how-to, and `doc/llm-cookbook.md` with copy-pasteable code snippets an LLM can adapt. Every public class and function gets a docstring with a worked example.
10. **Sanity check the format.** Re-run the formatters and linters after the doc additions.
11. **Stop. Do not commit.** Sal reviews everything before any commit lands. Do not push. Do not configure PyPI trusted publishing. Tell Sal it's ready for review.

## Important constraints

- **GPL-3 license** on every new source file you create. Headers are not required (the LICENSE file at the project root suffices), but be conscious of the copyleft direction.
- **uv only** for dependency management. Never `pip install`, never `poetry add`.
- **Python 3.12+** is the minimum. Use modern syntax freely (`X | None`, `dict[str, Y]`, `from __future__ import annotations` where helpful for forward refs).
- **No emojis in source files.** Existing validator output uses a couple - if you preserve that, fine; do not add new ones.
- **No upstream dependencies.** Do not import anything from `mind_of_steele.*`. Anything you need that lives only in the upstream project must be copied (and adapted) into this repo.
- **No paths from Sal's machine.** Tests and code must work for anyone who clones the repo. The upstream tests already do this via `monkeypatch` against `subprocess.run` - mirror the pattern.

## Tone for your work

The upstream code is good. It is small, focused, stdlib-only at the core, and battle-tested. You are not writing a new library - you are doing a careful, minimal extraction. Resist the urge to rewrite, refactor, "improve while you're here", or add features. Port faithfully; if you see something genuinely worth fixing, write it down in [`responses/questions/`](responses/) and ask before changing it.

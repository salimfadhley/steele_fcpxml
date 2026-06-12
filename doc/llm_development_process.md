# LLM-Assisted Development Process

**Status:** DRAFT — consolidated from 10 existing repo copies. Decisions marked ⏳ still pending.

This document describes the process used when developing features with LLM assistance. It applies to all work done with Claude Code, Codex, or any other LLM coding assistant.

---

## Process Overview

```
1. Requirement → 2. Dual Plans → 2.5 Plan Critique (optional) → 3. Synthesis →
4. Branch + Stub PIR → 5. Implement → 6. Verify → 7. Report → 8. Review → 9. Merge
```

**Key workflow rules:**

- **Explicit ordering required for implementation.** Making a plan or synthesising a plan MUST NOT automatically trigger implementation. Step 5 (Implement) only begins when the human explicitly orders it.
- **Review happens before merge.** You cannot meaningfully review code that is already merged. Review is a merge gate (Step 8), not a post-merge retrospective.
- **One question at a time.** When an LLM has multiple design or clarification questions, ask the most important one first and wait for the answer before asking the next. No lists of questions.

---

## Naming convention

Artefacts use a `<prefix>` that may be either:

- **A date** (ISO 8601, e.g. `20260424`) for ad-hoc work with no ticket
- **An issue number** (e.g. `598`) for ticketed work

---

## Step 1: Write a Requirement

**Location:** `doc/requirements/<prefix>_<title>.md`

The requirement describes **what** we want, not **how** to build it:

- `**From:**` / `**Date:**` metadata at the top (required for audit trail)
- `**Ticket:**` link (if ticketed), e.g. `[org/repo#35](https://...)`
- Background / context
- Numbered requirements (R1, R2, …)
- Non-goals (what we explicitly don't want)
- Success criteria (checkboxes)
- **Artefact Paths** section listing every file the feature will create or modify

The requirement is committed to `main` before planning begins.

---

## Step 2: Generate Dual Plans

Two LLMs independently produce implementation plans from the same requirement:

- **Claude plan:** `doc/plans/<prefix>_<title>/plan_claude_opus_4_6.md`
- **Codex plan:** `doc/plans/<prefix>_<title>/plan_codex.md`

Each plan describes **how** to implement the requirement:

- Phase summary table (what each phase delivers, how to validate)
- Detailed implementation steps with code examples
- Files to create/modify
- Testing strategy
- Verification checklist

**Single-plan fallback:** If only one LLM is available for this work, skip Step 2.5 and proceed to Step 3 using the single plan. Record in the synthesised plan that no dual-plan comparison was possible.

---

## Step 2.5: Plan Critique (optional)

A third LLM (e.g. Gemini) reviews both plans and produces a critique:

- `doc/plans/<prefix>_<title>/plan_critique.md`

The critique identifies gaps, duplicated effort, and unanswered questions in both plans. The human uses it as input to Step 3.

Skip this step unless a third LLM is available and the work is complex enough to justify the overhead.

---

## Step 3: Synthesise Plans

**⚠️ Do not auto-trigger.** Wait for explicit human instruction.

The human reviews both plans (and the critique if present) and identifies discrepancies. Each discrepancy is discussed **one at a time**. The human makes the final decision on each.

Synthesis checklist:

- [ ] All discrepancies identified
- [ ] Each discrepancy resolved with a documented decision
- [ ] All Artefact Paths reconciled
- [ ] Success criteria unchanged from the requirement
- [ ] Testing strategy agreed
- [ ] Deployment approach agreed

Result: `doc/plans/<prefix>_<title>/plan_synthesized.md`

This plan incorporates the best elements from both, with all design decisions explicitly recorded.

---

## Step 4: Create Branch and Stub PIR

Create the feature branch:

```
<prefix>_<short-slug>
```

**At the same time, create a stub post-implementation report:**

- `doc/post_implementation_report/<prefix>_<title>.md`

The stub contains only the section headers and `TODO` markers. This makes an unfinished PIR visible in the repo — if the author forgets to write the report, the empty file blocks the merge gate.

---

## Step 5: Implement

**⚠️ Do not auto-trigger.** Implementation only begins when the human explicitly orders it. Making or synthesising a plan is NOT implicit permission to implement.

Follow the synthesised plan. Deviations must be recorded in the PIR.

**Secrets handling:** Never hard-code credentials. All secrets go into AWS Secrets Manager following the path convention in CLAUDE.md. When a secret is added or moved, note it in the PIR.

**Read before write:** For any remote or shared configuration change (Jenkins `config.xml`, OneNote pages, REST endpoints), always GET the current state first, diff it against your intended change, then POST. Never assume the config is unchanged from a previous read.

---

## Step 6: Verify

Run the project's quality gates:

- Tests (unit, integration, regtest as applicable)
- Static checks (type checking, linting, format)
- Security analysis

The specific tools vary by repo — each repo's `AGENTS.md` should name its canonical gates.

---

## Step 7: Fill in the PIR

**Location:** `doc/post_implementation_report/<prefix>_<title>.md` (stub was created at Step 4)

The PIR contains 13 sections:

1. **Summary** — one paragraph, what shipped
2. **Requirement reference** — link to the requirement doc
3. **Plan reference** — link to the synthesised plan
4. **What was delivered** — numbered list matching R1, R2, …
5. **Decision rationale** — why key choices were made (especially non-obvious ones)
6. **Plan deviations** — where implementation diverged from the plan, and why
7. **Testing performed** — what was run, what results
8. **Security / secrets notes** — any credentials added/moved/rotated
9. **Production impact** — what changed in prod, rollback plan
10. **Known limitations** — things that work but aren't ideal
11. **Not done / not verified** — explicitly scoped out or not covered
12. **Follow-up work** — new tickets or tasks spawned
13. **Attribution** — who did what (person + LLM, if LLM-assisted)

---

## Step 8: Review

**⚠️ Merge gate — all items must be green before Step 9.**

Review checklist (⏳ to be finalised with user):

1. Plan is synthesised and committed to the branch
2. All quality gates pass (Step 6)
3. PIR is filled in (not stub)
4. Rival review is complete (if Step 2.5 was used)
5. Explicit merge approval given by the designated reviewer

---

## Step 9: Merge

Only after Step 8's gate is green.

---

## LLM Completion Checklist (⏳ to be finalised)

Before reporting a task complete, confirm:

1. Requirement committed to `main`
2. Plans (dual + critique if used) committed
3. Synthesised plan committed
4. Branch created with stub PIR
5. Implementation committed on branch
6. All quality gates pass
7. PIR filled in (all 13 sections)
8. Review gate green and merged

---

## Templates

- `doc/prompts/requirement_template.md` (⏳ to create)
- `doc/prompts/plan_template.md` (⏳ to create)
- `doc/prompts/post_implementation_report_template.md` (⏳ to create)
- `doc/prompts/rival_review_template.md` (⏳ to create)

---

## Open decisions (being resolved one at a time)

- [x] Step order: Report → Review → Merge
- [x] Prefix can be date or issue number
- [x] PIR location: `doc/post_implementation_report/`
- [x] PIR depth: 13 sections (from infra-snowflake)
- [x] Step 2.5 Plan Critique: optional
- [x] No auto-triggering of implementation from planning
- [x] Stub PIR at branch creation
- [ ] Explicit 5-item merge gate — pending user decision on exact items
- [ ] 8-item completion checklist — pending user review
- [ ] One-question-at-a-time rule — adopted (aligned with global CLAUDE.md)
- [ ] Template files — to be created separately
- [ ] Secrets handling paragraph — included, pending refinement
- [ ] Read-before-write principle — included, aligned with global CLAUDE.md

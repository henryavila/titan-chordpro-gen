# Handoff to Sonnet — Phase A Execution

> **For Sonnet (or whichever Claude model runs this):** Read this entire file before anything else. It is the single-page brief that orients you to what you need to do, the discipline expected, and where to escalate when stuck.

---

## Mission

Execute **Phase A** of the Titan ChordPro Lib v0.1 implementation plan. Phase A builds the pure-Python foundation (schemas, protocols, fusion engine, output writer, CLI, mocks, CI) so the pipeline produces valid `.chordpro` files using mock engines. Phase B (ML engines) follows in a separate session.

## Authoritative documents (read in this order, end to end)

1. **`docs/superpowers/plans/2026-05-12-titan-v0.1-phase-a.md`** — THE PLAN. ~7340 lines. 34 tasks (T01-T34). Has a mandatory **Executor playbook** section near the top (around line 16) that you MUST read before starting T01.

2. **`docs/superpowers/specs/2026-05-09-titan-v0.1-design.md`** — design spec. Reference when the plan points you at a specific section.

3. **`docs/research/09-chord-on-syllable.md`** — calibration source for tolerance windows in fusion engine (T20).

4. **`docs/roadmap.md`** — living tracker. Update at the end of Phase A (T34 Step 4).

## How to execute

Use the `superpowers:executing-plans` skill (or `superpowers:subagent-driven-development` if available — they both reference the plan's checkbox syntax `- [ ]`). Execute tasks **strictly sequentially** T01 → T34. No parallel execution.

Each task has 5 steps (or 6 for tasks creating multiple files):
1. Write failing tests
2. Run tests, verify failure
3. Implement
4. Run tests, verify pass
5. Commit

**Both Step 2 and Step 4 are gates, not formalities.** Verify the actual pytest output before moving on. The plan states the expected test count for every task — confirm pytest collects that number.

## The Reference Implementation contract (critical)

Many tasks contain `> **Reference Implementation (Opus-authored, 2026-05-12)**` blocks. The code inside those blocks is **contract**, not suggestion. The Executor playbook in the plan has a DO/DO NOT table — internalize it before T01. TL;DR: copy verbatim, including docstrings and comments; do not refactor, do not add `try/except`, do not rename, do not "type: ignore" anything.

## Architectural Checkpoints (your auto-checks)

At the end of each Week, the plan has a `🔍 Architectural Checkpoint` subsection. Run the smoke commands listed there BEFORE tagging the Week complete. If anything fails:

1. STOP. Do not start the next Week.
2. Document the failure (paste pytest/mypy/ruff output to a scratch file).
3. Report to Henry. He will invoke an Opus review using `docs/superpowers/checkpoints/week-<N>-review.md`.

If the checkpoint passes, tell Henry "Week N done, smoke clean" and wait for his go-ahead before continuing. He may run the optional Opus review even on a clean checkpoint — that's his call.

## When stuck — escalation protocol

1. Re-read the Reference Implementation block — clues live in inline comments.
2. Check the spec section linked at the top of the task.
3. If a test passes but the spec example doesn't match → trust the spec; the test may have a typo. Surface the discrepancy.
4. If both fail → **stop, do not improvise**. Report to Henry with: file path, line numbers, expected vs actual output.

## Branch + commit strategy

- Work in local branch (no PRs).
- One commit per task, using the commit message block verbatim from the plan.
- **NEVER** add "Generated with Claude Code" or `Co-Authored-By: Claude` to commits. Henry's repo uses Conventional Commits without AI attribution.
- After T34 Step 3 (smoke test), Henry tags `v0.1.0-a0` MANUALLY after his final review. Do not tag yourself.

## What's already in place

- Git initialized, branch `main`, 5 commits ahead with docs (research, spec, plan, roadmap).
- `.gitignore` already configured (includes `~/.cache/titan-chordpro/`, mdprobe artifacts).
- No Python code yet — T01 creates the package skeleton.
- Memory system at `~/.claude/projects/-Volumes-External-code-titan-chordpro-lib/memory/` documents prior decisions; you can read it for context but the plan supersedes it.

## What's explicitly out of scope for Phase A

- Any ML engine implementation (torch, whisper, chordino) — Phase B.
- Real audio processing — mocks only.
- Tier 2/3 validation harness — Phase C.
- Documentation site, demo video, PyPI publish — Phase D.

## Per-Week deliverables

| Week | Tasks | Tag at end |
|---|---|---|
| 1 | T01-T12 | (none — work continues into W2) |
| 2 | T13-T20 | `git tag v0.1.0-a0.week2 -m "Week 2 complete: fusion engine"` |
| 3 | T21-T33 | (none — T34 tags Phase A) |
| Wrap | T34 | Henry tags `v0.1.0-a0` manually after review |

## Test commands you'll run constantly

```bash
# Per-task (Step 4)
pytest <test_file> -v

# Per-Week smoke (in checkpoint subsections)
pytest tests/unit/<module>/ -v --collect-only

# Phase A wrap-up (T34)
pytest --cov=titan_chordpro --cov-report=term --cov-fail-under=80
pytest --collect-only -q | tail -1
ruff check titan_chordpro/ tests/
mypy titan_chordpro/
```

## What I (the Opus session that wrote this) verified before handoff

- Plan internal consistency reviewed 3 times (`/atomic-skills:review-plan-internal`).
- 4 critical findings fixed (test count claims, char_position bug in T23 example).
- 2 significant findings fixed (T21 ordering caveat, file structure missing entries).
- Reference Implementations authored for the 10 algorithmically-risky tasks (T13, T19, T20, T22-T27, T29).
- Executor playbook + DO/DO NOT contract added at top of plan.
- 3 architectural checkpoints + final review prompt files written in `docs/superpowers/checkpoints/`.

## Final instruction

Start with the Executor playbook in the plan (around line 16-90). Then T01. Don't skip ahead.

If you finish Week 1 cleanly, tell Henry. If a checkpoint smoke fails, tell Henry. If you're stuck for more than 5 minutes on a single step, tell Henry. Otherwise just execute.

Good luck. The plan is detailed for a reason — trust it.

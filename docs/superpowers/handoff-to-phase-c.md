# Handoff — Phase C planning + execution

> **For the next Claude session (any model):** Read this entire file before anything else. Phase A and Phase B are shipped (`v0.1.0-a0`, `v0.1.0-b0`, `v0.1.0-b1`). Phase C does NOT have a written plan yet — your first job is to **write the plan**, not execute it. Henry will approve the plan before you create the initiative and start coding.

---

## Mission

Plan and execute **Phase C** of the Titan ChordPro Lib v0.1: end-to-end validation harness against the iasdermelinda.com.br corpus (151 worship songs with YouTube URLs + native ChordPro ground truth), plus the bass-note inversion carry-over from the Codex hot-fix review.

Per `docs/roadmap.md:164-191`, Phase C is Weeks 8-9:
- Week 8: `benchmarks/audio_downloader.py` (yt-dlp), `benchmarks/validation_runner.py` (pipeline + mir_eval), `benchmarks/divergence_ranker.py`, nightly cron, Tier 2 sample stratification, **F-004 bass-note**.
- Week 9: first nightly run (30 songs), divergence review, bug fixes, CLI polish (progress bars via `rich`), README badges + install + demo.

Validation targets at end of Phase C:
- Tier 2 WCSR-majmin ≥ 70%
- Beat F-measure ≥ 0.85
- Word alignment median offset < 100ms
- Top-10 divergences ≤ 3 are "Titan errado"

## Authoritative documents (read in this order)

1. **`docs/superpowers/specs/2026-05-09-titan-v0.1-design.md`** — design spec (1807 lines). Source of truth. Phase C interest: §406 (Chordino + bass-note inversions), §1099-1110 (StageConfidence aggregation, now wired but unverified on real audio), §1300-1400 (writer/profile rendering — must remain stable).

2. **`.atomic-skills/reviews/2026-05-18-2116-phase-a-b-full-codebase-vs-spec-codex.md`** — Codex cross-model review of the full Phase A+B codebase against spec. **F-004 bass-note inversion is deferred to Phase C** with a doc-only marker in `titan_chordpro/engines/chord/chordino.py:supports_inversions`. Read this review to understand the scope of work F-004 implies (chroma analysis on `bass_stem`).

3. **`docs/roadmap.md`** — Updates log entry `### 2026-05-19 (Codex hot-fix v0.1.0-b1)` summarizes the 8 applied + 1 deferred findings. Phase C table at `:164-191` lists Weeks 8-9 deliverables.

4. **`.atomic-skills/initiatives/titan-phase-b.md`** and **`.atomic-skills/initiatives/titan-codex-fixes-v0.1.0-b1.md`** (both archived) — historical context. The Phase B initiative's `next_action` field also mentioned "cache JSON serialization" as a Phase C candidate — surface this to Henry when scoping.

5. **`docs/superpowers/plans/2026-05-12-titan-v0.1-phase-a.md`** and **`docs/superpowers/plans/2026-05-17-titan-v0.1-phase-b.md`** — template references for the plan you'll write. Follow the same structure (Executor playbook at top, atomic numbered tasks, embedded Reference Implementations for algorithmically risky tasks, inline Architectural Checkpoints, commit message blocks per task).

## What's in place right now (verified 2026-05-19)

- **Tag `v0.1.0-b1`** on `main` (commit `254d88b`), pushed to `origin`.
- **No active initiative** (PROJECT-STATUS confirms). HARD-GATE requires a new initiative or explicit ad-hoc declaration before any code edits.
- **Test suite: 320 passed / 10 skipped** (the 10 skipped are integration smokes that need real extras — `[mac]`/VAMP).
- **Codex review reject verdict** transitioned to acceptance via F-004 deferral; all other findings shipped.

### Corpus artifacts (already provided by Henry)

- **`chordpros.csv/songs.csv`** — 155 rows. Columns: `title`, `external_link`, `chordpro`. **151 rows have a YouTube URL** (103 `youtu.be` + 48 `www.youtube.com`); 4 have empty `external_link` and must be skipped. The `chordpro` column is the full ChordPro source as ground truth — no DB joins needed at runtime.
- **`chordpros.csv/chordpros.csv`** — older export, redundant with `songs.csv` (no URL column). Decision pending: keep both or remove the older one when implementing `benchmarks/corpus.py`. Ask Henry.

### Dependencies pending

- **`yt-dlp`** is not installed. Add it as a new extra `[validation]` in `pyproject.toml`; document install in `docs/setup-validation.md` (analogous to the existing `docs/setup-vamp.md`).
- **`mir_eval`** is already declared in `pyproject.toml:225` dev/validation deps — confirm import works.

## Open scope decisions (you must surface these to Henry before writing the plan)

1. **Corpus size for Tier 2.** Roadmap says 30 stratified. Henry has 151 with URLs. Options:
   - Start with all 6 PT-BR worship songs already cadastrados (per memory `references.md`) for first end-to-end validation, then expand.
   - Stratify 30 across slash chords / 6-8 time / melisma immediately.
   - Run all 151 from day one as Tier 2.5.
2. **F-004 implementation depth.** Bass-note inversion needs chroma analysis on the bass stem. Options:
   - Full implementation (chromagram per chord interval + bass-note class → letter mapping) using `librosa`.
   - Skip librosa: hand-roll a chroma extractor with `numpy` + `scipy` only.
   - Minimum-viable: only emit bass_note when bass stem chroma has > 0.7 confidence; otherwise None.
3. **Cache JSON serialization** mentioned in Phase B archived initiative. Cache currently writes nothing per stage (look at `titan_chordpro/core/cache.py` to confirm). If included in Phase C scope: opt-in `cache=True` writes `<.titan-cache>/<audio_id>/<stage>.json` (separation/transcription/etc). Significant scope addition — may justify deferring to v0.2.
4. **Plan reviewer.** Phase A/B used Codex (`atomic-skills:review-plan-with-codex`) for cross-model adversarial review before approving. Henry likely wants the same for Phase C — confirm.
5. **Executor model.** Memory `executor_model_experiment.md` records that Henry wanted Opus (not Sonnet) as executor for Phase B T59+ to test quality. Confirm whether Phase C continues with Opus executor or returns to Sonnet.

## What to do (in order)

1. **Read the authoritative docs** end-to-end (spec, Codex review, roadmap update entry, both archived initiatives).
2. **Inspect the corpus**: `head chordpros.csv/songs.csv` and `wc -l chordpros.csv/songs.csv` to confirm shape; sample 3 ChordPros to understand format variability.
3. **Ask Henry** the 5 open-scope-decisions above. Wait for answers.
4. **Draft the Phase C plan** at `docs/superpowers/plans/2026-05-19-titan-v0.1-phase-c.md`, following the Phase A/B template exactly. Suggested rough task layout (subject to Henry's scope decisions):
   - T60: pyproject `[validation]` extra (`yt-dlp`, `mir_eval`, `librosa` if approved) + setup doc
   - T61: `benchmarks/__init__.py` + `benchmarks/corpus.py` (loads songs.csv)
   - T62: `benchmarks/audio_downloader.py` (yt-dlp wrapper with cache)
   - T63-T64: Chordino bass-note implementation (F-004) — RI required, this is algorithmic
   - T65: `benchmarks/validation_runner.py` (transcribe → parse ground-truth → mir_eval)
   - T66: `benchmarks/divergence_ranker.py` (severity scoring per spec)
   - T67: `.github/workflows/nightly.yml`
   - T68: First Tier 2 run + top-10 review (manual checkpoint with Henry)
   - T69: CLI polish (`rich` progress bars, error messages)
   - T70: README badges + install + demo invocation
   - T71: Phase C wrap-up — roadmap update + tag `v0.1.0-c0`
5. **Architectural Checkpoints** at end of each Week — prompt files at `docs/superpowers/checkpoints/phase-c-week-{8,9}-review.md` mirroring the Phase B pattern.
6. **Get plan reviewed** (Henry will invoke `atomic-skills:review-plan-with-codex` or similar) before creating the initiative.
7. **Create the initiative** `.atomic-skills/initiatives/titan-phase-c.md` only after plan approval. Update PROJECT-STATUS.
8. **Execute** the plan task-by-task, same discipline as Phase A/B (TDD, verbatim Reference Implementations, no improvisation, checkpoint smokes before continuing).

## Discipline (DO / DO NOT)

**DO:**
- Read the entire spec section any task references before implementing.
- Quote `file:line` evidence when reporting problems to Henry.
- Run the full pytest suite after each task. 320 passing is the floor.
- Add new dependencies behind extras (`[validation]`), never the base install.
- Skip the 4 songs in `songs.csv` with empty `external_link` — document the skip count in metrics.
- Cache audio downloads under `~/.cache/titan-chordpro/audio/` (per `references.md`).
- Tag `v0.1.0-c0` only after Henry's final review.

**DO NOT:**
- Start coding before the plan is written and approved.
- Add `yt-dlp` or `librosa` to the base install — they go in `[validation]`.
- Modify the writer profiles or chordpro syntax — frozen since Phase A.
- Touch the Chordino subprocess boundary — F-001 (blocker) was dropped in Codex review because chord_extractor uses a VAMP subprocess; don't break that property.
- Update `docs/roadmap.md` mid-execution — that's the final wrap-up task.
- Commit with `Co-Authored-By: Claude` or "Generated with Claude Code" — Henry's repo uses Conventional Commits clean.
- Push the v0.1.0-c0 tag yourself — Henry tags manually after final review.

## When stuck — escalation protocol

1. Re-read the Reference Implementation block in the task (if there is one).
2. Check the spec section the task points at.
3. If a real-audio integration test fails: capture `pytest -v` output + audio file path + which engine produced the bad event, before changing anything. Many failures will be Phase C reality smashing into Phase B assumptions — Henry needs to see the raw signal.
4. **Do not improvise around F-004.** Bass-note derivation is algorithmically delicate; if the RI doesn't match observed behavior, surface the discrepancy.
5. After 5 minutes stuck on one step, ask Henry.

## Memory pointers (read for context, not as source of truth)

- `~/.claude/projects/-Volumes-External-code-titan-chordpro-lib/memory/MEMORY.md` — index.
- `references.md` — corpus location, YouTube ID handling, library license notes (yt-dlp UNLICENSE is fine, mir_eval MIT is fine).
- `feedback_patterns.md` — Henry's collaboration style (terse, contextualize before asking, test don't deduce).
- `project_decisions.md` — macro decisions; v0.1 deferrals.
- `executor_model_experiment.md` — Opus vs Sonnet executor experiment.

## Git state at handoff

```
Branch: main
HEAD: e143b68 chore(meta): archive titan-codex-fixes-v0.1.0-b1 — hot-fix complete + Phase C entry
Tags: v0.1.0-a0, v0.1.0-a0.week2, v0.1.0-b0, v0.1.0-b1
Remote: origin (github.com:henryavila/titan-chordpro-lib.git) up to date
Working tree: only titan_chordpro/__pycache__/*.pyc (legacy tracked; ignore)
```

## Final instruction

Start by reading the authoritative docs and the Codex review carefully. Then ask Henry the 5 open scope decisions. Do not write a single line of code before the plan exists and is approved. The Phase A and Phase B plans are 7342 and 4420 lines respectively — they invested heavily in spec-rigor up front, and that's why both phases shipped on schedule with green test suites. Phase C deserves the same investment.

Good luck. Phase C is where Titan stops being a mock pipeline and starts producing actual chord charts from actual audio.

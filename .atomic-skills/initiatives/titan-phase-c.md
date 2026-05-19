---
initiative_id: titan-phase-c
title: Titan ChordPro Lib v0.1 Phase C — validation harness + corpus testing + F-004 bass-note
status: active
branch: main
started: 2026-05-19
last_updated: 2026-05-19T14:30:00Z
plan_link: docs/superpowers/plans/2026-05-19-titan-v0.1-phase-c.md
next_action: "Execute T60: pyproject [validation] extra + docs/setup-validation.md + gitignore"
max_stack_depth_warning: 5
stack: []
tasks:
  PLAN: {title: "Draft Phase C implementation plan (15 tasks: T-pre + T60..T73; 5 RIs; 2 checkpoints)", status: done, closed_at: 2026-05-19T13:00:00Z}
  REVIEW: {title: "Cross-model plan review via review-plan-with-codex (6 findings, all applied)", status: done, closed_at: 2026-05-19T14:00:00Z}
  INIT: {title: "Flip initiative to status: active; repoint plan_link to the reviewed plan", status: done, closed_at: 2026-05-19T14:30:00Z}
  EXEC: {title: "Execute T-pre + T60..T73 task-by-task (TDD; per-Week checkpoints)", status: pending}
  TAG: {title: "Tag v0.1.0-c0 (Henry tags manually after final review)", status: pending}
parked: []
emerged: []
---

## Context

Phase A (pure-Python core, mocks, fusion, writer, CLI) shipped as `v0.1.0-a0` on 2026-05-17.
Phase B (7 ML engines: htdemucs_ft, whisper.cpp, torchaudio align, Chordino, BeatThis, gruut PT, g2p_en EN) shipped as `v0.1.0-b0` on 2026-05-18.
Hot-fix `v0.1.0-b1` (2026-05-19) applied 8/9 Codex cross-model review findings and explicitly deferred F-004 (Chordino bass-note inversion derivation) to Phase C alongside the validation harness.

Phase C is the first phase where Titan stops being a mock pipeline and starts producing actual chord charts from actual audio. Validation targets at end of Phase C (per `docs/roadmap.md:186-190`):

- Tier 2 WCSR-majmin ≥ 70%
- Beat F-measure ≥ 0.85
- Word alignment median offset < 100ms
- Top-10 divergences ≤ 3 are "Titan errado"

## Corpus already provisioned

Henry exported the iasdermelinda.com.br catalog to `chordpros.csv/songs.csv` (155 rows, columns: `title`, `external_link`, `chordpro`). 151 rows have a YouTube URL (103 `youtu.be` + 48 `www.youtube.com`); the 4 without `external_link` will be skipped by the harness. The `chordpro` column is the full ChordPro source — ground truth needs no DB joins.

## 5 open scope decisions (must resolve before drafting the plan)

1. **Tier 2 corpus size.** Roadmap says 30 stratified. Options: 6 PT-BR cadastrados (smoke) / 30 stratified across slash chords + 6-8 time + melisma / 151 all.
2. **F-004 implementation depth.** Bass-note inversion needs chroma analysis on the bass stem. Options: full librosa / hand-roll with numpy+scipy / minimum-viable (only emit `bass_note` when confidence > 0.7).
3. **Cache JSON serialization** (mentioned in Phase B archived `next_action`). Include in Phase C scope or defer to v0.2.
4. **Plan reviewer.** Phase A/B used `atomic-skills:review-plan-with-codex` cross-model. Same for Phase C?
5. **Executor model.** Memory `executor_model_experiment.md` records Henry chose Opus executor (vs Sonnet) for Phase B T59+ as quality experiment. Continue Opus executor for Phase C or revert to Sonnet?

## Notes

- HARD-GATE intact: `status: planning` does NOT authorize code edits. Flip to `status: active` only after plan written and reviewed.
- `plan_link` currently points to the handoff brief, not the (yet-unwritten) plan. Update once the real plan exists at `docs/superpowers/plans/2026-05-19-titan-v0.1-phase-c.md`.
- This planning initiative was created by the previous session (2026-05-19) so that `/atomic-skills:project-status` surfaces Phase C immediately when the next session opens. See full bridge brief at `docs/superpowers/handoff-to-phase-c.md`.

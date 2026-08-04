---
schemaVersion: "0.1"
slug: titan-v01-f2-phase-c-validation-and-quality
title: Phase C Validation and quality
goal: Validation harness over the 151-song corpus, F-004 bass inversions, stage
  cache, and quality loop until sample WCSR and placement are release-credible;
  then CLI polish and tag `v0.1.0-c0`.
summary: Phase C Validation and quality
status: active
branch: plan/titan-v01
started: 2026-08-04T16:08:35Z
lastUpdated: 2026-08-04T16:08:35Z
startedCommit: fdd8abf8c0c096de5954872c8ee0648ef44a2fa9
nextAction: "Execute T-003: T70 quality loop (detection and placement)"
parentPlan: titan-v01
phaseId: F2
businessIntent:
  value: Gerar cifras ChordPro editáveis a partir de áudio, com acordes na sílaba
    correta (Mac-first).
  workflow: Áudio → separation/transcription/align/chord/beat/lang → fusion
    placement → writer profiles → validation harness vs corpus iasdermelinda.
  rules: Protocol-based engines (sem torch no orchestrator); TDD + gates
    WCSR/human review; Conventional commits por task; Nested plan SoT em
    projects/titan-chordpro-lib/titan-v01.
  outOfScope: v0.2 CUDA/BTC/mlx engines; editor visual / LearnableChordEngine;
    Windows first-class support.
  doneWhen: Tag v0.1.0 com DoD de qualidade (WCSR sample/Tier, docs, known-issues)
    e Phase C c0 fechada antes.
tasksDone: 2
tasksTotal: 6
gatesMet: 0
gatesTotal: 3
weightDone: 2
weightTotal: 8
exitGates:
  - id: F2-G1
    description: Sample or Tier 2.5 mean WCSR-majmin ≥ 0.70
    status: pending
    verifier:
      kind: manual
      description: Confirm benchmarks/reports latest mean WCSR ≥ 0.70
    verifierLabel: manual
  - id: F2-G2
    description: Henry GO on top divergences (≤ 3 Titan-wrong in top-N)
    status: pending
    verifier:
      kind: manual
      description: Owner review of top-divergences.md
    verifierLabel: manual
  - id: F2-G3
    description: Tag v0.1.0-c0 exists after T73
    status: pending
    verifier:
      kind: shell
      command: git rev-parse v0.1.0-c0
    verifierLabel: "shell: git rev-parse v0.1.0-c0"
stack:
  - id: 1
    title: Phase C Validation and quality
    type: task
    openedAt: 2026-08-04T16:08:35Z
tasks:
  - id: T-001
    title: Validation harness (T60–T69)
    description: Extra `[validation]`, corpus loader, yt-dlp downloader,
      runner/metrics/parser, divergence ranker, nightly workflow, F-004
      `bass_chroma`, cache dump/load + orchestrator wiring. **Already in tree.**
    status: done
    lastUpdated: 2026-08-04T16:08:35Z
    summary: Harness T60–T69 no tree
    weight: 1
    closedAt: 2026-08-04T16:08:35Z
  - id: T-002
    title: T70 structural placement fixes
    description: Local `parent_word_idx` reindex, melisma remap, orphan
      InstrumentalLines, sectioner midpoint coverage, stress single-source,
      beat_snap end clamp. **Landed 2026-08-04; sample mean WCSR still ~0.21.**
    status: done
    lastUpdated: 2026-08-04T16:08:35Z
    summary: Structural placement fixes 2026-08-04
    weight: 1
    closedAt: 2026-08-04T16:08:35Z
  - id: T-003
    title: T70 quality loop (detection and placement)
    description: Reduce stacking, improve chord/time agreement vs ground truth on
      the 3-song sample then broader corpus; target mean WCSR-majmin ≥ 0.70 and
      Henry GO on top divergences.
    status: active
    lastUpdated: 2026-08-04T16:08:35Z
    summary: Quality loop WCSR/stacking
    weight: 2
  - id: T-004
    title: T71 CLI polish
    description: Rich progress bars and `--validate` flag on `titan-chordpro` CLI.
    status: pending
    lastUpdated: 2026-08-04T16:08:35Z
    summary: CLI rich + --validate
    weight: 1
  - id: T-005
    title: T72 README validation section
    description: Badges plus validation harness docs (setup/quick-start already exist).
    status: pending
    lastUpdated: 2026-08-04T16:08:35Z
    summary: README validation section
    weight: 1
  - id: T-006
    title: T73 close Phase C
    description: Sync roadmap, write CHANGELOG `[0.1.0c0]`, bump package to
      `0.1.0c0`, final review, Henry tags `v0.1.0-c0`.
    status: pending
    lastUpdated: 2026-08-04T16:08:35Z
    summary: CHANGELOG + tag c0
    weight: 2
parked: []
emerged: []
planTitle: Titan ChordPro Lib v0.1 — from research to release
planActive: true
current: true
---

# Narrative / notes

Initiative for phase **F2 — Phase C Validation and quality** (adopt mid-flight 2026-08-04).

## Decisions

- Adopted from cleaned source `docs/superpowers/plans/2026-08-04-titan-v01-adopt-source.md`.
- Supersedes legacy flat plan/initiatives under `.atomic-skills/legacy-flat-pre-adopt-2026-08-04/`.

## Links

- Roadmap: `docs/roadmap.md`
- Design: `docs/superpowers/specs/2026-05-09-titan-v0.1-design.md`

---
schemaVersion: "0.1"
slug: titan-v01-f1-phase-b-ml-integration
title: Phase B ML Integration
goal: Seven real ML engines on Mac-first hardware with factory fail-fast and
  Codex hot-fix to `v0.1.0-b1`.
summary: Phase B ML Integration
status: done
branch: plan/titan-v01
started: 2026-08-04T16:12:00Z
lastUpdated: 2026-08-04T16:12:00Z
startedCommit: fdd8abf8c0c096de5954872c8ee0648ef44a2fa9
nextAction: Phase done — archived at adopt
parentPlan: titan-v01
phaseId: F1
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
tasksTotal: 2
gatesMet: 2
gatesTotal: 2
weightDone: 2
weightTotal: 2
exitGates:
  - id: F1-G1
    description: Real engines selectable via factory on Apple Silicon path
    status: met
    metAt: 2026-08-04T16:12:00Z
    verifier:
      kind: test
      runner: pytest
      pattern: tests/integration/test_factory_real.py
    evidence:
      verifierKind: test
      verifiedAt: 2026-08-04T16:12:00Z
      passed: true
      exitCode: 0
      testsCollected: 1
      outputSummary: Historical Phase A/B shipped; suite green on 2026-08-04 placement
        campaign.
    verifierLabel: "test: pytest tests/integration/test_factory_real.py"
    evidenceSummary: passed · 1 tests · 2026-08-04
  - id: F1-G2
    description: Tag v0.1.0-b1 exists
    status: met
    metAt: 2026-08-04T16:12:00Z
    verifier:
      kind: shell
      command: git rev-parse v0.1.0-b1
    evidence:
      verifierKind: shell
      verifiedAt: 2026-08-04T16:12:00Z
      passed: true
      exitCode: 0
      outputSummary: 97f8ffbdda0f517c6dce01177e874ee15a3dda39
    verifierLabel: "shell: git rev-parse v0.1.0-b1"
    evidenceSummary: passed · 2026-08-04
stack: []
tasks:
  - id: T-001
    title: Integrate seven engines
    description: BeatThis, htdemucs_ft, whisper.cpp, torchaudio align, Chordino,
      gruut PT, g2p_en EN under `titan_chordpro/engines/`.
    status: done
    lastUpdated: 2026-08-04T16:08:35Z
    summary: Integrate seven engines
    weight: 1
    closedAt: 2026-08-04T16:08:35Z
  - id: T-002
    title: Codex hot-fix b1
    description: Apply 8/9 A+B findings; defer F-004 bass inversions to Phase C; tag
      `v0.1.0-b1`.
    status: done
    lastUpdated: 2026-08-04T16:08:35Z
    summary: Codex hot-fix b1
    weight: 1
    closedAt: 2026-08-04T16:08:35Z
parked: []
emerged: []
---

# Narrative / notes

Initiative for phase **F1 — Phase B ML Integration** (adopt mid-flight 2026-08-04).

## Decisions

- Adopted from cleaned source `docs/superpowers/plans/2026-08-04-titan-v01-adopt-source.md`.
- Supersedes legacy flat plan/initiatives under `.atomic-skills/legacy-flat-pre-adopt-2026-08-04/`.

## Links

- Roadmap: `docs/roadmap.md`
- Design: `docs/superpowers/specs/2026-05-09-titan-v0.1-design.md`

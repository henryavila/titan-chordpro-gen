---
schemaVersion: "0.1"
slug: titan-v01-f0-phase-a-foundation
title: Phase A Foundation
goal: "Pure-Python core: schemas, protocols, fusion engine, writer (5 profiles),
  CLI, mocks — no GPU required."
summary: Phase A Foundation
status: done
branch: plan/titan-v01
started: 2026-08-04T16:12:00Z
lastUpdated: 2026-08-04T16:12:00Z
startedCommit: fdd8abf8c0c096de5954872c8ee0648ef44a2fa9
nextAction: Phase done — archived at adopt
parentPlan: titan-v01
phaseId: F0
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
  - id: F0-G1
    description: Pipeline with mocks produces valid ChordPro end-to-end
    status: met
    metAt: 2026-08-04T16:12:00Z
    verifier:
      kind: test
      runner: pytest
      pattern: tests/unit/test_smoke.py tests/integration/test_cli.py
    evidence:
      verifierKind: test
      verifiedAt: 2026-08-04T16:12:00Z
      passed: true
      exitCode: 0
      testsCollected: 1
      outputSummary: Historical Phase A/B shipped; suite green on 2026-08-04 placement
        campaign.
    verifierLabel: "test: pytest tests/unit/test_smoke.py tests/integration/test_cli.…"
    evidenceSummary: passed · 1 tests · 2026-08-04
  - id: F0-G2
    description: Tag v0.1.0-a0 exists on the remote
    status: met
    metAt: 2026-08-04T16:12:00Z
    verifier:
      kind: shell
      command: git rev-parse v0.1.0-a0
    evidence:
      verifierKind: shell
      verifiedAt: 2026-08-04T16:12:00Z
      passed: true
      exitCode: 0
      outputSummary: 9c7d407b09e3f879ec94a6effb616f91ca61ab17
    verifierLabel: "shell: git rev-parse v0.1.0-a0"
    evidenceSummary: passed · 2026-08-04
stack: []
tasks:
  - id: T-001
    title: Ship foundation package
    description: Delivered as tag v0.1.0-a0 (2026-05-17).
    status: done
    lastUpdated: 2026-08-04T16:08:35Z
    summary: Core/fusion/writer/CLI shipped
    weight: 1
    closedAt: 2026-08-04T16:08:35Z
  - id: T-002
    title: Tag and archive Phase A
    description: Annotated tag v0.1.0-a0.
    status: done
    lastUpdated: 2026-08-04T16:08:35Z
    summary: Tag v0.1.0-a0
    weight: 1
    closedAt: 2026-08-04T16:08:35Z
parked: []
emerged: []
---

# Narrative / notes

Initiative for phase **F0 — Phase A Foundation** (adopt mid-flight 2026-08-04).

## Decisions

- Adopted from cleaned source `docs/superpowers/plans/2026-08-04-titan-v01-adopt-source.md`.
- Supersedes legacy flat plan/initiatives under `.atomic-skills/legacy-flat-pre-adopt-2026-08-04/`.

## Links

- Roadmap: `docs/roadmap.md`
- Design: `docs/superpowers/specs/2026-05-09-titan-v0.1-design.md`

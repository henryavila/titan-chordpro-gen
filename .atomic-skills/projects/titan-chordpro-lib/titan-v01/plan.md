---
schemaVersion: "0.1"
slug: titan-v01
title: Titan ChordPro Lib v0.1 — from research to release
version: "1.0"
status: active
started: 2026-05-08T00:00:00Z
lastUpdated: 2026-08-04T16:12:00Z
branch: plan/titan-v01
currentPhase: F2
parallelismAllowed: false
supersedes:
  path: .atomic-skills/legacy-flat-pre-adopt-2026-08-04/plans/titan-v01.md
  supersedeScope: full
principles:
  - id: P1
    title: Mac-first, CUDA later
    body: M-series Apple Silicon is the primary dev/test platform.
  - id: P2
    title: Protocol-based engines
    body: Orchestrator never imports torch/whisper directly.
  - id: P3
    title: TDD + measured quality
    body: Features land behind tests; Phase C gates on WCSR and human review.
  - id: P4
    title: One commit per atomic task
    body: Conventional Commits; sequential execution inside a phase.
  - id: P5
    title: Nested plan is the execution SoT
    body: Runtime tracking under projects/titan-chordpro-lib/titan-v01/.
glossary:
  - term: WCSR-majmin
    definition: Weighted Chord Symbol Recall on major/minor alphabet via mir_eval.
  - term: Tier 2.5
    definition: Full 151-song iasdermelinda corpus (Phase C scope decision).
  - term: F-004
    definition: Bass-note inversion via bass-stem chroma — implemented in Phase C.
  - term: T70
    definition: Phase C quality loop until gates pass.
  - term: curta
    definition: External consumer of the narrow core.hardware contract (0.1.0b2).
  - term: inline_slash
    definition: Default ChordPro output profile.
phases:
  - id: F0
    slug: titan-v01-f0-phase-a-foundation
    title: Phase A Foundation
    summary: Core puro Python + fusion + writer + CLI.
    goal: "Pure-Python core: schemas, protocols, fusion, writer, CLI, mocks."
    dependsOn: []
    subPhaseCount: 2
    status: done
    exitGate:
      summary: 2 criteria met
      criteria:
        - id: F0-G1
          description: Mocks e2e ChordPro
          status: met
          metAt: 2026-08-04T16:12:00Z
          verifier:
            kind: test
            runner: pytest
            pattern: tests/unit/test_smoke.py
          evidence: &a1
            verifierKind: test
            verifiedAt: 2026-08-04T16:12:00Z
            passed: true
            exitCode: 0
            testsCollected: 1
            outputSummary: Historical Phase A/B shipped; suite green on 2026-08-04 placement
              campaign.
        - id: F0-G2
          description: Tag v0.1.0-a0
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
  - id: F1
    slug: titan-v01-f1-phase-b-ml-integration
    title: Phase B ML Integration
    summary: Sete engines ML + hot-fix b1.
    goal: Seven real ML engines; tag v0.1.0-b1.
    dependsOn:
      - F0
    subPhaseCount: 2
    status: done
    exitGate:
      summary: 2 criteria met
      criteria:
        - id: F1-G1
          description: Factory real engines
          status: met
          metAt: 2026-08-04T16:12:00Z
          verifier:
            kind: test
            runner: pytest
            pattern: tests/integration/test_factory_real.py
          evidence: *a1
        - id: F1-G2
          description: Tag v0.1.0-b1
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
  - id: F2
    slug: titan-v01-f2-phase-c-validation-and-quality
    title: Phase C Validation and quality
    summary: Harness + quality loop até tag c0.
    goal: Validation harness over the 151-song corpus, F-004 bass inversions, stage
      cache, and quality loop until sample WCSR and placement are
      release-credible; then CLI polish and tag `v0.1.0-c0`.
    dependsOn:
      - F1
    subPhaseCount: 6
    status: active
    businessIntent:
      value: Gerar cifras ChordPro editáveis a partir de áudio, com acordes na sílaba
        correta (Mac-first).
      workflow: Áudio → separation/transcription/align/chord/beat/lang → fusion
        placement → writer profiles → validation harness vs corpus
        iasdermelinda.
      rules: Protocol-based engines (sem torch no orchestrator); TDD + gates
        WCSR/human review; Conventional commits por task; Nested plan SoT em
        projects/titan-chordpro-lib/titan-v01.
      outOfScope: v0.2 CUDA/BTC/mlx engines; editor visual / LearnableChordEngine;
        Windows first-class support.
      doneWhen: Tag v0.1.0 com DoD de qualidade (WCSR sample/Tier, docs, known-issues)
        e Phase C c0 fechada antes.
    exitGate:
      summary: 3 criteria to meet
      criteria:
        - id: F2-G1
          description: Sample or Tier 2.5 mean WCSR-majmin ≥ 0.70
          verifier:
            kind: manual
            description: Confirm benchmarks/reports latest mean WCSR ≥ 0.70
          status: pending
        - id: F2-G2
          description: Henry GO on top divergences (≤ 3 Titan-wrong in top-N)
          verifier:
            kind: manual
            description: Owner review of top-divergences.md
          status: pending
        - id: F2-G3
          description: Tag v0.1.0-c0 exists after T73
          verifier:
            kind: shell
            command: git rev-parse v0.1.0-c0
          status: pending
  - id: F3
    slug: titan-v01-f3-phase-d-pre-release
    title: Phase D Pre-release
    summary: Docs, demo, tag v0.1.0.
    goal: User docs, demo, CHANGELOG to 0.1.0, known-issues, snapshot tests, final
      tag `v0.1.0`. Blocked until F2 tags `v0.1.0-c0`.
    dependsOn:
      - F2
    subPhaseCount: 0
    status: pending
    exitGate:
      summary: 2 criteria to meet
      criteria:
        - id: F3-G1
          description: docs/method.md profiles.md troubleshooting.md exist
          verifier:
            kind: shell
            command: test -f docs/method.md && test -f docs/profiles.md && test -f
              docs/troubleshooting.md
          status: pending
        - id: F3-G2
          description: Tag v0.1.0 exists
          verifier:
            kind: shell
            command: git rev-parse v0.1.0
          status: pending
references:
  - kind: file
    path: docs/roadmap.md
    label: Roadmap
  - kind: file
    path: docs/superpowers/specs/2026-05-09-titan-v0.1-design.md
    label: Design spec
  - kind: file
    path: docs/superpowers/plans/2026-08-04-titan-v01-adopt-source.md
    label: Adopt source
planActive: true
planTitle: Titan ChordPro Lib v0.1 — from research to release
---

# Titan ChordPro Lib v0.1 — from research to release

## 1. Context

Python library that turns audio into ChordPro with chord-on-syllable placement.
Adopted 2026-08-04 into nested layout under `projects/titan-chordpro-lib/titan-v01/`.

## 2. Principles

See frontmatter `principles[]`.

## 3. Phase tree

F0 Foundation DONE · F1 ML DONE · **F2 Validation ACTIVE** · F3 Pre-release PENDING.

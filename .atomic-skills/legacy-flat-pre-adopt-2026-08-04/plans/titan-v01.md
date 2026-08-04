---
schemaVersion: "0.1"
slug: titan-v01
title: "Titan ChordPro Lib v0.1 — from research to release"
version: "0.1.0"
status: active
started: 2026-05-08T00:00:00Z
lastUpdated: 2026-05-26T15:00:00Z
currentPhase: F2
parallelismAllowed: false
principles:
  - id: P1
    title: Mac-first, CUDA later
    body: "M-series Apple Silicon is the primary dev/test platform. CUDA paths exist in pyproject.toml but are not exercised until v0.2."
  - id: P2
    title: Protocol-based engine abstraction
    body: "Orchestrator never imports torch/whisper/librosa directly. Engine Protocols in core/protocols.py are the contract boundary."
  - id: P3
    title: TDD + Reference Implementations
    body: "Every task follows 5-step TDD. RI blocks are CONTRACT — copy verbatim, do not improvise."
  - id: P4
    title: One commit per task
    body: "Conventional Commits format. No AI attribution. Sequential execution, no skipping."
  - id: P5
    title: Roadmap is the source of truth
    body: "docs/roadmap.md is the living master plan. This Plan file links the tracking infrastructure; the roadmap owns scope."
glossary:
  - term: WCSR-majmin
    definition: "Weighted Chord Symbol Recall, major/minor alphabet only. mir_eval's chord.weighted_accuracy with Thirds mapping."
  - term: Tier 2.5
    definition: "Full 151-song iasdermelinda corpus run (originally Tier 2 was 30, Tier 3 was 147; Phase C scope decision escalated to 151)."
  - term: F-004
    definition: "Codex review finding: Chordino bass-note inversion derivation. Deferred from v0.1.0-b1 to Phase C."
  - term: RI
    definition: "Reference Implementation — Opus-authored code blocks in the plan that executors copy verbatim."
phases:
  - id: F0
    title: "Phase A — Foundation (no GPU)"
    status: done
    initiativeSlug: titan-phase-a
    goal: "Pure-Python core: schemas, protocols, fusion engine, writer, CLI, mocks."
    started: 2026-05-12
    completed: 2026-05-17
    tag: v0.1.0-a0
    taskCount: 34
    planDoc: docs/superpowers/plans/2026-05-12-titan-v0.1-phase-a.md
  - id: F1
    title: "Phase B — ML Integration (Mac-first)"
    status: done
    initiativeSlug: titan-phase-b
    goal: "7 real ML engines integrated with factory fallback to mocks."
    started: 2026-05-17
    completed: 2026-05-18
    tag: v0.1.0-b1
    taskCount: 25
    planDoc: docs/superpowers/plans/2026-05-17-titan-v0.1-phase-b.md
    dependsOn: [F0]
  - id: F2
    title: "Phase C — Validation + F-004 + Cache"
    status: active
    initiativeSlug: titan-phase-c
    goal: "End-to-end corpus validation (151 songs), F-004 bass-note inversions, cache wiring, CLI polish."
    started: 2026-05-19
    tag: null
    taskCount: 15
    planDoc: docs/superpowers/plans/2026-05-19-titan-v0.1-phase-c.md
    dependsOn: [F1]
  - id: F3
    title: "Phase D — Pre-release"
    status: pending
    initiativeSlug: titan-phase-d-pre-release
    goal: "User docs, demo, LICENSE, CHANGELOG final, CI ubuntu, DoD orphans, tag v0.1.0."
    started: null
    tag: null
    taskCount: 13
    planDoc: null
    dependsOn: [F2]
references:
  - "docs/superpowers/specs/2026-05-09-titan-v0.1-design.md — consolidated design spec"
  - "docs/roadmap.md — living master plan (source of truth for scope)"
  - "docs/research/ — 9 research streams + synthesis"
---

## §1 Context

Titan ChordPro Lib v0.1 is a Python library that generates ChordPro files from audio + lyrics using AI-based beat/chord detection. The owner (Henry) runs iasdermelinda.com.br, a worship music catalog with 151 songs in native ChordPro format — the validation ground truth.

The v0.1 journey started with Phase 0 (research + design, 9 parallel streams) and is structured into 4 implementation phases: Foundation → ML Integration → Validation → Pre-release. Each phase has its own detailed implementation plan in `docs/superpowers/plans/`.

## §2 Principles

See frontmatter `principles[]`. Key insight from Phase A+B: the Reference Implementation contract is the primary defense against model-executor drift. Opus plans, Opus (or Sonnet) executes, Henry reviews at checkpoints.

## §3 Phase tree

```
F0  Phase A — Foundation (DONE, v0.1.0-a0)
    34 tasks, Weeks 1–3. Schemas, protocols, fusion, writer, CLI, mocks.
    259 tests, 93% coverage.

F1  Phase B — ML Integration (DONE, v0.1.0-b1)
    ~25 tasks, Weeks 4–7. 7 engines + Codex cross-model review.
    318 tests + 8/9 hot-fixes applied.

F2  Phase C — Validation + F-004 + Cache (ACTIVE)
    15 tasks (T-pre + T60–T73), Weeks 8–9.
    T60-T69 ✅. T70 partial (chord placement blocker). T71-T73 pending.
    451 tests at last count.

F3  Phase D — Pre-release (PENDING, blocked by F2)
    ~13 tasks (8 genuine + 5 DoD orphans).
    Docs (method, profiles, troubleshooting), demo, LICENSE, CHANGELOG,
    CI ubuntu, tag v0.1.0.
```

## §4 Overlap warnings (discovered 2026-05-26)

1. **Phase D itens 1-2 do roadmap são redundantes com Phase C T70.** Phase C scope decision escalou corpus de 30 → 151 songs. "Tier 3 run" e "review top 20" não são trabalho novo de Phase D.
2. **Phase C T72 (README) parcialmente coberta por trabalho ad-hoc.** Install + Quick start + Operator scripts já commitados. Faltam badges + validation section.
3. **4 emerged problems de T70-iter4 sem task formal:** chord placement (bloqueio), downbeat noise, lyric lines fragmentadas, off-by-1 syllable.
4. **DoD items sem dono:** CI ubuntu, snapshot tests 5 profiles, chordpro_ref parsing, known-issues.md.
5. **Beat F ≥ 0.85 e word offset < 100ms gates:** inalcançáveis sem labeled corpus (spec §1697-1702).

## §5 Reviews

_(Pending — will be populated after adversarial review.)_

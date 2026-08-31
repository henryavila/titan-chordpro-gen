---
schemaVersion: "0.1"
slug: titan-v01
title: Titan ChordPro Lib v0.1 — from research to release
version: "1.0"
status: active
started: 2026-05-08T00:00:00Z
lastUpdated: 2026-08-30T21:48:50Z
branch: plan/titan-v01
currentPhase: F2
executionMode: automate
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

## Ground-truth review

**Status:** complete-with-findings
**Codebase class:** populated
**Scanned:** titan_chordpro/, benchmarks/, tests/, scripts/, .github/workflows/, docs/, pyproject.toml → 122 product/test `.py` files under titan_chordpro+benchmarks+tests
**Commit:** d2093cf
**At:** 2026-08-31T00:19:26Z

### A — Plan premises vs code

| # | Premise | Result | Evidence |
|---|---------|--------|----------|
| 1 | Protocol contracts live in `titan_chordpro/core/protocols.py` (orchestrator never imports torch/whisper directly) | ok | `titan_chordpro/core/protocols.py` exists; `titan_chordpro/orchestrator.py` imports protocols/cache/schemas, not torch |
| 2 | Seven ML engines under `titan_chordpro/engines/` (beat, separation, transcription, align, chord, lang PT/EN) | ok | dirs: beat/, separation/, transcription/, alignment/, chord/, lang/ |
| 3 | Phase C validation harness already in tree (`[validation]`, corpus, yt-dlp, runner/metrics/parser, divergence ranker, nightly) | ok | `benchmarks/{corpus,audio_downloader,validation_runner,metrics,chordpro_parser,divergence_ranker}.py`; `.github/workflows/nightly.yml` |
| 4 | F-004 bass inversions via `bass_chroma` implemented | ok | `titan_chordpro/engines/chord/bass_chroma.py` |
| 5 | Stage cache dump/load + orchestrator wiring | ok | `titan_chordpro/core/cache.py:82` `dump_stage` / `:104` `load_stage` |
| 6 | T70 structural placement fixes landed (`parent_word_idx` reindex, melisma, sectioner, stress, beat_snap) | ok | reindex `orchestrator.py:520`; modules `fusion/{melisma,sectioner,stress,beat_snap,placer}.py` |
| 7 | Latest sample report mean WCSR-majmin still below gate 0.70 | ok | `benchmarks/reports/2026-08-04/top-divergences.md` Mean WCSR-majmin **0.211** (3 songs) |
| 8 | 3-song sample selection for T70 | ok | `scripts/sample_run.py:26-28` pins `9yZt5ekdceI`, `LvoYT0loqLQ`, `LL5Pak4zcuA` |
| 9 | Tags `v0.1.0-a0` and `v0.1.0-b1` exist | ok | `git rev-parse` → `9c7d407…`, `97f8ffb…` |
| 10 | CLI entrypoint `titan-chordpro` with `--validate` + rich Progress | ok | `titan_chordpro/cli.py:50` `--validate`; `:122`/` :156` `Progress` |
| 11 | Factory real-engines integration test exists | ok | `tests/integration/test_factory_real.py` |
| 12 | Docs: roadmap + setup-validation + design/adopt sources | ok | `docs/roadmap.md`, `docs/setup-validation.md`, `docs/superpowers/specs/2026-05-09-titan-v0.1-design.md` |
| 13 | Package version / CHANGELOG at `0.1.0c0` (T-006 landed; tag still operator-owned) | ok | `pyproject.toml:7`, `titan_chordpro/version.py:1`, `CHANGELOG.md`; tag `v0.1.0-c0` absent by design |
| 14 | F3 user docs (`docs/method.md` etc.) exist | ok (not F2 premise) | missing today; F3 creates them |

### B — Code present, plan silent (impact candidates)

| # | Finding | Location | Impact | Disposition |
|---|---------|----------|--------|-------------|
| 1 | Stage cache (`dump_stage`/`load_stage`) affects every re-run of sample/quality loop; harness often calls `cache=True` | `titan_chordpro/core/cache.py`, `benchmarks/validation_runner.py` | direct | **task T-003** — invalidate/bypass when measuring post-fix WCSR |
| 2 | Sibling **match_rate** toolchain (`compare_chordpro_to_gt`, `run_h3_h4_eval`, `redetect_chords_from_cache`) ≠ WCSR gate | `scripts/compare_chordpro_to_gt.py`, `scripts/run_h3_h4_eval.py`, `docs/research/chord-lane-2026-08-05.md` | direct | **oos/diagnostic** — F2-G1 SSOT is **only** Mean WCSR-majmin in latest `benchmarks/reports/*/top-divergences.md`; match_rate must not close the gate |
| 3 | `scripts/sample_run.py` + demo render scripts share orchestrator/cache | `scripts/` | direct | **task T-003** owns `sample_run.py`; `render_*` accepted residual for ad-hoc demos |
| 4 | `core/hardware.py` narrow backend probe is a curta-facing contract | `titan_chordpro/core/hardware.py:28` | indirect | **oos / accepted** — do not widen `detect_backend` in F2 |
| 5 | Five writer profiles share placement Document model | `titan_chordpro/writer/profiles/*` | indirect | **scopeBoundary T-003** — no wholesale profile rewrites |
| 6 | Nightly + CI workflows run corpus/validation paths | `.github/workflows/{nightly,ci}.yml` | indirect | **accepted residual** — keep harness APIs stable |
| 7 | Dual `[mac]`/`[cuda]` extras + deferred CUDA path | `pyproject.toml` | none (oos) | **outOfScope** businessIntent — v0.2 CUDA/BTC/mlx |
| 8 | Reports under `benchmarks/reports/` are measurement SSOT (latest still **0.211**; initiative/handoff ~0.26 is stale prose) | `benchmarks/reports/2026-08-04/` | direct | **gates F2-G1/G2 + T-003 verifier** — file mean wins over chat/handoff numbers |
| 9 | Package/`CHANGELOG` already `0.1.0c0` while F2-G1/G2 open and git tag `v0.1.0-c0` absent | `pyproject.toml`, `CHANGELOG.md` | direct | **accepted split** — package bump ≠ gate met ≠ operator tag |
| 10 | `docs/roadmap.md` may say Phase C closed / WCSR carry-forward while plan F2-G1 still ≥0.70 | `docs/roadmap.md` | direct | **plan overrides roadmap for gates** — F2-G1/G2 stay open until WCSR+GO; T-003 continues |
| 11 | `fusion/syllabifier.py` on critical path but not in T-003 `outputs[]` | `titan_chordpro/fusion/syllabifier.py` | indirect | **accepted residual** — edit only if quality loop requires; otherwise leave outside T-003 fence |
| 12 | Older May reports still on disk; verifier picks lexicographic latest folder | `benchmarks/reports/2026-05-*` | indirect | **accepted** — T-003 must write a newer dated report so gate reads post-fix mean |

**Counts:** premises=14 (missing=0, false=0); impacts=12 (direct=5, indirect=5, none/oos=2)

## Reviews

- ground-truth: complete-with-findings | mode=ground-truth | fp=407e48463b15 | premises=14 | impacts=12 @ d2093cf (2026-08-31T00:19:26Z)

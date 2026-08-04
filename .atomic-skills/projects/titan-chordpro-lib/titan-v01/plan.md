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

## Ground-truth review

**Status:** complete-with-findings
**Codebase class:** populated
**Scanned:** titan_chordpro/, benchmarks/, tests/, scripts/, .github/workflows/, docs/, pyproject.toml → 120 product/test `.py` files under titan_chordpro+benchmarks+tests
**Commit:** a682a64
**At:** 2026-08-04T16:54:31Z

### A — Plan premises vs code

| # | Premise | Result | Evidence |
|---|---------|--------|----------|
| 1 | Protocol contracts live in `titan_chordpro/core/protocols.py` (orchestrator never imports torch/whisper directly) | ok | `titan_chordpro/core/protocols.py` exists; `titan_chordpro/orchestrator.py` imports protocols/cache/schemas, not torch |
| 2 | Seven ML engines under `titan_chordpro/engines/` (beat, separation, transcription, align, chord, lang PT/EN) | ok | dirs: beat/, separation/, transcription/, alignment/, chord/, lang/ with beatthis, htdemucs, whisper_cpp, torchaudio_align, chordino, portuguese, english |
| 3 | Phase C validation harness already in tree (`[validation]`, corpus, yt-dlp, runner/metrics/parser, divergence ranker, nightly) | ok | `pyproject.toml` optional-deps `validation`; `benchmarks/{corpus,audio_downloader,validation_runner,metrics,chordpro_parser,divergence_ranker}.py`; `.github/workflows/nightly.yml` |
| 4 | F-004 bass inversions via `bass_chroma` implemented | ok | `titan_chordpro/engines/chord/bass_chroma.py`; `tests/unit/engines/chord/test_bass_chroma.py` |
| 5 | Stage cache dump/load + orchestrator wiring | ok | `titan_chordpro/core/cache.py` `dump_stage`/`load_stage`; wired in `titan_chordpro/orchestrator.py` |
| 6 | T70 structural placement fixes landed (`parent_word_idx` reindex, melisma, InstrumentalLine, sectioner, stress, beat_snap) | ok | reindex in `orchestrator.py` (~L427); modules `fusion/{melisma,sectioner,stress,beat_snap,placer}.py`; sample report mean still low |
| 7 | Sample mean WCSR-majmin still ~0.21 (pre quality-loop) | ok | `benchmarks/reports/2026-08-04/top-divergences.md` Mean WCSR-majmin **0.211** (3 songs) |
| 8 | 3-song sample selection for T70 | ok | `scripts/sample_run.py` pins youtube_ids `9yZt5ekdceI`, `LvoYT0loqLQ`, `LL5Pak4zcuA` |
| 9 | Tags `v0.1.0-a0` and `v0.1.0-b1` exist | ok | `git rev-parse` → `9c7d407…`, `97f8ffb…` |
| 10 | CLI entrypoint `titan-chordpro` | ok | `pyproject.toml` `[project.scripts]`; `titan_chordpro/cli.py` |
| 11 | Factory real-engines integration test exists | ok | `tests/integration/test_factory_real.py` |
| 12 | Docs: roadmap + setup-validation + design/adopt sources | ok | `docs/roadmap.md`, `docs/setup-validation.md`, referenced superpowers paths present |
| 13 | Tag `v0.1.0-c0` exists | ok (not an existence premise) | **creates** via F2-G3 / operator after T-006 — currently absent by design |
| 14 | F3 user docs (`docs/method.md` etc.) exist | ok (not F2 premise) | missing today; F3 creates them |

### B — Code present, plan silent (impact candidates)

| # | Finding | Location | Impact | Disposition |
|---|---------|----------|--------|-------------|
| 1 | Stage cache (`dump_stage`/`load_stage`) affects every re-run of sample/quality loop | `titan_chordpro/core/cache.py`, `orchestrator.py` | direct | **task T-003** — reuse cache; invalidate/bypass when measuring post-fix WCSR; do not redesign cache API unless broken |
| 2 | `scripts/sample_run.py` + `scripts/render_from_url.py` are real validation entrypoints not listed as phase outputs | `scripts/` | direct | **task T-003** outputs include `scripts/sample_run.py`; render_from_url accepted residual for ad-hoc demos |
| 3 | `core/hardware.py` narrow backend probe is a curta-facing contract | `titan_chordpro/core/hardware.py` | indirect | **oos / accepted** — do not widen contract in F2; quality loop must not break `detect_backend` semantics |
| 4 | Five writer profiles share placement Document model | `titan_chordpro/writer/profiles/*` | indirect | **scopeBoundary T-003** — no wholesale profile rewrites; placement fixes stay in fusion/orchestrator |
| 5 | Nightly + CI workflows run corpus/validation paths | `.github/workflows/{nightly,ci}.yml` | indirect | **accepted residual** — keep harness APIs stable; T-003 does not own workflow rewrites unless flags break |
| 6 | `rich` is already a core dependency but CLI has no Progress/`--validate` yet | `pyproject.toml`, `titan_chordpro/cli.py` | direct | **task T-004** — CLI polish owns Progress + `--validate` |
| 7 | Package version still `0.1.0b2`; no CHANGELOG.md | `pyproject.toml`, `titan_chordpro/version.py` | direct | **task T-006** — bump to `0.1.0c0` + CHANGELOG; tag is operator |
| 8 | Dual `[mac]`/`[cuda]` extras + deferred CUDA path | `pyproject.toml` | none (oos) | **outOfScope** businessIntent — v0.2 CUDA/BTC/mlx |
| 9 | Reports under `benchmarks/reports/` (incl. top-divergences) are measurement SSOT for gates | `benchmarks/reports/2026-08-04/` | direct | **gates F2-G1/G2 + T-003 verifier** — mean WCSR + human GO on top-divergences |

**Counts:** premises=14 (missing=0, false=0); impacts=9 (direct=5, indirect=3, none/oos=1)

## Reviews

- ground-truth: complete-with-findings | mode=ground-truth | fp=eebf99ccc9d8 | premises=14 | impacts=9 @ a682a64 (2026-08-04T16:54:31Z)

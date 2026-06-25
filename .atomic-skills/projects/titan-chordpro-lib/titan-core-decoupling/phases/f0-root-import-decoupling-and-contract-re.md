---
schemaVersion: "0.1"
slug: titan-core-decoupling-f0-root-import-decoupling-and-contract-re
title: Root import decoupling and contract release
summary: Isola o import de hardware e publica o contrato externo mínimo.
goal: Replace the eager package-root imports with lazy public exports, prove
  `titan_chordpro.core.hardware` imports without ChordPro-domain modules, and
  publish the narrow hardware contract as version `0.1.0b2`.
status: done
branch: plan/titan-core-decoupling
started: 2026-06-24T18:13:43.582Z
lastUpdated: 2026-06-25T00:04:10Z
nextAction: Decide whether to mark/archive titan-core-decoupling plan.
parentPlan: titan-core-decoupling
phaseId: F0
tasksDone: 3
tasksTotal: 3
gatesMet: 4
gatesTotal: 4
weightDone: 7
weightTotal: 7
exitGates:
  - id: F0-G1
    description: Importing `titan_chordpro.core.hardware` in a fresh interpreter
      does not load blocked ChordPro-domain modules or lazy optional
      dependencies.
    status: met
    metAt: 2026-06-24T23:45:35Z
    verifier:
      kind: test
      runner: pytest
      pattern: tests/unit/core/test_import_isolation.py
    evidence:
      verifierKind: test
      verifiedAt: 2026-06-24T23:45:35Z
      passed: true
      exitCode: 0
      testsCollected: 3
      outputSummary: "env
        PATH=/Volumes/External/code/titan-chordpro-lib/.worktrees/titan-core-de\
        coupling/.venv/bin:$PATH pytest
        tests/unit/core/test_import_isolation.py: collected 3 items; 3 passed in
        0.48s"
    verifierLabel: "test: pytest tests/unit/core/test_import_isolation.py"
    evidenceSummary: passed · 3 tests · 2026-06-24
  - id: F0-G2
    description: The package top-level public API remains importable after lazy
      export conversion.
    status: met
    metAt: 2026-06-24T23:45:35Z
    verifier:
      kind: test
      runner: pytest
      pattern: tests/unit/core/test_import_isolation.py tests/unit/test_smoke.py
    evidence:
      verifierKind: test
      verifiedAt: 2026-06-24T23:45:35Z
      passed: true
      exitCode: 0
      testsCollected: 4
      outputSummary: "env
        PATH=/Volumes/External/code/titan-chordpro-lib/.worktrees/titan-core-de\
        coupling/.venv/bin:$PATH pytest tests/unit/core/test_import_isolation.py
        tests/unit/test_smoke.py: collected 4 items; 4 passed in 0.31s"
    verifierLabel: "test: pytest tests/unit/core/test_import_isolation.py tests/unit/…"
    evidenceSummary: passed · 4 tests · 2026-06-24
  - id: F0-G3
    description: The external infra contract is documented with the exact public
      hardware functions, exclusions, and target `0.1.0b2` version.
    status: met
    metAt: 2026-06-24T23:45:35Z
    verifier:
      kind: test
      runner: pytest
      pattern: tests/unit/test_public_infra_contract.py tests/unit/test_smoke.py
        tests/unit/core/test_hardware.py
    evidence:
      verifierKind: test
      verifiedAt: 2026-06-24T23:45:35Z
      passed: true
      exitCode: 0
      testsCollected: 13
      outputSummary: "env
        PATH=/Volumes/External/code/titan-chordpro-lib/.worktrees/titan-core-de\
        coupling/.venv/bin:$PATH pytest tests/unit/test_public_infra_contract.py
        tests/unit/test_smoke.py tests/unit/core/test_hardware.py: collected 13
        items; 10 passed, 3 skipped in 0.10s"
    verifierLabel: "test: pytest tests/unit/test_public_infra_contract.py tests/unit/…"
    evidenceSummary: passed · 13 tests · 2026-06-24
  - id: F0-G4
    description: The full existing test suite remains green after the lazy root
      export and public contract release changes.
    status: met
    metAt: 2026-06-24T23:45:35Z
    verifier:
      kind: test
      runner: pytest
      pattern: tests
    evidence:
      verifierKind: test
      verifiedAt: 2026-06-24T23:45:35Z
      passed: true
      exitCode: 0
      testsCollected: 489
      outputSummary: "uv run --extra dev --extra validation pytest tests: collected
        489 items / 5 skipped; 478 passed, 16 skipped, 20 warnings in 47.16s"
    verifierLabel: "test: pytest tests"
    evidenceSummary: passed · 489 tests · 2026-06-24
stack:
  - id: 1
    title: Root import decoupling and contract release
    type: task
    openedAt: 2026-06-24T18:13:43.582Z
tasks:
  - id: T0.1
    title: Add import-isolation regression coverage
    summary: Cria o teste que captura vazamento de imports do domínio musical.
    weight: 2
    description: Write the failing subprocess tests before changing package imports.
    status: done
    closedAt: 2026-06-24T23:40:40Z
    lastUpdated: 2026-06-24T23:40:40Z
    scopeBoundary:
      - Do not edit production modules, docs, version files, or existing
        hardware behavior in this task.
    acceptance:
      - A fresh subprocess import of `titan_chordpro.core.hardware` fails the
        test if `titan_chordpro.orchestrator`, `titan_chordpro.factory`,
        `titan_chordpro.fusion`, `titan_chordpro.core.schemas`, `torch`, or
        `pydantic` appears in `sys.modules`; a separate subprocess verifies
        `from titan_chordpro import transcribe, ChordProDocument, __version__`
        remains valid.
    verifier:
      kind: test
      runner: pytest
      pattern: tests/unit/core/test_import_isolation.py
    evidence:
      verifierKind: test
      verifiedAt: 2026-06-24T23:40:40Z
      passed: true
      exitCode: 0
      testsCollected: 3
      outputSummary: "env
        PATH=/Volumes/External/code/titan-chordpro-lib/.worktrees/titan-core-de\
        coupling/.venv/bin:$PATH pytest
        tests/unit/core/test_import_isolation.py: collected 3 items;
        tests/unit/core/test_import_isolation.py ... [100%]; 3 passed in 0.29s"
    outputs:
      - kind: file
        path: tests/unit/core/test_import_isolation.py
  - id: T0.2
    title: Implement lazy package-root exports
    summary: Torna os exports do pacote raiz lazy sem quebrar a API pública.
    weight: 2
    description: Replace eager root imports with PEP 562 lazy resolution while
      preserving the public names.
    status: done
    closedAt: 2026-06-24T23:40:40Z
    lastUpdated: 2026-06-24T23:40:40Z
    scopeBoundary:
      - Do not move `core.hardware`, do not change `orchestrator`, `fusion`,
        `factory`, `core.schemas`, `core.protocols`, engine behavior, or writer
        behavior.
    acceptance:
      - "`import titan_chordpro.core.hardware` no longer imports the blocked
        domain modules; `from titan_chordpro import transcribe,
        ChordProDocument, __version__` still succeeds; unknown package
        attributes raise `AttributeError`; type-checking imports do not execute
        at runtime."
    verifier:
      kind: test
      runner: pytest
      pattern: tests/unit/core/test_import_isolation.py tests/unit/test_smoke.py
    evidence:
      verifierKind: test
      verifiedAt: 2026-06-24T23:40:40Z
      passed: true
      exitCode: 0
      testsCollected: 4
      outputSummary: "env
        PATH=/Volumes/External/code/titan-chordpro-lib/.worktrees/titan-core-de\
        coupling/.venv/bin:$PATH pytest tests/unit/core/test_import_isolation.py
        tests/unit/test_smoke.py: collected 4 items;
        tests/unit/core/test_import_isolation.py ... [75%];
        tests/unit/test_smoke.py . [100%]; 4 passed in 0.41s"
    outputs:
      - kind: file
        path: titan_chordpro/__init__.py
  - id: T0.3
    title: Document and version the hardware contract
    summary: Documenta a API pública de hardware e alinha a versão beta.
    weight: 3
    description: Document the SemVer-stable hardware surface and align the
      downstream beta version to `0.1.0b2`.
    status: done
    closedAt: 2026-06-24T23:43:14Z
    lastUpdated: 2026-06-24T23:43:14Z
    scopeBoundary:
      - Do not document all of `titan_chordpro.core` as public, do not add a new
        package, and do not change runtime behavior beyond the version string.
    acceptance:
      - README names only `titan_chordpro.core.hardware.detect_backend`,
        `titan_chordpro.core.hardware.hardware_to_torch_device`, and
        `titan_chordpro.core.hardware.release_gpu_memory` as externally consumed
        infra API; `pyproject.toml`, `titan_chordpro/version.py`, and tests
        agree on version `0.1.0b2`; docs state that `titan_chordpro.core.cache`
        and ChordPro-domain modules are outside the `curta` contract.
    verifier:
      kind: test
      runner: pytest
      pattern: tests/unit/test_public_infra_contract.py tests/unit/test_smoke.py
        tests/unit/core/test_import_isolation.py
        tests/unit/core/test_hardware.py
    evidence:
      verifierKind: test
      verifiedAt: 2026-06-24T23:43:14Z
      passed: true
      exitCode: 0
      testsCollected: 16
      outputSummary: "env
        PATH=/Volumes/External/code/titan-chordpro-lib/.worktrees/titan-core-de\
        coupling/.venv/bin:$PATH pytest tests/unit/test_public_infra_contract.py
        tests/unit/test_smoke.py tests/unit/core/test_import_isolation.py
        tests/unit/core/test_hardware.py: collected 16 items; 13 passed, 3
        skipped in 0.63s"
    outputs:
      - kind: file
        path: README.md
      - kind: file
        path: pyproject.toml
      - kind: file
        path: titan_chordpro/version.py
      - kind: file
        path: tests/unit/test_smoke.py
      - kind: file
        path: tests/unit/test_public_infra_contract.py
parked: []
emerged: []
planTitle: Titan Core Hardware Decoupling
planActive: true
current: true
---

# Narrative / notes

Initiative for phase **F0 — Root import decoupling and contract release**.

## Decisions

_(record decisions here as they are made)_

## Links

_(plan doc, external refs)_

## Self-review against code-quality gates

- **G1 read-before-claim**: 3 tasks closed, each with `outputs[]` and `evidence.outputSummary` from the verifier run.
- **G2 soft-language**: scanned `nextAction`, task descriptions, and criterion descriptions; 0 violations in the completion claims.
- **G6 reference-or-strike**: 4 exit criteria met with `evidence.passed: true`; 0 deferred; 0 unverified.
- **Codex review**: local review-code gate ran at HEAD = `ca07f8d7ecb70bf48fa7c7143cf8641b09d164be`, verdict `0 blocker/critical/major/minor findings`, file `.atomic-skills/reviews/2026-06-24-2048-titan-core-decoupling-f0-local.md`.
- **Review gate (G2)**: recorded on the phase descriptor as `reviewGate: { status: passed, at: ca07f8d7ecb70bf48fa7c7143cf8641b09d164be, mode: local }`.
- **Lessons (G1)**: no lessons distilled (clean phase).

## Session handoff
- **Narrative:** F0 is closed: 3/3 tasks are `done`, 4/4 exit gates are `met`, and `.atomic-skills/projects/titan-chordpro-lib/titan-core-decoupling/plan.md` records `phases[0].reviewGate.at: ca07f8d7ecb70bf48fa7c7143cf8641b09d164be`. The code/doc/test payload landed in commit `ca07f8d7ecb70bf48fa7c7143cf8641b09d164be`. The plan is still `active` so the operator can decide whether to mark/archive `titan-core-decoupling`.
- **Decision log:** Routing stayed Mode 1 because `.atomic-skills/status/routing.json` is absent. `T0.1` produced the failing import-isolation regression first; its first verifier run failed with leaked modules from eager package-root imports, then `T0.2` changed only `titan_chordpro/__init__.py` and both `T0.1` and `T0.2` verifiers passed. `F0-G4` uses `uv run --extra dev --extra validation pytest tests` because `pytest tests` in the dev-only environment failed on `ModuleNotFoundError: No module named 'librosa'`. The review-code gate ran local inline with degraded isolation because this session's subagent tool policy allows subagents only when the user explicitly requests delegation.
- **Single nextAction:** Decide whether to mark/archive titan-core-decoupling plan.
- **Verbatim state:** Commands and observed outputs:
  - `rtk proxy env PATH=/Volumes/External/code/titan-chordpro-lib/.worktrees/titan-core-decoupling/.venv/bin:$PATH pytest tests/unit/core/test_import_isolation.py` -> `collected 3 items` and `3 passed in 0.48s`
  - `rtk proxy env PATH=/Volumes/External/code/titan-chordpro-lib/.worktrees/titan-core-decoupling/.venv/bin:$PATH pytest tests/unit/core/test_import_isolation.py tests/unit/test_smoke.py` -> `collected 4 items` and `4 passed in 0.31s`
  - `rtk proxy env PATH=/Volumes/External/code/titan-chordpro-lib/.worktrees/titan-core-decoupling/.venv/bin:$PATH pytest tests/unit/test_public_infra_contract.py tests/unit/test_smoke.py tests/unit/core/test_hardware.py` -> `collected 13 items` and `10 passed, 3 skipped in 0.10s`
  - `rtk uv run --extra dev --extra validation pytest tests` -> `collected 489 items / 5 skipped` and `478 passed, 16 skipped, 20 warnings in 47.16s`
  - `rtk node /Volumes/External/code/atomic-skills/scripts/validate-state.js .atomic-skills/projects/titan-chordpro-lib/titan-core-decoupling/plan.md .atomic-skills/projects/titan-chordpro-lib/titan-core-decoupling/phases/f0-root-import-decoupling-and-contract-re.md` -> `All 2 file(s) valid, 1 plan(s) cross-validated (schemaVersion 0.1/0.2)`
  - `rtk git commit -m "feat(core): decouple hardware import contract"` -> `ca07f8d feat(core): decouple hardware import contract`
  - Failed environment probe before validation extra: `rtk proxy env PATH=/Volumes/External/code/titan-chordpro-lib/.worktrees/titan-core-decoupling/.venv/bin:$PATH pytest tests` -> `ModuleNotFoundError: No module named 'librosa'`
- **Uncommitted changes:** clean tree after committing the phase-close state.

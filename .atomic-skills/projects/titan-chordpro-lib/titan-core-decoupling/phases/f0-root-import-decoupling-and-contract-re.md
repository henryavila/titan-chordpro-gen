---
schemaVersion: "0.1"
slug: titan-core-decoupling-f0-root-import-decoupling-and-contract-re
title: Root import decoupling and contract release
summary: Isola o import de hardware e publica o contrato externo mínimo.
goal: Replace the eager package-root imports with lazy public exports, prove
  `titan_chordpro.core.hardware` imports without ChordPro-domain modules, and
  publish the narrow hardware contract as version `0.1.0b2`.
status: active
branch: plan/titan-core-decoupling
started: 2026-06-24T18:13:43.582Z
lastUpdated: 2026-06-24T18:13:43.582Z
nextAction: "Start T0.1: Add import-isolation regression coverage"
parentPlan: titan-core-decoupling
phaseId: F0
tasksDone: 0
tasksTotal: 3
weightDone: 0
weightTotal: 7
gatesMet: 0
gatesTotal: 4
exitGates:
  - id: F0-G1
    description: Importing `titan_chordpro.core.hardware` in a fresh interpreter
      does not load blocked ChordPro-domain modules or lazy optional
      dependencies.
    status: pending
    verifier:
      kind: test
      runner: pytest
      pattern: tests/unit/core/test_import_isolation.py
  - id: F0-G2
    description: The package top-level public API remains importable after lazy
      export conversion.
    status: pending
    verifier:
      kind: test
      runner: pytest
      pattern: tests/unit/core/test_import_isolation.py tests/unit/test_smoke.py
  - id: F0-G3
    description: The external infra contract is documented with the exact public
      hardware functions, exclusions, and target `0.1.0b2` version.
    status: pending
    verifier:
      kind: test
      runner: pytest
      pattern: tests/unit/test_public_infra_contract.py tests/unit/test_smoke.py
        tests/unit/core/test_hardware.py
  - id: F0-G4
    description: The full existing test suite remains green after the lazy root
      export and public contract release changes.
    status: pending
    verifier:
      kind: test
      runner: pytest
      pattern: tests
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
    status: pending
    lastUpdated: 2026-06-24T18:13:43.582Z
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
    outputs:
      - kind: file
        path: tests/unit/core/test_import_isolation.py
  - id: T0.2
    title: Implement lazy package-root exports
    summary: Torna os exports do pacote raiz lazy sem quebrar a API pública.
    weight: 2
    description: Replace eager root imports with PEP 562 lazy resolution while
      preserving the public names.
    status: pending
    lastUpdated: 2026-06-24T18:13:43.582Z
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
    outputs:
      - kind: file
        path: titan_chordpro/__init__.py
  - id: T0.3
    title: Document and version the hardware contract
    summary: Documenta a API pública de hardware e alinha a versão beta.
    weight: 3
    description: Document the SemVer-stable hardware surface and align the
      downstream beta version to `0.1.0b2`.
    status: pending
    lastUpdated: 2026-06-24T18:13:43.582Z
    scopeBoundary:
      - Do not document all of `titan_chordpro.core` as public, do not add a new
        package, and do not change runtime behavior beyond the version string.
    acceptance:
      - README names only `titan_chordpro.core.hardware.detect_backend`,
        `titan_chordpro.core.hardware.hardware_to_torch_device`, and
        `titan_chordpro.core.hardware.release_gpu_memory` as externally consumed
        infra API; `pyproject.toml`, `titan_chordpro/version.py`, and tests
        agree on version `0.1.0b2`; docs state that
        `titan_chordpro.core.cache` and ChordPro-domain modules are outside the
        `curta` contract.
    verifier:
      kind: test
      runner: pytest
      pattern: tests/unit/test_public_infra_contract.py tests/unit/test_smoke.py
        tests/unit/core/test_import_isolation.py tests/unit/core/test_hardware.py
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
---

# Narrative / notes

Initiative for phase **F0 — Root import decoupling and contract release**.

## Decisions

_(record decisions here as they are made)_

## Links

_(plan doc, external refs)_

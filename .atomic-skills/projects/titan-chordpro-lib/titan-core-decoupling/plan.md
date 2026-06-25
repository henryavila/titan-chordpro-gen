---
schemaVersion: "0.1"
slug: titan-core-decoupling
title: Titan Core Hardware Decoupling
version: "1.0"
status: active
started: 2026-06-24T18:13:43.582Z
lastUpdated: 2026-06-25T00:41:30Z
branch: plan/titan-core-decoupling
currentPhase: F0
parallelismAllowed: false
principles:
  - id: P1
    title: Preserve top-level API
    body: "`from titan_chordpro import transcribe, ChordProDocument, __version__`
      remains valid while the runtime import cost moves to attribute access."
  - id: P2
    title: Keep the contract narrow
    body: only `titan_chordpro.core.hardware` becomes an external infra contract;
      `core.schemas`, `core.protocols`, `core.cache`, orchestration, fusion,
      writer, and engines stay out of scope.
  - id: P3
    title: Gate the boundary mechanically
    body: a fresh subprocess import-isolation test guards against future eager
      imports from the package root.
glossary:
  - term: import isolation
    definition: A fresh Python interpreter import that loads only the requested
      infra module and its allowed dependencies.
  - term: lazy root export
    definition: A package-level `__getattr__` export that resolves a public symbol
      on first attribute access instead of during package import.
  - term: infra contract
    definition: The documented external API surface that consumers can pin and rely
      on across compatible releases.
phases:
  - id: F0
    slug: titan-core-decoupling-f0-root-import-decoupling-and-contract-re
    title: Root import decoupling and contract release
    summary: Isola o import de hardware e publica o contrato externo mínimo.
    goal: Replace the eager package-root imports with lazy public exports, prove
      `titan_chordpro.core.hardware` imports without ChordPro-domain modules,
      and publish the narrow hardware contract as version `0.1.0b2`.
    dependsOn: []
    subPhaseCount: 3
    exitGate:
      summary: 4 criteria to meet
      criteria:
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
            outputSummary: "env PATH=/Volumes/External/code/titan-chordpro-lib/.worktrees/titan-core-decoupling/.venv/bin:$PATH pytest tests/unit/core/test_import_isolation.py: collected 3 items; 3 passed in 0.48s"
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
            outputSummary: "env PATH=/Volumes/External/code/titan-chordpro-lib/.worktrees/titan-core-decoupling/.venv/bin:$PATH pytest tests/unit/core/test_import_isolation.py tests/unit/test_smoke.py: collected 4 items; 4 passed in 0.31s"
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
            outputSummary: "env PATH=/Volumes/External/code/titan-chordpro-lib/.worktrees/titan-core-decoupling/.venv/bin:$PATH pytest tests/unit/test_public_infra_contract.py tests/unit/test_smoke.py tests/unit/core/test_hardware.py: collected 13 items; 10 passed, 3 skipped in 0.10s"
        - id: F0-G4
          description: The full existing test suite remains green after the lazy root
            export and public contract release changes.
          status: met
          metAt: 2026-06-24T23:45:35Z
          verifier:
            kind: shell
            command: uv run --extra dev --extra validation pytest tests
          evidence:
            verifierKind: shell
            verifiedAt: 2026-06-24T23:45:35Z
            passed: true
            exitCode: 0
            testsCollected: 489
            outputSummary: "uv run --extra dev --extra validation pytest tests: collected 489 items / 5 skipped; 478 passed, 16 skipped, 20 warnings in 47.16s"
    status: done
    reviewGate:
      status: passed
      mode: local
      at: ca07f8d7ecb70bf48fa7c7143cf8641b09d164be
      reviewFile: .atomic-skills/reviews/2026-06-24-2048-titan-core-decoupling-f0-local.md
      verifiedAt: 2026-06-25T00:04:10Z
references:
  - kind: file
    path: .atomic-skills/projects/titan-chordpro-lib/titan-core-decoupling/design.md
    label: Approved design
  - kind: file
    path: .atomic-skills/projects/titan-chordpro-lib/titan-core-decoupling/source.md
    label: Decompose source
  - kind: file
    path: /Volumes/External/code/curta/PATHFINDER-2026-06-23/11-titan-core-decoupling-prompt.md
    label: Curta decoupling prompt
  - kind: url
    path: https://github.com/henryavila/titan-chordpro-lib/pull/1
    label: "PR #1"
planActive: true
planTitle: Titan Core Hardware Decoupling
---

# Titan Core Hardware Decoupling

## 1. Context

Create a narrow, versioned public contract for Titan's hardware backend helpers
as `0.1.0b2` so the `curta` project can consume backend detection and GPU
memory release without importing Titan's ChordPro pipeline. The design is
intentionally limited to the package-root import fix plus documented
`core.hardware` contract.

## 2. Inviolable principles

- **P1 Preserve top-level API** — `from titan_chordpro import transcribe, ChordProDocument, __version__` remains valid while the runtime import cost moves to attribute access.
- **P2 Keep the contract narrow** — only `titan_chordpro.core.hardware` becomes an external infra contract; `core.schemas`, `core.protocols`, `core.cache`, orchestration, fusion, writer, and engines stay out of scope.
- **P3 Gate the boundary mechanically** — a fresh subprocess import-isolation test guards against future eager imports from the package root.

## 3. Phase tree

_(Canonical list in frontmatter `phases:`. aiDeck renders the tree visually when running.)_

## Self-review against code-quality gates

- **G1 read-before-claim**: existing-code claims live in the approved design at `design.md`; this plan body derives from the design and carries no additional source-code claims beyond the materialized task targets.
- **G2 soft-language**: scanned the plan and phase initiative for the configured banned phrases; 0 occurrences.
- **G6 reference-or-strike**: task and gate claims are backed by deterministic verifiers in the phase initiative and the source/design/Curta prompt are attached in `references[]`.

## Reviews

- internal: 1 finding applied @ a4c7781 (2026-06-24T18:17:49Z)
- codex: 4 findings applied @ .atomic-skills/reviews/2026-06-24-1734-titan-core-decoupling.md (2026-06-24T17:34:00-03:00)

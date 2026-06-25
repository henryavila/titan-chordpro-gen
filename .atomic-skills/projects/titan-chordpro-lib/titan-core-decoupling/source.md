# Titan Core Hardware Decoupling

Create a narrow, versioned public contract for Titan's hardware backend helpers so
the `curta` project can consume backend detection and GPU memory release without
importing Titan's ChordPro pipeline. The design is intentionally limited to the
package-root import fix plus documented `core.hardware` contract.

## Inviolable principles

- **P1 Preserve top-level API** — `from titan_chordpro import transcribe, ChordProDocument, __version__` remains valid while the runtime import cost moves to attribute access.
- **P2 Keep the contract narrow** — only `titan_chordpro.core.hardware` becomes an external infra contract; `core.schemas`, `core.protocols`, `core.cache`, orchestration, fusion, writer, and engines stay out of scope.
- **P3 Gate the boundary mechanically** — a fresh subprocess import-isolation test guards against future eager imports from the package root.

## Glossary

- **import isolation** — A fresh Python interpreter import that loads only the requested infra module and its allowed dependencies.
- **lazy root export** — A package-level `__getattr__` export that resolves a public symbol on first attribute access instead of during package import.
- **infra contract** — The documented external API surface that consumers can pin and rely on across compatible releases.

## F0 — Root import decoupling and contract release

Goal: Replace the eager package-root imports with lazy public exports, prove `titan_chordpro.core.hardware` imports without ChordPro-domain modules, and publish the narrow hardware contract as version `0.1.0b2`.

```yaml
exit_gate:
  - id: F0-G1
    description: Importing `titan_chordpro.core.hardware` in a fresh interpreter does not load blocked ChordPro-domain modules or lazy optional dependencies.
    verifier: { kind: test, runner: pytest, pattern: "tests/unit/core/test_import_isolation.py" }
  - id: F0-G2
    description: The package top-level public API remains importable after lazy export conversion.
    verifier: { kind: test, runner: pytest, pattern: "tests/unit/core/test_import_isolation.py tests/unit/test_smoke.py" }
  - id: F0-G3
    description: The external infra contract is documented with the exact public hardware functions, exclusions, and target `0.1.0b2` version.
    verifier: { kind: test, runner: pytest, pattern: "tests/unit/test_public_infra_contract.py tests/unit/test_smoke.py tests/unit/core/test_hardware.py" }
  - id: F0-G4
    description: The full existing test suite remains green after the lazy root export and public contract release changes.
    verifier: { kind: test, runner: pytest, pattern: "tests" }
```

### T0.1 Add import-isolation regression coverage

Write the failing subprocess tests before changing package imports.

- Files: tests/unit/core/test_import_isolation.py
- scopeBoundary: Do not edit production modules, docs, version files, or existing hardware behavior in this task.
- acceptance: A fresh subprocess import of `titan_chordpro.core.hardware` fails the test if `titan_chordpro.orchestrator`, `titan_chordpro.factory`, `titan_chordpro.fusion`, `titan_chordpro.core.schemas`, `torch`, or `pydantic` appears in `sys.modules`; a separate subprocess verifies `from titan_chordpro import transcribe, ChordProDocument, __version__` remains valid.
- verifier: { kind: test, runner: pytest, pattern: "tests/unit/core/test_import_isolation.py" }
- RED GREEN: The new import-isolation test fails before the lazy root export change and passes after T0.2.

### T0.2 Implement lazy package-root exports

Replace eager root imports with PEP 562 lazy resolution while preserving the public names.

- Files: titan_chordpro/__init__.py
- scopeBoundary: Do not move `core.hardware`, do not change `orchestrator`, `fusion`, `factory`, `core.schemas`, `core.protocols`, engine behavior, or writer behavior.
- acceptance: `import titan_chordpro.core.hardware` no longer imports the blocked domain modules; `from titan_chordpro import transcribe, ChordProDocument, __version__` still succeeds; unknown package attributes raise `AttributeError`; type-checking imports do not execute at runtime.
- verifier: { kind: test, runner: pytest, pattern: "tests/unit/core/test_import_isolation.py tests/unit/test_smoke.py" }
- RED GREEN: T0.1 supplies the failing boundary test, and this task makes it pass without broadening the public contract.

### T0.3 Document and version the hardware contract

Document the SemVer-stable hardware surface and align the downstream beta version to `0.1.0b2`.

- Files: README.md, pyproject.toml, titan_chordpro/version.py, tests/unit/test_smoke.py, tests/unit/test_public_infra_contract.py
- scopeBoundary: Do not document all of `titan_chordpro.core` as public, do not add a new package, and do not change runtime behavior beyond the version string.
- acceptance: README names only `titan_chordpro.core.hardware.detect_backend`, `titan_chordpro.core.hardware.hardware_to_torch_device`, and `titan_chordpro.core.hardware.release_gpu_memory` as externally consumed infra API; `pyproject.toml`, `titan_chordpro/version.py`, and tests agree on version `0.1.0b2`; docs state that `titan_chordpro.core.cache` and ChordPro-domain modules are outside the `curta` contract.
- verifier: { kind: test, runner: pytest, pattern: "tests/unit/test_public_infra_contract.py tests/unit/test_smoke.py tests/unit/core/test_import_isolation.py tests/unit/core/test_hardware.py" }
- RED GREEN: The smoke test fails on the old version string after the bump decision and passes once all version declarations are aligned.

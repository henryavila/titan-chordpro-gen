# Review: titan-core-decoupling F0 local gate

- Scope: WIP diff against `0616b287bb6dd88b012d320f0e2858e3d50af6cf`
- Mode: local
- Isolation: degraded; subagent spawn was not used because this Codex session policy only allows subagents when the user explicitly requests delegation.
- Files reviewed:
  - `titan_chordpro/__init__.py`
  - `titan_chordpro/version.py`
  - `README.md`
  - `pyproject.toml`
  - `tests/unit/core/test_import_isolation.py`
  - `tests/unit/test_public_infra_contract.py`
  - `tests/unit/test_smoke.py`
  - `.atomic-skills/projects/titan-chordpro-lib/titan-core-decoupling/plan.md`
  - `.atomic-skills/projects/titan-chordpro-lib/titan-core-decoupling/phases/f0-root-import-decoupling-and-contract-re.md`

## Findings

No blocker, critical, major, or minor findings.

## Evidence Read

- `titan_chordpro/__init__.py`: lazy `__getattr__` maps only `ChordProDocument` and `transcribe`, imports `__version__` eagerly from `titan_chordpro.version`, and raises `AttributeError` for unknown names.
- `tests/unit/core/test_import_isolation.py`: subprocess tests cover hardware submodule import isolation, root public API importability, and unknown attribute handling.
- `tests/unit/test_public_infra_contract.py`: README contract section is checked for exactly three public hardware symbols plus version alignment.
- `uv run --extra dev --extra validation pytest tests`: `478 passed, 16 skipped, 20 warnings in 47.16s`.

## Self-review against code-quality gates

- G1 read-before-claim: applied — review cited changed source files and verifier output above.
- G2 soft-language: applied — review verdict uses counts and cited evidence.
- G3 anti-tautology: applied — import-isolation tests fail if blocked modules appear or unknown attributes do not raise.
- G4 fixture realism: not applicable — no new fixtures.
- G7 anti-premature-abstraction: applied — no new abstraction beyond the package-level lazy export map.

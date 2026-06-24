# Titan Core Hardware Decoupling

## Context

This design exists because the `curta` project needs the Titan hardware backend
selection and GPU release helpers without importing Titan's ChordPro pipeline.

Evidence from the package root:

```python
from titan_chordpro.core.schemas import ChordProDocument
from titan_chordpro.orchestrator import transcribe
from titan_chordpro.version import __version__

__all__ = ["ChordProDocument", "transcribe", "__version__"]
```

verified_by: `titan_chordpro/__init__.py:1-5`.

Evidence from the orchestrator import surface:

```python
from titan_chordpro import factory
from titan_chordpro.core.cache import Stage, dump_stage, load_stage
from titan_chordpro.core.hardware import release_gpu_memory
from titan_chordpro.core.schemas import (
```

verified_by: `titan_chordpro/orchestrator.py:20-23`.

Evidence that the orchestrator imports the chord-fusion domain:

```python
from titan_chordpro.fusion import (
    melisma as melisma_module,
)
from titan_chordpro.fusion import (
    placer,
    sectioner,
    stress,
)
from titan_chordpro.fusion.melisma import Melisma
```

verified_by: `titan_chordpro/orchestrator.py:43-51`.

Evidence that `core.hardware` is already a narrow runtime surface:

```python
def detect_backend(prefer: str | None = None) -> Backend:
```

verified_by: `titan_chordpro/core/hardware.py:28`.

```python
def hardware_to_torch_device(backend: Backend) -> Any:
```

verified_by: `titan_chordpro/core/hardware.py:95`.

```python
def release_gpu_memory() -> None:
```

verified_by: `titan_chordpro/core/hardware.py:109`.

Fresh-interpreter evidence:

```text
['titan_chordpro.core.schemas', 'titan_chordpro.factory', 'titan_chordpro.fusion', 'titan_chordpro.fusion.beat_snap', 'titan_chordpro.fusion.melisma', 'titan_chordpro.fusion.onset_fusion', 'titan_chordpro.fusion.placer', 'titan_chordpro.fusion.sectioner', 'titan_chordpro.fusion.stress', 'titan_chordpro.fusion.syllabifier', 'titan_chordpro.orchestrator']
```

verified_by: `.venv/bin/python -c "import sys; b=set(sys.modules); import titan_chordpro.core.hardware; print(sorted(m for m in set(sys.modules)-b if m.startswith('titan_chordpro') and any(k in m for k in ('orchestrator','fusion','factory','schemas','engines'))))"`.

## Decisions

1. Titan will fix package-root eager imports by making `titan_chordpro.__init__`
   lazy for `transcribe` and `ChordProDocument`.
   verified_by: `titan_chordpro/__init__.py:1-5` shows those names are eager
   imports today.

2. Titan will preserve the public top-level API:
   `from titan_chordpro import transcribe, ChordProDocument, __version__`.
   verified_by: `titan_chordpro/__init__.py:5` shows those names are the package
   `__all__` today.

3. Titan will document a SemVer-stable external contract only for
   `titan_chordpro.core.hardware`, not for all of `titan_chordpro.core`.
   verified_by: `titan_chordpro/core/protocols.py:12-22` shows `core.protocols`
   imports `core.schemas`, so the whole `core` package is not a neutral
   infrastructure boundary.

4. The implementation will add an import-isolation regression test in a fresh
   subprocess.
   verified_by: the fresh-interpreter command in `Context` reproduces the leak
   and gives the exact failure class to guard.

5. The release target will be a backward-compatible beta bump for the current
   package, with the exact version selected during implementation.
   verified_by: `pyproject.toml:7` and `titan_chordpro/version.py:1` currently
   define `0.1.0b1`.

## Chosen approach

Chosen approach: make `titan_chordpro/__init__.py` use module-level
`__getattr__` and `__dir__`, keep `__version__` cheap, and resolve
`transcribe` plus `ChordProDocument` only on attribute access.

Weighed approaches:

- Lazy package root. This directly fixes the verified import path while keeping
  `core.hardware` in place. verified_by: `titan_chordpro/__init__.py:1-5` is the
  eager import point, and `titan_chordpro/core/hardware.py:18` shows hardware's
  only top-level Titan dependency is `core.exceptions`.
- Separate infrastructure package. This creates a cleaner long-term boundary
  but adds packaging, dependency, release, and migration work for a single known
  consumer. unverified: no second external consumer has been identified in this
  session.
- `curta` native adapter with duplicated backend logic. This avoids a dependency
  on Titan but leaves the verified Titan import bug unfixed for future consumers.
  verified_by: the fresh-interpreter command in `Context` shows the Titan package
  has an import-isolation regression independent of `curta`.

The chosen approach keeps the design reversible. A future package split remains
available after the minimal contract is measured in real use.

## Blast radius

The expensive-to-reverse decision is the declaration that
`titan_chordpro.core.hardware` is an external public contract.

Containment:

- The contract is limited to `detect_backend`, `hardware_to_torch_device`, and
  `release_gpu_memory`.
  verified_by: `titan_chordpro/core/hardware.py:28`, `titan_chordpro/core/hardware.py:95`,
  and `titan_chordpro/core/hardware.py:109`.
- `core.schemas`, `core.protocols`, `core.cache`, orchestration, fusion, writer,
  and engine modules remain outside the external infra contract.
  verified_by: `titan_chordpro/core/protocols.py:12-22` imports schemas, and
  `titan_chordpro/orchestrator.py:43-51` imports fusion modules.
- The regression test becomes the release gate for the contract. It fails when
  importing `titan_chordpro.core.hardware` loads `titan_chordpro.orchestrator`,
  `titan_chordpro.factory`, `titan_chordpro.fusion`, `titan_chordpro.core.schemas`,
  `torch`, or `pydantic`.
  verified_by: the fresh-interpreter command in `Context` shows the current leak.
- The `curta` integration keeps its own thin adapter and can remove the Titan
  dependency if only one call site survives.
  unverified: the single-call-site count is sourced from
  `/Volumes/External/code/curta/PATHFINDER-2026-06-23/11-titan-core-decoupling-prompt.md:141-142`.

## Non-goals

- This design does not extract a new package or namespace for shared runtime
  infrastructure.
- This design does not promise that every module under `titan_chordpro.core` is
  safe for external consumers.
- This design does not alter chord, fusion, writer, engine, cache, or orchestration
  behavior.
- This design does not make `core.cache` generic for `curta`.

## Rejected alternatives

- Extract a standalone infra package now. Rejected because no second external
  consumer is verified, and the current leak is resolved at the package root.
- Declare all of `titan_chordpro.core` public. Rejected because `core.protocols`
  imports `core.schemas`, which carries ChordPro-domain models.
- Leave Titan unchanged and duplicate hardware logic in `curta`. Rejected as the
  only Titan-side action because the import leak remains a verified package bug.
- Move `core.hardware` out of `core`. Rejected because the current path already
  has internal users and the import leak is not caused by the file location.

## Open questions

- Which exact version string will ship the contract: `0.1.0b2` or another
  release marker? Evidence needed: maintainer release decision before editing
  `pyproject.toml` and `titan_chordpro/version.py`.
- Does the package dependency list need an infra extra with fewer install-time
  dependencies? Evidence needed: `curta` dependency policy and installation
  constraints. This is outside the minimal import-isolation fix.
- Does `curta` keep the Titan dependency after its adapter has only one call
  site? Evidence needed: `curta` implementation review after the Titan release.

## Self-review against code-quality gates

- G1 read-before-claim: applied. Claims about eager imports, orchestrator imports,
  `core.protocols`, `core.hardware`, and current version cite file lines or the
  subprocess command output in this document.
- G2 soft-language: applied. Scanned manually for the configured banned English
  phrases; zero occurrences remain.
- G6 reference-or-strike: applied. Assertions about existing code carry
  `verified_by:`. External-consumer count and install-policy questions are marked
  `unverified:` or kept as open questions.

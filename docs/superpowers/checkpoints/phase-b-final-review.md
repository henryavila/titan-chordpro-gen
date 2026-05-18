# Phase B — Final Architectural Review (BEFORE tag v0.1.0-b0)

You are an Opus subagent doing the FINAL architectural review of Phase B. Sonnet has executed T35-T58 and is about to run T59 (tag step). Your job is to look at the whole forest — all 7 engines, the factory, the orchestrator, the CI matrix, the license posture — and decide whether Henry should proceed to tag.

## What was supposed to be built

The complete Phase B plan: `docs/superpowers/plans/2026-05-17-titan-v0.1-phase-b.md`.

## Snapshot Sonnet prepared for you

```bash
cat /tmp/phase-b-commits.txt        # git log v0.1.0-a0..HEAD --oneline
cat /tmp/phase-b-diff-stat.txt      # git diff v0.1.0-a0..HEAD --stat
cat /tmp/phase-b-test-output.txt    # pytest tests/ -v --tb=short
```

Also examine:
- `gh run list --limit 5` — recent CI runs (especially the `integration-tests-real` job).
- `titan_chordpro/engines/` — full tree.
- `titan_chordpro/factory.py` — selection logic.
- `titan_chordpro/cli.py` — Phase B flags.
- `.github/workflows/ci.yml` — matrix shape.
- `pyproject.toml` — extras + version bump (should still be `0.1.0a0` at this point; T59 bumps to `0.1.0b0`).

## Focus areas

### 1. Architecture diff vs Phase A (one-page)

Produce a one-page diff:
- What new modules exist? (`core/hardware.py`, `core/cache.py`, `engines/*`)
- What pre-existing modules were MODIFIED? (`factory.py`, `cli.py`, `tests/conftest.py`, `.github/workflows/ci.yml`, `pyproject.toml`)
- What pre-existing modules are UNTOUCHED? (`core/schemas.py`, `core/protocols.py`, `core/exceptions.py`, `fusion/*`, `writer/*`, `orchestrator.py`)
- Confirm: NO Protocol from Phase A was changed. If any was, that is a Critical drift — escalate immediately.

### 2. License-contagion sweep

- Chordino: GPL-2.0. Confirm subprocess-only linkage (no static link, no Python import that triggers GPL artifact loading at module load time).
- gruut: MIT. ✅
- g2p_en: Apache-2.0 / MIT-style. ✅
- BeatThis: MIT. ✅
- htdemucs_ft / python-audio-separator: MIT. ✅
- torchaudio / torch: BSD-3-Clause. ✅
- pywhispercpp / whisper.cpp: MIT. ✅

Verify the project `LICENSE` file is still MIT and the README's license badge is not misleading.

### 3. Factory selection correctness (32 combinations)

There are 5 ML stages (separation, transcription, alignment, chord, beat) + 2 lang variants = 7 selection points. Each can be (real, mock, force_mock). Walk through the matrix:

For each stage:
- When the optional dep is importable → factory returns the real engine?
- When the optional dep is NOT importable → factory returns the matching mock?
- When `force_mock=True` is passed → factory ALWAYS returns the mock, ignoring dep availability?
- When the real engine `__init__` raises `EngineUnavailableError` post-import (rare) → factory falls back to mock cleanly?

Confirm `_LAST_SELECTION` is populated for every stage on every call (drives `--list-engines`).

### 4. No torch at module top-level

Run:
```bash
grep -nE "^(import|from) torch" titan_chordpro/engines/**/*.py
```
Any hit is a Critical finding — every torch import must be inside a function so that `import titan_chordpro.engines.beat.beatthis` does not trigger torch import (which fails on a fresh box without `[mac]` extras).

Exceptions: `core/hardware.py` is allowed to import torch at module level (it has a try/except that converts ImportError to cached `"cpu"` backend).

### 5. CI matrix coverage gaps

Inspect the actual CI runs (`gh run list`):
- Did lint pass on the latest main? 
- Did `unit-tests` pass on all 4 cells (macos-14 + ubuntu-latest, py3.11 + py3.12)?
- Did `integration-tests-mocks` pass on both OS?
- Did `integration-tests-real` run? Did it pass, fail-with-continue-on-error, or skip everything?

Document explicitly:
- Is the CUDA path verified anywhere? (No — Henry has no CUDA in CI; flag as known gap for v0.2.)
- Is Python 3.12 + macOS-14 actually tested in `integration-tests-real`, or only in `unit-tests`?

### 6. End-to-end smoke

Re-run on Sonnet's machine:
```bash
pytest tests/integration/test_orchestrator.py::test_real_factory_smoke_on_silent_wav -v
```
Then:
```bash
titan-chordpro tests/fixtures/silent.wav --output /tmp/silent.chordpro --list-engines
cat /tmp/silent.chordpro
```
Confirm: a valid ChordPro document was produced, AND the `--list-engines` output shows which engines actually ran (mock vs real per stage).

### 7. Provenance integrity

In the produced ChordPro document, inspect `doc.provenance`:
- `titan_version` reads `"0.1.0a0"` (will be bumped to `"0.1.0b0"` in T59 Step 1)?
- `engines: EngineRegistry` lists each stage with the engine that ran?
- `confidence: list[StageConfidence]` has at least one entry per stage?

### 8. Docs sync

- Does `docs/roadmap.md` accurately reflect Phase B status (T59 will mark Weeks 4-7 as ✅)?
- Does `docs/setup-vamp.md` work end-to-end (an executor following it from scratch can run `test_chordino_smoke.py`)?
- Does `README.md` need updates? (Phase B did not touch README; mark as Phase D polish if updates are warranted.)

## What NOT to review

- v0.2 / v0.3 features — out of scope.
- Phase C plan content — that's a separate planning session.
- Performance / benchmarks — Phase C territory.

## Output format

```
# Phase B Final Architectural Review

## Status
[Ready to tag / Ready with caveats / NO — fix first]

## Architecture diff vs Phase A
[One paragraph]

## License posture
[Confirm — all 7 engines have license boundaries respected]
[VIOLATION — describe]

## Factory selection matrix
[Confirm — all 32 combinations behave correctly]
[Gap — describe untested cases]

## Module-level torch imports
[None — all engines lazy-import]
[Found — list file:line]

## CI matrix gaps
- Verified: [list]
- Gaps: [list]

## End-to-end smoke
[ChordPro produced — paste first 20 lines]
[Failure — describe]

## Findings
1. [File:line] — Issue — Severity (Critical/Significant/Minor)

## Recommendation
[Tag v0.1.0-b0]
[Tag v0.1.0-b0 with N follow-up issues filed]
[DO NOT tag — fix blockers first]

## Notes for Henry
```

Max 1200 words. This is the only chance to catch architectural drift before the tag becomes permanent reference.

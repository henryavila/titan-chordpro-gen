# Phase B — Week 4 Architectural Review (Bootstrap + BeatThis)

You are an Opus subagent doing architectural review of Phase B Week 4 (T35-T40: pyproject extras, hardware probe, engines skeleton, audio fixtures, BeatThisEngine). Sonnet has finished Week 4. Your job is to catch foundation bugs that would compound through every subsequent engine wrapper (T41/T44/T46/T48/T51/T52 all consume the patterns laid down here).

## What was supposed to be built

1. `docs/superpowers/plans/2026-05-17-titan-v0.1-phase-b.md` — Week 4 section (T35-T40 + Checkpoint 4).
2. `docs/superpowers/specs/2026-05-09-titan-v0.1-design.md` — Section 2.5 (BeatTrackingEngine Protocol).
3. `docs/research/04-beat-tracking.md` — BeatThis library rationale.

## What actually got built

```bash
ls -la titan_chordpro/core/hardware.py titan_chordpro/engines/
git log --oneline v0.1.0-a0..HEAD
pytest tests/unit/core/test_hardware.py tests/unit/engines/beat/ -v
pytest tests/integration/test_beatthis_smoke.py -v
```

Read in full:
- `titan_chordpro/core/hardware.py`
- `titan_chordpro/engines/beat/beatthis.py`
- `tests/conftest.py` (only the Phase B additions appended at end)
- `pyproject.toml` (the new extras)

## Focus areas

### 1. Hardware probe (T36)
- Does `detect_backend()` handle the 4-way matrix correctly? (torch present × mps available × cuda available × prefer override)
- Is the cache reset path documented so tests can re-probe?
- Does `prefer="cpu"` return "cpu" EVEN when torch is missing, or does it just bypass the import?
- Is `hardware_to_torch_device("cpu")` safe to call when torch is missing? (Should raise — torch is required to construct a device.)

### 2. Engine wrapper pattern (T39 sets the precedent)
- Is the lazy `_load_*` function pattern consistent? (Module import never touches torch / native libs.)
- Is `EngineUnavailableError` raised with `engine=` AND `cause=` populated?
- Does the wrapper expose `info` as a property (NOT a method) per Protocol?
- Is `info.backend` derived from the hardware probe (NOT hardcoded)?

### 3. BeatThis-specific (T39)
- Is the BPM estimate using the MEDIAN inter-beat interval (robust to outliers) NOT the mean?
- Are downbeat indices computed via nearest-neighbor mapping (downbeats may have float drift vs beats)?
- Does `bpm <= 0` raise `BeatTrackingError` (defensive against pathological inputs)?
- Does `beats=[]` raise `BeatTrackingError`? (Spec Section 5: fusion cannot proceed without beats.)

### 4. Audio fixtures (T38)
- Is `tone_a4_2s.wav` checked-in as binary (no LFS)?
- Is the fade-in/out long enough to avoid click artifacts (≥50ms)?
- Are the conftest fixtures discoverable from both `tests/unit/` and `tests/integration/`?

### 5. pyproject.toml (T35)
- Are `[mac]` and `[cuda]` extras separate (so a user installs only the wheel set they need)?
- Is the `beat-this` dep pinned to a git ref (since it has no PyPI release at time of writing)?
- Does `[dev]` STILL pass the install path without resolving `[mac]` deps (CI lint job needs this)?

### 6. Integration test discipline (T40)
- Does the test use `pytest.importorskip` rather than a `try/except ImportError` block (faster collection)?
- Does the test accept BOTH "engine raised BeatTrackingError" AND "engine returned a valid BeatGrid" outcomes on the degenerate tone fixture (it has no actual rhythm)?

## What NOT to review

- BeatThis model accuracy on real music — that is Phase C territory.
- CI matrix performance (job runtime) — Phase D polish.
- `[cuda]` extras being identical to `[mac]` — they are intentionally so for v0.1 since CUDA PyTorch is installed via separate index URL.

## Output format

```
# Phase B Week 4 Architectural Review

## Status
[Sound / Drift detected / Pattern bug found]

## Findings
1. [File:line] — Issue — Severity (Critical/Significant/Minor)
   Explanation 1-3 sentences. Cite the test that should catch it (existing or proposed).

## Pattern lock-in
[Confirm — Sonnet should use this exact pattern in T41/T44/T46/T48/T51/T52]
[Drift — flag the deviation BEFORE T41 starts]

## Continue to Week 5?
[Yes / Yes with caveats / NO — fix first]

## Notes for Henry
```

Max 600 words. The patterns established here (lazy import, EngineUnavailableError shape, info property shape) propagate to 6 more wrappers — extra scrutiny.

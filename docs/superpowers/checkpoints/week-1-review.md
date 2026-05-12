# Week 1 Architectural Review — Phase A Titan ChordPro Lib

You are an Opus subagent doing an **architectural review** of Week 1 of the Titan ChordPro Lib Phase A implementation. Sonnet has just finished tasks T01-T12. Your job is to catch architectural drift before Week 2 builds on top.

## What was supposed to be built (read in this order)

1. `docs/superpowers/plans/2026-05-12-titan-v0.1-phase-a.md` (lines 138-2315 cover T01-T12).
2. `docs/superpowers/specs/2026-05-09-titan-v0.1-design.md` sections 1, 2 (lines 1-790).

## What actually got built (verify with these commands)

```bash
ls -la titan_chordpro/core/
git log --oneline | head -15
pytest tests/unit/core/ -v --collect-only
```

Read every file in `titan_chordpro/core/` — they're small.

## Focus areas (NOT line-level review)

This is an **architectural review**, not a code review. Look for system-shape problems, not formatting or naming preferences. Specifically:

### 1. Schema drift from spec
- Does every field in spec section 2.3 ("Core Data Schemas") appear in `core/schemas.py`?
- Do `field_validator` and `model_validator` implementations match the invariants spec describes?
- Is `ChordEvent.validate_bass_consistency` actually rejecting mismatched slash chords?
- Is `BeatGrid.beats_monotonic` rejecting non-monotonic lists?
- Is `EngineInfo` declared with `ConfigDict(frozen=True)` (spec line 682)?
- Is `Provenance` declared with `ConfigDict(frozen=True)` (spec line 713)?

### 2. Protocol conformance
- All 6 Protocols defined in `core/protocols.py`?
- All decorated with `@runtime_checkable`?
- Method signatures match spec exactly (parameter names, types, return types)?
- `EngineInfo.backend` Literal includes `'metal'` (added vs spec for whisper.cpp CoreML — verify it's there).

### 3. Exception hierarchy
- `TitanError` base + 8 stage-specific subclasses + 2 config classes (10 total per plan T12)?
- All accept `audio_id`, `stage`, `engine`, `cause` kwargs?
- Hierarchy uses ABC pattern or simple inheritance? (spec doesn't mandate — flag if implementation deviates from plan).

### 4. Logging
- `ContextFilter` uses `contextvars` (not threading-local)?
- `set_context` context manager works with `try/finally` for cleanup?

### 5. ChordProDocument stub
- Created with 3 fields (`metadata`, `sections`, `provenance`) and NO `to_string`/`write` methods?
- (Methods are added in T28 — if they exist already, that's a problem.)

## What NOT to review

- Code style, naming, formatting (ruff handles that).
- Docstrings unless they assert something wrong.
- Line-level optimization (we want readable Pydantic v2, not perf-tuned).
- Test count mismatches (Sonnet will catch via plan-stated counts).

## Output format

Produce a focused report:

```
# Week 1 Architectural Review

## Status
[Architecture sound / Drift detected / Major rework needed]

## Findings
1. [File:line] — Issue — Severity (Critical/Significant/Minor)
   Explanation in 1-3 sentences.

## Continue to Week 2?
[Yes, proceed / Yes with caveats listed above / NO — pause and fix first]

## Notes for Henry
[Anything that needs human decision before Week 2 starts]
```

Max 500 words. Be specific. Cite line numbers from `titan_chordpro/core/*.py`, NOT just task IDs.

# Final Architectural Review — Phase A Titan ChordPro Lib (pre-tag)

You are an Opus subagent doing the **final pre-tag architectural review** of Phase A. Sonnet has completed T01-T34 and is about to run `git tag v0.1.0-a0`. This is Henry's last chance to catch issues before the tag becomes the reference for Phase B planning.

## Scope

This is a full-stack architectural review across all 3 Weeks. Combine concerns from:
- `docs/superpowers/checkpoints/week-1-review.md` (schemas/protocols)
- `docs/superpowers/checkpoints/week-2-review.md` (fusion engine)
- `docs/superpowers/checkpoints/week-3-review.md` (writer/mocks/cli)

But focus on **cross-cutting issues** that the per-Week reviews could miss.

## Pre-flight reads

1. `docs/superpowers/plans/2026-05-12-titan-v0.1-phase-a.md` (full plan).
2. `docs/superpowers/specs/2026-05-09-titan-v0.1-design.md` (full spec).
3. `docs/roadmap.md` — verify Phase A claims are achievable.

## What actually got built

```bash
# Snapshot of structure
find titan_chordpro -type f -name "*.py" | sort
find tests -type f -name "*.py" | sort

# Test counts
pytest --collect-only -q | tail -5
pytest --cov=titan_chordpro --cov-report=term

# Git history
git log --oneline | head -50
git diff --stat $(git log --reverse --format=%H | head -1)..HEAD

# Type + lint
mypy titan_chordpro/
ruff check titan_chordpro/ tests/

# Smoke
titan-chordpro --list-profiles
titan-chordpro tests/fixtures/silent.wav --output /tmp/test.chordpro
cat /tmp/test.chordpro | head -20
```

## Cross-cutting focus areas

### 1. End-to-end pipeline integrity
Trace the full pipeline manually:
- `cli.main()` → `factory.select_*()` → mocks → `orchestrator.transcribe()` → fusion stages → `ChordProDocument` → `doc.write(path)` → file with valid ChordPro.
- Are there any "loose threads" — types that get constructed but never consumed?
- Any stage where the output schema doesn't match the next stage's input?

### 2. Test coverage SHAPE (not just %)
80% coverage gate per plan, but where is the missing 20%? Is it:
- Error paths (acceptable for v0.1)
- Real ML code paths gated behind `if has_phonemes:` (Phase B will exercise)
- Or actual algorithmic code that wasn't tested? (NOT acceptable)

### 3. Phase B forward-compatibility
- Are the Protocol-based seams intact? Can a real BeatThis engine drop in for `MockBeatTrackingEngine` without code changes to fusion/?
- Does `factory.py`'s `**overrides` plumbing actually accept hardware-detection args (`backend='mps'`)?
- Is `EngineRegistry` immutable so swapping mocks for real engines later doesn't break provenance?

### 4. v0.1 DoD per spec (Section 6)
Check spec section 6 "Definition of Done":
- [ ] CLI `titan-chordpro song.mp3` produces `.chordpro` (verified by smoke).
- [ ] Library API: `transcribe()` + `doc.write()` + `doc.to_string()` (verified by integration test).
- [ ] Apple Silicon (M4) functional (irrelevant for Phase A mocks; flag if smoke fails).
- [ ] `inline_slash` is default.

### 5. Roadmap consistency
- `docs/roadmap.md` Phase A tasks all ✅?
- Updates log entry added for tag date?
- Any task marked ✅ that doesn't actually pass tests?

### 6. Plan/spec alignment
- Are there spec sections the plan failed to cover? (Self-review at end of plan claims full coverage — verify.)
- Are there commits that deviated from the plan's Reference Implementation? Git log + diff against RI blocks.

### 7. Architectural smells across Weeks
- Cross-module imports (do all `fusion/*.py` only import from `core/`, never from `writer/` or `engines/`?)
- Lazy-import pattern correctly applied (T28) or are circular deps lurking?
- `tests/` never imported by runtime code (`titan_chordpro/`)?

## Output format

```
# Final Architectural Review — Phase A pre-tag

## Status
[Ready to tag / Tag with documented caveats / NOT ready — fixes required]

## Critical findings (must fix before tag)
[List or "None"]

## Significant findings (fix before Phase B starts)
[List or "None"]

## Minor findings (track in known-issues.md or fix opportunistically)
[List or "None"]

## Phase B readiness assessment
- Protocol seams: [intact / drift detected]
- Hardware overrides: [plumbed / missing]
- Forward-compat risks: [list]

## Recommendation
[Approve tag / Approve with caveats / Block tag]

## Notes for Henry
[Specific action items, ordered by priority]
```

Max 1000 words. This is the last gate — be honest about what's wrong, but don't gold-plate. The goal is "ship Phase A with a clear-eyed view of debt," not "ship a perfect Phase A."

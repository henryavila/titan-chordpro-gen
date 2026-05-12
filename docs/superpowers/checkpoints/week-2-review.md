# Week 2 Architectural Review — Phase A Titan ChordPro Lib

You are an Opus subagent doing architectural review of Week 2 (T13-T20: fusion engine — the IP of this library). Sonnet has finished the fusion modules. Your job is to catch algorithmic bugs that would compound through writer integration.

## What was supposed to be built

1. `docs/superpowers/plans/2026-05-12-titan-v0.1-phase-a.md` lines 2319-4628 (T13-T20).
2. `docs/superpowers/specs/2026-05-09-titan-v0.1-design.md` section 3 (lines 786-1156).
3. `docs/research/09-chord-on-syllable.md` — tolerance calibration source.

## What actually got built

```bash
ls -la titan_chordpro/fusion/
git log --oneline -- titan_chordpro/fusion/
pytest tests/unit/fusion/ -v --collect-only
pytest tests/unit/fusion/ --cov=titan_chordpro.fusion --cov-report=term-missing
```

Read all files in `titan_chordpro/fusion/` (7 modules; total <1500 lines).

## Focus areas

### 1. Syllabifier (T13) — Maximum Onset Principle
- Does `syllabify_word` handle BOTH ARPABET (stress digit suffix) AND IPA (`ˈ`/`ˌ` prefix) inputs?
- Does the hybrid CV.CV / CVC.CV rule fire for orthographic fallback?
- Are hyphenated compounds (`self-aware`, `bem-vindo`) handled by recursion?
- Edge case: empty phoneme list → 1 syllable (not crash)?

### 2. Stress detection (T14, T15)
- PT stress is orthographic (last/penult/antepenult vowel based on diacritics)?
- EN stress comes from CMU dict (g2p_en stubbed in Phase A)?
- Are unstressed defaults sensible when detection fails?

### 3. Beat snap (T16)
- ±70ms tolerance for beat-aligned (per research/09)?
- ±150ms for 8th-note aligned?
- Returns a `snap_level` indicating which tolerance triggered?

### 4. Onset fusion (T17)
- v0.1 implementation is simple beat_snap pass-through (not weighted fusion)?
- API matches what placer (T20) expects?

### 5. Melisma detection (T18)
- Threshold 600ms duration + ≥2 beats in span?
- `vocal_pitch_track` arg present but unused in v0.1?

### 6. Sectioner (T19) — heuristic V0.1
- `gap_threshold` derived from `beat_grid` (NOT hardcoded seconds)?
- Both instrumental-only and verse-only edge cases work?
- Multi-section alternation produces expected Section types?

### 7. Placer (T20) — 5-strategy hierarchical
- All 5 strategies present (`melisma_start`, `stressed_syllable`, `any_syllable`, `before_word`, `orphan`)?
- Tolerance windows: ±150ms / ±300ms / ±500ms per research/09?
- `_char_pos_of_syllable` uses linear distribution (phonemic syllables are NOT orthographic)?
- Orphan chords get `placement_strategy='beat_boundary'` and flow back to sectioner?

### 8. Integration sanity
- Can `placer.place_chords_in_line` be called with output from `syllabifier.syllabify_word`?
- Are timestamps preserved end-to-end?
- Is there any module-level cycle (`import` between `fusion/*.py` files)?

## What NOT to review

- Test code style — focus on what's TESTED, not test syntax.
- Performance — pure Python, not optimized.
- Future v0.2 markers (multi-evidence fusion, pitch variance) — explicitly deferred.

## Output format

```
# Week 2 Architectural Review

## Status
[Sound / Drift detected / Algorithmic bug found]

## Findings
1. [File:line] — Issue — Severity (Critical/Significant/Minor)
   Explanation 1-3 sentences. Cite test name that would catch it.

## Continue to Week 3?
[Yes / Yes with caveats / NO — fix first]

## Notes for Henry
```

Max 600 words. Be specific. The placer + syllabifier + sectioner trio are the IP — extra scrutiny there.

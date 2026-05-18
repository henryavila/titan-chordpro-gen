# Phase B — Week 7 Architectural Review (Chordino + EN/PT Lang) — ESSENTIAL

You are an Opus subagent doing architectural review of Phase B Week 7 (T48-T53: Chordino, VAMP setup, PT/EN syllabifier wrappers). This is the ESSENTIAL checkpoint of Phase B:

- Chordino is the only engine running OUTSIDE Python (VAMP subprocess via sonic-annotator).
- Chordino is GPL-2.0 — wrong linkage leaks the license into the wheel.
- The lang wrappers consume Phase A `fusion/syllabifier.py` + `fusion/stress.py` public surface; a name mismatch here cascades into Phase C corpus validation.

## What was supposed to be built

1. `docs/superpowers/plans/2026-05-17-titan-v0.1-phase-b.md` — Week 7 section (T48-T53 + Checkpoint 7).
2. `docs/superpowers/specs/2026-05-09-titan-v0.1-design.md` — Section 2.4 (ChordRecognitionEngine), 2.6 (SyllabificationEngine).
3. `docs/research/03-chord-recognition.md` — Chordino vocab + GPL boundary rationale.
4. Phase A `titan_chordpro/fusion/syllabifier.py` + `fusion/stress.py` — the existing public surface the lang wrappers MUST consume.

## What actually got built

```bash
ls -la titan_chordpro/engines/chord/ titan_chordpro/engines/lang/ scripts/install_vamp.sh docs/setup-vamp.md
git log --oneline -- titan_chordpro/engines/chord/ titan_chordpro/engines/lang/ scripts/
pytest tests/unit/engines/chord/ tests/unit/engines/lang/ -v
pytest tests/integration/test_chordino_smoke.py tests/integration/test_lang_wrappers_smoke.py -v
```

Read in full:
- `titan_chordpro/engines/chord/chordino.py`
- `titan_chordpro/engines/lang/portuguese.py`
- `titan_chordpro/engines/lang/english.py`
- `scripts/install_vamp.sh`
- `titan_chordpro/fusion/syllabifier.py` (verify public surface — IS it what T51/T52 RIs assumed?)
- `titan_chordpro/fusion/stress.py` (same — IS `stressed_syllable_index` actually exported?)

## Focus areas

### 1. License contagion — Chordino (T48)
- Does the wrapper STATICALLY link any GPL artifact? (It should NOT — `chord_extractor` runs sonic-annotator as a subprocess, GPL stays at runtime boundary.)
- Are there any `import chord_extractor` calls at module top-level? (Should be lazy inside `_load_extractor`.)
- Is the GPL boundary documented in the module docstring AND in `docs/setup-vamp.md`?

### 2. Chord symbol normalization (T48)
- Does `_normalize_chord_symbol` correctly map all 24 majmin classes?
  - "C:maj" → "C", "G:min" → "Gm", "F:maj7" → "Fmaj7", "G:min7" → "Gm7", "N" → None, "" → None
- Does the colon stripping at the end handle non-quality-marked outputs (e.g., "C:7" → "C7")?
- Does `vocabulary` property return `"majmin"` (NOT `"sevenths"` or anything else — Chordino is baseline)?

### 3. ChordEvent end-time derivation (T48)
- Are end times derived as `start_of_next_chord` (NOT a fixed window)?
- Does the LAST chord run to the audio duration (probed via soundfile)?
- Are zero-duration events discarded (defensive against duplicate timestamps)?
- Does `bass_note=None` for every event (Phase B baseline — bass detection is Phase C)?

### 4. Lang wrapper fusion-surface dependencies (T51, T52)
- Does `titan_chordpro/fusion/syllabifier.py` actually export `syllabify_word_from_phonemes` and `group_arpabet_into_syllables`?
- Does `titan_chordpro/fusion/stress.py` actually export `stressed_syllable_index`?
- If ANY of these is missing, was it (a) added as a shim in a NEW commit before T51/T52 ran, OR (b) the wrapper renamed to match what exists?
- Are there any DUPLICATE implementations of syllabification or stress logic inside the lang wrappers? Phase A established these as the single source of truth — wrappers must call, not reimplement.

### 5. Lang wrapper timestamp interpolation (T51, T52)
- For a word with N syllables and duration D, does each syllable span `[start + D*i/N, start + D*(i+1)/N]`?
- Are spans contiguous (no gaps, no overlap)?
- Does the LAST syllable end exactly at `word.timestamp.end`?
- Single-syllable word → is_stressed = True (always)?

### 6. Stress detection consistency
- Does `is_stressed` in lang wrappers come from `fusion.stress` (PT) or ARPABET stress digits (EN)? NEVER from a parallel implementation.
- Does ARPABET `STRESSED_TOKEN1` lookup correctly identify primary stress (digit suffix `1`)?

### 7. Install script (T49)
- Does the script work non-interactively (no prompts)?
- Does it set `set -euo pipefail` at the top (fail-fast on any error)?
- Does it verify install success via `sonic-annotator -l | grep chordino`?
- Are the macOS and Linux paths correctly mapped to where VAMP plugins must live (`~/Library/Audio/Plug-Ins/Vamp` vs `~/vamp`)?

### 8. Integration test skip pattern (T50)
- Does `test_chordino_smoke.py` use BOTH `pytest.importorskip("chord_extractor")` AND `pytestmark = pytest.mark.skipif(not _vamp_host_present(), ...)`?
- Are skips silent (no spurious warnings on CI)?

## What NOT to review

- Chordino accuracy on real music — Phase C territory.
- gruut PT G2P quality vs reference — Phase C bug-fix.
- g2p_en CMU coverage vs OOV handling — Phase C.

## Output format

```
# Phase B Week 7 Architectural Review — ESSENTIAL

## Status
[Sound / Drift detected / GPL contagion / Phase A surface mismatch]

## Findings
1. [File:line] — Issue — Severity (Critical/Significant/Minor)

## License boundary
[Confirm — Chordino stays at runtime subprocess boundary]
[VIOLATION — describe specifically with file:line]

## Phase A surface dependency
[Confirm — all called names exist in fusion/syllabifier.py + fusion/stress.py]
[MISSING — list names + recommend shim vs rename]

## Continue to wrap-up?
[Yes / Yes with caveats / NO — fix first]

## Notes for Henry
```

Max 800 words. This is the only checkpoint with hard stops on license AND public-surface compat. Henry MUST receive the report before T54 starts.

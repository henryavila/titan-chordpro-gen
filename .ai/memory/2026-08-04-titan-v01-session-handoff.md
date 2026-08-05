# Handoff — titan-v01 F2 quality loop (2026-08-04)

## Branch
`plan/titan-v01` — plan/initiative branch. Quality work also lived on `impl/titan-quality-loop` (merged into plan).

## Active work
- Plan: `titan-v01` · Phase **F2** active · `executionMode: automate`
- Initiative: `titan-v01-f2-phase-c-validation-and-quality`
- **T-003** still **active** (WCSR gate ≥0.70 not met; quality loop human-driven)
- **T-004 / T-005 / T-006** closed with post-merge evidence (CLI --validate, README, 0.1.0c0)
- Exit gates F2-G1/G2/G3 still pending

## Quality loop progress (Ao olhar pra cruz / `9yZt5ekdceI`)
Eval-only song; **no song hardcodes** in product code.

| Stage | Bracket LCS majmin vs GT | Notes |
|-------|-------------------------:|-------|
| Pre-loop (broken) | ~57% | 1 syllable/word; 67 chords |
| After RC1–RC5 | ~92% | multi-syl, sectioner, reseg, placer |
| Chord engine v5 | ~93% events / ~92% brackets | primary-only reseg; bass after split |

### Root causes fixed (generic)
1. **RC1 syllabify:** MMS_FA numeric token IDs → orthographic fallback (`fusion/syllabifier.py`, `engines/lang/portuguese.py`)
2. **RC2 sectioner:** soft gaps + lyric-repetition chorus labels
3. **RC3/RC5:** chroma reseg multi-bar holds + span-aware placer windows
4. **Chord v5:** reseg only I/IV/V/vi/bVII (kill false Em iii); recompute bass after reseg

### Separation path (do not “fix” without new evidence)
- Chordino on **other+bass** only; vocals/drums excluded by design
- Full mix / other-only measured **worse** than other+bass

### Remaining chord errors (GT vs v5 sequence)
- **Faltam:** Am7 (procurei), G (2º derrama), Am7+C no outro final
- **Extras:** Am + C flutter em “clamar/abrir”
- **Diff raiz:** G→C/G (prostrarei), C/E→Em7, outro Am→Dm / C/E→Am7/E
- **Pior residual:** último **F hold ~14.7s** engole cadência final do outro
- Detailed report (if present locally): `/tmp/titan-quality-loop/COMPARE-gt-vs-v5.md`

## Operator workflow
Human-in-the-loop: generate cifra → operator validates → agents RCA/fix generic → re-render. Placement often OK; symbol/timeline still needs work especially **outro**.

## Resume
```bash
cd /Volumes/External/code/titan-chordpro-lib && git checkout plan/titan-v01
# re-render one song (correct cache_root is wired in scripts/render_from_url.py):
.venv-py312/bin/python scripts/render_from_url.py 9yZt5ekdceI \
  --title "Ao olhar pra cruz" --output /tmp/titan-quality-loop/ao-olhar.chordpro --language pt
# next agent focus: outro long-hold split + inversions C/E + remaining skip-G
```

# PROMOTE — chord explore → plan/titan-v01

**Date:** 2026-08-05  
**Branch:** `impl/chord-explore`  
**Status:** **conditional promote** (infra + optional BTC; **not** default engine flip)

## Paths to merge

```
titan_chordpro/engines/chord/btc.py
titan_chordpro/engines/chord/_btc/**          # vendored BTC (MIT LICENSE inside)
titan_chordpro/engines/chord/chroma_viterbi.py
titan_chordpro/engines/chord/chordino.py      # multi-pass reseg + force_decode_long_holds
titan_chordpro/factory.py                    # TITAN_CHORD_BACKEND
scripts/compare_chordpro_to_gt.py
scripts/redetect_chords_from_cache.py
tests/unit/engines/chord/test_btc.py
docs/research/chord-lane-2026-08-05.md
PROMOTE.md
```

**Do not merge:** `.atomic-skills/**`, default factory change to BTC, large `btc_model.pt` binary (cache path only).

## Metrics vs H0

| Hyp | mean match | song1 | song2 | song3 | Promote default? |
|-----|------------|-------|-------|-------|------------------|
| H0 Chordino | 0.765 | 0.933 | 0.857 | 0.505 | current |
| H1 multipass | 0.765 | 0.933 | 0.857 | 0.505 | yes (neutral) |
| H6 BTC | 0.758 | 0.952 | 0.929 | 0.392 | **no** (−11pp song3) |

## Risks

1. **BTC weights** must be installed out-of-band (`~/.cache/titan-chordpro/models/btc_model.pt`).
2. **BTC default** would regress song 3 hard — leave opt-in.
3. Vendored BTC code is research-grade; only majmin path is wired.
4. Multi-pass reseg slightly more CPU on long tracks (still << separation).

## Tests

```bash
.venv-py312/bin/python -m pytest tests/unit/engines/chord -q
```

## Operator actions after merge

1. Optional: copy BTC weights; try `TITAN_CHORD_BACKEND=btc` on Ao olhar / Teu santo nome.
2. Keep known-issues: song-class residuals, WCSR 0.70 stretch, GT not oracle.
3. Expand eval sample before any default flip.

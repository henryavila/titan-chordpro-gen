# Handoff — titan-v01 T70 (2026-08-04)

## Branch
`plan/titan-v01` — plan/initiative branch. Do not work Phase C on feat/audio-extra.

## Active work
- Plan: `titan-v01` · Phase **F2** active
- Initiative: `titan-v01-f2-phase-c-validation-and-quality`
- **NEXT: T-003** — T70 quality loop (detection + placement): reduce stacking, raise WCSR toward ≥0.70, Henry GO on divergences
- T-001 (harness) and T-002 (structural placement) marked done

## Sample quality (2026-08-04)
- Mean WCSR-majmin **~0.21** (gate 0.70) — reports gitignored under `benchmarks/reports/2026-08-04/`
- Structural fixes landed; product quality still blocked on chord detection + de-stack

## Structural fixes already in tree
- orchestrator: local parent_word_idx, melisma remap, orphan InstrumentalLines, expanded line spans
- sectioner: midpoint full coverage of chords
- stress: single-source immutable
- beat_snap: clamp end after snap
- metrics: sort intervals by onset

## Resume
```bash
cd /Volumes/External/code/titan-chordpro-lib && git checkout plan/titan-v01
# invalidate document cache then sample:
rm -f ~/.cache/titan-chordpro/cache/*/document.json
.venv-py312/bin/python scripts/sample_run.py
```

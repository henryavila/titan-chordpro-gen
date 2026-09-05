# Preview gen → titan-chordpro-ui

- Date: 2026-09-05
- Branch: `plan/preview-ui` (gen) + `feat/preview-dir` (ui)

## Decision

Do **not** vendor the Vue viewer into gen and do **not** start the Titan app.
Gen launches the sibling checkout (`TITAN_CHORDPRO_UI` or `../titan-chordpro-ui`)
with `TITAN_PREVIEW_DIR` set. The demo lists those charts at `/__titan_preview`.
Harness cifras written as `.txt` count as ChordPro for preview.

## Henry visual GO (2026-09-05)

Henry approved the **display** of the 2026-08-04 sample in ChordproViewer:

- `benchmarks/reports/2026-08-04/cifras/Ao-olhar-pra-cruz.txt`
- URL: `http://127.0.0.1:5173/?song=Ao-olhar-pra-cruz`

This is product approval of the generated chart **as seen in the UI**, not a
WCSR-majmin ≥ 0.70 close of titan-v01 F2 T-003. The chart text itself was
produced by the gen pipeline on 2026-08-04, not re-transcribed in the preview
session.

## CLI

```
titan-chordpro-gen preview                  # latest harness cifras/
titan-chordpro-gen preview path/to/file.cho
titan-chordpro-gen AUDIO --preview
```

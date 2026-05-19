# Validation harness setup

Phase C ships an opt-in validation harness that runs the full Titan pipeline against the iasdermelinda.com.br corpus (151 songs with YouTube URLs + native ChordPro ground truth) and scores accuracy via `mir_eval`.

## Install

```bash
pip install ".[mac,validation]"     # Apple Silicon
pip install ".[cuda,validation]"    # CUDA
pip install ".[validation]"         # CPU-only (slow; use for smoke runs)
```

The `[validation]` extra brings in `yt-dlp`, `mir_eval`, `librosa`, `scipy`, and `rich`. `librosa` is also part of `[mac]`/`[cuda]` — pip dedupes.

## Corpus location

Phase C uses `chordpros.csv/songs.csv` (155 rows, 151 with YouTube URLs). The file is NOT checked into git (owner-licensed PT-BR worship corpus). Place it at the repo root before running validation. The harness skips the 4 rows with empty `external_link` and logs the skip count in the report.

## Audio cache

Downloaded audio lives at `~/.cache/titan-chordpro/audio/<youtube_id>.<format>.<quality>` (yt-dlp managed). Default format: `bestaudio[ext=m4a]/bestaudio`. Re-running validation is idempotent — cached audio is not re-downloaded.

## Running validation

Single song dry-run (no yt-dlp; uses a fixture):

```bash
pytest tests/integration/test_validation_smoke.py -v
```

Full 151-song nightly (locally — takes ~3-5h on M-series):

```bash
BENCHMARKS_SAMPLE_SIZE=151 pytest -m corpus_full -v
```

Smaller sample (Henry's smoke runs):

```bash
BENCHMARKS_SAMPLE_SIZE=6 pytest -m corpus_full -v
```

Output: `benchmarks/reports/<YYYY-MM-DD>/top-divergences.md` (gitignored).

## Caveats

- yt-dlp is sensitive to YouTube TOS changes; if downloads fail wholesale, update yt-dlp first (`pip install -U yt-dlp`).
- `mir_eval.chord.evaluate` requires both alphabets to be in `mir_eval`'s syntax (`C:maj`, `G:min7`, `N`). The harness adapter handles conversion — see `benchmarks/metrics.py`.
- F-004 (slash chord) detection ships in Phase C but is *opportunistic*. If bass-stem chroma confidence is below 0.5, the chord defaults to root position. This is intentional: false-positive slash chords are worse than false negatives for chart readability.

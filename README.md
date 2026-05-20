# Titan ChordPro Lib

Audio-to-ChordPro Python library with chord-on-syllable placement.

**Status:** Phase C (validation harness + real-corpus testing) — under construction. Phase A (`v0.1.0-a0`, 2026-05-17) and Phase B (`v0.1.0-b0`, 2026-05-18) shipped. See `docs/roadmap.md`.

## Quick start — render a `.chordpro` from a YouTube URL

The fastest path from a URL to a chord chart is the `render_from_url.py` wrapper, which chains audio download → full ML pipeline (htdemucs / whisper.cpp / Chordino / torchaudio align / BeatThis / gruut) → ChordPro writer. Per-stage results are cached under `~/.cache/titan-chordpro/`, so re-runs are sub-second.

```bash
# Basic — URL or 11-char id; outputs ./<slug>.chordpro in cwd
.venv-py312/bin/python scripts/render_from_url.py 9yZt5ekdceI

# Custom title + output path + beat-grid diagnostic sidecar
.venv-py312/bin/python scripts/render_from_url.py https://youtu.be/9yZt5ekdceI \
    --title "Ao olhar pra cruz" \
    --output ao-olhar.chordpro \
    --beatgrid

# Full URL form also accepted
.venv-py312/bin/python scripts/render_from_url.py "https://www.youtube.com/watch?v=9yZt5ekdceI"
```

Flags: `--title` (embedded in `{title:}`; default = YouTube id), `--language` (default `pt`), `--output`, `--profile` (default `inline_slash` — run `titan-chordpro --list-profiles` for the full set), `--beatgrid` (writes `<slug>.beatgrid.txt` next to the chord chart).

Cold first run on a new URL is ~5 min (audio download + htdemucs separation + whisper medium + chord/beat/align). Same URL re-run is <1 s — the orchestrator hits the document-level cache directly.

## Operator scripts (`scripts/`)

| Script | Purpose |
|---|---|
| `render_from_url.py` | One-shot: YouTube URL → `.chordpro` (above). |
| `render_chordpros.py` | Re-render every cached `document.json` under `~/.cache/titan-chordpro/cache/` to `.txt` under `benchmarks/reports/<date>/cifras/`. Useful after a writer or sectioner change. |
| `render_beatgrid.py` | Diagnostic: same cached docs, but markers are `\|1 \|2 \|3 \|4` per measure beat instead of chord names — to visually validate the beat tracker and meter detector against the audio (independent of chord placement quality). Convention: `\|1 An` = beat before vocal; `\|1An` = beat on vocal head; `cego, \|4` = beat after. |
| `sample_run.py` | Run the full pipeline on three pinned PT-BR songs (`Ao olhar pra cruz`, `Teu santo nome`, `Jesus Tu És a Minha Vida`) and produce a divergence report. |
| `install_vamp.sh` | Build & install the Chordino Vamp plugin from `c4dm/nnls-chroma` source on macOS arm64 (upstream mirror was unmaintained at time of writing). |

All Python scripts run from the repo root with the project venv: `.venv-py312/bin/python scripts/<name>.py [args]`.

## Documentation

- [Roadmap](docs/roadmap.md) — Status and milestones
- [Design spec](docs/superpowers/specs/2026-05-09-titan-v0.1-design.md)
- [Research](docs/research/) — Background

## License

MIT

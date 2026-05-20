# Titan ChordPro Lib

Audio-to-ChordPro Python library with chord-on-syllable placement.

**Status:** Phase C (validation harness + real-corpus testing) — under construction. Phase A (`v0.1.0-a0`, 2026-05-17) and Phase B (`v0.1.0-b0`, 2026-05-18) shipped. See `docs/roadmap.md`.

**Supported platform:** macOS Apple Silicon (M-series) only at this time. Linux/CUDA paths are wired in `pyproject.toml` (extra `[cuda]`) and `scripts/install_vamp.sh` (Linux branch) but are not exercised in the current dev loop; treat them as best-effort. Windows is unsupported.

## Setup (fresh clone)

One command installs everything `scripts/render_from_url.py` needs to run: Homebrew prerequisites (`python@3.12`, `ffmpeg`, `git`, `vamp-plugin-sdk`, `boost`), the project virtualenv at `.venv-py312/`, all Python deps including the ML extras, and the Chordino Vamp plugin built from source for Apple Silicon.

```bash
./scripts/install.sh
```

The script is idempotent — safe to re-run. It does NOT pre-download ML model weights (whisper medium ~1.5 GB, htdemucs_ft, BeatThis, torchaudio MMS); those download lazily on first pipeline run and are cached locally. Cold first transcription on a new URL therefore takes ~5 min; re-runs hit `~/.cache/titan-chordpro/` and finish in well under a second.

Requirements before running the script:
- macOS Apple Silicon (M1/M2/M3/M4)
- [Homebrew](https://brew.sh) installed
- ~3 GB free disk for the venv + ML models that will download lazily on first use

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
| `install.sh` | End-to-end setup on macOS Apple Silicon (Homebrew tools + Python 3.12 venv + project deps + Chordino plugin). See [Setup](#setup-fresh-clone) above. |
| `render_from_url.py` | One-shot: YouTube URL → `.chordpro` (above). |
| `render_chordpros.py` | Re-render every cached `document.json` under `~/.cache/titan-chordpro/cache/` to `.txt` under `benchmarks/reports/<date>/cifras/`. Useful after a writer or sectioner change. |
| `render_beatgrid.py` | Diagnostic: same cached docs, but markers are `\|1 \|2 \|3 \|4` per measure beat instead of chord names — to visually validate the beat tracker and meter detector against the audio (independent of chord placement quality). Convention: `\|1 An` = beat before vocal; `\|1An` = beat on vocal head; `cego, \|4` = beat after. |
| `sample_run.py` | Run the full pipeline on three pinned PT-BR songs (`Ao olhar pra cruz`, `Teu santo nome`, `Jesus Tu És a Minha Vida`) and produce a divergence report. |
| `install_vamp.sh` | Build & install the Chordino Vamp plugin from `c4dm/nnls-chroma` source. Called by `install.sh`; can also be re-run standalone if the plugin needs to be rebuilt. |

All Python scripts run from the repo root with the project venv: `.venv-py312/bin/python scripts/<name>.py [args]`.

## Documentation

- [Roadmap](docs/roadmap.md) — Status and milestones
- [Design spec](docs/superpowers/specs/2026-05-09-titan-v0.1-design.md)
- [Research](docs/research/) — Background

## License

MIT

# Titan ChordPro Lib → **Gen**

[![CI](https://github.com/henryavila/titan-chordpro-lib/actions/workflows/ci.yml/badge.svg)](https://github.com/henryavila/titan-chordpro-lib/actions/workflows/ci.yml)
[![Nightly](https://github.com/henryavila/titan-chordpro-lib/actions/workflows/nightly.yml/badge.svg)](https://github.com/henryavila/titan-chordpro-lib/actions/workflows/nightly.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0c0-blue.svg)](CHANGELOG.md)

Audio-to-ChordPro Python **generator** with chord-on-syllable placement.

**Rebrand (locked):** this repo renames to **`titan-chordpro-gen`**. Sibling UI (view+edit) = **`titan-chordpro-ui`**, separate repo — not a monorepo. Execute: [`docs/REBRAND-HANDOFF.md`](docs/REBRAND-HANDOFF.md).

**Status:** Phase C (validation harness + quality loop) — closing toward tag `v0.1.0-c0`. Phase A (`v0.1.0-a0`) and Phase B (`v0.1.0-b0`/`b1`) shipped. See [`docs/roadmap.md`](docs/roadmap.md).

**Supported platform:** macOS Apple Silicon (M-series) only at this time. Linux/CUDA paths are wired in `pyproject.toml` (extra `[cuda]`) and `scripts/install_vamp.sh` (Linux branch) but are not exercised in the current dev loop; treat them as best-effort. Windows is unsupported.

## Public infra contract for `curta`

Version: `0.1.0c0`

The public infra API consumed outside this project is limited to these hardware
helpers:

- `titan_chordpro.core.hardware.detect_backend`
- `titan_chordpro.core.hardware.hardware_to_torch_device`
- `titan_chordpro.core.hardware.release_gpu_memory`

`titan_chordpro.core.cache` and ChordPro-domain modules are outside the `curta`
contract. ChordPro-domain modules are outside the `curta` contract whether they
live at package root, in orchestration/factory/fusion code, or under
`titan_chordpro.core.schemas`.

## Install

Apple Silicon (M-series, recommended for v0.1):

```bash
pip install ".[mac]"
```

Or one-shot setup (Homebrew tools + `.venv-py312` + Chordino Vamp plugin):

```bash
./scripts/install.sh
```

CUDA (Linux/Windows with NVIDIA GPU — best-effort):

```bash
pip install ".[cuda]"
```

To run the **validation harness** against the iasdermelinda corpus, add the
`validation` extra:

```bash
pip install ".[mac,validation]"
```

Chordino (VAMP plugin) is installed separately — see [`docs/setup-vamp.md`](docs/setup-vamp.md).

Requirements for `./scripts/install.sh`:
- macOS Apple Silicon (M1/M2/M3/M4)
- [Homebrew](https://brew.sh) installed
- ~3 GB free disk for the venv + ML models that download lazily on first use

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

# Or use the CLI entrypoint on a local file
titan-chordpro path/to/audio.mp3 --output song.chordpro --profile inline_slash
```

Flags: `--title` (embedded in `{title:}`; default = YouTube id), `--language` (default `pt`), `--output`, `--profile` (default `inline_slash` — run `titan-chordpro --list-profiles` for the full set), `--beatgrid` (writes `<slug>.beatgrid.txt` next to the chord chart).

Cold first run on a new URL is ~5 min (audio download + htdemucs separation + whisper medium + chord/beat/align). Same URL re-run is <1 s — the orchestrator hits the document-level cache directly.

## Validation harness

Phase C measures Titan against 151 PT-BR worship songs from
[iasdermelinda.com.br](https://iasdermelinda.com.br/musicas/listagem-banda) —
the corpus owner's native ChordPro charts serve as ground truth. The metric is
**WCSR-majmin** (weighted chord symbol recall at major/minor vocabulary) via
`mir_eval`.

| Tier   | Songs | Cadence | Metric target          |
|--------|-------|---------|------------------------|
| Tier 1 | —     | Per PR  | Unit/integration tests |
| Tier 2 | 151   | Nightly | WCSR-majmin ≥ 70%      |
| Tier 3 | 151   | Manual  | Top-20 review          |

### Quick-start (sample / corpus)

```bash
# Install harness deps
pip install ".[mac,validation]"

# Place corpus at chordpros.csv/songs.csv (not in git — owner-licensed)

# 3-song sample (pinned youtube_ids in scripts/sample_run.py)
.venv-py312/bin/python scripts/sample_run.py

# Or CLI: first N corpus rows with rich progress
titan-chordpro --validate chordpros.csv/songs.csv --sample-size 3

# Larger sample / full corpus (slow — hours on M-series)
titan-chordpro --validate chordpros.csv/songs.csv --sample-size 30
BENCHMARKS_SAMPLE_SIZE=151 pytest -m corpus_full -v
```

Reports land in `benchmarks/reports/<YYYY-MM-DD>/top-divergences.md` (gitignored)
with per-song WCSR, severity ranking, and mean WCSR-majmin.

**Full setup, audio cache layout, and caveats:**
[`docs/setup-validation.md`](docs/setup-validation.md).

## Operator scripts (`scripts/`)

| Script | Purpose |
|---|---|
| `install.sh` | End-to-end setup on macOS Apple Silicon (Homebrew tools + Python 3.12 venv + project deps + Chordino plugin). |
| `render_from_url.py` | One-shot: YouTube URL → `.chordpro` (above). |
| `render_chordpros.py` | Re-render every cached `document.json` under `~/.cache/titan-chordpro/cache/` to `.txt` under `benchmarks/reports/<date>/cifras/`. Useful after a writer or sectioner change. |
| `render_beatgrid.py` | Diagnostic: same cached docs, but markers are `\|1 \|2 \|3 \|4` per measure beat instead of chord names — to visually validate the beat tracker and meter detector against the audio (independent of chord placement quality). |
| `sample_run.py` | Run the full pipeline on three pinned PT-BR songs and produce a divergence report (WCSR sample). |
| `install_vamp.sh` | Build & install the Chordino Vamp plugin from `c4dm/nnls-chroma` source. Called by `install.sh`; can also be re-run standalone. |

All Python scripts run from the repo root with the project venv: `.venv-py312/bin/python scripts/<name>.py [args]`.

## Documentation

- [Roadmap](docs/roadmap.md) — Status and milestones
- [Validation harness setup](docs/setup-validation.md)
- [Vamp / Chordino setup](docs/setup-vamp.md)
- [Design spec](docs/superpowers/specs/2026-05-09-titan-v0.1-design.md)
- [Research](docs/research/) — Background

## License

MIT

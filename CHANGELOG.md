# Changelog

All notable changes to this project are documented in this file. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **Rebrand:** distribution / project name `titan-chordpro-lib` → **`titan-chordpro-gen`**.
- Python import package remains **`titan_chordpro`** (Option A — no caller import churn).
- CLI primary entrypoint is **`titan-chordpro-gen`**; **`titan-chordpro`** kept as a compatibility alias.
- Live docs / product title strings updated to **Titan ChordPro Gen**. GitHub repo and local folder rename remain operator-owned (see `docs/REBRAND-HANDOFF.md`).
- Follow-up (not this change): optional extract of a thin infra `-lib` package for `curta`; deferred.

## [0.1.0c0] — 2026-08-04

Phase C closeout package (`0.1.0c0`). Operator tags `v0.1.0-c0` after final review
(this release does **not** auto-tag).

### Added
- `benchmarks/` package: corpus loader, audio_downloader (yt-dlp), validation_runner
  (mir_eval), divergence_ranker, chordpro_parser, metrics.
- `engines/chord/bass_chroma.py` — librosa-based bass-note class extractor (F-004 / T64).
- `core/cache.py` `dump_stage` / `load_stage` — atomic JSON I/O for all 8 pipeline stages.
- `orchestrator.transcribe(cache=True, cache_root=...)` — full per-stage cache wiring (T66).
- CLI `--validate <csv> --sample-size <n>` + `rich.progress` bars (CLI-only; library
  import surface unchanged) (T71).
- `.github/workflows/nightly.yml` — cron 06:00 UTC, full 151-song Tier 2.5 run with
  cached audio + stages (T69).
- `[validation]` extra in pyproject (yt-dlp, mir_eval, librosa, scipy, rich).
- `corpus_full` pytest marker.
- README badges + Validation harness section linking `docs/setup-validation.md` (T72).
- Chord post-processing: short-flutter merge, adjacent same-majmin collapse, key
  estimation + diatonic snap (T70 quality loop).
- Placer anti-stack destack for multi-chord same `char_position` (T70).
- Orchestrator harmonic mix (`other` + `bass`) for Chordino input (spec) (T70).

### Changed
- Package version `0.1.0b2` → **`0.1.0c0`**.
- `engines/chord/chordino.py` — `supports_inversions` is `True`; emits `bass_note`
  when bass-stem chroma confidence ≥ 0.5 AND detected note differs from chord root.
- Whisper default model `medium` with word-level timestamps + anti-hallucination.
- Adaptive sectioner (median inter-word gap); document surfaces `beat_grid`.

### Fixed
- Codex F-004 — Chordino bass-note inversion derivation (deferred from v0.1.0-b1;
  closed in T64).
- Placement structural blockers: local `parent_word_idx` reindex, melisma remap,
  orphan InstrumentalLines, sectioner midpoint coverage, stress single-source,
  beat_snap end clamp (T70-iter5, 2026-08-04).

### Known issues
- Sample mean WCSR-majmin on the 3-song pinned set is still **below** the Tier 2
  gate of 0.70 (~0.26 after T70 quality loop; Chordino majmin + equal-interval GT
  methodology). Carry-over: better ACR (e.g. BTC-ISMIR19 in v0.2) and/or timed GT.

## [0.1.0b2] — 2026-06-25

- titan-core-decoupling F0: lazy package-root exports; `core.hardware` public
  contract for **curta**. Tag `v0.1.0b2`.

## [0.1.0-b1] — 2026-05-19

- Hot-fix on top of v0.1.0-b0; 8/9 Codex cross-model review findings applied.
  See `.atomic-skills/reviews/2026-05-18-2116-phase-a-b-full-codebase-vs-spec-codex.md`.

## [0.1.0-b0] — 2026-05-18

- Phase B: 7 ML engines + factory + CI matrix.

## [0.1.0-a0] — 2026-05-17

- Phase A: pure-Python core, mocks, fusion, writer, CLI.

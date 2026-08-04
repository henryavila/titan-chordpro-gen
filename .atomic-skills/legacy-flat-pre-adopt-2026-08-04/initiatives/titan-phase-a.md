---
initiative_id: titan-phase-a
title: Titan ChordPro Lib v0.1 Phase A Implementation
status: archived
branch: main
started: 2026-05-12
last_updated: 2026-05-17T12:00:00Z
plan_link: docs/superpowers/plans/2026-05-12-titan-v0.1-phase-a.md
next_action: "Phase A COMPLETE — begin Phase B (ML integration: BeatThis → htdemucs → whisper.cpp → Chordino)"
max_stack_depth_warning: 5
stack: []
tasks:
  T01: {title: "Project scaffold + Python package structure", status: done, closed_at: 2026-05-16T14:23:00Z}
  T02: {title: "Pre-commit hooks (ruff, mypy, pytest)", status: done, closed_at: 2026-05-16T14:24:00Z}
  T03: {title: "Test infrastructure (conftest + smoke test)", status: done, closed_at: 2026-05-16T14:25:00Z}
  T04: {title: "GitHub Actions CI pipeline", status: done, closed_at: 2026-05-16T14:26:00Z}
  T05: {title: "Core schema — TimeStamp and Confidence types", status: done, closed_at: 2026-05-16T14:27:00Z}
  T06: {title: "Event type schemas (Word, Phoneme, Syllable, Chord)", status: done, closed_at: 2026-05-16T14:30:00Z}
  T07: {title: "Beat tracking + pipeline result schemas", status: done, closed_at: 2026-05-16T14:32:00Z}
  T13: {title: "Syllabifier module (ARPABET/IPA + orthographic fallback)", status: done, closed_at: 2026-05-16T17:53:00Z}
  T14: {title: "Portuguese stress detector", status: done, closed_at: 2026-05-16T18:27:00Z}
  T15: {title: "English stress detector", status: done, closed_at: 2026-05-16T18:30:00Z}
  T16: {title: "Beat quantization with mir_eval tolerances", status: done, closed_at: 2026-05-16T18:32:00Z}
  T17: {title: "Simple fusion module (onset_fusion v0.1)", status: done, closed_at: 2026-05-16T18:34:00Z}
  T18: {title: "Heuristic sectioner with tempo-aware gap threshold", status: done, closed_at: 2026-05-16T18:34:00Z}
  T19: {title: "5-strategy hierarchical chord placement algorithm", status: done, closed_at: 2026-05-16T18:45:00Z}
  T20: {title: "Melisma detection (600ms + multi-beat heuristic)", status: done, closed_at: 2026-05-16T18:45:00Z}
  T21: {title: "OutputProfile Protocol + profiles registry", status: done, closed_at: 2026-05-17T09:00:00Z}
  T22: {title: "writer/serializer.py — shared rendering helpers", status: done, closed_at: 2026-05-17T09:01:00Z}
  T23: {title: "inline_slash profile (DEFAULT)", status: done, closed_at: 2026-05-17T09:02:00Z}
  T24: {title: "chordpro_ref profile with {sog}/{eog} grids", status: done, closed_at: 2026-05-17T09:03:00Z}
  T25: {title: "onsong profile", status: done, closed_at: 2026-05-17T09:04:00Z}
  T26: {title: "propresenter profile", status: done, closed_at: 2026-05-17T09:04:00Z}
  T27: {title: "songbookpro profile", status: done, closed_at: 2026-05-17T09:04:00Z}
  T28: {title: "document.py render/write helpers + ChordProDocument methods", status: done, closed_at: 2026-05-17T09:05:00Z}
  T29: {title: "Mock engines + conftest fixtures for all 6 protocols", status: done, closed_at: 2026-05-17T09:06:00Z}
  T30: {title: "factory.py — engine selection", status: done, closed_at: 2026-05-17T12:00:00Z}
  T31: {title: "orchestrator.py — transcribe() master pipeline", status: done, closed_at: 2026-05-17T12:00:00Z}
  T32: {title: "cli.py — argparse entry point titan-chordpro", status: done, closed_at: 2026-05-17T12:00:00Z}
  T33: {title: "benchmarks/export_corpus.py stub", status: done, closed_at: 2026-05-17T12:00:00Z}
  T34: {title: "Phase A wrap-up — fixture, roadmap, tag v0.1.0-a0", status: done, closed_at: 2026-05-17T12:00:00Z}
parked: []
emerged: []
---

## Context

Python library for generating ChordPro files from audio + lyrics via AI-based beat/chord detection.

**Week 1 (T01-T07):** Foundation complete — package structure, CI, core schemas (TimeStamp, Confidence, event types, BeatGrid, StemSet, Result).

**Week 2 (T13-T20):** Fusion engine complete — syllabifier, stress detectors (PT + EN), beat quantization, onset_fusion, heuristic sectioner, melisma detection, and 5-strategy hierarchical chord placer.

**Schema bugfix:** `beat_boundary` strategy renamed to `orphan` in ChordMarker to match spec (commit 7cb0672).

**Week 3 (T21-T34):** Writer + CLI + pipeline complete — 5 output profiles, serializer, factory, orchestrator, CLI entrypoint, mock engines, integration tests. 259 tests, 92.55% coverage, end-to-end smoke test passing. Tagged `v0.1.0-a0`.

## Notes

- Python 3.14 compatibility deviations documented (type: ignore removals, import merges)
- mir_eval used for beat quantization tolerances
- 5-strategy placer is core IP: stressed syllable → beat boundary → nearest beat → orphan → fallback
- Literal["majmin"...] annotation on MockChordRecognitionEngine.vocabulary required for Protocol conformance
- orchestrator._place_all_chords uses id(w) as word identity key for per-line syllable lookup

---
initiative_id: titan-phase-b
title: Titan ChordPro Lib v0.1 Phase B Implementation (ML engines, Mac-first)
status: archived
branch: main
started: 2026-05-17
last_updated: 2026-05-18T19:30:00Z
plan_link: docs/superpowers/plans/2026-05-17-titan-v0.1-phase-b.md
next_action: "Phase B COMPLETE — begin Phase C (corpus validation harness 30/147 songs, nightly cron, bass-note detection, cache JSON serialization)"
max_stack_depth_warning: 5
stack: []
tasks:
  T35: {title: "Phase B bootstrap — pyproject extras [mac]/[cuda] + dependencies", status: done, closed_at: 2026-05-17T18:00:00Z}
  T36: {title: "core/hardware.py — backend probe (mps/cuda/cpu) + cached singleton", status: done, closed_at: 2026-05-17T18:00:00Z}
  T37: {title: "engines/ package skeleton + EngineUnavailableError import audit", status: done, closed_at: 2026-05-17T18:00:00Z}
  T38: {title: "tests/fixtures audio helpers + checked-in tone_a4_2s.wav synthetic", status: done, closed_at: 2026-05-17T18:00:00Z}
  T39: {title: "engines/beat/beatthis.py — BeatTrackingEngine impl", status: done, closed_at: 2026-05-17T18:00:00Z}
  T40: {title: "BeatThis integration test (silent.wav + tone smoke)", status: done, closed_at: 2026-05-17T18:00:00Z}
  T41: {title: "engines/separation/htdemucs.py — SourceSeparationEngine via python-audio-separator", status: done, closed_at: 2026-05-17T20:00:00Z}
  T42: {title: "htdemucs integration test (4 stems generated)", status: done, closed_at: 2026-05-17T20:00:00Z}
  T43: {title: "core/cache.py — opt-in cache_dir(audio_id) helper", status: done, closed_at: 2026-05-17T20:00:00Z}
  T44: {title: "engines/transcription/whisper_cpp.py — TranscriptionEngine via pywhispercpp", status: done, closed_at: 2026-05-18T00:00:00Z}
  T45: {title: "whisper.cpp integration test (silent.wav empty words; tone no-crash)", status: done, closed_at: 2026-05-18T00:00:00Z}
  T46: {title: "engines/alignment/torchaudio_align.py — AlignmentEngine forced_align (MPS+CUDA)", status: done, closed_at: 2026-05-18T00:00:00Z}
  T47: {title: "torchaudio align integration test (synthetic vocal + transcript)", status: done, closed_at: 2026-05-18T00:00:00Z}
  T48: {title: "engines/chord/chordino.py — ChordRecognitionEngine via chord-extractor", status: done, closed_at: 2026-05-18T12:00:00Z}
  T49: {title: "scripts/install_vamp.sh + docs/setup-vamp.md", status: done, closed_at: 2026-05-18T12:00:00Z}
  T50: {title: "chordino integration test with skipif(no_vamp)", status: done, closed_at: 2026-05-18T12:00:00Z}
  T51: {title: "engines/lang/portuguese.py — SyllabificationEngine via gruut", status: done, closed_at: 2026-05-18T12:00:00Z}
  T52: {title: "engines/lang/english.py — SyllabificationEngine via g2p_en", status: done, closed_at: 2026-05-18T12:00:00Z}
  T53: {title: "Lang wrappers integration tests (both EN + PT)", status: done, closed_at: 2026-05-18T12:00:00Z}
  T54: {title: "factory.py rewrite — real engine selection + mock fallback", status: done, closed_at: 2026-05-18T16:00:00Z}
  T55: {title: "Orchestrator integration test with real engines via factory", status: done, closed_at: 2026-05-18T16:00:00Z}
  T56: {title: "CLI extension — --device flag + engine summary print", status: done, closed_at: 2026-05-18T16:00:00Z}
  T57: {title: ".github/workflows/ci.yml activation (matrix macOS-14 + ubuntu)", status: done, closed_at: 2026-05-18T16:00:00Z}
  T58: {title: "CI VAMP handling — apt-get vamp on ubuntu OR skip", status: done, closed_at: 2026-05-18T16:00:00Z}
  T59: {title: "Phase B wrap-up — roadmap update + tag v0.1.0-b0", status: done, closed_at: 2026-05-18T17:30:00Z}
  F01: {title: "Codex F-001 — propagate force_mock to syllabification factory", status: done, closed_at: 2026-05-18T19:00:00Z}
  F02: {title: "Codex F-002 — Chordino receives harmonic mix (not bass stem)", status: done, closed_at: 2026-05-18T19:00:00Z}
  F03: {title: "Codex F-003 — preserve N markers as interval boundaries", status: done, closed_at: 2026-05-18T19:00:00Z}
  F04: {title: "Codex F-004 — plumb backend to audio_separator (htdemucs)", status: done, closed_at: 2026-05-18T19:00:00Z}
parked: []
emerged: []
---

## Context

Phase A entregou pure-Python core (schemas, protocols, fusion engine, writer, mocks, orchestrator, CLI). Tagged `v0.1.0-a0` em 2026-05-17 com 259 testes, 92.55% cobertura.

Phase B substitui os 6 mocks por engines reais sem trocar nenhuma interface — Protocols garantem compatibilidade:

| Stage | Mock (Phase A) | Real (Phase B) |
|---|---|---|
| Separation | `MockSourceSeparationEngine` | `htdemucs_ft` via `python-audio-separator` |
| Transcription | `MockTranscriptionEngine` | `whisper.cpp` via `pywhispercpp` |
| Alignment | `MockAlignmentEngine` | `torchaudio.functional.forced_align` (MPS+CUDA) |
| Chord recognition | `MockChordRecognitionEngine` | Chordino via `chord-extractor` (VAMP plugin) |
| Beat tracking | `MockBeatTrackingEngine` | BeatThis (CPJKU 2024, MIT, PyTorch CUDA+MPS) |
| Syllabification | `MockSyllabificationEngine` | `engines/lang/portuguese.py` (gruut) + `engines/lang/english.py` (g2p_en) |

Scope decisions locked-in (2026-05-17 conversation):
- **Engines**: todos 7 (BeatThis + htdemucs_ft + whisper.cpp + torchaudio align + Chordino + EN + PT)
- **Chordino**: setup script + skip-if-VAMP-missing; sem bundling GPL no wheel
- **Integration tests**: smoke-only com fixtures sintéticas (silent.wav + tone curto checked-in); corpus real adiado para Phase C
- **CI**: ativar matrix macOS-14 + ubuntu-latest (encerra débito Phase A)

**Phase B wrap-up (2026-05-18):** Todas as 25 tasks (T35-T59) entregues + 4 Codex cross-model fixes (F-001 a F-004) aplicados pós-tag dry-run. 318 testes passando, 10 skipped, ~85% cobertura. 7 ML engine wrappers integrados com transparent mock fallback. Tagged `v0.1.0-b0` (annotated). 6 MIT/BSD libs + Chordino GPL isolado via subprocess.

## Notes

- Mesmo workflow Sonnet-executa + Opus-revisa por Week via prompt files em `docs/superpowers/checkpoints/phase-b-*.md`
- Tag final: `v0.1.0-b0`
- Phase C (validation harness) e Phase D (pre-release) ficam para planos separados
- Protocols de Phase A não mudam — se algum engine precisar mudar Protocol, escalate (não improvisar)
- Codex cross-model review (gpt-5) catched 4 actionable findings (F-001..F-004) — applied pre-release; full report em `.atomic-skills/reviews/2026-05-18-1558-phase-b-pre-tag-codex.md`
- 3 Minor findings deferred (Pydantic object.__setattr__ hack, PT/EN init asymmetry, install_vamp sudo prompt) — decisão separada
- htdemucs stem-resolver substring fragility documentada no plan
- CUDA path não verificado em CI (sem hardware CUDA)

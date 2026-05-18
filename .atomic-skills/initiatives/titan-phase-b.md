---
initiative_id: titan-phase-b
title: Titan ChordPro Lib v0.1 Phase B Implementation (ML engines, Mac-first)
status: active
branch: main
started: 2026-05-17
last_updated: 2026-05-17T14:11:06Z
plan_link: docs/superpowers/plans/2026-05-17-titan-v0.1-phase-b.md
next_action: "Sonnet executes T35 (Phase B bootstrap — pyproject extras [mac]/[cuda] + deps)"
max_stack_depth_warning: 5
stack: []
tasks:
  T35: {title: "Phase B bootstrap — pyproject extras [mac]/[cuda] + dependencies", status: done}
  T36: {title: "core/hardware.py — backend probe (mps/cuda/cpu) + cached singleton", status: done}
  T37: {title: "engines/ package skeleton + EngineUnavailableError import audit", status: done}
  T38: {title: "tests/fixtures audio helpers + checked-in tone_a4_2s.wav synthetic", status: done}
  T39: {title: "engines/beat/beatthis.py — BeatTrackingEngine impl", status: done}
  T40: {title: "BeatThis integration test (silent.wav + tone smoke)", status: done}
  T41: {title: "engines/separation/htdemucs.py — SourceSeparationEngine via python-audio-separator", status: pending}
  T42: {title: "htdemucs integration test (4 stems generated)", status: pending}
  T43: {title: "core/cache.py — opt-in cache_dir(audio_id) helper", status: pending}
  T44: {title: "engines/transcription/whisper_cpp.py — TranscriptionEngine via pywhispercpp", status: pending}
  T45: {title: "whisper.cpp integration test (silent.wav empty words; tone no-crash)", status: pending}
  T46: {title: "engines/alignment/torchaudio_align.py — AlignmentEngine forced_align (MPS+CUDA)", status: pending}
  T47: {title: "torchaudio align integration test (synthetic vocal + transcript)", status: pending}
  T48: {title: "engines/chord/chordino.py — ChordRecognitionEngine via chord-extractor", status: pending}
  T49: {title: "scripts/install_vamp.sh + docs/setup-vamp.md", status: pending}
  T50: {title: "chordino integration test with skipif(no_vamp)", status: pending}
  T51: {title: "engines/lang/portuguese.py — SyllabificationEngine via gruut", status: pending}
  T52: {title: "engines/lang/english.py — SyllabificationEngine via g2p_en", status: pending}
  T53: {title: "Lang wrappers integration tests (both EN + PT)", status: pending}
  T54: {title: "factory.py rewrite — real engine selection + mock fallback", status: pending}
  T55: {title: "Orchestrator integration test with real engines via factory", status: pending}
  T56: {title: "CLI extension — --device flag + engine summary print", status: pending}
  T57: {title: ".github/workflows/ci.yml activation (matrix macOS-14 + ubuntu)", status: pending}
  T58: {title: "CI VAMP handling — apt-get vamp on ubuntu OR skip", status: pending}
  T59: {title: "Phase B wrap-up — roadmap update + tag v0.1.0-b0", status: pending}
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

## Notes

- Mesmo workflow Sonnet-executa + Opus-revisa por Week via prompt files em `docs/superpowers/checkpoints/phase-b-*.md`
- Tag final: `v0.1.0-b0`
- Phase C (validation harness) e Phase D (pre-release) ficam para planos separados
- Protocols de Phase A não mudam — se algum engine precisar mudar Protocol, escalate (não improvisar)

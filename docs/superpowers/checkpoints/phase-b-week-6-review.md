# Phase B — Week 6 Architectural Review (Transcription + Alignment)

You are an Opus subagent doing architectural review of Phase B Week 6 (T44-T47: whisper.cpp + torchaudio forced_align). This is the most complex 2-stage handoff in the pipeline — whisper.cpp returns `phonemes=None`, which means the orchestrator MUST call the alignment engine. A bug on either side breaks the fusion engine's chord placement (it needs phoneme-grained timing).

## What was supposed to be built

1. `docs/superpowers/plans/2026-05-17-titan-v0.1-phase-b.md` — Week 6 section (T44-T47 + Checkpoint 6).
2. `docs/superpowers/specs/2026-05-09-titan-v0.1-design.md` — Section 2.2 (TranscriptionEngine), 2.3 (AlignmentEngine).
3. `docs/research/02-transcription-and-alignment.md` — torchaudio MMS_FA bundle, whisper.cpp license/perf rationale.

## What actually got built

```bash
ls -la titan_chordpro/engines/transcription/ titan_chordpro/engines/alignment/
git log --oneline -- titan_chordpro/engines/transcription/ titan_chordpro/engines/alignment/
pytest tests/unit/engines/transcription/ tests/unit/engines/alignment/ -v
pytest tests/integration/test_whisper_cpp_smoke.py tests/integration/test_torchaudio_align_smoke.py -v
```

Read in full:
- `titan_chordpro/engines/transcription/whisper_cpp.py`
- `titan_chordpro/engines/alignment/torchaudio_align.py`

## Focus areas

### 1. whisper.cpp wrapper (T44)
- Does the wrapper return `phonemes=None` (NOT `phonemes=[]`) when whisper.cpp ran but produced words? The Protocol distinguishes — the orchestrator uses `is None` to decide whether to call alignment.
- Is the centisecond → second conversion exact (`t0 / 100.0`, not `t0 / 100` integer division)?
- Are inverted t0/t1 ranges clamped (whisper.cpp emits these for very short segments)?
- Is empty `text` ("") skipped (whitespace-only segments)?
- Is `EngineInfo.backend` set to `"cpu"` (whisper.cpp does not dispatch via torch even on Metal)?

### 2. torchaudio forced_align wrapper (T46) — highest-risk
- Is `_FRAME_SECONDS = 320/16000 = 0.02` exactly? (Off-by-stride bugs are silent.)
- Is the model loaded via `torchaudio.pipelines.MMS_FA` (NOT `WAV2VEC2_ASR_BASE_960H`, which lacks a `blank_id`)?
- Does `_run_forced_align` correctly group consecutive identical token frames into a single span (CTC collapse)? Inspect the loop in `_run_forced_align`.
- Are blank-token frames excluded from spans (they are not real phonemes)?
- Is the audio resampled to 16kHz BEFORE feeding the model (`MMS_FA` expects 16kHz)?
- Is the audio mixed down to mono BEFORE the model call (`waveform.mean(dim=0, keepdim=True)`)?
- Does `align(vocals, words=[])` short-circuit and return empty result (avoids tokenizing nothing)?

### 3. Word boundary derivation (T46)
- Is the word span correctly the union of its phoneme spans (`min(start) ... max(end)`)?
- When a word has no aligned phonemes (silence run-on), does the wrapper KEEP the original word event (vs dropping it)?
- Is `WordEvent.source_engine` set to `"torchaudio_align"` for refined words (NOT preserving `"whisper_cpp"`)? The Provenance must reflect which engine last touched it.

### 4. Schema invariants
- All `TimeStamp` instances satisfy `end >= start`? Pydantic catches this but better to assert in the wrapper too.
- All `PhonemeEvent.parent_word_idx` are valid indices into the refined words list?
- All `Confidence` values are in `[0, 1]`?

### 5. Exception wrapping
- `RuntimeError` from torchaudio (e.g., MPS missing operator) is wrapped as `AlignmentError` with `cause=`?
- The wrapper does NOT mask exceptions silently (no `try/except Exception: pass`)?

### 6. MPS-specific gotchas
- Is `emissions.cpu()` called before `forced_align` (forced_align may not have MPS kernel)?
- Does the model `.to(device)` work when device is mps but the model has unsupported ops? Document the fallback path.

## What NOT to review

- whisper.cpp model accuracy on real lyrics — Phase C.
- Per-language tokenizer quality (MMS is multilingual, baseline) — Phase C bug-fix territory if PT alignment drifts.
- `_g2p` performance on long words — Phase C.

## Output format

```
# Phase B Week 6 Architectural Review

## Status
[Sound / Drift detected / Frame-conversion bug / CTC-collapse bug found]

## Findings
1. [File:line] — Issue — Severity (Critical/Significant/Minor)

## CTC collapse correctness
[Confirm — group_consecutive logic in _run_forced_align is correct]
[Bug found — describe specifically]

## Continue to Week 7?
[Yes / Yes with caveats / NO — fix first]

## Notes for Henry
```

Max 700 words. Extra scrutiny on the frame→seconds conversion AND the CTC collapse loop — those are the two places where a one-character bug invalidates every alignment.

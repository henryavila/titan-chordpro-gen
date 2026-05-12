# Lyrics Transcription and Word-Level Alignment (2024-2026)

> Research conducted for Titan ChordPro Lib. Goal: transcribe lyrics from vocal stems with word-level (or syllable-level) timestamps accurate enough for ChordPro chord placement.
> Last updated: 2026-05-08

## Overview

Lyrics transcription with reliable word-level timestamps is the single hardest unsolved sub-problem in this pipeline. The state of the art in 2026 is still **Whisper-family models on top of music source separation (Demucs/MDX)**, with a separate forced-alignment step to fix Whisper's notoriously sloppy timestamps. No music-native ASR has caught up — the field has effectively converged on "make the input look more like speech, then use Whisper".

Two facts dominate the design space:

1. **Whisper is trained for speech, not song.** Even on isolated vocal stems, Whisper exhibits significantly higher WER on sung material than on spoken material, drops non-lexical vocables (oohs, ahs, ad-libs), and is prone to hallucinations on artifacts produced by source separators. The 2024 *Schubert Winterreise* study measured **WER 0.56 sung vs WER 0.14 spoken** on identical text, performed by the same Whisper model — a ~4× degradation purely from the singing style.
2. **Whisper's native timestamps are unreliable.** They are produced as an inference-time trick over predicted timestamp tokens, with no explicit timestamp loss in training. For chord placement we need ≤100 ms accuracy at the word boundary, and ideally syllable-level alignment. This is what dedicated alignment tools (WhisperX wav2vec2, stable-ts DTW, CrisperWhisper, MFA, CTC-segmentation) exist to fix.

The recommended pattern in 2024–2026 literature and in production tools:

```
audio → Demucs (vocal stem) → VAD (RMS or silero) → Whisper large-v3 → forced alignment (wav2vec2 / DTW)
```

This stack gives an open-source SOTA on the Jam-ALT long-form ALT benchmark.

## ASR Engines Investigated

### openai/whisper (reference)
- **Backbone:** Whisper (encoder-decoder Transformer, 1.55 B for large-v3; 809 M for large-v3-turbo).
- **License:** MIT.
- **Repository:** https://github.com/openai/whisper — quasi-frozen since 2023, used as the reference checkpoint store. New checkpoints (large-v3, large-v3-turbo) released through HuggingFace.
- **Hardware:** PyTorch — CUDA, CPU, MPS (Apple Silicon, slower than CUDA, more memory-hungry, batch size limited to ~4 at 12 GB).
- **Speech WER on LibriSpeech:** large-v3 ≈ 2.7 % (clean); 8–12 % WER on real-world English.
- **Music/lyrics WER:** WER 0.56 on Schubert Winterreise; ~20–24 % WER on Jam-ALT depending on configuration.
- **Timestamp granularity:** Segment + word (via cross-attention DTW; not trained for timestamps).
- **Strengths:** Reference quality; checkpoints reused by every other engine here.
- **Weaknesses:** Slow PyTorch implementation; hallucinations; mediocre timestamps.

### faster-whisper (CTranslate2)
- **Backbone:** Whisper (re-implemented in CTranslate2 C++/CUDA).
- **License:** MIT.
- **Repository:** https://github.com/SYSTRAN/faster-whisper — actively maintained (last push 2025-11-19, v1.2.1 released 2025-10-31, 22.7 k stars).
- **Hardware:** CUDA 12 + cuDNN 9 (GPU); CPU with AVX2 / Apple Accelerate; **no MPS, no Metal** — issue #911 (2024-07) explicitly: `ValueError: unsupported device mps`. CTranslate2 supports ROCm via a community AMD blog post but it is not in mainline.
- **Speech WER:** Identical to Whisper (uses same checkpoints, quantization optional).
- **Music/lyrics WER:** Inherits Whisper's behaviour.
- **Timestamp granularity:** Word-level via DTW on cross-attention; the official docs admit "timestamp accuracy cannot be guaranteed compared to other implementations".
- **Strengths:** ~4× faster than reference Whisper at large-v3, 8 GB VRAM for large-v3 with int8_float16, integrates with WhisperX and stable-ts.
- **Weaknesses:** **Hard non-starter for Apple Silicon GPU acceleration** — runs CPU only on Mac. This is the single biggest portability constraint for a CUDA+Mac dual-target library.

### whisper.cpp
- **Backbone:** Whisper (re-implemented in C/C++ via ggml/GGUF).
- **License:** MIT.
- **Repository:** https://github.com/ggml-org/whisper.cpp — extremely active (last push 2026-05-07, v1.8.4 in March 2026, 49.5 k stars).
- **Hardware:** Metal (Apple Silicon GPU), CoreML (Apple Neural Engine, ~3× speed-up over CPU), CUDA, Vulkan, OpenVINO, ROCm/HIP, ARM NEON, x86 AVX, POWER VSX, Ascend NPU. Most portable backend in the ecosystem.
- **Music/lyrics WER:** Same Whisper checkpoints, same WER as faster-whisper.
- **Timestamp granularity:** Segment + word (`-ml 1` for word-level boundaries; uses Whisper's native timestamp tokens, not DTW by default — DTW is implemented in some forks).
- **Strengths:** Best **single backend** for cross-platform deployment; CoreML+Metal beats faster-whisper on M-series for many models; compiles to a static binary with no Python.
- **Weaknesses:** Less mature word-timestamp pipeline than stable-ts/WhisperX; ecosystem of Python wrappers is thinner; CoreML model conversion is a separate manual step (`coremltools`, ANE compilation lazy on first run).

### mlx-whisper (ml-explore)
- **Backbone:** Whisper, ported to Apple's MLX framework.
- **License:** MIT.
- **Repository:** https://github.com/ml-explore/mlx-examples (whisper subdir). Active (last push 2026-04-06).
- **Hardware:** Apple Silicon only (unified memory, MLX runs on Metal). No CUDA path.
- **Music/lyrics WER:** Same Whisper checkpoints (re-quantized to MLX format on HF `mlx-community`).
- **Timestamp granularity:** Word-level via `word_timestamps=True`.
- **Strengths:** ~30–40 % faster than faster-whisper on Apple Silicon according to community benchmarks (Medium / mac-whisper-speedtest). Native unified memory model = no host-device copies for the audio tensor. **Lightning-Whisper-MLX** claims 4× faster than mlx-whisper using batched/quantized variants.
- **Weaknesses:** Apple-only; ecosystem is young — no first-class diarization or alignment integration; word-timestamp implementation lags behind stable-ts in stability.

### WhisperX (m-bain)
- **Backbone:** faster-whisper (CTranslate2) + wav2vec2 phoneme alignment + pyannote VAD/diarization.
- **License:** BSD-2-Clause.
- **Repository:** https://github.com/m-bain/whisperX — active, v3.8.5 in April 2026, 21.8 k stars.
- **Hardware:** CUDA-first (claims 70× realtime large-v2 batched). CPU mode supported. **Apple Silicon: falls back to CPU**; documented as not utilizing MPS — community workaround is `--device cpu --compute_type int8`.
- **Speech WER:** Inherits faster-whisper.
- **Music/lyrics WER:** Inherits faster-whisper, but with significantly tighter timestamps because of wav2vec2 alignment (the WhisperX paper, Interspeech 2023, reports lowest insertion-error rate on Kincaid46 + TED-LIUM).
- **Timestamp granularity:** **Phoneme-level via wav2vec2 forced alignment**, then aggregated to word-level. This is the most precise word-timestamp method in the open-source ecosystem when the alignment model has the right vocabulary.
- **Strengths:** Best-in-class word timestamps; integrated VAD removes most Whisper hallucinations; multilingual alignment models for EN/FR/DE/ES/IT (torchaudio) and many more on HuggingFace.
- **Weaknesses:** CUDA-only effective deployment. Cannot align tokens that don't exist in the wav2vec2 vocabulary (numerals, currency, proper nouns spelled out) — they are dropped from the timestamp output.

### Distil-Whisper
- **Backbone:** Distilled Whisper (fewer decoder layers).
- **License:** MIT.
- **Repository:** https://github.com/huggingface/distil-whisper — last push 2025-01-08; 4 k stars; cadence has slowed.
- **Hardware:** Same as Whisper (PyTorch, transformers, optionally ONNX).
- **Speech WER:** ~1 % absolute behind large-v3 on speech.
- **Music/lyrics WER:** **[UNCERTAIN]** — no published evaluation on lyrics benchmarks. Distillation included only segment-level timestamps; word-level uses untuned attention heads and is known to be less accurate than parent.
- **Strengths:** ~6× faster than large-v3.
- **Weaknesses:** Word timestamps explicitly weaker than Whisper proper; no music tuning. Not recommended where chord-syllable accuracy is needed.

### Insanely-Fast-Whisper
- **Backbone:** Whisper via HuggingFace `transformers` + `torch.compile` + flash attention; can use BetterTransformer.
- **License:** Apache-2.0.
- **Repository:** https://github.com/Vaibhavs10/insanely-fast-whisper — last push 2025-10-25, 12.9 k stars.
- **Hardware:** CUDA + MPS (this is one of the few PyTorch wrappers that genuinely runs on MPS for Whisper). CPU.
- **Speech WER:** Same as Whisper.
- **Music/lyrics WER:** Same as Whisper.
- **Timestamp granularity:** Word-level via Whisper's built-in `return_timestamps="word"`.
- **Strengths:** Single tool that runs on both CUDA and Apple MPS without different backends.
- **Weaknesses:** Word timestamps inherit Whisper's flaws; no built-in alignment refinement.

### Whisper Large-v3-Turbo
- **Backbone:** Same encoder as large-v3, decoder reduced from 32 → 4 layers (809 M total).
- **Speech WER:** "minor degradation" vs large-v3; described as "as good as large-v2 at 6× the speed".
- **Music/lyrics WER:** **[UNCERTAIN]** — no Jam-ALT row published yet for turbo variants (research targets large-v2 / large-v3 mainly).
- **Recommendation:** Useful for real-time / preview pass; for the production ChordPro pass, large-v3 at higher cost is safer.

### CrisperWhisper (nyrahealth)
- **Backbone:** Fine-tuned Whisper with adjusted tokenizer + DTW alignment.
- **License:** Non-commercial research license (check repo before shipping).
- **Repository:** https://github.com/nyrahealth/CrisperWhisper. Paper Interspeech 2024.
- **Speech WER:** Verbatim ASR (preserves fillers, disfluencies).
- **Timestamp granularity:** Word-level + filler events; reports SOTA mIoU on word-segmentation benchmarks (especially with narrow temporal collars). Specifically designed to address Whisper's poor timestamp behaviour on pauses.
- **Music/lyrics WER:** **[UNCERTAIN]** — evaluated on speech.
- **Note:** Worth experimenting if the wav2vec2 alignment route (WhisperX) hits the numeral/proper-noun limitation; CrisperWhisper sidesteps that because it stays inside the Whisper decoder.

## Alignment Tools

### stable-ts (jianfch)
- **Method:** Cross-attention DTW; v2.x switched away from cross-attention argmax to DTW for better stability. Optional silence suppression and audio refinement passes.
- **License:** MIT.
- **Repository:** https://github.com/jianfch/stable-ts — active (last push 2025-10-29; v2.19.x in 2025); 2.2 k stars.
- **Backends supported:** Reference Whisper, faster-whisper (`stable_whisper.load_faster_whisper`), HuggingFace pipeline. Refinement is reported slower on faster-whisper.
- **Hardware:** PyTorch device flexibility — CUDA, CPU, MPS (whatever PyTorch is built for).
- **Granularity:** Word.
- **Strengths:** Drop-in stabilizer; the most popular timestamp post-processor; works with whatever Whisper variant you already have. Has explicit silence suppression which helps in instrumental-bridge sections.
- **Weaknesses:** Operates on Whisper's internal alignment signals — bounded by Whisper's own attention quality. On music with melisma (multiple notes per syllable), DTW often "smears".

### whisper-timestamped (linto-ai)
- **Method:** Cross-attention DTW + per-word confidence (linguistic + acoustic).
- **License:** **AGPL-3.0** — copyleft, requires careful review for shipping in a closed-source product. For an open-source library it's fine, but downstream users have to inherit AGPL.
- **Repository:** https://github.com/linto-ai/whisper-timestamped — active (last push 2025-09-09); 2.8 k stars.
- **Backends supported:** Reference Whisper.
- **Hardware:** PyTorch (CUDA, CPU, MPS).
- **Granularity:** Word with confidence scores.
- **Strengths:** Confidence per word is uniquely useful for "should we drop this chord on a low-confidence syllable?" heuristics.
- **Weaknesses:** AGPL license is a real concern; slightly older code path than stable-ts; same fundamental limitation (Whisper attention-bound).

### WhisperX wav2vec2 alignment
See WhisperX engine entry. Worth restating: this is the **only widely-used method that does NOT depend on Whisper's attention** — it does a clean second-pass forced alignment of the Whisper transcript against the audio using a CTC-trained wav2vec2 phoneme model. Independent of Whisper's timestamp quality.

### Montreal Forced Aligner (MFA)
- **Method:** Kaldi-based GMM-HMM acoustic models, trainable on custom data; G2P phonemizer.
- **License:** MIT.
- **Repository:** https://github.com/MontrealCorpusTools/Montreal-Forced-Aligner — active (last push 2026-03-31, 3.x docs current); 1.8 k stars.
- **Hardware:** CPU-only effectively (Kaldi). Cross-platform.
- **Granularity:** Phoneme + word.
- **Music applicability:** Studied directly for singing — *Research on Recognition and Application of MFA for Singing Audio* (2024) showed MFA's pretrained speech model degrades on singing but **a fine-tuned model trained on annotated singing samples recovers usable accuracy**. Realistic for our use case only if we have an aligned-singing dataset to fine-tune on.
- **Strengths:** Well-studied, deterministic, CPU-friendly. No ML environment required at runtime.
- **Weaknesses:** Pretrained speech models alone are not enough; requires per-language pretrained model (lots are available); installation pulls in Kaldi which is heavy. Not ideal as default.

### CTC-segmentation / torchaudio forced_align
- **Method:** Run wav2vec2 (or HuBERT/MMS) on audio, then use the CTC posterior matrix + Viterbi to align an external transcript.
- **License:** wav2vec2 MIT/Apache; ctc-segmentation Apache.
- **Tooling:** torchaudio's `forced_align()` API + `Wav2Vec2FABundle` (PyTorch ≥ 2.x), `MahmoudAshraf97/ctc-forced-aligner` for HF integration, `lumaku/ctc-segmentation` for the original algorithm.
- **Hardware:** CUDA, CPU, MPS (PyTorch).
- **Granularity:** Phoneme/character → word.
- **Music applicability:** Same wav2vec2 backbone WhisperX uses, but DIY. The 2024 ISMIR paper Ou et al. ("Transfer Learning of Wav2Vec 2.0 for Automatic Lyric Transcription") demonstrated wav2vec2 transfer-learning on lyrics outperforms multilingual baselines.
- **Strengths:** Lightweight, deterministic, no Whisper dependency for this stage.
- **Weaknesses:** Requires already-known transcript text. Limited by wav2vec2 dictionary — cannot align numerals, OOV tokens, or stylized spellings without preprocessing.

### NUS AutoLyrixAlign (Gupta et al.)
- **Method:** Polyphonic-music-tuned acoustic model with MFA-style HMM alignment, by HLT-NUS.
- **Repository:** https://github.com/chitralekha18/AutoLyrixAlign — quasi-stale (research artifact).
- **Granularity:** Word.
- **Music applicability:** Designed specifically for polyphonic music (no source separation needed). Reported mean alignment error ~0.35 s on standard datasets at the time of publication, which **outperformed prior SOTA by an order of magnitude** (ICASSP 2019).
- **Strengths:** Music-native, doesn't need source separation upstream.
- **Weaknesses:** Older, English-only, not actively maintained, less accurate today than wav2vec2 alignment of separated vocals. Worth citing as a baseline; not recommended as the production aligner.

### Genius/manual lyrics + alignment
- Manual or scraped lyrics text + any of the above forced aligners. This decouples transcription accuracy from alignment accuracy entirely. Most commercial karaoke-style products do exactly this.
- Legal note: Genius lyrics are not licensed for redistribution; users must supply their own text or fetch via a licensed API for production use.

## How well does Whisper work on sung vocals?

**Short answer: usable for English pop/rock at ~20% WER on long-form, much worse on classical, opera, metal, and non-English genres.**

Numbers from the open literature (do not extrapolate beyond stated datasets):

| Setting | WER | Source |
|---|---|---|
| Whisper large-v2 + Demucs vocals + lang hint, Jam-ALT | ~24 % (community; AudioShake commercial system reports −57 % vs this baseline) | AudioShake Jam-ALT page |
| Whisper large-v2 + RMS-VAD, Jam-ALT long-form | **20.35 %** (open-source SOTA) | arXiv 2506.15514 (June 2025) |
| Whisper large-v2 + RMS-VAD on **vocal stems**, MUSDB-ALT | **14.98 %** | arXiv 2506.15514 |
| Whisper large-v2 + RMS-VAD on **mixture**, MUSDB-ALT | 22.72 % | arXiv 2506.15514 |
| Whisper unmodified, Schubert Winterreise (classical) | **0.56 (56 %)** | Berendes et al., NLP4MusA 2024 |
| Same lyrics spoken, same model | **0.14 (14 %)** | same paper |
| Whisper LibriSpeech clean (speech, reference) | ~2.7 % | OpenAI / multiple replications |

Findings that constrain our pipeline design:

1. **Source separation primarily helps deletion errors** by giving VAD something cleaner to gate on. It does not eliminate hallucinations and can *introduce* them (mdx artifacts in MUSDB-ALT triggered new hallucinations).
2. **Non-lexical vocables (oohs, ahs, scat) are deleted ~50 % of the time** regardless of separator quality — Whisper was trained to filter "non-speech".
3. **Singing style matters more than instrumental bleed.** Operatic, melismatic, screamed vocals all degrade Whisper much more than guitar bleed at moderate volume. Pop/rock vocals are the easy case.
4. **VAD strategy matters more than the separator.** RMS-VAD on vocal stems beats Whisper's own long-form chunker; silero VAD is the production default. WhisperX uses pyannote VAD.
5. **No music-specific Whisper checkpoint exists in open-source SOTA.** Closed-source AudioShake claims the lead; LyricWhiz (ISMIR 2023) gets the open-source crown by post-correcting Whisper output with GPT-4 — pragmatic but adds API cost and latency.

For chord placement timing accuracy specifically, **WER is not the main metric** — what matters is the timestamp error on words that *were* transcribed. There is no published Jam-ALT-equivalent benchmark for word-timestamp accuracy on sung music. CrisperWhisper benchmarks mIoU on speech only; WhisperX wav2vec2 alignment benchmarks WER-impact only.

## Comparison Tables

### ASR engines

| Engine | CUDA | MPS | Apple GPU/ANE | Word TS method | License | Lyrics-suitable |
|---|---|---|---|---|---|---|
| openai/whisper | yes | yes (slow) | no | DTW (in code) | MIT | reference |
| faster-whisper | yes | **no** | no | DTW | MIT | yes (CUDA only) |
| whisper.cpp | yes | yes (Metal+CoreML) | yes | native tokens (`-ml`) | MIT | yes (best portability) |
| mlx-whisper | no | n/a | yes (MLX→Metal) | flag | MIT | yes (Apple only) |
| WhisperX | yes | CPU fallback | no | wav2vec2 align | BSD-2 | **yes (best timestamps)** |
| insanely-fast-whisper | yes | yes | partial | flag | Apache-2 | yes |
| Distil-Whisper | yes | yes | partial | weak | MIT | maybe (untested) |
| CrisperWhisper | yes | yes | partial | DTW (improved) | non-comm. | maybe |

### Alignment tools

| Tool | Method | Independent of Whisper attention? | Hardware | License |
|---|---|---|---|---|
| stable-ts | DTW on cross-attn | no | PyTorch (CUDA/MPS/CPU) | MIT |
| whisper-timestamped | DTW + confidence | no | PyTorch | **AGPL-3.0** |
| WhisperX wav2vec2 | CTC forced align | **yes** | PyTorch (CUDA/CPU; MPS limited) | BSD-2 |
| MFA | Kaldi GMM-HMM | yes | CPU | MIT |
| torchaudio forced_align | CTC (wav2vec2/MMS) | yes | PyTorch (CUDA/MPS/CPU) | BSD-2 |
| AutoLyrixAlign | music-tuned HMM | yes | CPU | research |

## Hardware Support Deep Dive

Three deployment realities collide here:

**A. faster-whisper / CTranslate2 has no MPS or Metal backend.** Issue #911 (2024-07) is still open with no maintainer roadmap; CTranslate2 4.5+ targets CUDA 12 + cuDNN 9 exclusively for GPU. On a Mac Mini M4 it falls back to CPU (Apple Accelerate, BLAS) — usable for small models but unacceptably slow at large-v3.

**B. mlx-whisper is Apple-only.** No CUDA path. MLX uses Metal as its backend and unified memory as its data plane. Cannot deploy MLX checkpoints on the RTX 5070Ti.

**C. The same Whisper checkpoint runs on all backends, with format conversion.** large-v3 weights live as `.pt` (HF/PyTorch) → CTranslate2 binary → GGUF (whisper.cpp) → MLX safetensors. So the *quality* is identical; the *speed and hardware fit* are not.

This forces a choice. Three viable strategies:

1. **Backend abstraction layer.** Define `TranscriptionBackend` protocol; ship `FasterWhisperBackend` (CUDA target) and `MlxWhisperBackend` (Apple target), with `WhisperCppBackend` as portable fallback. WhisperX's wav2vec2 alignment can run as a separate stage on either platform via PyTorch. Most flexible; most code.
2. **whisper.cpp everywhere.** Single C++ runtime; CoreML on Mac, CUDA on Linux/Windows, Vulkan or CPU as fallback. Loses some Python ergonomics but eliminates the dual-backend problem. WhisperX-style wav2vec2 alignment then has to be re-implemented with a separate runtime (ggml's wav2vec2, or a thin PyTorch alignment-only step).
3. **PyTorch everywhere via insanely-fast-whisper or HF transformers.** Works on CUDA + MPS without dual backends. Slower than mlx-whisper on Apple Silicon and slower than faster-whisper on CUDA, but uniform.

Migration cost between #1 and #2 or #3 is moderate (the audio→stem→VAD pipeline doesn't change; only the ASR call). Recommendation: start with #1 because the published WERs we want come from faster-whisper + WhisperX combos.

## Recommendations for Titan ChordPro Lib

**Default architecture: separate transcription from alignment.**

This is non-negotiable: Whisper-internal timestamps (segment or word) are not accurate enough for chord-on-syllable placement, and they degrade further on sung vocals. Always run a forced-alignment pass.

```
vocal_stem (from Demucs)
  → VAD (silero or pyannote, NOT Whisper's native long-form chunker)
  → Whisper large-v3 transcription (any fast backend)
  → wav2vec2 / WhisperX forced alignment on the stem
  → word-level start/end → chord placement
```

**CUDA stack (RTX 5070Ti, primary dev target):**
- ASR: `faster-whisper` large-v3 (`compute_type="float16"`, beam_size 5)
- VAD: silero-vad (already what WhisperX uses)
- Alignment: WhisperX `align()` with the language-appropriate wav2vec2 model
- Optional re-rank: stable-ts refinement on top of WhisperX output for confidence scores

Why: matches the open-source SOTA on Jam-ALT (~20 % WER long-form) and produces phoneme-level timestamps via wav2vec2 — the most precise option in OSS today.

**Apple Silicon stack (Mac Mini M4):**
- ASR: `mlx-whisper` large-v3 OR `whisper.cpp` large-v3 with CoreML.
  - Prefer `mlx-whisper` for ~30–40 % faster decoding and a Python API; prefer `whisper.cpp` if you want a single static binary.
- VAD: silero-vad (PyTorch, runs on MPS/CPU) or whisper.cpp's built-in VAD.
- Alignment: PyTorch wav2vec2 forced alignment via `torchaudio.functional.forced_align` (runs on MPS) — re-implements WhisperX's alignment step without the faster-whisper dependency.

Why: WhisperX's full pipeline does not effectively use Apple Silicon GPU (CUDA-only paths internally + faster-whisper CTranslate2 has no MPS), so we replicate the alignment step natively in torchaudio.

**Weights compatibility:** Yes — the same Whisper large-v3 checkpoint (1.55 B params) underpins all backends. Only the on-disk format differs (.pt vs CTranslate2 vs GGUF vs MLX). WERs across backends are within noise of each other when quantization matches. The wav2vec2 alignment models are HF-hosted and run identically under PyTorch on either platform.

**Avoid for now:**
- whisper-timestamped — AGPL license is a downstream contagion risk.
- Distil-Whisper for the production pass — weak word timestamps; useful only for fast preview.
- MFA without fine-tuning — pretrained speech models degrade noticeably on singing per the 2024 study.
- Hand-rolling AutoLyrixAlign — superseded by wav2vec2-based approaches.

**For polish (post-MVP):**
- LyricWhiz-style GPT-4 post-correction of the Whisper transcript before alignment — buys back several WER points but introduces API dependency.
- CrisperWhisper for verbatim/filler-aware transcription if vocables are important to ChordPro output.
- Source-separator-aware VAD (RMS-VAD per the 2025 paper) replacing silero — meaningful WER reduction on long-form.

## Open Questions / Things to Validate Empirically

1. **Hallucination rate on Demucs/MDX-separated vocals at large-v3 vs large-v3-turbo.** Turbo's reduced decoder may behave differently under separator artifacts; no published data.
2. **Word-timestamp drift on melismatic singing** (one syllable, multiple notes — common in pop ballads, gospel, R&B). DTW-based methods (stable-ts) are theoretically vulnerable; CTC-based wav2vec2 alignment (WhisperX) more robust. Needs an internal melisma test set.
3. **MLX-whisper vs faster-whisper output parity** — WERs should match within noise but `large-v3` MLX quantizations differ; need a side-by-side run on MUSDB-ALT subset.
4. **wav2vec2 alignment behaviour on non-English vocals** (Spanish, Japanese) — torchaudio bundles only EN/FR/DE/ES/IT models; HF community models for other languages vary in quality.
5. **Latency budget per song.** On RTX 5070Ti, expect ~5–10× realtime for large-v3 + WhisperX. On M4 with mlx-whisper expect ~3–5× realtime. Acceptable for batch; not for live.
6. **Numeral and proper-noun dropping in WhisperX alignment.** Songs with "1999", "24/7", "U2" etc. will lose those words from timestamps — needs a fallback (e.g., interpolate from adjacent word boundaries).
7. **Whether to swap in CrisperWhisper** when Whisper drops vocables that the user wants chord-marked.

## Sources

- arXiv 2506.15514 (June 2025) — *Exploiting Music Source Separation for Automatic Lyrics Transcription with Whisper* — https://arxiv.org/html/2506.15514v1
- ACL Anthology 2024.nlp4musa-1.3 — Berendes/Schwär/Müller, *Lyrics Transcription in Western Classical Music with Whisper: Schubert's Winterreise* — https://aclanthology.org/2024.nlp4musa-1.3/
- arXiv 2408.06370 — *Lyrics Transcription for Humans: A Readability-Aware Benchmark* (Jam-ALT, ISMIR 2024) — https://arxiv.org/abs/2408.06370
- AudioShake Jam-ALT site — https://audioshake.github.io/jam-alt/
- arXiv 2306.17103 — *LyricWhiz: Robust Multilingual Zero-shot Lyrics Transcription by Whispering to ChatGPT* (ISMIR 2023) — https://arxiv.org/abs/2306.17103
- arXiv 2303.00747 — *WhisperX: Time-Accurate Speech Transcription of Long-Form Audio* (Interspeech 2023) — https://arxiv.org/abs/2303.00747
- arXiv 2408.16589 — *CrisperWhisper: Accurate Timestamps on Verbatim Speech Transcriptions* (Interspeech 2024) — https://arxiv.org/abs/2408.16589
- arXiv 2501.11378 — *Investigation of Whisper ASR Hallucinations Induced by Non-Speech Audio* — https://arxiv.org/html/2501.11378v1
- ICASSP 2019, Gupta et al. — *Automatic Lyrics-to-Audio Alignment on Polyphonic Music Using Singing-Adapted Acoustic Model* (NUS AutoLyrixAlign) — https://smcnus.comp.nus.edu.sg/archive/pdf/2019-2021/2019_ChitraICASSP.pdf
- ISMIR 2022, Ou et al. — *Transfer Learning of Wav2Vec 2.0 for Automatic Lyric Transcription* — https://archives.ismir.net/ismir2022/paper/000107.pdf
- DRPress 2024 — *Research on the Recognition and Application of Montreal Forced Aligner for Singing Audio* — https://drpress.org/ojs/index.php/jceim/article/view/19965
- GitHub: https://github.com/SYSTRAN/faster-whisper (v1.2.1, 2025-10-31)
- GitHub: https://github.com/m-bain/whisperX (v3.8.5, 2026-04)
- GitHub: https://github.com/jianfch/stable-ts (v2.19.x, 2025)
- GitHub: https://github.com/linto-ai/whisper-timestamped (AGPL-3.0)
- GitHub: https://github.com/ggml-org/whisper.cpp (v1.8.4, March 2026)
- GitHub: https://github.com/ml-explore/mlx-examples (whisper subdir)
- GitHub: https://github.com/Vaibhavs10/insanely-fast-whisper
- GitHub: https://github.com/huggingface/distil-whisper
- GitHub: https://github.com/MontrealCorpusTools/Montreal-Forced-Aligner
- GitHub: https://github.com/chitralekha18/AutoLyrixAlign
- GitHub: https://github.com/nyrahealth/CrisperWhisper
- faster-whisper MPS issue #911 — https://github.com/SYSTRAN/faster-whisper/issues/911
- faster-whisper Apple Metal issue #515 — https://github.com/SYSTRAN/faster-whisper/issues/515
- mac-whisper-speedtest benchmarking repo — https://github.com/anvanvan/mac-whisper-speedtest
- Modal blog, *Choosing between Whisper variants* (2025) — https://modal.com/blog/choosing-whisper-variants
- torchaudio forced alignment tutorial — https://docs.pytorch.org/audio/stable/tutorials/forced_alignment_tutorial.html
- ctc-forced-aligner — https://github.com/MahmoudAshraf97/ctc-forced-aligner
- ctc-segmentation — https://github.com/lumaku/ctc-segmentation
- Deepgram, *Whisper-v3 Hallucinations on Real World Data* — https://deepgram.com/learn/whisper-v3-results
- Voicci, *Apple Silicon Whisper Performance* — https://www.voicci.com/blog/apple-silicon-whisper-performance.html

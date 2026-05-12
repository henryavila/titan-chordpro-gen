# Hardware and Platform Strategy: CUDA vs Apple Silicon (2026)

> Research conducted for Titan ChordPro Lib. Goal: decide whether to support dual-platform (NVIDIA CUDA + Apple Silicon) from day 1, and how.
> Last updated: 2026-05-08

---

## Executive Summary

The user is targeting two production machines that sit on opposite sides of the deepest split in modern ML tooling: an **NVIDIA RTX 5070 Ti (CUDA 12.x, Blackwell)** and a **Mac Mini M4 (Apple Silicon, 16 GB unified memory)**. The empirical record from 2023-2026 of similar audio-ML libraries shows three clear lessons:

1. **Single-platform-first is the dominant pattern.** Almost every important audio-ML lib (faster-whisper, demucs, audiocraft, Spleeter, basic-pitch) shipped on its native platform first (CUDA-or-CPU for PyTorch libs, TensorFlow for Spotify/Deezer libs), and dual-platform support emerged later as either community PRs, forks, or completely separate projects (mlx-whisper, mlx-demucs, mlx-audio).
2. **Apple Silicon support is rarely free**, and choosing the wrong upstream dependency (CTranslate2 being the canonical example) can lock a project out of MPS/Metal *forever* without an engine swap.
3. **The libs that succeeded cross-platform did it through a backend abstraction** (whisper.cpp/ggml, Spotify basic-pitch's TF/CoreML/TFLite/ONNX selector, PyTorch's `torch.device`) — not by writing one platform-specific implementation and then porting.

Recommendation up front: **Day-1 dual-platform support is feasible and cheap *if* the lib commits to a backend-abstraction architecture from the first commit and avoids CTranslate2-class lock-in dependencies.** It is expensive and painful if dual-platform is bolted on later. Detailed reasoning in the [Recommendation](#recommendation-for-titan-chordpro-lib) section.

---

## Apple Silicon ML Stack in 2026

### MLX (state, maturity, audio coverage)

Apple released MLX in December 2023. By May 2026 it has matured significantly:

- **Latest stable release**: MLX 0.31.2 (April 22, 2026), 73 releases total, 26k GitHub stars, 1.8k forks. ([github.com/ml-explore/mlx](https://github.com/ml-explore/mlx))
- **Design**: NumPy-like Python API; C++/C/Swift bindings; lazy evaluation; dynamic graphs (no compilation delays on shape changes); unified memory model (no host↔device transfers).
- **Inspirations**: NumPy, PyTorch, JAX, ArrayFire — feels familiar to PyTorch users but is *not* a drop-in replacement.
- **Stability/breaking changes**: API has stabilized through 2025-2026; the 0.x version number is conservative — the project has not advertised a 1.0 yet, but public examples and downstream libs (mlx-audio, mlx-whisper) are not having to chase weekly breakages.

**Audio model coverage in MLX (2026)**:

| Model | Status | Notes |
|---|---|---|
| Whisper (all sizes, incl. large-v3-turbo) | First-class | `mlx-whisper` PyPI package; pre-converted weights on `mlx-community/*` HF org. Supports word-level timestamps. |
| Demucs / Hybrid Demucs | Community port | `lextoumbourou/mlx-demucs`, `andrade0/demucs-mlx`. Reportedly separates a 7-min song in ~12s on M-series. Not endorsed by Meta. |
| MusicGen / EnCodec | Reference impl in `mlx-examples` | Functional; small model generates 8s audio in ~6s on M4 Max (faster than realtime). |
| Parakeet (NVIDIA NeMo ASR) | Yes | `parakeet-mlx`, ~0.50s on M4 24GB for the test clip. |
| TTS (Kokoro, Qwen3-TTS, CSM, Chatterbox, etc.) | 17+ models | Via `mlx-audio` — Blaizzy/mlx-audio has 7k+ stars, 23 releases, latest v0.4.3 April 2026. |
| Source separation (SAM-Audio) | In `mlx-audio` | Speech-only target. |
| Speech enhancement (MossFormer2, DeepFilterNet) | In `mlx-audio` | |

Sources: [mlx-audio repo](https://github.com/Blaizzy/mlx-audio), [mlx-examples](https://github.com/ml-explore/mlx-examples), [mlx-whisper PyPI](https://pypi.org/project/mlx-whisper/), [demucs-mlx port writeup](https://medium.com/@andradeolivier/i-ported-demucs-to-apple-silicon-it-separates-a-7-minute-song-in-12-seconds-6c4e5cffb5c3).

**Verdict**: MLX in 2026 covers every audio sub-task Titan needs — Whisper for transcription, Demucs/Hybrid Demucs for source separation, plus Parakeet as an alternative ASR. The catch is that nearly every port is community-maintained, not first-party from the original model author.

### MPS (PyTorch Metal)

PyTorch's MPS backend (`torch.device("mps")`) ships with PyTorch ≥1.12. State in 2026:

- **Coverage**: Most common ops work. The remaining gaps disproportionately hit *audio*: complex tensors, certain FFT paths, custom CUDA kernels used by some research code, and sparse-tensor ops needed by pyannote diarization. ([State of PyTorch Hardware Acceleration 2025](https://tunguz.github.io/PyTorch_Hardware_2025/))
- **Compiler maturity**: "Most users run in Eager Mode on MPS, and while performance is adequate for inference, the lack of a mature compiler stack means complex fusions often fall back to CPU or run as unfused generic Metal kernels." (same source)
- **Audio-specific gotchas**:
  - **Demucs on MPS**: Officially mostly works (Demucs-GUI 1.3.2 ships with MPS), but "complex tensors, custom ops, and various incompatibilities get in the way." The community fix has been to port Demucs to MLX rather than wait for MPS feature parity. ([demucs MPS issue](https://github.com/facebookresearch/demucs/issues/432))
  - **insanely-fast-whisper on MPS**: Diarization throws `NotImplementedError` for sparse tensors on MPS; users fall back to CPU for diarization while keeping the rest on MPS. ([insanely-fast-whisper#258](https://github.com/Vaibhavs10/insanely-fast-whisper/issues/258))
  - **AudioCraft / MusicGen on MPS**: Decoder must be moved to CPU mid-pipeline; full-MPS path not viable. ([blog.peddals.com walkthrough](https://blog.peddals.com/en/apple-mps-to-generate-audio-with-meta-audiogen/))
  - **FFT 1D + complex**: torchaudio's FFT-based ops work on MPS in 2025-2026 but historically had more sharp edges than CUDA. STFT / iSTFT are stable; some less-common transforms still fall back.

**Verdict**: MPS is a pragmatic *baseline* for PyTorch-based audio code on Apple Silicon — it works, but it's noticeably less reliable than CUDA, and audio-specific gaps will keep biting. For best-in-class Apple Silicon performance, MLX is the answer.

### CoreML

CoreML has matured into a viable production target for transformer audio models:

- **Conversion path**: `coremltools` + Hugging Face `exporters` package. Most encoder/decoder transformer architectures convert; "newly-released models usually require some manual tweaking." ([HF blog: Releasing Swift Transformers](https://huggingface.co/blog/swift-coreml-llm))
- **Constraints**:
  - Flexible input shapes only run on CPU, not GPU/ANE.
  - Model size matters: ANE has hard limits and prefers fp16/int8 quantized models.
  - Graph splitting is sometimes required to keep parts of the model on ANE while leaving exotic ops on CPU.
- **Audio examples shipping in production**: `whisper.cpp` ships CoreML-encoded encoder weights for ~3× speedup on M-series; WhisperKit (Argmax) achieves 2.2% WER with Whisper Large v3 Turbo on ANE, real-time streaming. ([WhisperKit paper, arXiv 2507.10860](https://arxiv.org/html/2507.10860v1))
- **Spotify basic-pitch** ships CoreML by default on macOS (alongside TFLite for Linux, ONNX for Windows) — exemplary multi-runtime packaging. ([basic-pitch repo](https://github.com/spotify/basic-pitch))

### Neural Engine (ANE)

When the ANE actually gets used:

- **Only via CoreML**, never via PyTorch MPS or MLX directly (MLX runs on GPU, not ANE; PyTorch MPS runs on GPU).
- Model must be CoreML-converted, with `compute_units=ALL` or `CPU_AND_NE` requested.
- ANE prefers static shapes, limited op set, fp16/int8.
- Encoder-only models (like Whisper's encoder) map well to ANE; full encoder-decoder is harder.
- **whisper.cpp with `WHISPER_COREML=1`** is the canonical way to use ANE for Whisper today.

**Practical implication for Titan**: To use the M4's ANE, you need a CoreML conversion path. That is a separate engineering investment from MLX. Most projects pick **either** MLX (GPU + unified memory, easier dev loop) **or** CoreML/ANE (lower latency, lower power, harder pipeline) — not both.

---

## Performance: M4 vs RTX 5070 Ti

**[UNCERTAIN — head-to-head benchmark on the exact pair (Mac Mini M4 base 16GB vs RTX 5070 Ti) was not located in public sources as of May 2026. The numbers below are assembled from individual benchmarks on each side.]**

### Whisper (large-v3-turbo, ~10s audio clip)

From the [`anvanvan/mac-whisper-speedtest`](https://github.com/anvanvan/mac-whisper-speedtest) benchmark on a MacBook Pro M4 24GB:

| Implementation | Model | Time (10s clip) |
|---|---|---|
| FluidAudio CoreML (Parakeet) | parakeet-tdt-0.6b-v2-coreml | 0.19 s |
| Parakeet MLX | parakeet-tdt-0.6b-v2 | 0.50 s |
| MLX Whisper | whisper-large-v3-turbo | 1.02 s |
| whisper.cpp + CoreML | large-v3-turbo-q5_0 | 1.23 s |
| faster-whisper (CPU int8) | large-v3-turbo | 6.96 s |

The Mac Mini M4 (base, 10-core GPU) will be ~10-15% slower than the MacBook Pro M4 (10-core GPU, same generation) under sustained load due to thermals — not categorical differences. The 16GB ceiling is more likely to bite than raw compute.

For NVIDIA, the closest reference is RTX 4090 with `insanely-fast-whisper` doing a 10-minute clip in ~8s ([owehrens.com](https://owehrens.com/whisper-nvidia-rtx-4090-vs-m1pro-with-mlx/)). The RTX 5070 Ti has 8,960 CUDA cores and 896 GB/s memory bandwidth (Blackwell), with native FP4/FP8 paths via TensorRT — for Whisper-class encoder-decoder transformer inference it should land between the 4090 and 4070 Ti. **[UNCERTAIN]** — exact 5070 Ti Whisper numbers were not located.

There is a confirmed regression report: [faster-whisper#1287](https://github.com/SYSTRAN/faster-whisper/issues/1287) ("faster-whisper performs worse on a 5070 TI than a 4070 TI Super") — likely a CTranslate2/cuDNN tuning issue specific to Blackwell.

### Demucs / Source Separation

- **CUDA**: 7-min song in low single-digit seconds on RTX 4090; RTX 5070 Ti expected similar or slightly slower. Strict requirement: ≥3 GB VRAM, ≥7 GB recommended. ([demucs README](https://github.com/facebookresearch/demucs))
- **MLX-Demucs (community)**: 7-min song in ~12s on M-series Macs. ([demucs-mlx writeup](https://medium.com/@andradeolivier/i-ported-demucs-to-apple-silicon-it-separates-a-7-minute-song-in-12-seconds-6c4e5cffb5c3))
- **PyTorch MPS Demucs**: Works in Demucs-GUI but with caveats around complex tensors; performance significantly worse than MLX port.

### Order-of-magnitude rule of thumb (for budgeting)

Based on [owehrens.com](https://owehrens.com/whisper-nvidia-rtx-4090-vs-m1pro-with-mlx/), [voicci.com Apple Silicon benchmarks](https://www.voicci.com/blog/apple-silicon-whisper-performance.html), and the M4 speedtest:

- **M4 (any) ≈ RTX 4070-class for transformer inference** when the right framework is used (MLX for Apple, TensorRT/insanely-fast for NVIDIA).
- **RTX 5070 Ti will be roughly 1.5-2× faster than M4 base** on transformer inference, less of a gap once thermal-limited.
- **Power draw differential is dramatic**: 4090 system idle differential +242W, M1 Pro +38W. The Mac Mini will be the energy-efficient option by a factor of ~6x.

For Titan's actual workload (ChordPro generation from a song), realistic latency expectations:
- 4-min song, full pipeline (separate stems → transcribe vocals → align lyrics → detect chords → beat track): **30-90s on RTX 5070 Ti**, **60-180s on Mac Mini M4** depending on which models are picked. Both are usable.

---

## Case Studies: How Similar Libs Handle Multi-Backend

### faster-whisper

- **Initial release platform**: CUDA-only (May 2023), via CTranslate2.
- **Apple Silicon support today (May 2026)**: **None natively.** `device="mps"` raises `ValueError: unsupported device mps`. CPU backend works on Apple Silicon but is dramatically slower — ~7x slower than mlx-whisper on the same M4 hardware in the speedtest above.
- **Strategy**: Single-backend reliance on CTranslate2. CTranslate2 supports CPU (x86-64 + ARM64 via Accelerate), CUDA, and ROCm — but not Metal/MPS, and there is no public roadmap for it.
- **Cost of expansion**: Effectively infinite for the maintainers — they'd need to either add a Metal backend to CTranslate2 (a major multi-month C++ project) or rewrite faster-whisper around a different engine. Neither is on the public roadmap as of May 2026.
- **Lesson**: Choosing CTranslate2 was a *one-way door*. faster-whisper is effectively a **CUDA-or-CPU lib**, and it will likely remain so.

Sources: [faster-whisper README](https://github.com/SYSTRAN/faster-whisper), [#911](https://github.com/SYSTRAN/faster-whisper/issues/911), [#515](https://github.com/SYSTRAN/faster-whisper/issues/515), [Modal blog comparison](https://modal.com/blog/choosing-whisper-variants).

### demucs (Meta)

- **Initial release platform**: CUDA + CPU via PyTorch (2019).
- **Apple Silicon support today**: Partial via PyTorch MPS (works in Demucs-GUI 1.3.2 with caveats around complex tensors and custom ops). Best-in-class Apple Silicon performance only available via *separate community ports* (`lextoumbourou/mlx-demucs`, `andrade0/demucs-mlx`).
- **Strategy**: PyTorch's `torch.device` abstraction was supposed to handle this for free, but audio's reliance on complex tensors and custom kernels has meant MPS support is "mostly works" rather than "production-ready." The official repo is **archived** as of late 2024 — "As I am no longer working at Meta, this repository is not maintained anymore."
- **Cost of expansion**: Dual support was free in *theory* via PyTorch but in *practice* required a full MLX rewrite by community contributors when MPS gaps proved unfixable upstream.
- **Lesson**: `torch.device` is necessary but not sufficient — audio-specific PyTorch ops need separate validation on each backend. And relying on a single corporate-sponsored project (Meta) is a bus-factor risk.

Sources: [demucs repo](https://github.com/facebookresearch/demucs), [#432](https://github.com/facebookresearch/demucs/issues/432).

### audiocraft (Meta — MusicGen, AudioGen, EnCodec)

- **Initial release platform**: CUDA + CPU (June 2023).
- **Apple Silicon support today**: Workable via PyTorch MPS but with mid-pipeline CPU fallbacks (the decoder must move to CPU). Community fork [`trizko/audiocraft`](https://github.com/trizko/audiocraft) cleans this up. MLX port of MusicGen achieves faster-than-realtime generation on M4 Max.
- **Strategy**: Rely on PyTorch MPS, accept the workarounds.
- **Cost of expansion**: Apple Silicon "feature request" issues sat open for ~2 years (#31, #43). Community forks shipped before official support did.
- **Lesson**: When core PyTorch ops aren't on MPS, even Meta-scale teams don't prioritize Apple Silicon — community has to pick up the slack.

Sources: [audiocraft#31](https://github.com/facebookresearch/audiocraft/issues/31), [audiocraft#43](https://github.com/facebookresearch/audiocraft/issues/43), [trizko/audiocraft](https://github.com/trizko/audiocraft).

### whisper.cpp

- **Initial release platform**: Cross-platform from day 1 (October 2022). Plain C/C++, GGML backend.
- **Apple Silicon support today**: Excellent. Metal GPU + CoreML for ANE-accelerated encoder, ARM NEON CPU path, Accelerate framework integration. ~3× speedup from CoreML over CPU-only.
- **Strategy**: **Backend abstraction at the lowest level (GGML).** GGML is the portable backend; whisper.cpp delegates all hardware specifics to it. Backends today: Metal, CUDA, Vulkan, OpenVINO, MUSA, CANN, plus all CPU SIMD intrinsics.
- **Cost of expansion**: New backends added by community contributors — Vulkan, MUSA, CANN all came after CUDA and Metal. Each backend is a self-contained module behind a common interface.
- **Lesson**: This is the **gold standard for cross-platform audio ML**. The architecture choice (C/C++ + GGML interface) was made on day 1 with portability as a core requirement. Adding a new backend is a discrete, scoped task — not a rewrite.

Sources: [whisper.cpp repo](https://github.com/ggml-org/whisper.cpp), [discussions/126 roadmap](https://github.com/ggml-org/whisper.cpp/discussions/126), [issue/2124 on ANE](https://github.com/ggml-org/whisper.cpp/issues/2124).

### mlx-whisper

- **Relationship to faster-whisper**: **Independent reimplementation, not a backend swap.** Different framework (MLX vs CTranslate2), different code, but uses the *same OpenAI Whisper weights* (or pre-converted MLX-format mirrors from `mlx-community/*` on HF).
- **Output compatibility**: Tokens, timestamps (incl. word-level), and language detection match OpenAI's reference output to within numerical precision differences. Outputs are interchangeable for downstream consumers.
- **Why it exists separately**: Because faster-whisper *can't* be made to run on Apple Silicon GPU. mlx-whisper exists *as the Apple Silicon answer to faster-whisper*.

Sources: [mlx-whisper](https://pypi.org/project/mlx-whisper/), [mlx-examples/whisper](https://github.com/ml-explore/mlx-examples).

### mlx-audio

- **Scope**: TTS (17+ models incl. Kokoro, Qwen3-TTS, Chatterbox), STT (10+ incl. Whisper, Parakeet, Voxtral), STS, source separation (SAM-Audio), speech enhancement (MossFormer2, DeepFilterNet), and multimodal audio LLMs.
- **Maturity**: 7k+ stars, 23 releases, v0.4.3 (April 2026). OpenAI-compatible REST API, quantization (3-8 bit), Swift package for iOS/macOS.
- **Limitation**: Apple Silicon-only. Not a cross-platform lib; a destination for "I have a Mac and want everything in one place."

Source: [mlx-audio repo](https://github.com/Blaizzy/mlx-audio).

### basic-pitch (Spotify)

- **Initial release**: TensorFlow-based, mid-2022.
- **Strategy today**: **Multi-runtime selector**. Ships TF + CoreML + TFLite + ONNX models. At runtime, picks based on platform: CoreML on macOS, TFLite on Linux, ONNX on Windows. TensorFlow itself only auto-installed on Python 3.11+.
- **Cost of expansion**: Each runtime is a separate model export from the same source TF graph. Adding a runtime = export + plumb into the loader.
- **Apple Silicon constraint**: Mac M1+ requires Python 3.10 specifically — a real friction point for downstream packagers.
- **Lesson**: When the model architecture is small and stable, **export to multiple runtimes** is a clean strategy. Doesn't scale as well to fast-moving research models.

Sources: [basic-pitch repo](https://github.com/spotify/basic-pitch), [DeepWiki overview](https://deepwiki.com/spotify/basic-pitch/1-overview).

### Spleeter (Deezer)

- **Initial release**: TensorFlow 1.x-era, ~2019.
- **Maintenance status today**: **Effectively unmaintained.** Last release v2.3.0, September 2021. 242 open issues, 33 open PRs, no recent activity.
- **Apple Silicon support**: Only via Apple's own Metal-TensorFlow build, with workaround instructions; no first-party support.
- **Lesson**: A TF1-era lib that pegged to a specific TF version aged badly across both the TF1→TF2 transition *and* the x86→Apple Silicon transition. Cautionary tale on framework lock-in.

Sources: [spleeter repo](https://github.com/deezer/spleeter), [#696 Apple Silicon discussion](https://github.com/deezer/spleeter/issues/696).

### Summary table

| Lib | Day-1 platforms | Apple Silicon today | Pattern | Cost of expansion |
|---|---|---|---|---|
| **faster-whisper** | CUDA, CPU | CPU only (no MPS, no Metal) | Single-engine (CTranslate2) | **Effectively impossible** without engine swap |
| **demucs** | CUDA, CPU | Partial MPS; community MLX ports | `torch.device` + community forks | Years of community work; official archived |
| **audiocraft** | CUDA, CPU | Partial MPS w/ workarounds; community forks | `torch.device` | 2+ years of open issues |
| **whisper.cpp** | All major | First-class (Metal + CoreML/ANE) | **GGML backend abstraction** | Per-backend, scoped, additive |
| **mlx-whisper** | Apple Silicon only | Yes | Native MLX | Built as the Apple-side counterpart |
| **basic-pitch** | TF; converts to all | First-class via CoreML | **Multi-runtime export selector** | One export per runtime |
| **Spleeter** | TF (CUDA/CPU) | Workaround via Apple TF | Frozen on TF1 | Stalled; project abandoned |

---

## Patterns for Multi-Backend Lib Design

### Strategy / Backend abstraction

The pattern that *actually worked*: define a clean interface for the operations the lib needs (`encode_audio`, `transcribe`, `separate_stems`), then have multiple concrete implementations behind that interface — one per backend.

- **whisper.cpp / GGML**: C struct of function pointers; backends register themselves at compile time. Adding Vulkan or MUSA was a discrete project that didn't touch the high-level inference code.
- **basic-pitch's loader**: A thin Python loader that picks among `tf` / `coreml` / `tflite` / `onnxruntime` based on platform + availability. Applications above the loader don't know which is in use.

### `torch.device` (built-in PyTorch)

PyTorch already abstracts CPU/CUDA/MPS/XPU/etc. behind a single `Tensor.to(device)` call. **Necessary but not sufficient** for audio: as the demucs and audiocraft case studies show, MPS feature gaps in audio-specific ops force per-device branches anyway.

If you stay in PyTorch, the discipline is:
1. Always parameterize on `device` — never hardcode `"cuda"`.
2. Have a CI matrix that runs tests on CPU, CUDA, and MPS — surface ops that fall back early.
3. Wrap MPS-incompatible ops with a fallback decorator that moves to CPU and back.

### Adapter pattern (for swapping engines)

Keep upstream models behind your own protocol. Example:

```python
class TranscriptionEngine(Protocol):
    def transcribe(self, audio: np.ndarray, language: str | None = None) -> Transcript: ...

class FasterWhisperEngine: ...   # CUDA path
class MLXWhisperEngine: ...      # Apple Silicon path
class WhisperCppEngine: ...      # universal fallback
```

The lib picks an engine at runtime based on platform detection (or user override). The downstream consumer of `Transcript` doesn't care which engine produced it. This is exactly how `whisply` works ([whisply on PyPI](https://pypi.org/project/whisply/)) — a thin orchestrator over faster-whisper, insanely-fast-whisper, and mlx-whisper depending on hardware.

### Plugin pattern (for shipping)

Optional dependencies declared via Python extras:
```
pip install titan-chordpro-lib[cuda]      # pulls faster-whisper, torch+cu12, etc.
pip install titan-chordpro-lib[apple]     # pulls mlx, mlx-whisper, etc.
pip install titan-chordpro-lib[universal] # pulls whisper.cpp bindings, ONNX runtime
```

This keeps the install footprint small and lets each platform's user avoid pulling competing native libs.

### Lock-in risks to avoid

- **CTranslate2 dependency** → CUDA/CPU only, no realistic path to Apple GPU. The faster-whisper situation.
- **Direct CUDA kernels in custom ops** → unportable without a rewrite. Some research-paper code does this.
- **TensorRT-only inference paths** → NVIDIA-only. Fine if you scope around it (e.g., as the CUDA-fast-path while another backend covers everything else).
- **`device="cuda"` hardcodes** → trivial to fix early, expensive to fix after the codebase has grown.
- **Pinning to a TF1 / TF2-old major version** → the Spleeter trap. Stay on actively-maintained framework versions.

What KEEPS options open:

- ONNX as an intermediate format. Convert once, run on ONNX Runtime with the appropriate execution provider (CUDAExecutionProvider, CoreMLExecutionProvider, DmlExecutionProvider on Windows, etc.). Trade-off: you give up some peak performance for portability.
- Pure-PyTorch implementations using only well-supported ops.
- Dependency on whisper.cpp/ggml-class libs that already solved cross-platform.
- Any architecture where the engine is behind an interface, not directly imported by user code.

---

## Single-Platform vs Dual-Platform: Empirical Evidence

What the case studies tell us about expansion cost:

1. **Going from CUDA-only to Apple Silicon retroactively, with the wrong dependency, is essentially impossible** without a rewrite. faster-whisper is the canonical example: 3+ years in, no path to Apple GPU because of CTranslate2.
2. **Going from CUDA-only to Apple Silicon with PyTorch as the foundation costs years and produces second-class support.** demucs and audiocraft both took 1-2+ years of open issues, ended up with workarounds (move-to-CPU mid-pipeline, complex-tensor caveats), and the *best* Apple Silicon experience came from independent MLX ports — not from the upstream project.
3. **Day-1 cross-platform via a backend interface (whisper.cpp's approach) is by far the most successful pattern**, and adding a new backend is a discrete, well-scoped task.
4. **Day-1 cross-platform via multi-runtime export (basic-pitch's approach) works for stable, small models** but doesn't scale to bleeding-edge research models that change shape.
5. **Apple Silicon as an afterthought always disappoints** — it ends up either dramatically slower (faster-whisper CPU mode), feature-incomplete (audiocraft on MPS), or shipped by someone other than the original team (mlx-whisper, mlx-demucs, mlx-audio).

The cost ratio is roughly:
- Day-1 dual-platform via abstraction: ~1.3-1.5× the engineering cost of single-platform.
- Retrofit dual-platform onto a single-platform codebase: ~3-10× the original engineering cost, often blocked entirely by a dependency.

---

## Recommendation for Titan ChordPro Lib

**Direct answer: Go dual-platform from day 1, but do it via backend abstraction — not by writing both backends today.**

Concretely:

1. **Architect for swappable engines from the first commit.** Define `TranscriptionEngine`, `SourceSeparationEngine`, `BeatTrackingEngine`, `ChordRecognitionEngine` as Protocols. The orchestrator that turns audio into a ChordPro file should not import faster-whisper or mlx-whisper directly — it should import `TranscriptionEngine`.

2. **Pick day-1 implementations that already support both platforms.** This is the single most consequential decision:
   - **Transcription**: Use `whisper.cpp` (via `pywhispercpp` or similar bindings) as the *primary* day-1 engine. It runs on CUDA on the 5070 Ti and on Metal+CoreML on the M4. You get cross-platform for free. Keep `faster-whisper` and `mlx-whisper` as optional extras for users who want maximum performance on one specific platform.
   - **Source separation**: Demucs via PyTorch is cross-platform-ish (CUDA full speed, MPS with caveats). For Apple-Silicon users wanting maximum speed, expose `mlx-demucs` as an optional backend. Stems are stems — outputs are interchangeable.
   - **Chord/beat**: Most chord recognition libs (madmom, librosa, autochord) are CPU-bound or CPU-only — already cross-platform.
   - **Pitch detection / tab transcription**: basic-pitch ships CoreML + TFLite + ONNX out of the box, dual-platform handled.

3. **Avoid CTranslate2 as a *required* dependency.** Make it optional, behind the engine abstraction. If a CUDA user wants `faster-whisper` performance, they install `titan-chordpro-lib[cuda-fast]` and the engine factory picks it up. If it's not there, fall back to whisper.cpp.

4. **Use Python extras for backend installs:**
   ```
   pip install titan-chordpro-lib                 # universal: whisper.cpp + librosa + onnxruntime
   pip install titan-chordpro-lib[cuda]           # adds: faster-whisper, torch+cu12, demucs[gpu]
   pip install titan-chordpro-lib[apple]          # adds: mlx, mlx-whisper, mlx-demucs (when stable)
   ```

5. **CI matrix from day 1**: GitHub Actions runs on `ubuntu-latest` (CPU + optional CUDA self-hosted), `macos-14`+ (Apple Silicon). Run the `universal` install path in both. CUDA-specific paths run on a self-hosted runner or skipped with marks.

6. **Docs**: Be explicit about the engine matrix — which engines run where, and which is the default per platform. Spotify basic-pitch's docs are a good template.

7. **Defer MLX-specific backends** until day 1 ships. Ship the cross-platform `whisper.cpp`-based path first. *Then* add `mlx-whisper` and `mlx-demucs` as optional optimizations for Apple Silicon users who want best-in-class speed. Same on the CUDA side: `faster-whisper` is an optional speedup, not the foundation.

The key insight: **you don't need to write two implementations on day 1. You need to write the abstraction on day 1**, pick a portable default engine for each subsystem, and then *optionally* add platform-specific fast-path engines as the lib matures. This is the best of both worlds — dual-platform from the first release, without the engineering cost of two parallel codebases.

The user's two production machines are well-served by this architecture: the M4 Mac Mini gets a working day-1 experience via whisper.cpp+CoreML, and can opt into mlx-whisper for max speed; the RTX 5070 Ti gets a working day-1 experience via whisper.cpp+CUDA, and can opt into faster-whisper for max speed. Both environments share the same orchestration code, the same ChordPro output, the same APIs.

The wrong move is to start with `faster-whisper` as the only transcription engine because "the 5070 Ti is the dev machine." The case-study evidence is unambiguous: that decision permanently locks Apple Silicon out as a first-class target.

---

## Open Questions

1. **whisper.cpp Python binding maturity in 2026**: Need to validate that `pywhispercpp` / `whispercpp` Python bindings expose word-level timestamps, language detection, and the latest large-v3-turbo model with feature parity to the CLI. Some bindings lag.
2. **Demucs on MLX in production**: Community ports have impressive demos but uncertain long-term maintenance. May need to budget for either contributing fixes or owning a fork.
3. **RTX 5070 Ti regression in faster-whisper #1287**: Need to verify whether this is fixed before relying on faster-whisper as the CUDA fast-path.
4. **CoreML conversion of madmom/librosa/autochord chord models**: These are mostly classical DSP and shouldn't need acceleration, but if any modern chord-recognition transformer is adopted, its CoreML/MLX path must be checked.
5. **Mac Mini M4 base 16GB ceiling**: Whether large-v3-turbo + Demucs + whisperX simultaneously fit in 16GB unified memory under realistic background-app load. May force a sequential pipeline rather than parallel.
6. **Apple's 2026/2027 ML compiler maturity**: If Apple ships a PyTorch compiler for Metal that closes the MPS gaps, the calculus shifts toward "just use PyTorch everywhere." Worth tracking.

---

## Sources

- [MLX framework repo (ml-explore/mlx)](https://github.com/ml-explore/mlx)
- [MLX examples (ml-explore/mlx-examples)](https://github.com/ml-explore/mlx-examples)
- [mlx-whisper on PyPI](https://pypi.org/project/mlx-whisper/)
- [mlx-audio (Blaizzy/mlx-audio)](https://github.com/Blaizzy/mlx-audio)
- [demucs (facebookresearch/demucs)](https://github.com/facebookresearch/demucs)
- [demucs MPS issue #432](https://github.com/facebookresearch/demucs/issues/432)
- [demucs-mlx port writeup](https://medium.com/@andradeolivier/i-ported-demucs-to-apple-silicon-it-separates-a-7-minute-song-in-12-seconds-6c4e5cffb5c3)
- [faster-whisper (SYSTRAN/faster-whisper)](https://github.com/SYSTRAN/faster-whisper)
- [faster-whisper #911 — MPS unsupported](https://github.com/SYSTRAN/faster-whisper/issues/911)
- [faster-whisper #515 — Apple Metal/MPS request](https://github.com/SYSTRAN/faster-whisper/issues/515)
- [faster-whisper #1287 — 5070 Ti regression](https://github.com/SYSTRAN/faster-whisper/issues/1287)
- [whisper.cpp (ggml-org/whisper.cpp)](https://github.com/ggml-org/whisper.cpp)
- [whisper.cpp roadmap discussion #126](https://github.com/ggml-org/whisper.cpp/discussions/126)
- [whisper.cpp ANE issue #2124](https://github.com/ggml-org/whisper.cpp/issues/2124)
- [audiocraft Apple Silicon issue #31](https://github.com/facebookresearch/audiocraft/issues/31)
- [audiocraft #43](https://github.com/facebookresearch/audiocraft/issues/43)
- [trizko/audiocraft Apple Silicon fork](https://github.com/trizko/audiocraft)
- [basic-pitch (spotify/basic-pitch)](https://github.com/spotify/basic-pitch)
- [basic-pitch DeepWiki overview](https://deepwiki.com/spotify/basic-pitch/1-overview)
- [Spleeter (deezer/spleeter)](https://github.com/deezer/spleeter)
- [Spleeter Apple Silicon discussion #696](https://github.com/deezer/spleeter/issues/696)
- [insanely-fast-whisper MPS issue #258](https://github.com/Vaibhavs10/insanely-fast-whisper/issues/258)
- [Mac whisper speedtest (anvanvan/mac-whisper-speedtest)](https://github.com/anvanvan/mac-whisper-speedtest)
- [RTX 4090 vs M1 Pro Whisper benchmark — owehrens.com](https://owehrens.com/whisper-nvidia-rtx-4090-vs-m1pro-with-mlx/)
- [State of PyTorch Hardware Acceleration 2025](https://tunguz.github.io/PyTorch_Hardware_2025/)
- [Apple Developer — Accelerated PyTorch on Mac](https://developer.apple.com/metal/pytorch/)
- [Modal blog — choosing Whisper variants](https://modal.com/blog/choosing-whisper-variants)
- [WhisperKit paper — arXiv 2507.10860](https://arxiv.org/html/2507.10860v1)
- [Apple Silicon Whisper performance benchmarks — voicci.com](https://www.voicci.com/blog/apple-silicon-whisper-performance.html)
- [whisply CLI orchestrator](https://pypi.org/project/whisply/)
- [HuggingFace — Releasing Swift Transformers](https://huggingface.co/blog/swift-coreml-llm)
- [PyTorch Device Management documentation](https://docs.pytorch.org/docs/main/accelerator/device.html)
- [CTranslate2 hardware support docs](https://opennmt.net/CTranslate2/hardware_support.html)
- [Mac Mini M4 16GB local LLM benchmarks — like2byte.com](https://like2byte.com/mac-mini-m4-16gb-local-llm-benchmarks-roi/)
- [Whisper on Mac M4 analysis — DEV community](https://dev.to/theinsyeds/whisper-speech-recognition-on-mac-m4-performance-analysis-and-benchmarks-2dlp)

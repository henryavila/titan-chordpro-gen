# Source Separation: State of the Art (2024-2026)

> Research conducted for Titan ChordPro Lib. Goal: select source separation tool(s) for stem extraction (vocals/bass/drums/other).
> Last updated: 2026-05-08

## Overview

Music source separation (MSS) has moved decisively past the U-Net / BLSTM era. The field now sits in a clear "transformer + band-split" plateau, where the dominant family is **RoFormer-style** models (Band-Split RoFormer / Mel-Band RoFormer) trained with extra data, and the previously-dominant **Hybrid Transformer Demucs (HTDemucs)** is now considered the strong baseline rather than the SOTA. ByteDance AI Labs introduced BS-RoFormer (Lu et al., 2023) and Mel-RoFormer (Wang et al., 2023, 2024); these architectures swept the MDX'23 Sound Demixing Challenge and have been the de-facto reference ever since, with community fine-tunes (notably by `viperx` distributed via `ZFTurbo/Music-Source-Separation-Training`) pushing vocal SDR past 11 dB on the Multisong leaderboard.

The original Demucs project (`facebookresearch/demucs`) was **archived on 2025-01-01**, with the maintainer noting they no longer work at Meta. A community fork (`adefossez/demucs`) exists but explicitly states "this project is not actively maintained anymore and only important bug fixes will be processed." Practical Demucs usage in 2026 therefore happens through ecosystem wrappers — `python-audio-separator` (UVR-derived, MIT) and the MLX port `demucs-mlx` (MIT, actively developed) — not through the original repo. ([demucs README](https://github.com/facebookresearch/demucs); [BS-RoFormer paper](https://arxiv.org/abs/2310.01809))

For Titan ChordPro Lib's two-platform target (NVIDIA RTX 5070Ti + Apple Silicon M4), the practical decision splits along hardware lines. CUDA gets the full menu (BS-RoFormer, Mel-RoFormer, SCNet-XL, HTDemucs-FT, ensembles via `python-audio-separator`). Apple Silicon is more constrained: PyTorch's MPS backend has known gaps for the complex-tensor ops Demucs and RoFormer rely on, so the cleanest native Mac story is **`demucs-mlx`** (no PyTorch, custom Metal kernels, ~73x realtime on M4 Max) — or alternatively **CoreML-converted UVR models** through `python-audio-separator`. RoFormer models do not yet have a first-class MLX or CoreML port; running them on Mac means PyTorch with `PYTORCH_ENABLE_MPS_FALLBACK=1` (slow) or CPU.

## Tools Investigated

### HTDemucs / HTDemucs-FT (Demucs v4)
- **Type:** Hybrid spectrogram + waveform U-Net with cross-domain Transformer Encoder (self-attention within domain, cross-attention across domains)
- **License:** MIT
- **Repository:** https://github.com/facebookresearch/demucs (archived 2025-01-01, read-only); fork at https://github.com/adefossez/demucs (bug-fix only). Last release `v4.0.1` on 2022-12-07. ([Demucs repo](https://github.com/facebookresearch/demucs))
- **Hardware support:** CUDA: ✅, MPS: ⚠️ (works with `PYTORCH_ENABLE_MPS_FALLBACK=1` because complex-tensor ops aren't in MPS — STFT/iSTFT fall back to CPU; users on M1 Max report ~2 s/s realtime via this path), MLX: ✅ via separate `demucs-mlx` port, CoreML: ✅ via `python-audio-separator`, CPU: ✅
- **Performance:** Average SDR ≈ **9.00 dB** on MUSDB18-HQ (htdemucs trained on MUSDB-HQ + 800 extra songs); fine-tuned `htdemucs_ft` reaches **9.20 dB** average SDR. Per-stem numbers from the original paper (htdemucs, MUSDB18-HQ): vocals ≈ 7.93 dB, drums ≈ 8.24 dB, bass ≈ 8.76 dB, other ≈ 5.59 dB. **[UNCERTAIN]** — exact per-stem table is in the paper; aggregate 9.00/9.20 is widely cited and confirmed in the README. ([Hybrid Transformers paper](https://arxiv.org/abs/2211.08553))
- **Inference speed:** `htdemucs` ~real-time on a recent CUDA GPU; `htdemucs_ft` is ~4x slower because it is an ensemble of four per-source fine-tunes. On Apple Silicon via PyTorch MPS, a 3:15 stereo track took ~6.9 s on M4 Max ([demucs-mlx benchmarks](https://github.com/ssmall256/demucs-mlx)).
- **Strengths:** Strong all-rounder, MIT-licensed, native 4-stem (vocals/drums/bass/other) output that exactly matches Titan's pipeline needs, well-documented, baked into dozens of downstream tools, 6-stem variant (`htdemucs_6s`) adds piano + guitar.
- **Weaknesses:** Repo archived; SDR is now ~2 dB behind RoFormer SOTA on vocals; 6-stem piano output is officially flagged as poor; PyTorch MPS path is brittle.
- **Citation:** Rouard, Massa, Défossez. "Hybrid Transformers for Music Source Separation," 2022. https://arxiv.org/abs/2211.08553

### BS-RoFormer (Band-Split RoFormer)
- **Type:** Hierarchical Transformer with Rotary Position Embedding (RoPE), band-split scheme over STFT, dual-axis attention (intra-band + inter-band)
- **License:** MIT (`lucidrains/BS-RoFormer` reference impl); training/checkpoint repo `ZFTurbo/Music-Source-Separation-Training` is also MIT
- **Repository:** https://github.com/lucidrains/BS-RoFormer (last release `v1.1.0` on 2026-02-01, actively maintained); checkpoints via https://github.com/ZFTurbo/Music-Source-Separation-Training (latest release "MVSep Mega 53 Stems" on 2026-04-20; 22 releases total). ([BS-RoFormer repo](https://github.com/lucidrains/BS-RoFormer); [ZFTurbo repo](https://github.com/ZFTurbo/Music-Source-Separation-Training))
- **Hardware support:** CUDA: ✅, MPS: ⚠️ (PyTorch model — depends on op coverage; STFT issues common, no first-party MPS support), MLX: ❌ (no native port as of 2026-05), CoreML: ❌ (not converted), CPU: ✅ (slow)
- **Performance:** **9.80 dB** average SDR on MUSDB18-HQ without extra data (smaller variant); BS-RoFormer trained on MUSDB18-HQ + 500 extra songs **won 1st place in MDX'23 / SDX'23 MSS track** with 12.9 dB SDR for vocals on the challenge leaderboard. The viperx-finetuned 2025.07 checkpoint hosted on MVSep reports vocals SDR **11.89 dB (Multisong)** / 14.58 dB (Synth) and instrumental **18.20 dB (Multisong)**. ([MVSep BS Roformer page](https://mvsep.com/algorithms/34); [BS-RoFormer paper](https://arxiv.org/abs/2309.02612))
- **Inference speed:** Comparable order-of-magnitude to HTDemucs on CUDA; somewhat slower per inference but typically used as a single-pass model rather than 4x ensemble. **[UNCERTAIN]** — exact ms/min figures vary widely by checkpoint and chunk size.
- **Strengths:** Current SOTA for vocals + instrumental; very high SDR with a single architecture; checkpoints are MIT and easy to swap; community has produced fine-tunes for bass, drums, etc.
- **Weaknesses:** Highest-SDR checkpoints are typically vocal/instrumental specialists, not native 4-stem — getting bass/drums/other often means ensembling separate fine-tunes (the ZFTurbo approach); no Apple Silicon native path; checkpoint provenance is community-driven and version drift is real.
- **Citation:** Lu, Wang, Kong, Li, Hung, Wang. "Music Source Separation with Band-Split RoPE Transformer," 2023. https://arxiv.org/abs/2309.02612

### Mel-RoFormer / Mel-Band RoFormer
- **Type:** RoFormer with mel-scale band splitting (instead of empirically-defined linear bands)
- **License:** MIT (community impl); model weights distributed by ByteDance researchers and community
- **Repository:** No standalone authoritative repo from ByteDance; reference implementation lives in `lucidrains/BS-RoFormer` (Mel variant) and `ZFTurbo/Music-Source-Separation-Training`
- **Hardware support:** CUDA: ✅, MPS: ⚠️ (same caveats as BS-RoFormer), MLX: ❌, CoreML: ❌, CPU: ✅
- **Performance:** Outperforms BS-RoFormer on vocals, drums, and other stems on MUSDB18-HQ per the original paper. Community vocal fine-tune hits SDR vocals **11.28 dB**, instrumental **17.59 dB** on the MVSep Multisong leaderboard. ([Mel-Band RoFormer paper](https://arxiv.org/abs/2310.01809))
- **Inference speed:** Roughly comparable to BS-RoFormer.
- **Strengths:** Currently the highest-quality vocal separator generally available; perceptually-motivated band split outperforms BS-RoFormer's empirical splits; same MIT-friendly ecosystem.
- **Weaknesses:** Same caveats as BS-RoFormer (no Mac-native path, vocal/instrumental specialists rather than native 4-stem); slightly fewer pretrained checkpoints than BS-RoFormer.
- **Citation:** Wang, Lu, et al. "Mel-Band RoFormer for Music Source Separation," 2023. https://arxiv.org/abs/2310.01809

### SCNet / SCNet-XL (Sparse Compression Network)
- **Type:** Frequency-domain U-Net with explicit subband split and sparsity-based encoder (different compression ratios per subband)
- **License:** MIT (community PyTorch impl; integrated into ZFTurbo training repo)
- **Repository:** https://github.com/amanteur/SCNet-PyTorch (unofficial); training + checkpoints via `ZFTurbo/Music-Source-Separation-Training`. Original paper from ICASSP 2024.
- **Hardware support:** CUDA: ✅, MPS: ⚠️ (PyTorch, not validated), MLX: ❌, CoreML: ❌, CPU: ✅
- **Performance:** Base SCNet **9.0 dB** average SDR on MUSDB18-HQ without extra data — beating HTDemucs at the time of publication while running ~2x faster on CPU. SCNet-Large doubles channel dim → 41.2 M params. SCNet-XL community fine-tunes on MVSep ensembles report vocal SDR contributions up to **+0.07 dB** on top of RoFormer ensembles, and a bass-specialist SCNet-XL hits **13.81 dB SDR** for bass alone (the highest single-bass SDR currently published). ([SCNet paper](https://arxiv.org/abs/2401.13276))
- **Inference speed:** SCNet's CPU inference time is ~48% of HTDemucs (i.e. ~2x faster on CPU). GPU inference comparable.
- **Strengths:** Excellent quality-for-compute trade-off; strongest known bass result via SCNet-XL bass fine-tune; pure CNN architecture is simpler to deploy than transformer-based models.
- **Weaknesses:** Best results require XL variants and ensembling; no first-class MLX/CoreML port; less ecosystem traction than RoFormer.
- **Citation:** Tong, Zhu, Chen, Kang, Jiang, Li, Wu, Meng. "SCNet: Sparse Compression Network for Music Source Separation," ICASSP 2024. https://arxiv.org/abs/2401.13276

### MDX-Net / MDX23 (KUIELab + ZFTurbo MVSEP-MDX23)
- **Type:** TFC-TDF U-Net family in frequency domain (MDX-Net) and ensemble Demucs4 + MDX (MVSEP-MDX23)
- **License:** MIT (both repos)
- **Repository:** https://github.com/kuielab/sdx23 (challenge baseline, 2023); https://github.com/ZFTurbo/MVSEP-MDX23-music-separation-model (3rd place Leaderboard C, MDX'23). Limited active development post-2024.
- **Hardware support:** CUDA: ✅, MPS: ⚠️, MLX: ❌, CoreML: ✅ (MDX-Net family is one of the architectures supported by `python-audio-separator`'s CoreML backend), CPU: ✅
- **Performance:** Pre-RoFormer SOTA. MVSEP-MDX23 produces 4-stem output; on the MDX'23 hidden test set it placed 3rd. Specific MUSDB18-HQ numbers are not authoritative for the ensemble. **[UNCERTAIN]** — single MDX-Net SDR on MUSDB18-HQ is reported around 8.5 dB average, below SCNet/HTDemucs.
- **Strengths:** Battle-tested ensemble; works well with ZFTurbo's UVR ecosystem; widely deployed via UVR / `python-audio-separator`; CoreML conversions exist.
- **Weaknesses:** Superseded by RoFormer family on quality; ensemble is slow.
- **Citation:** Fabbro et al. "The Sound Demixing Challenge 2023," ISMIR 2024. https://transactions.ismir.net/articles/10.5334/tismir.171

### Spleeter (Deezer)
- **Type:** U-Net on STFT magnitude
- **License:** MIT
- **Repository:** https://github.com/deezer/spleeter — last release `v2.3.0` on 2021-09-03; Deezer officially stopped active maintenance ~2022. GitHub issues from 2024-2025 confirm install regressions on modern Python.
- **Hardware support:** CUDA: ✅ (legacy TF1/2), MPS: ❌ (TensorFlow on Apple Silicon is fragile, M1 install is documented as broken without manual workarounds), MLX: ❌, CoreML: ❌ (no first-class conversion), CPU: ✅
- **Performance:** SDR vocals ≈ 6.5 dB / 4-stem average ≈ 5.9 dB on MUSDB18 — significantly below all newer systems. ([Spleeter paper, ISMIR 2019](https://archives.ismir.net/ismir2019/paper/000058.pdf))
- **Inference speed:** Very fast (real-time CPU, ~100x realtime on GPU).
- **Strengths:** Speed; historical baseline familiarity.
- **Weaknesses:** Quality is now ~3-4 dB behind SOTA; TensorFlow dependency is a liability for Mac and modern CUDA stacks; effectively unmaintained.
- **Citation:** Hennequin, Khlif, Voituret, Moussallam. "Spleeter: a fast and efficient music source separation tool," 2020. https://github.com/deezer/spleeter

### Open-Unmix (UMX / UMX-HQ / UMXL)
- **Type:** 3-layer bidirectional LSTM on magnitude spectrogram
- **License:** MIT (UMX, UMX-HQ); UMXL weights are CC-BY-NC-SA 4.0 (non-commercial)
- **Repository:** https://github.com/sigsep/open-unmix-pytorch — last release `v1.3.0` on 2024-04-16; community-focused, modest activity. ([Open-Unmix repo](https://github.com/sigsep/open-unmix-pytorch))
- **Hardware support:** CUDA: ✅, MPS: ✅ (vanilla PyTorch LSTM, mostly works on MPS), MLX: ❌, CoreML: ❌, CPU: ✅
- **Performance:** UMX 6.32 / 5.23 / 5.73 / 4.02 dB SDR (vocals/bass/drums/other on MUSDB18). UMX-HQ 6.25 / 5.07 / 6.04 / 4.28. UMXL (with extra data, non-commercial weights) 7.21 / 6.02 / 7.15 / 4.89.
- **Inference speed:** Fast.
- **Strengths:** Reference implementation, simple, MPS-friendly, paper-quality reproducible baseline.
- **Weaknesses:** ~3 dB below SOTA; UMXL weights are non-commercial — only UMX-HQ weights are MIT-compatible.
- **Citation:** Stöter, Uhlich, Liutkus, Mitsufuji. "Open-Unmix - A Reference Implementation for Music Source Separation," JOSS 2019. https://sigsep.github.io/open-unmix/

### demucs-mlx (Apple Silicon native port)
- **Type:** Re-implementation of Demucs (HTDemucs, HDemucs) on Apple's MLX framework with custom fused Metal kernels (GroupNorm+GELU, GroupNorm+GLU, OLA)
- **License:** MIT
- **Repository:** https://github.com/ssmall256/demucs-mlx — last release `v1.4.3` on 2026-03-06, actively developed. Companion `mlx-community/demucs-mlx` weight repo on Hugging Face. A second independent port exists at https://github.com/lextoumbourou/mlx-demucs (early/beta). ([demucs-mlx repo](https://github.com/ssmall256/demucs-mlx))
- **Hardware support:** CUDA: ❌, MPS: ❌ (does not need it — bypasses PyTorch entirely), MLX: ✅ (native), CoreML: ❌, CPU: ✅ (Linux fallback path with Metal-free kernels)
- **Performance:** Same model weights as upstream Demucs (htdemucs / htdemucs_ft / htdemucs_6s / hdemucs_mmi / mdx / mdx_extra) — therefore same SDR. Speed: 3:15 stereo track in **2.7 s on M4 Max** (≈ 73x realtime), 2.6x faster than PyTorch-MPS Demucs. Numerical error vs PyTorch reference: 0.03% (lextoumbourou port).
- **Inference speed:** ~2.7 s per 3-minute song on M4 Max → ~0.9 s per minute of audio.
- **Strengths:** Best Mac-native option; no PyTorch dependency; uses Apple unified memory efficiently; same MIT weights as upstream; actively maintained as of early 2026.
- **Weaknesses:** Demucs-only (no RoFormer port yet); only one developer; smaller community.
- **Citation:** ssmall256, "demucs-mlx," 2026. https://github.com/ssmall256/demucs-mlx

### python-audio-separator (UVR ecosystem wrapper)
- **Type:** Inference-only Python library wrapping multiple architectures: MDX-Net, VR Arch, Demucs v4, MDX23C, **Mel-Band Roformer, BS Roformer**
- **License:** MIT (with attribution requirement to UVR project for the model weights)
- **Repository:** https://github.com/nomadkaraoke/python-audio-separator — actively maintained, frequent releases, on PyPI as `audio-separator`. ([python-audio-separator repo](https://github.com/nomadkaraoke/python-audio-separator))
- **Hardware support:** CUDA: ✅ (11.8 / 12.2), MPS: ⚠️ (model-dependent), MLX: ❌, CoreML: ✅ (M1+ on macOS Sonoma+ — first-class), CPU: ✅
- **Performance:** Inherits SDR of the underlying model (BS-Roformer, Mel-Roformer, Demucs, etc.); the value-add is unified API + ensembling.
- **Strengths:** Single Python API for the entire UVR-vintage model zoo; CoreML acceleration for Apple Silicon; model auto-download; CLI + library + Docker.
- **Weaknesses:** UVR weight provenance is community-curated (not all model authors have published official MIT weights); CoreML path doesn't yet cover RoFormer.
- **Citation:** https://github.com/nomadkaraoke/python-audio-separator

## Comparison Table

| Tool | Vocals SDR | Bass SDR | Drums SDR | Other SDR | Avg | CUDA | MPS | MLX | License | Active? |
|------|-----------|----------|-----------|-----------|-----|------|-----|-----|---------|---------|
| Mel-RoFormer (vocal fine-tune) | **11.28** [1] | n/a | n/a | n/a | n/a | ✅ | ⚠️ | ❌ | MIT | ✅ |
| BS-RoFormer (viperx 2025.07) | **11.89** [2] | n/a | n/a | n/a | n/a | ✅ | ⚠️ | ❌ | MIT | ✅ |
| BS-RoFormer (paper, MUSDB18-HQ only) | ~9.8 [3] | ~10.0 | ~10.5 | ~6.5 | **9.80** | ✅ | ⚠️ | ❌ | MIT | ✅ |
| SCNet-XL (bass specialist) | n/a | **13.81** [4] | n/a | n/a | n/a | ✅ | ⚠️ | ❌ | MIT | ✅ |
| SCNet (paper) | ~10.0 | ~8.7 | ~9.5 | ~6.5 | **9.00** [5] | ✅ | ⚠️ | ❌ | MIT | ✅ |
| HTDemucs-FT | ~8.0 | ~9.0 | ~8.7 | ~6.0 | **9.20** [6] | ✅ | ⚠️ | ✅ via demucs-mlx | MIT | ⚠️ archived |
| HTDemucs | 7.93 | 8.76 | 8.24 | 5.59 | **9.00** [6] | ✅ | ⚠️ | ✅ via demucs-mlx | MIT | ⚠️ archived |
| MDX23 ensemble | ~8.5 | ~8.0 | ~8.5 | ~5.5 | ~8.5 | ✅ | ❌ | ❌ | MIT | ⚠️ |
| Open-Unmix UMXL | 7.21 | 6.02 | 7.15 | 4.89 | **6.32** [7] | ✅ | ✅ | ❌ | CC-BY-NC-SA (weights) | ⚠️ low activity |
| Open-Unmix UMX-HQ | 6.25 | 5.07 | 6.04 | 4.28 | **5.41** [7] | ✅ | ✅ | ❌ | MIT | ⚠️ low activity |
| Spleeter (4-stem) | ~6.55 | ~5.10 | ~6.71 | ~4.13 | **~5.6** [8] | ✅ | ❌ (TF) | ❌ | MIT | ❌ unmaintained |

[1] Mel-RoFormer vocal fine-tune, MVSep Multisong leaderboard, 2024-10 — [MVSep news](https://mvsep.com/en/news)
[2] BS-RoFormer viperx 2025.07, Multisong — [MVSep BS Roformer](https://mvsep.com/algorithms/34)
[3] BS-RoFormer paper (MUSDB18-HQ, no extra data), small variant 9.80 dB avg — [arXiv 2309.02612](https://arxiv.org/abs/2309.02612)
[4] SCNet-XL bass — [ZFTurbo MSST releases](https://github.com/ZFTurbo/Music-Source-Separation-Training/releases)
[5] SCNet paper — [arXiv 2401.13276](https://arxiv.org/abs/2401.13276)
[6] HTDemucs paper (MUSDB18-HQ + 800 extra songs) — [arXiv 2211.08553](https://arxiv.org/abs/2211.08553); per-stem values are paper estimates and should be verified against Table 2 of the paper [UNCERTAIN]
[7] Open-Unmix README — [sigsep/open-unmix-pytorch](https://github.com/sigsep/open-unmix-pytorch)
[8] Spleeter ISMIR 2019 paper

## Hardware Support Deep Dive

**NVIDIA RTX 5070Ti (CUDA 12.x):** No constraints. Every tool listed runs on CUDA. The recommended path is `python-audio-separator` on CUDA, which exposes BS-Roformer + Mel-Roformer + HTDemucs + MDX23C with one API and supports ensembling.

**Apple Silicon M4 (MLX / Metal / Neural Engine):** This is where the field bifurcates.

- **Demucs / HTDemucs:** The PyTorch MPS path technically works because the Demucs codebase falls back to CPU for the complex-tensor STFT/iSTFT ops that MPS does not implement. Performance on M4 Max is around 6.9 s for a 3:15 stereo track (~28x realtime) — usable but not ideal. The far better path is **`demucs-mlx`** which natively runs on MLX with custom Metal kernels (~73x realtime, no PyTorch). CoreML conversion is also available through `python-audio-separator`.
- **BS-RoFormer / Mel-RoFormer:** No native MLX or CoreML port exists as of 2026-05. Running them on Mac means either (a) `python-audio-separator` with CPU-only execution (slow, but works), (b) PyTorch with `PYTORCH_ENABLE_MPS_FALLBACK=1` (slow due to STFT/complex ops falling back), or (c) staying CUDA-only. A native MLX port of BS-RoFormer is the single biggest missing piece for Mac users — Mixxx's GSoC 2025 ONNX-conversion project for Demucs is a precedent for what's needed.
- **SCNet:** Same story as RoFormer — PyTorch model, no native Apple port.
- **Open-Unmix:** Vanilla LSTM, MPS-friendly out of the box. Quality is far from SOTA though.
- **Spleeter:** TensorFlow-based; Apple Silicon support is fragile. Skip.
- **Neural Engine (ANE):** None of the surveyed tools currently target ANE directly. CoreML conversion (where available, e.g. UVR MDX-Net) is the pragmatic path; CoreML can dispatch to ANE/GPU/CPU at runtime.

**Apple Silicon practical takeaway for Titan:** A pipeline that needs all four stems on M4 today must either accept that Demucs is the ceiling on Mac (via demucs-mlx, ~9.0 dB avg SDR), or accept CPU-bound execution for the RoFormer family (perhaps acceptable for batch / non-interactive workflows but not real-time). On CUDA the answer is unambiguous: BS-RoFormer ensembled with SCNet-XL bass fine-tune.

## Recommendations for Titan ChordPro Lib

The audio in Titan goes to four downstream consumers with different sensitivity profiles:

1. **Vocals → lyrics transcription.** Modern ASR (Whisper / WhisperX / NeMo Parakeet) is reasonably tolerant of vocal residual; +1 dB of vocal SDR helps but is not transformative. **Mel-RoFormer** would be ideal but **HTDemucs is sufficient**.
2. **Bass → chord-root inference.** Bass is where RoFormer/SCNet-XL shines hardest (+3 dB over Demucs in some cases). For root detection on a clean bass stem, even HTDemucs is typically usable; for difficult mixes (orchestral, lo-fi, sub-heavy production) an SCNet-XL bass specialist is meaningfully better.
3. **Other → chord/solo detection.** "Other" is the noisiest stem in every model. Consider running chord detection on the **mix** (or `mix - vocals - drums`) rather than the `other` stem, since chord models like Chordino were trained on full mixes anyway. The choice of separator matters less here.
4. **Drums → beat tracking.** Madmom / BeatNet are very robust; HTDemucs drums (~8.2 dB) is more than enough.

**Concrete recommendation — two-tier strategy:**

- **Tier 1 (default, cross-platform): `python-audio-separator` with `htdemucs_ft` model.** Single dependency, MIT-licensed, works on CUDA, CoreML on Mac, and CPU. Gives you native 4-stem output with ~9.2 dB avg SDR. Zero plumbing for the user. This is the right MVP default.

- **Tier 2 (CUDA-only "high quality" mode): BS-RoFormer (or Mel-RoFormer) for vocals + instrumental, then re-run HTDemucs on the instrumental for bass/drums/other splitting.** Optionally swap the bass stem for an SCNet-XL bass-specialist output. This is the arrangement used by MVSep and by the top Sound Demixing Challenge submissions. Expose it as `quality="best"` or similar; document the CUDA requirement.

- **Tier 3 (Apple Silicon "fast" mode): `demucs-mlx` with `htdemucs_ft`.** ~73x realtime on M4 Max. Same SDR as upstream Demucs, dramatically faster on Mac than PyTorch-MPS or CoreML paths. Add it as a runtime-detected backend so users on Apple Silicon get this automatically.

**License compatibility:** All recommended tools and their MIT-licensed weights are compatible with an MIT-licensed library. Avoid: Open-Unmix UMXL weights (CC-BY-NC-SA, non-commercial), and exercise normal due-diligence on UVR-distributed RoFormer checkpoints (most are community fine-tunes that inherit MIT but a few specialty fine-tunes carry no clear license — verify per-checkpoint before bundling).

**Architectural implication:** Design Titan's stem-separation layer as a pluggable `Separator` interface with a backend selector (`htdemucs`, `htdemucs_ft`, `bs_roformer`, `mel_roformer`, `scnet_xl_bass`, ...) and a hardware selector (`auto`, `cuda`, `mlx`, `cpu`). Default to `auto + htdemucs_ft`. Do not hard-code Demucs.

## Open Questions / Things to Validate Empirically

- **Per-stem MUSDB18-HQ SDR for HTDemucs and HTDemucs-FT** — I cite paper aggregates of 9.00 / 9.20 dB confidently but the per-stem values in this doc for HTDemucs-FT are estimates. Pull Table 2 from the Rouard 2022 paper before publishing any user-facing benchmark.
- **End-to-end pipeline quality with Tier 2 routing** — Does running BS-RoFormer for vocal/instrumental then HTDemucs on the instrumental actually improve downstream chord detection on the `other` stem vs. running HTDemucs once? Worth a controlled A/B on 20 songs.
- **MLX BS-RoFormer port viability** — MLX has the primitives needed (complex tensors landed in MLX 0.13+); a port is feasible but requires effort. Track community work.
- **CoreML latency on M4 vs MLX** — `python-audio-separator`'s CoreML path might already be fast enough that demucs-mlx is unnecessary as a separate dependency. Benchmark before committing.
- **Memory footprint** — HTDemucs needs ~7 GB peak GPU memory for 4-stem inference on a full track without segmentation. RoFormer models are larger. Validate against the 5070Ti's 16 GB and Mac M4 unified memory budgets.
- **Real-time vs offline** — Titan's roadmap doesn't yet specify whether stem extraction needs to be streaming. If yes, look at Band-SCNet (Interspeech 2025), a causal lightweight variant of SCNet aimed at real-time.

## Sources

- [Demucs (facebookresearch) — archived 2025-01-01](https://github.com/facebookresearch/demucs)
- [Demucs fork (adefossez) — bug-fix only](https://github.com/adefossez/demucs)
- [Hybrid Transformers for Music Source Separation, Rouard et al. 2022](https://arxiv.org/abs/2211.08553)
- [BS-RoFormer reference impl, lucidrains](https://github.com/lucidrains/BS-RoFormer)
- [Music Source Separation with Band-Split RoPE Transformer, Lu et al. 2023](https://arxiv.org/abs/2309.02612)
- [Mel-Band RoFormer for Music Source Separation, Wang et al. 2023](https://arxiv.org/abs/2310.01809)
- [Mel-RoFormer for Vocal Separation and Vocal Melody Transcription, Wang et al. 2024](https://arxiv.org/pdf/2409.04702)
- [SCNet: Sparse Compression Network, Tong et al. ICASSP 2024](https://arxiv.org/abs/2401.13276)
- [ZFTurbo Music-Source-Separation-Training (checkpoints + training code)](https://github.com/ZFTurbo/Music-Source-Separation-Training)
- [MVSep BS Roformer algorithm card](https://mvsep.com/algorithms/34)
- [MVSep news / leaderboards](https://mvsep.com/en/news)
- [MUSDB18-HQ benchmark on Papers with Code](https://paperswithcode.com/sota/music-source-separation-on-musdb18-hq)
- [Sound Demixing Challenge 2023 (TISMIR)](https://transactions.ismir.net/articles/10.5334/tismir.171)
- [MVSEP-MDX23, ZFTurbo](https://github.com/ZFTurbo/MVSEP-MDX23-music-separation-model)
- [demucs-mlx, ssmall256](https://github.com/ssmall256/demucs-mlx)
- [mlx-demucs, lextoumbourou](https://github.com/lextoumbourou/mlx-demucs)
- [I Ported Demucs to Apple Silicon (Medium write-up)](https://medium.com/@andradeolivier/i-ported-demucs-to-apple-silicon-it-separates-a-7-minute-song-in-12-seconds-6c4e5cffb5c3)
- [python-audio-separator (UVR wrapper)](https://github.com/nomadkaraoke/python-audio-separator)
- [Spleeter, Deezer](https://github.com/deezer/spleeter)
- [Open-Unmix PyTorch, sigsep](https://github.com/sigsep/open-unmix-pytorch)
- [PyTorch MPS limitations / fallback docs](https://docs.pytorch.org/serve/hardware_support/apple_silicon_support.html)
- [Apple Metal PyTorch](https://developer.apple.com/metal/pytorch/)
- [Mixxx GSoC 2025 — Demucs to ONNX](https://mixxx.org/news/2025-10-27-gsoc2025-demucs-to-onnx-dhunstack/)
- [Music AI source separation benchmarks](https://music.ai/blog/research/source-separation-benchmarks/)

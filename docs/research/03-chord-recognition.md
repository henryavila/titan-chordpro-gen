# Automatic Chord Recognition: State of the Art (2024-2026)

> Research conducted for Titan ChordPro Lib. Goal: detect chord progressions including inversions/slash chords, with timing accurate enough for beat-grid quantization.
> Last updated: 2026-05-08

## Overview

Automatic Chord Recognition (ACR) is one of the oldest and most studied tasks in Music Information Retrieval (MIR). After a wave of deep-learning progress between roughly 2015 and 2019 (CNN/CRNN/Transformer chroma models), the field is widely acknowledged to have **plateaued on the basic major/minor task** — small-vocabulary frame-wise accuracy on Isophonics has been stuck around 83-86% for several years, a "glass ceiling" attributed to ambiguous ground truth, annotator disagreement, and the long-tail distribution of chord types in Western popular music.

What has changed since 2022-2026 is the **direction** of research:

1. **Large-vocabulary recognition** (170-301 chord classes including 7ths, sus, dim, aug, and slash chords) is now the active problem. Chord-structure decomposition (Jiang et al., ISMIR 2019) became the de-facto template, and ChordFormer (2025) and BACHI (2025) are the current SOTA on this harder task.
2. **Conformer architectures** (CNN + self-attention) overtook pure Transformers (BTC) for audio ACR around 2024-2025.
3. **LLM-based post-correction** (GPT-4o chain-of-thought re-ranking using bass-stem features) emerged in late 2025 as a way to squeeze 1-3 extra MIREX points without retraining acoustic models.
4. **Source-separation-aware ACR** — running ACR on Demucs stems (or fusing with the bass stem) is now an established trick rather than a research curiosity.

But: **production-grade, pip-installable, large-vocabulary ACR with first-class slash-chord support does not really exist yet in open source.** Every off-the-shelf option has a serious limitation — outdated hardware support, majmin-only output, no maintenance, or lab-quality code. Titan ChordPro Lib will need to either accept the chord-extractor (Chordino) baseline, fine-tune BTC-large-voca, or port ChordFormer / Jiang-2019 weights.

## Key Datasets and Metrics

### Datasets

| Dataset | Songs | Genre | Notes |
|---|---|---|---|
| **Isophonics** | ~290 | Beatles, Queen, Carole King, Zweieck, Michael Jackson | The de-facto ACR benchmark since 2009. Annotations from QMUL (C4DM). |
| **RWC Pop** | 100 | Japanese pop | Higher annotation quality than Isophonics for some quality classes. |
| **McGill Billboard** | 890 (740 unique) | US pop 1958-1991 | Widely used; includes inversions and 7ths. NNLS Chroma is provided for all tracks. |
| **JAAH** | 113 | Jazz | Test of out-of-distribution generalisation; rarely reported but increasingly cited (2023+). |
| **HookTheory / ChoCo** | thousands | Crowdsourced multi-genre | Used for ChordSync and large-scale weak supervision; alignment-only. |
| **UsPop2002** | ~200 | Pop | Used as auxiliary test set (ACE / LLM-CoT 2025). |
| **Schubert Winterreise** | 24 | Classical lieder | Out-of-distribution test in Harmony Transformer 2025 paper. |

### Metrics — MIREX Audio Chord Estimation

The MIREX 2024 task definition (unchanged since 2018) defines five evaluation classes computed via the `mir_eval` library, all reported as **Weighted Chord Symbol Recall (WCSR)** — the duration-weighted fraction of frames where the prediction maps to the same equivalence class as the ground truth:

| Class | Vocabulary | Tests… |
|---|---|---|
| **Root** | 12 pitch classes + N | Just the root note |
| **MajMin** | `{N, maj, min}` | Triad quality (no inversions) |
| **MajMinBass** | `{N, maj, min, maj/3, min/b3, maj/5, min/5}` | Triads + first/second inversions |
| **Sevenths** | `{N, maj, min, maj7, min7, 7}` | Adds three seventh qualities |
| **SeventhsBass** | 19 classes incl. inversions of all 7ths | The most demanding standard class |

Note that "Tetrads" is *not* a standard MIREX class — that name is used informally in the literature for SeventhsBass-equivalent vocabularies. Vocabularies with sus/dim/aug or extended jazz chords (9, 11, 13, alt) are reported with custom metrics; comparing across papers is fragile.

A separate **Chord Content Metric (CCM)** has gained traction in 2024-2025 papers as a partial-credit score for tetrad classification.

## Tools/Models Investigated

### Chordino (NNLS Chroma)
- **Architecture:** NNLS-based pitch-salience chroma + HMM Viterbi over a hand-crafted chord template dictionary (Mauch & Dixon, 2010).
- **License:** GPL.
- **Vocabulary:** maj, min, dim, aug, sus2, sus4, maj6, min6, maj7, min7, 7, dim7, hdim7, plus N (no chord). Reports a separate **bass note** for every frame. ~13 qualities × 12 roots ≈ 156 classes plus bass.
- **Inversion support:** Yes, indirectly — bass note is reported separately so a `C` chord with bass `E` is recoverable. This is unusual among open-source tools.
- **Repository:** https://github.com/c4dm/nnls-chroma — last meaningful commit ~2014; effectively frozen but stable.
- **Hardware support:** Pure C++ DSP, CPU-only, runs anywhere a Vamp host runs (including Apple Silicon natively).
- **Performance:** ~75% MajMin WCSR on Isophonics (historical baseline). Below modern deep models on majmin, but its bass-note output gives it surprisingly competitive inversion behavior in chord-extractor pipelines.
- **Strengths:** Battle-tested in Sonic Visualiser, Chordify, Last.fm. No ML dependencies. Outputs both chord symbol AND separated bass note.
- **Weaknesses:** Pre-deep-learning accuracy. Vamp plugin dependency is a packaging headache (binary `.dylib`/`.so`/`.dll` per platform). GPL license is restrictive for proprietary pipelines.

### chord-extractor (ohollo) — Chordino wrapper
- **Architecture:** Python wrapper around vamp + Chordino with multiprocessing.
- **License:** Apache-2.0 wrapper (Chordino itself is GPL — be careful).
- **Vocabulary / Inversions:** Same as Chordino (bass note included).
- **Repository:** https://github.com/ohollo/chord-extractor — modest activity, last meaningful release 2022.
- **Hardware:** CPU-only (Vamp).
- **Notes:** This is the easiest path to "Chordino in Python today," at the cost of the Vamp/SDK installation. Numpy must be installed before `pip install chord-extractor` because of the `vamp` package.

### BTC / BTC-ISM (Park et al., ISMIR 2019)
- **Architecture:** Bi-directional Transformer with self-attention, position-wise convolutions, learned positional encoding. ISM = Improved Spectrogram-input Model (variant from same group).
- **License:** MIT.
- **Vocabulary:** Two trained variants — `voca=False` for majmin (25 classes) and `voca=True` for "large vocabulary" (170 classes covering maj, min, 7, maj7, min7, dim, aug, sus2, sus4, plus inversions).
- **Inversion support:** Yes in large-voca model.
- **Repository:** https://github.com/jayg996/BTC-ISMIR19 — 196★, 37 forks, 14 commits total, last commit 2020. Effectively unmaintained but checkpoints work. Requires PyTorch ≥ 1.0, which means modern PyTorch (2.x with CUDA / MPS / MLX) works fine after small Python compatibility fixes.
- **Hardware support:** PyTorch — CUDA out of the box; MPS works with `.to('mps')` after one or two surgical edits to the device-handling code.
- **Performance (paper, large-voca):** WCSR-Root ≈ 84.0%, MajMin ≈ 83.9%, Sevenths ≈ 75.3%, SeventhsBass ≈ 70.0%, MIREX-extended ≈ 73.5% on a combined Isophonics+RWC+UsPop+Billboard test split. These were SOTA in 2019; ChordFormer and BACHI now beat them by 2-6 pp.
- **Strengths:** Single-stage training (no separate language model). Bidirectional attention captures long-range harmonic context. Still the most-cited reproducible ACR baseline.
- **Weaknesses:** Six years old; no maintenance; inference code is research-grade (Python script, not a library).

### autochord (CJ Bayron, ISMIR 2021 Late-Breaking Demo)
- **Architecture:** Bi-LSTM-CRF over NNLS chroma features (TensorFlow).
- **License:** Apache-2.0 (model). Underlying NNLS chroma is GPL-via-Vamp.
- **Vocabulary:** **25 classes only — 12 major + 12 minor + N.** No 7ths, no slash chords.
- **Inversion support:** No.
- **Repository:** https://github.com/cjbayron/autochord — 160★, 19 forks. PyPI: `pip install autochord`. Tested on Ubuntu 18.04; macOS works with extra config; Windows unsupported.
- **Hardware:** TensorFlow + Vamp. GPU optional. No native MPS path.
- **Performance:** 67.33% reported test accuracy (note: the project's own metric, not strictly WCSR).
- **Strengths:** True one-line `pip install` experience. Outputs `.lab` files compatible with `mir_eval`.
- **Weaknesses:** majmin-only and modest accuracy. Out of scope for slash-chord output. TF dependency is heavy.

### madmom — DeepChromaChordRecognitionProcessor
- **Architecture:** DeepChroma (CNN) feature extractor + linear-chain CRF Viterbi decoder. Also a separate `CNNChordRecognitionProcessor` using Korzeniowski & Widmer's 2016 CNN with CRF.
- **License:** Source code BSD; model weights CC-BY-NC-SA 4.0 (non-commercial!).
- **Vocabulary:** **Major and minor chords only** (`DeepChromaChordRecognitionProcessor` docstring is explicit about this).
- **Inversion support:** No.
- **Repository:** https://github.com/CPJKU/madmom — last release v0.16.1 (Nov 2018); `main` branch has commits but no release for 7+ years. The library is widely used but partially abandoned, with notable Python 3.11+ compatibility issues (Cython, numpy 2.x).
- **Hardware:** CPU (custom NN inference, not PyTorch/TF).
- **Performance:** ~83% MajMin WCSR on Isophonics (Korzeniowski & Widmer 2016). Strong for majmin given CPU-only.
- **Strengths:** Robust, deterministic, no GPU needed. Pairs well with madmom's beat tracker if you stay in that ecosystem.
- **Weaknesses:** majmin-only (showstopper for ChordPro). NC license on weights blocks commercial deployment. Stale package.

### Large-Vocabulary Chord Recognition (Jiang et al., ISMIR 2019)
- **Architecture:** Multi-task CRNN with **chord structure decomposition** — separate heads for triad, bass, and seventh that recompose to a 170-class label, side-stepping the long-tail problem.
- **License:** MIT.
- **Vocabulary:** "submission" dictionary used at MIREX 2019 (170 classes incl. slash chords); also "ismir2017" and "full" (MARL) options.
- **Inversion support:** Yes — bass head is a first-class output.
- **Repository:** https://github.com/music-x-lab/ISMIR2019-Large-Vocabulary-Chord-Recognition — 58★, 17 forks, only 7 commits.
- **Hardware:** PyTorch.
- **Performance:** Paper reports ~76% WCSR on the SeventhsBass class (combined Isophonics+Billboard+MARL test set), then-SOTA for large vocabulary.
- **Strengths:** Decomposition idea is the foundation for ChordFormer / BACHI / LLM-CoT. Pre-trained checkpoints provided.
- **Weaknesses:** Tiny community; no documentation beyond the README; almost certainly will need a port to current PyTorch.

### ChordFormer (Akram et al., 2025, arXiv:2502.11840)
- **Architecture:** Conformer (convolution-augmented transformer) with chord structure decomposition heads (triad / bass / seventh).
- **License:** Paper CC-BY-NC-SA 4.0; **no public code repository as of search date.**
- **Vocabulary:** 301 classes including triads, inverted triads, sevenths, extended (9/11/13), suspended, slash.
- **Inversion support:** Yes (explicit bass head).
- **Performance:** Paper claims +2 pp frame-wise and +6 pp class-wise over prior large-vocab SOTA (BTC-large + Jiang-2019). Specific WCSR per dataset not extracted from abstract.
- **Strengths:** Current SOTA for large vocabulary as of 2025; conformer block lets it model both local timbre and global harmony.
- **Weaknesses:** No code or weights released yet. Non-commercial license on the paper's IP.

### BACHI (2025, arXiv:2510.06528)
- **Architecture:** Boundary-Aware symbolic chord recognition with masked iterative decoding. Predicts chord boundaries, then iteratively decodes (in confidence order) bass → quality → root, conditioning each step on the previous.
- **Note:** **Symbolic (MIDI / piano-roll) input, not audio**, in its original form. Not directly applicable to audio ACR but the iterative-decode idea is being adopted in audio research.
- **Performance:** 69% full-chord accuracy on classical (SOTA on classical), strong on pop benchmarks too.
- **Relevance to Titan:** Useful as a *post-processing* layer over the polyphonic transcription stage (basic-pitch / MT3) to refine chords with inversions.

### LLM Chain-of-Thought ACR (Yamashita et al., 2025, arXiv:2509.18700)
- **Architecture:** Pipeline: ACR baseline (large-voca CRNN, 301 classes) → 5-stage GPT-4o reasoning (analyse → bass-correct → quality-refine → harmonic-context → output). Uses Demucs bass stem to extract a separate bass-root estimate that the LLM cross-references against the chord prediction to drive inversion correction.
- **License:** Research code; commercial use of GPT-4o has cost implications.
- **Performance:** +1 to +2.77 pp on MIREX metric over the underlying CRNN, on IdolSongsJp / UsPop2002 / in-house test sets.
- **Relevance:** **First major paper to formalise "use the bass stem to fix slash chords"** — directly answers question 6. The bass-correction stage takes Demucs bass output, computes a frame-wise root estimate, and prompts the LLM to (a) keep the chord, (b) change inversion, or (c) replace with a diatonic alternative.

### ChordSync (Pasini et al., SMC 2024)
- **Architecture:** Conformer + CTC forced-alignment.
- **License:** MIT.
- **Repository:** https://github.com/andreamust/ChordSync — 41 commits, MIT.
- **Purpose:** **Alignment, not recognition.** Given an existing chord sequence (e.g., from Ultimate Guitar) and audio, snap chord boundaries to the audio. Useful adjacent capability for Titan if we're ingesting human chord sheets, but not a recognizer.

### ChordMini / ChordMiniApp (ptnghia-j)
- **Architecture:** Web app that bundles BTC-SL and BTC-PL variants alongside beat tracking, lyrics, and visualisation.
- **Note:** Application, not a clean library. Useful as a reference implementation for "BTC in production."

### music21 (cuthbertLab) — `roman.romanNumeralFromChord`
- **Architecture:** Symbolic music analysis. Takes a `Chord` object and a `Key`, returns a Roman numeral with figured-bass inversion symbols.
- **Relevance:** **Not an audio recognizer.** This is the right tool for the *downstream* step of converting recognised chords (from any of the audio models above) into roman-numeral analysis or for normalising ChordPro output (e.g., enharmonic spellings, key-aware chord rendering).

### librosa
- **Relevance:** Provides chroma features (`librosa.feature.chroma_cqt`, `chroma_cens`) but **no chord recogniser of its own.** It's a feature-extraction substrate, not a baseline.

### ChordRec / StructuredChord
- These names appear in the literature as informal references. "Structured training for large-vocabulary chord recognition" (McFee & Bello, ISMIR 2017) is the canonical "structured training" paper and was a key precursor to Jiang-2019 and ChordFormer.

## Comparison Table

| Model | Vocab size | Inversions | WCSR-MajMin (~Isophonics) | WCSR-Sevenths | CUDA | MPS | License | Active? | Pip-installable? |
|---|---|---|---|---|---|---|---|---|---|
| Chordino | ~156 | yes (bass) | ~75% | n/a | n/a | n/a (CPU C++) | GPL | frozen | via `chord-extractor` |
| autochord | 25 | no | ~67%* | n/a | TF | no | Apache-2.0 | low (2021-22) | yes |
| madmom DeepChroma | 25 | no | ~83% | n/a | no | no | BSD code / NC weights | low (last release 2018) | yes (with Cython pain) |
| BTC large-voca (2019) | 170 | yes | ~83.9% | ~75.3% | yes | yes (port) | MIT | unmaintained | no |
| Jiang-2019 large-voca | 170-300 | yes | ~83% | ~76% (sevenths-bass) | yes | yes (port) | MIT | unmaintained | no |
| ChordFormer (2025) | 301 | yes | SOTA | SOTA (+2/+6 pp) | yes (paper) | unknown | CC-BY-NC-SA | no code yet | no |
| LLM-CoT (2025) | 301 (depends on base) | yes | base+1-2.77 pp | base+1-2.77 pp | yes | yes | research | needs OpenAI key | no |
| ChordSync | (alignment) | (alignment) | n/a | n/a | yes | yes | MIT | active 2024 | yes (clone+install) |

*autochord's reported number is "test accuracy," not strict mir_eval WCSR; treat as approximate.

## Slash Chord / Inversion Handling

### Approaches in the literature

1. **Direct multi-class output:** the chord head outputs a label like `C/E` directly (BTC-large-voca, ChordFormer). Suffers from data sparsity — `C/E` is much rarer than `C` so the long-tail problem hits hardest here.
2. **Structure decomposition (Jiang 2019, ChordFormer):** separate output heads for `{root, quality, bass}`, recomposed at inference. Dramatically improves rare-inversion recall because the bass head sees every chord, regardless of root/quality.
3. **Iterative confidence-ranked decoding (BACHI 2025):** predict the most-confident component first (in pop music, that's bass 66.9% of the time), then condition the next prediction on it. Inverse of how monolithic models work.
4. **Bass-stem post-correction (LLM-CoT 2025):** run the audio through Demucs, take the bass stem, run pitch detection or a chroma model on it to get a frame-wise bass-note estimate, then *correct* the inversion of the chord predicted by a separate full-mix model. This is the cleanest way to inject prior knowledge from the source-separation pipeline that Titan is already running.
5. **Chordino's "free" bass output:** the NNLS-Chroma plugin produces a bass-note stream as a side product. With chord-extractor you can read both and synthesise slash-chord labels in post-processing — a poor-man's version of (4) that requires no ML.

### Practical recommendation for Titan

Because Titan already runs Demucs upstream, the **bass-stem post-correction pattern** is essentially free architecturally. Concrete pipeline:

```
audio
 ├─ Demucs → bass stem → chroma / monophonic pitch → frame bass note
 └─ Demucs → other stems (or full mix) → ACR model → (root, quality)
                                                 ↓
                                  combine: if bass ∈ chord-tones(root,quality)
                                  and bass ≠ root → slash chord (root,quality)/bass
                                  else keep root
```

This works with *any* underlying ACR model — even a majmin one — and is the pragmatic answer to question 6.

## Hardware Support Deep Dive

| Stack | CUDA (RTX 5070 Ti) | Apple Silicon (M4) | CPU fallback |
|---|---|---|---|
| Chordino (Vamp C++) | n/a | native arm64 | yes (only mode) |
| madmom (custom NN) | no GPU support | CPU only | yes |
| autochord (TensorFlow) | yes (TF-GPU) | TF-Metal works but flaky | yes |
| BTC / Jiang / ChordFormer (PyTorch) | trivial | MPS via `.to('mps')` after device-string fixes; some ops fall back to CPU | yes |
| MLX (Apple) | n/a | native, fastest on M4 | n/a |

**For the Mac Mini M4 target, MPS via PyTorch is the correct path for any PyTorch-based model.** MLX would be even better but requires a model port — there is no public MLX implementation of any chord recognizer as of search date.

For RTX 5070 Ti, all PyTorch models work out of the box. Note that the 5070 Ti is Blackwell (sm_120), so PyTorch ≥ 2.4 with CUDA 12.6+ is required.

## Recommendations for Titan ChordPro Lib

The honest assessment is that there is **no perfect off-the-shelf solution** that ticks all boxes (large vocabulary + slash chords + maintained + permissive license + pip-installable + CUDA + MPS). Here are three realistic strategies, in order of pragmatism:

### Strategy A — Pragmatic baseline (ship in v0.1)
1. **Chord-extractor (Chordino)** as the recognizer for v0.1. CPU-only, runs everywhere, outputs bass note natively.
2. Combine Chordino's chord output with Demucs bass stem in a small fusion module (`bass-stem-aware-inversion.py`) to produce slash chords.
3. Pass through music21 `harmony.ChordSymbol` / `roman.romanNumeralFromChord` for normalisation and ChordPro string formatting.
4. **Risk:** Chordino is GPL — gates Titan's licensing. If Titan must be MIT/Apache, this strategy is blocked.

### Strategy B — BTC-large-voca, ported (recommended for v0.2-0.3)
1. Fork `BTC-ISMIR19`, fix Python 3.11+ compatibility and PyTorch 2.x device handling, package as `titan-btc` internal module.
2. Use `voca=True` (170-class) checkpoints. Outputs slash chords directly.
3. Add Demucs-bass-stem post-correction as a second-pass refinement (cheap, big quality win for inversions).
4. CUDA out of the box; MPS works after one or two device-string edits; CPU fallback fine for short clips.
5. **License:** MIT — clean.
6. **Risk:** unmaintained upstream; we own the maintenance forever. Mitigated by the model being small and the inference code being self-contained (~500 LOC).

### Strategy C — Train our own (long term, v1.x)
1. Reimplement ChordFormer (or wait for code release) using ChoCo + Isophonics + Billboard + JAAH.
2. Train against 300-class vocabulary with structure decomposition.
3. Add bass-aware iterative decoding (BACHI-style) as a post-processor.
4. **Risk:** large engineering effort; data licensing for Isophonics and Billboard is restricted (research-only — cannot redistribute weights derived from them without care).

### What NOT to do
- Do **not** rely on madmom for chord recognition: license on weights is non-commercial and it's majmin-only.
- Do **not** rely on `autochord` beyond a quick smoke-test: 25-class vocabulary cannot produce ChordPro output rich enough for the project's stated goals.
- Do **not** wait for ChordFormer code: as of search date there is no repo and the license is NC-SA, which is incompatible with most distribution paths.
- Do **not** ship LLM-CoT in a runtime path: GPT-4o cost per song would dominate inference cost. Keep it as an offline-only quality oracle for evaluation.

## Open Questions

1. **Will ChordFormer release code?** Worth tracking — would change Strategy B's calculus. Search the authors' (Akram, Dettori, Buttazzo) institutional pages quarterly.
2. **MLX port for M4?** Nobody has done this for any chord model. Could be a competitive moat for Titan if executed.
3. **How well does BTC generalize to non-Western pop?** Open question; JAAH evaluation is mixed in published results. May need a fine-tune step on user data.
4. **Is the 86% "glass ceiling" real on extended vocabularies?** Some papers (LLM-CoT 2025) suggest no — the ceiling is on majmin, where labels themselves are ambiguous, while large-voca has more headroom because ground truth is more specific.
5. **Can we use polyphonic transcription (Basic Pitch / MT3) outputs as auxiliary chord features?** BACHI shows symbolic chord recognition is now strong; combining it with audio ACR is unexplored.

## Sources

### Papers (peer-reviewed and arXiv)
- Park et al., *A Bi-directional Transformer for Musical Chord Recognition*, ISMIR 2019 — https://arxiv.org/abs/1907.02698
- Jiang et al., *Large-Vocabulary Chord Transcription Via Chord Structure Decomposition*, ISMIR 2019 — https://archives.ismir.net/ismir2019/paper/000078.pdf
- McFee & Bello, *Structured Training for Large-Vocabulary Chord Recognition*, ISMIR 2017 — https://brianmcfee.net/papers/ismir2017_chord.pdf
- Pasini et al., *ChordSync: Conformer-Based Alignment of Chord Annotations to Music Audio*, SMC 2024 — https://arxiv.org/abs/2408.00674
- Akram et al., *ChordFormer: A Conformer-Based Architecture for Large-Vocabulary Audio Chord Recognition*, 2025 — https://arxiv.org/abs/2502.11840
- *BACHI: Boundary-Aware Symbolic Chord Recognition Through Masked Iterative Decoding*, 2025 — https://arxiv.org/abs/2510.06528
- *Enhancing Automatic Chord Recognition through LLM Chain-of-Thought Reasoning*, 2025 — https://arxiv.org/html/2509.18700v1
- *From Discord to Harmony: Decomposed Consonance-based Training*, 2025 — https://arxiv.org/html/2509.01588
- *Training chord recognition models on artificially generated audio*, 2025 — https://arxiv.org/abs/2508.05878
- *Latency-controlled Automatic Chord Recognition with Contextual Block Processing Transformer*, SMC 2025 — https://smc25.iem.at/contributions/latency-controlled-chord-recognition/
- McVicar et al., *20 Years of Automatic Chord Recognition from Audio*, ISMIR 2019 (retrospective) — https://archives.ismir.net/ismir2019/paper/000004.pdf

### Repositories
- Chordino / NNLS Chroma — https://github.com/c4dm/nnls-chroma
- chord-extractor (Python wrapper) — https://github.com/ohollo/chord-extractor
- BTC-ISMIR19 — https://github.com/jayg996/BTC-ISMIR19
- Large-Vocabulary Chord Recognition (Jiang) — https://github.com/music-x-lab/ISMIR2019-Large-Vocabulary-Chord-Recognition
- autochord — https://github.com/cjbayron/autochord
- ChordSync — https://github.com/andreamust/ChordSync
- madmom — https://github.com/CPJKU/madmom
- ChordMiniApp (BTC reference impl) — https://github.com/ptnghia-j/ChordMiniApp

### Documentation / other
- MIREX 2024 Audio Chord Estimation — https://music-ir.org/mirex/wiki/2024:Audio_Chord_Estimation
- MIREX 2025 Audio Chord Estimation — https://music-ir.org/mirex/wiki/2025:Audio_Chord_Estimation
- Chordino / NNLS Chroma docs — http://www.isophonics.net/nnls-chroma
- The Deep Chroma Extractor (Korzeniowski post) — https://fdlm.github.io/post/deepchroma/
- madmom chord docs — https://madmom.readthedocs.io/en/latest/modules/features/chords.html
- music21 roman module — https://music21.org/music21docs/moduleReference/moduleRoman.html
- MIRFLEX (ISMIR 2024) — https://arxiv.org/html/2411.00469v1

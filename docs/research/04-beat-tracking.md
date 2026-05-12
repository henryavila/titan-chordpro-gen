# Beat Tracking, Downbeat Detection, Time Signature (2024-2026)

> Research conducted for Titan ChordPro Lib. Goal: extract beat grid, downbeats, and time signature from audio with high precision for chord-grid quantization.
> Last updated: 2026-05-08

## Overview

Beat tracking is the master clock of Titan ChordPro Lib. Every chord, lyric anchor, and slash mark in the output ChordPro file is referenced to a beat index, and a measure index is derived from the downbeat sequence and an estimated time signature. Errors here cascade: a missed downbeat shifts every measure boundary; a wrong meter (4/4 vs 6/8) corrupts the entire slash-grid representation; a bad tempo estimate destroys the rhythmic feel of intros and instrumentals where chords are notated as `[C] x///`.

The field has moved fast. The 2021-era pipeline (BeatNet/madmom: CRNN activations + DBN/particle filter postprocessing) is no longer the F-measure leader. As of 2025-2026, the strongest open offline beat trackers are:

1. **BeatThis** (Foscarin/Schlüter/Widmer, ISMIR 2024) — transformer-based, no DBN, MIT-licensed, PyTorch.
2. **BeatFM** (2025, ICASSP 2026) — pre-trained music foundation model + multi-dimensional aggregation; reports the highest published GTZAN downbeat F1 to date.
3. **All-In-One** (Kim & Nam, WASPAA 2023) — joint beat/downbeat/segment/structure on demixed audio with neighborhood attention; integrates structure analysis "for free."
4. **Beat Transformer** (Zhao/Xia/Wang, ISMIR 2022) — demixed input + dilated self-attention; still a strong baseline and useful when a DBN is desirable.
5. **BeatNet+** (Heydari et al., TISMIR Dec 2024) — best-in-class **online** tracker, builds on BeatNet's CRNN + particle filter.
6. **BEAST** (ICASSP 2024) — streaming Transformer with strong online F1 at sub-50 ms latency.

For Titan's offline workflow (audio file in, ChordPro file out, no real-time constraint), BeatThis is the leading default with All-In-One as an attractive joint alternative when structure segmentation is also wanted.

## Key Tasks and Metrics

Beat trackers are typically evaluated on a fixed set of public benchmarks:

- **Beatles** — 180 pop tracks, mostly 4/4 with occasional ambiguities. Standard 8-fold CV.
- **Hainsworth** — 222 mixed-genre tracks including classical with variable tempo. Hardest among the "easy" sets.
- **Ballroom** — 698 strongly metric ballroom dance tracks. The "easy" benchmark; nearly saturated above 95% F1.
- **GTZAN** — 1000 tracks across 10 genres. Used **test-only** (never train on it) for fair generalization comparison.
- **SMC** — 217 challenging classical/expressive tracks, used to stress-test variable tempo.
- **Harmonix Set** — ~900 commercial pop tracks with full beat/downbeat/structure annotations; used by All-In-One and others.
- **RWC Popular** — Japanese pop reference set.

The standard metrics (all from `mir_eval.beat`):

| Metric | Definition |
|---|---|
| **F-measure** | Harmonic mean of precision/recall with a ±70 ms tolerance window per beat. |
| **CMLt** | Correct Metric Level, total — fraction of time in continuously correct segments at the right tempo and phase. |
| **CMLc** | Correct Metric Level, continuous — same but only the longest correct segment. |
| **AMLt** | Allowed Metric Level — like CMLt but tolerant of double, half, and off-beat tempo. |
| **P-score / Cemgil** | Older continuous-error metrics; still reported. |
| **mir_eval defaults** | `f_measure(reference, estimated, f_measure_threshold=0.07)` (70 ms). Phase/period continuity thresholds default to 0.175. |

For Titan's chord-quantization use case, **F-measure** at ±70 ms is the most relevant headline number, but **CMLt and AMLt** matter too: a tracker that loses the meter halfway through a song will produce visibly wrong measure boundaries even if individual beats are dense around the right places.

For downbeat tracking, the same metrics are applied to downbeat-only sequences. Downbeat F1 is consistently 10-20 points lower than beat F1 — it is genuinely the harder problem.

## Tools Investigated

### BeatThis (CPJKU)

- **Architecture:** Frontend with alternating convolutions and partial transformers over frequency/time independently, then 6 stacked transformer (RoFormer-style) blocks with rotary positional embeddings. ~20M params (full) or ~2M params (small variant). Two output heads (beats, downbeats). Shift-tolerant weighted BCE loss with max-pooling across small temporal neighborhoods so that off-by-one-frame predictions are not penalized. **No DBN postprocessing** — direct peak-picking from the activation function.
- **Tasks:** Beat + downbeat. No tempo or explicit meter output (meter is inferred implicitly via beats-per-bar from downbeat spacing).
- **License:** MIT.
- **Repository / last activity:** `github.com/CPJKU/beat_this` — actively maintained as of 2026, latest tagged release v1.1.0 (Apr 2026), `pip install beat-this`.
- **Hardware support:** PyTorch 2.0+. CUDA primary, CPU fallback via `--gpu=-1`. **MPS (Apple Silicon)** works because the model is plain PyTorch with operators that all have MPS kernels (transformers + conv); set `device='mps'`. Optional `--float16` flag for fp16 GPU inference. C++ port (`beat_this_cpp`) and Rust bindings exist.
- **Performance (paper, 8-fold CV unless noted):**
  - Beatles: Beat F1 = **94.5%**, Downbeat F1 = **88.8%**
  - Hainsworth: Beat F1 = **91.9%**, Downbeat F1 = **80.0%**
  - Ballroom: Beat F1 = **97.5%**, Downbeat F1 = **95.3%**
  - GTZAN (test-only): Beat F1 = **89.1±0.3%**, Downbeat F1 = **78.3±0.4%**
- **Strengths:** SOTA F1 across most benchmarks at release; trained on 18 datasets (4,556 tracks) for genre/style generality including classical with tempo variation and tracks with **time-signature changes**. No DBN means it does not hard-constrain meter — handy for 6/8, 7/8, mixed-meter pieces. Pure PyTorch means MPS works.
- **Weaknesses:** Offline-only (full-file context). No explicit tempo/meter output. ~20M params is heavier than BeatNet but trivial on RTX 5070Ti and runs comfortably on M4 GPU.

### BeatFM (2025-2026)

- **Architecture:** Uses a pre-trained music foundation model (MusicFM-style) as encoder, then a multi-dimensional semantic aggregation module with three parallel sub-modules over temporal, frequency, and channel domains. Beat/downbeat heads on top.
- **Tasks:** Beat + downbeat.
- **License:** Not yet clearly licensed at time of writing; arXiv 2508.09790, IEEE ICASSP 2026.
- **Repository / last activity:** No widely-distributed open-source repo as of May 2026. Paper-stage.
- **Hardware support:** PyTorch (foundation model is large — billions of parameters in MusicFM family), strongly favors GPU inference.
- **Performance:** Reported **GTZAN Beat F1 ≈ 89.5%** in best ablation, **GTZAN Downbeat F1 = 79.6%** vs BeatThis 75.5% (their own re-evaluation). Suggests +4 points downbeat improvement over BeatThis on GTZAN.
- **Strengths:** New SOTA on downbeat F1; benefits from foundation-model semantics.
- **Weaknesses:** Heavyweight; depends on a frozen foundation model checkpoint. Code/pretrained weights not yet broadly released. Watch the repo, but do not depend on this for MVP.

### All-In-One (mir-aidj / Kim & Nam, WASPAA 2023)

- **Architecture:** Source-separated (demixed via Demucs, 4 stems) spectrograms → dilated neighborhood attention (NATTEN) over time + non-dilated attention for local instrumental dependencies. Joint heads for beat, downbeat, **functional segment boundaries**, and **functional segment labels** (intro/verse/chorus/bridge/outro).
- **Tasks:** Beat + downbeat + tempo (BPM) + structural segmentation/labeling. **No explicit meter output** but downbeat density implies it.
- **License:** MIT (Python package `allin1`).
- **Repository / last activity:** `github.com/mir-aidj/all-in-one` — maintained (38+ commits as of 2026); `pip install allin1`.
- **Hardware support:** PyTorch + Demucs + madmom (for some helpers) + **NATTEN**. CUDA strongly preferred. **NATTEN has no MPS kernels** (issue #17 still open as of mid-2024) — Mac users fall back to **CPU** for the attention path. Linux/Windows need manual NATTEN build with `make`.
- **Performance:** Reported SOTA at WASPAA 2023 across all four tasks on the Harmonix Set (8-fold CV). Specific F1 numbers for beat/downbeat are competitive with Beat Transformer and pre-BeatThis SOTA on Harmonix.
- **Strengths:** Single call returns BPM + beats + downbeats + structure labels — a **giant convenience win** for ChordPro, where you may want section labels (`{start_of_chorus}`) anyway. Demixed input gives robustness on dense mixes.
- **Weaknesses:** Heavy dependency stack (Demucs runs every time → multi-GB model download; NATTEN compilation pain on Linux/Windows; broken MPS path on Mac means slow on M4 unless you run Demucs separately and pass cached stems). madmom is a transitive dep, inheriting its Python/NumPy ceiling.

### Beat Transformer (Zhao et al., ISMIR 2022)

- **Architecture:** Transformer encoder over **demixed** spectrograms (5 instrument channels via Spleeter). Time-wise + instrument-wise attention with novel dilated self-attention (linear complexity).
- **Tasks:** Beat + downbeat.
- **License:** MIT (research code).
- **Repository / last activity:** `github.com/zhaojw1998/Beat-Transformer` — research-code style, last meaningful update around 2022-2023. Functional but not actively maintained.
- **Hardware support:** PyTorch + Spleeter (TensorFlow) for demixing. CUDA. MPS works for the PyTorch part, but the TF/Spleeter dependency complicates Apple Silicon setup.
- **Performance:** ~+4 percentage points downbeat F1 over previous TCN SOTA on GTZAN at release; Beatles/Hainsworth/Ballroom strongly competitive.
- **Strengths:** Validated demixed-input approach (later adopted by All-In-One and BeatThis-style multi-input experiments).
- **Weaknesses:** Spleeter dependency is a footgun in 2026; no MIT-grade software-engineering polish; superseded in F1 by BeatThis.

### BeatNet / BeatNet+ (Heydari et al.)

- **Architecture:** CRNN front-end → particle filter inference (BeatNet, ISMIR 2021). BeatNet+ (TISMIR Dec 2024) adds a two-stage approach with auxiliary training that learns a representation invariant to the amount of percussive content, plus adaptation strategies for non-percussive and isolated-vocal music.
- **Tasks:** Beat + downbeat + tempo + meter. **One of the few open systems with an explicit meter output.**
- **License:** CC-BY-4.0 (paper-style, not pure MIT). Madmom dependency carries BSD.
- **Repository / last activity:** `github.com/mjhydri/BeatNet`. v1.2.0 added a training pipeline. BeatNet+ paper exists; whether the `+` weights have been merged into the public repo is unclear as of mid-2026.
- **Hardware support:** PyTorch + librosa + **madmom** (v0.16.1 — the legacy bottleneck) + PyAudio (for mic streaming). CUDA via `device='cuda'`; **MPS** also accepted via `device='mps'`. CPU OK.
- **Performance:** BeatNet+ outperforms all online methods on beat/downbeat F1 on GTZAN test, including for isolated singing voice and non-percussive music; offline mode is competitive but no longer the leader vs BeatThis.
- **Strengths:** Real-time / online mode (causal). Built-in meter estimation (4/4, 3/4, 6/8, etc.) inside the particle filter. BeatNet+ explicitly handles non-percussive and a-cappella audio — relevant for Titan's "vocals + acoustic guitar" demos.
- **Weaknesses:** **Madmom dependency.** Madmom is unmaintained for modern Python (see below); BeatNet inherits its install fragility on Python 3.10+ and NumPy ≥1.24. The particle filter is CPU-bound regardless of GPU.

### BEAST (ICASSP 2024)

- **Architecture:** Streaming Transformer encoder with contextual block processing and relative positional encoding for online inference.
- **Tasks:** Beat + downbeat.
- **License:** MIT (research code).
- **Repository / last activity:** `github.com/WildHoneyPie/BEAST` — research code.
- **Hardware support:** PyTorch.
- **Performance:** At **<50 ms** maximum latency: Beat F1 = **80.04%**, Downbeat F1 = **46.78%** on GTZAN — about +5 points beat F1 over previous SOTA online tracker.
- **Strengths:** The strongest published low-latency online tracker.
- **Weaknesses:** Online focus is overkill for Titan; not the offline leader.

### Madmom (CPJKU)

- **Architecture:** Hand-crafted DSP + RNN/CRNN beat activations + DBN postprocessing. `RNNDownBeatProcessor` + `DBNDownBeatTrackingProcessor`.
- **Tasks:** Beat + downbeat + tempo + onset + chord. Time signature is implicit via DBN beats-per-bar parameter.
- **License:** BSD-3-Clause.
- **Repository / last activity:** `github.com/CPJKU/madmom`. **Last release 0.16.1 in Nov 2018.** A 0.17.dev0 has been "in progress" since 2022; milestone 5 is at ~57% as of 2024-2026. Issues report: NumPy ≥1.24 import errors (`np.float`, `np.int` removals), Python 3.10+ `collections.MutableSequence` import failure, repeated unanswered "can we get a release?" pleas. Patches for the NumPy/Python issues exist in the issue tracker (e.g., #557 in Feb 2026) but are not officially merged/released. **Effectively unmaintained on PyPI.**
- **Hardware support:** **CPU only.** Cython under the hood. No CUDA, no MPS. The DBN/HMM postprocessing is the bottleneck and is not GPU-portable in any practical sense.
- **Performance:** Historically the de-facto SOTA pre-2022 (DBNDownBeatTrackingProcessor with 4/4 + 3/4 priors typically reports beat F1 in the high 80s on Beatles, ~85% on Hainsworth, ~93% on Ballroom). Now eclipsed by BeatThis.
- **Strengths:** Mature DBN-based meter inference; handles 3/4 and 4/4 robustly; excellent baseline.
- **Weaknesses:** **Modern Python/NumPy install pain.** CPU-bound. F1 surpassed by BeatThis. Recommended only as a fallback or when a DBN-style meter prior is genuinely useful.

### librosa.beat

- **Architecture:** `beat_track` — DP over an onset-strength envelope with a global tempo prior. `plp` — predominant local pulse for variable-tempo robustness, suitable for streaming.
- **Tasks:** Beat only (no downbeat, no meter).
- **License:** ISC.
- **Repository / last activity:** Actively maintained, ships with every Python audio environment.
- **Hardware support:** CPU, NumPy/Numba.
- **Performance:** Substantially below deep-learning trackers; Beatles beat F1 typically reported in the 60s-70s. Useful as a fallback or sanity-check, not as a primary engine.

### Other notable 2024-2025 work

- **BeatFCOS (Ahn & Jung, arXiv 2510.14391, Oct 2025):** Reframes beat tracking as 1D object detection (FCOS-style), backbone from WaveBeat + Feature Pyramid Network, NMS for final picks. Outperforms peak-picking on most datasets (slight regression on GTZAN). Promising but not yet packaged for general use.
- **Dual-Path Beat Tracking (MDPI Applied Sciences, 2024):** TCN + Transformer in parallel; competitive but not industry-shifting.
- **PLPDP (Chiu et al., TASLP 2023):** Predominant Local Pulse + DP, specifically targeting expressive classical piano with rapidly varying tempo. Worth knowing if Titan ever targets classical/solo-piano content.
- **Singing-Beat Tracking with self-supervised front-end (ISMIR 2022):** A capella beat tracking baseline; BeatNet+ supersedes this for the same use case.
- **Beat/downbeat tracking on performance MIDI (arXiv 2507.00466, 2025):** End-to-end transformer for performance MIDI. Not directly relevant to audio-in pipeline but interesting as a downstream check if MIDI is generated.

## Comparison Table

| Tool | Beat F (GTZAN) | Downbeat F (GTZAN) | Meter? | CUDA | MPS | MLX | Active? |
|---|---|---|---|---|---|---|---|
| **BeatThis** (2024) | **89.1%** | 78.3% | implicit (no DBN) | yes | yes | no (PyTorch) | active (2026) |
| **BeatFM** (2025) | **89.5%** | **79.6%** | implicit | yes | likely (PyTorch) | no | paper, no public code yet |
| **All-In-One** (2023) | competitive on Harmonix | competitive on Harmonix | implicit | yes | partial (NATTEN broken) | no | active |
| **Beat Transformer** (2022) | ~88% | ~74% | implicit | yes | partial (Spleeter is TF) | no | research-frozen |
| **BeatNet+** (2024) | online SOTA | online SOTA | **explicit (4/4, 3/4, 6/8)** | yes | yes | no | active |
| **BeatNet** (2021) | ~84% | ~70% | **explicit** | yes | yes | no | active (slow) |
| **BEAST** (2024) | 80.04% (<50 ms) | 46.78% (<50 ms) | implicit | yes | yes | no | research |
| **Madmom** (2016/18) | ~85% | ~70% | **explicit (DBN prior)** | **no** | **no** | no | **stalled** (last release 2018) |
| **librosa** | low | n/a | no | no | no | no | active |

(Numbers are paper-reported F-measure on GTZAN test, ±70 ms tolerance, rounded; consult source papers for exact figures and confidence intervals. F1 directly across papers is only loosely comparable due to slight differences in evaluation protocol.)

## Time Signature / Meter Estimation

This is the most "still-open" sub-problem. Three families of approach exist:

1. **Implicit via downbeats.** Most modern trackers (BeatThis, Beat Transformer, All-In-One, BeatFM) emit downbeats but no explicit meter label. You compute beats-per-bar yourself by counting beats between successive downbeats, then take the mode. This works for steady 4/4 / 3/4 / 6/8 in pop, folk, and jazz; it fails (a) when downbeats are missed or doubled, (b) for songs with mid-piece meter changes, and (c) for compound vs simple time disambiguation (e.g. 6/8 vs 3/4 with strong off-beat snares).

2. **Explicit via DBN with meter prior.** Madmom's `DBNDownBeatTrackingProcessor(beats_per_bar=[3, 4])` (or `[3, 4, 6, 7]`) treats meter as a discrete latent in the HMM; it then emits beat positions tagged with their bar position. BeatNet's particle filter is similar. This is the only widely-deployed *explicit* meter inference in open systems. Trade-off: you must enumerate candidate meters; rare meters (5/4, 11/8) need to be added by hand.

3. **Dedicated time-signature classifiers.** A small but growing thread:
   - The 2024 EURASIP paper using **ResNet18** on Mel-spectra/MFCCs evaluated on the **METER2800** dataset (2,800 30-second clips across 4 meter classes: 3/4, 4/4, 5/4, 7/4, with extra 6/8 handling) reports ResNet18 outperforming SVM/RF/KNN/CNN/CRNN baselines. Specific F1/accuracy figures from that paper are class-imbalanced (5/4 and 7/4 each have only 200 clips, so beware overfitting claims).
   - Gulati et al.'s work on **irregular meters** (notably 7/8) in Indian classical music is a useful precedent for non-Western meters.
   - Time-signature-as-a-classification-from-audio is **not yet a solved problem** for arbitrary popular music. It's accurate for major classes (3/4 vs 4/4) and degrades for compound/odd meters.

**Practical recommendation for Titan:** Use **BeatThis for beat/downbeat** and **derive meter from downbeat-spacing voting** (mode of bar lengths over the song, with a sanity-check pass that's hand-coded for 6/8 vs 3/4 disambiguation using onset-density on the second/fifth beat). For the small fraction of songs that legitimately change meter mid-piece, allow per-section overrides. Add a fallback to BeatNet+ when explicit meter output (or a non-4/4 prior) is desired. Do **not** rely on a generic time-signature classifier as the primary signal — accuracy is too low.

## Hardware Support Deep Dive

### Madmom is genuinely a CPU bottleneck in 2026

The library is Cython, and the heaviest path is the DBN/HMM Viterbi decode, which is sequential by nature and would not benefit from a naive GPU port even if one existed. There is no maintained CUDA, MPS, or MLX port. Its wheels on PyPI are pinned to NumPy < 1.24 and Python < 3.10 — installable on modern systems only via the GitHub HEAD plus community patches (issue #557 contains a working patch as of Feb 2026). For a new pipeline, **avoid hard-coupling to madmom**.

### BeatNet's GPU story is mixed

The CRNN front-end is GPU-accelerated (PyTorch, works on CUDA and MPS). The particle filter postprocessing — the part that produces actual beats and meter — runs on CPU and is the bottleneck. On a song-length input this is still real-time on a modern CPU (M4 P-cores, RTX-host i5+), but it does not scale linearly with batch.

### BeatThis is the cleanest hardware story

Pure PyTorch. CUDA fast; MPS works (tested by community); fp16 supported. ~20M params → ~80 MB checkpoint. A 5-minute song at 22.05 kHz is processed in <1 s on RTX 5070Ti and a few seconds on M4 (CPU is also fine — it's not real-time but offline batch is trivial).

### All-In-One on Apple Silicon: the NATTEN problem

Neighborhood Attention (NATTEN) ships custom CUDA kernels and CPU fallbacks but **no MPS kernel** (open issue mir-aidj/all-in-one#17). On M4 the model falls back to CPU for the attention path, which is significantly slower than CUDA (multi-minute per song instead of seconds). Workarounds: pre-compute Demucs stems separately on MPS (which works fine — Demucs has good MPS support), then run All-In-One's CPU attention path on cached features. Or just run All-In-One on the RTX 5070Ti.

### MLX is not a player here

No mainstream beat tracker has an MLX port as of 2026. PyTorch on MPS is the de-facto Apple-Silicon path. If MLX support becomes a priority later, BeatThis (small, pure-PyTorch, no exotic ops) is the easiest port target.

## Drum-Stem vs Full-Mix Input

Empirical finding from Beat Transformer (2022) and All-In-One (2023): **demixing helps**. Both use Demucs/Spleeter to split the mix into ~4 stems and feed all stems jointly (with instrument-wise attention) rather than the mix alone. Reported gains are several F1 points on downbeat tracking specifically — chords/drums carry complementary metrical cues.

For Titan, since Demucs is already in the source-separation stage of the pipeline (see research note 01), it is essentially free to feed drum + bass + other stems into the beat tracker. Two pragmatic options:

1. **Use BeatThis on the full mix.** Simpler, fast, no demixing dependency for the beat-tracking stage. F1 is already SOTA on standard benchmarks because BeatThis was trained for generality.
2. **Use All-In-One** when stems are already computed for downstream stages — gets beat + downbeat + structure in one pass on the demixed input, with a demonstrated demixing-input advantage.

Drum-only beat tracking (passing only the Demucs `drums` stem to a tracker) is **not recommended** as the *primary* path. Drums alone carry the strongest metrical cue but lose harmonic-structure cues that help disambiguate downbeats and meter (especially in 3/4 vs 6/8). Use it only as a confidence cross-check.

## Quantization Tolerance

How close does a chord change need to be to a detected beat for "snap-to-beat" to be musically faithful?

- **Perceptual JND for rhythmic onset displacement**: ~30-50 ms for trained listeners on a steady pulse; ~80-100 ms before a chord change feels visibly "off-beat" in pop/rock context.
- **mir_eval beat-tracking tolerance**: ±70 ms is the standard, calibrated to reflect "what humans accept."
- **Practical chord-grid quantization**: Snap chord changes within **±100 ms of a beat** to that beat (approximately one 16th note at 120 BPM). For changes farther than 100 ms, **either** snap to the nearest 8th-note subdivision (interpolated between detected beats) **or** introduce a sub-beat marker in ChordPro using slash notation (`[C]/// [G]`).

Concrete heuristic for the Titan pipeline:

1. Detect beats with BeatThis → array `B = [b_0, b_1, ..., b_n]` (seconds).
2. For each chord change at time `t_c` from the chord-recognition stage:
   - If `min_i |t_c - b_i| < 0.07 s` → snap to nearest beat (high confidence).
   - Else if `< 0.15 s` → snap to nearest 8th-note (interpolate between adjacent beats).
   - Else → flag as off-grid; either keep raw timing or apply 16th-note snap with a warning.
3. For instrumental sections, emit one `x` per beat in the bar: `[C] x x x x` for 4/4, `[C] x x x` for 3/4, etc., or one slash per beat using the `/` shorthand.

Variable-tempo handling in ChordPro is naturally supported because beats are referenced positionally (beat-index), not by absolute time. As long as the detected beat sequence is correct, accelerandi and ritardandi are absorbed into the beat grid for free.

## Recommendations for Titan ChordPro Lib

**Default offline beat/downbeat tracker: BeatThis.**

- MIT, pure PyTorch, MPS-friendly, SOTA F1, no DBN constraint (so 6/8 / 7/8 / mid-piece meter changes are not silently corrupted).
- Wrap with a thin adapter that exposes `(beats: np.ndarray, downbeats: np.ndarray)` and let downstream code derive meter.

**Meter inference: hand-rolled voting + fallback.**

- Compute mode of (downbeat[i+1] − downbeat[i]) in beat units → meter candidate.
- Hand-rule for 6/8 vs 3/4 (compound vs simple): check onset-strength density on subdivisions inside the bar.
- For songs where confidence is low or the user asks for explicit meter, fall back to BeatNet+ (which has explicit meter output via particle filter).

**Optional: All-In-One for joint beat+structure.**

- When the user wants section labels (`{start_of_chorus}`, `{start_of_verse}`) in the ChordPro output, use All-In-One on RTX 5070Ti (CUDA path) and feed it pre-computed Demucs stems on Mac to dodge the NATTEN MPS gap.

**Avoid:**

- Madmom as a primary dependency. Install pain on modern Python/NumPy is genuine and growing. Keep it as an optional `extras_require` for users who specifically want DBN-based meter inference.
- Beat Transformer for new code — superseded by BeatThis with a worse dependency story (Spleeter/TF).
- BEAST and BeatFCOS — research-grade; not packaged for production.
- Pure-librosa beat tracking. Use it only as a sanity-check baseline.

**Hardware targeting:**

- RTX 5070Ti: `device='cuda'`, fp16 enabled. <1 s per song.
- Mac M4: `device='mps'` for BeatThis; expect a few seconds per song. NATTEN (All-In-One) falls back to CPU — slow but acceptable for batch.
- CPU baseline: BeatThis still works, ~10-20 s per 5-min song on a recent x86 CPU.

**Quantization policy:**

- Snap to nearest beat within ±70 ms; nearest 8th within ±150 ms; emit raw timing with a `comment` flag beyond that.
- Surface confidence per-beat from the activation function (BeatThis returns it natively) — useful for downstream UI to highlight uncertain regions.

## Open Questions

1. **Will BeatFM weights be released?** If yes, +4 downbeat F1 on GTZAN is a meaningful upgrade. Watch the `arXiv:2508.09790` authors' GitHub.
2. **Is there a maintained madmom fork worth pinning?** Issue #557 patch is community work; no official fork has emerged yet. Worth checking again before locking dependencies for v1.0.
3. **Can the beat tracker output be made truly streaming for live/real-time use cases?** Not on the v1 roadmap, but BeatNet+/BEAST are the candidate solutions if it becomes a requirement.
4. **6/8 vs 3/4 disambiguation** in the absence of DBN priors — how often is the heuristic wrong on real-world worship/folk/jazz repertoire, and is there a better 2024-2026 paper on it specifically?
5. **Does feeding BeatThis demixed stems improve F1?** BeatThis is trained on full mixes, but Beat Transformer's demixed-input gains suggest there may be free F1 left on the table. Worth a small ablation experiment using Demucs stems concatenated as multi-channel input.
6. **NATTEN MPS support** — track upstream. If/when it lands, All-In-One becomes a viable Mac default.

## Sources

- BeatThis paper (ISMIR 2024): https://arxiv.org/html/2407.21658v1
- BeatThis repo (CPJKU/beat_this): https://github.com/CPJKU/beat_this
- Beat Transformer (Zhao et al., ISMIR 2022): https://arxiv.org/abs/2209.07140 / https://github.com/zhaojw1998/Beat-Transformer
- All-In-One (Kim & Nam, WASPAA 2023): https://arxiv.org/abs/2307.16425 / https://github.com/mir-aidj/all-in-one
- All-In-One NATTEN MPS issue: https://github.com/mir-aidj/all-in-one/issues/17
- BeatNet (Heydari et al., ISMIR 2021): https://github.com/mjhydri/BeatNet
- BeatNet+ (TISMIR Dec 2024): https://transactions.ismir.net/articles/10.5334/tismir.198
- BEAST (ICASSP 2024): https://arxiv.org/abs/2312.17156 / https://github.com/WildHoneyPie/BEAST
- BeatFM (arXiv 2508.09790, ICASSP 2026): https://arxiv.org/abs/2508.09790
- BeatFCOS (arXiv 2510.14391, 2025): https://arxiv.org/abs/2510.14391
- Madmom repo: https://github.com/CPJKU/madmom
- Madmom Python/NumPy compatibility issues: https://github.com/CPJKU/madmom/issues
- librosa beat module: https://librosa.org/doc/main/_modules/librosa/beat.html
- mir_eval beat metrics: https://github.com/craffel/mir_eval/blob/master/mir_eval/beat.py
- Time Signature Detection Survey: https://pmc.ncbi.nlm.nih.gov/articles/PMC8512143/
- Music time signature detection (ResNet18, EURASIP 2024): https://link.springer.com/article/10.1186/s13636-024-00346-6
- METER2800 dataset: https://www.sciencedirect.com/science/article/pii/S2352340923008053
- PLPDP (variable tempo classical, TASLP 2023): https://arxiv.org/abs/2308.10355
- Tempo, Beat and Downbeat Estimation tutorial: https://tempobeatdownbeat.github.io/tutorial/
- Demucs (drum/source separation): https://github.com/facebookresearch/demucs

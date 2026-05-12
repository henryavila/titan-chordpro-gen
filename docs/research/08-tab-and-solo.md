# Tablature Generation and Solo Transcription (2024-2026)

> Research conducted for Titan ChordPro Lib. Goal: assess feasibility of detecting solos and generating ASCII tablature within `{sot}`/`{eot}` blocks.
> Last updated: 2026-05-08

## Overview

Automatic guitar tablature transcription is **semi-solved at best** in 2026. The community has well-defined sub-problems (audio to MIDI, MIDI to fret/string assignment, technique labelling) and there are functioning open-source pipelines, but end-to-end accuracy on real-world rock/pop solos is **not at parity with human transcribers**. The most rigorous benchmarks live on `GuitarSet`, which is a tiny, clean, mostly-acoustic dataset of solo guitar — not a pop song with bass, drums, and effected electric guitar bleeding through.

The honest summary:

- **Pitch transcription (audio to MIDI notes)** for clean, isolated guitar: workable, with note-level F1 in the 0.7-0.9 range on GuitarSet from current SOTA models.
- **Tablature (string/fret) assignment**: an additional model on top of MIDI; loses accuracy due to the under-determined nature of guitar (same pitch on multiple strings). Best `Tablature F-measure` on GuitarSet sits around **0.85-0.87** (constrained CRNN/Inception/Transformer architectures), but this is *with* clean isolated guitar input — not a separated stem from a real recording.
- **Technique transcription** (bends, slides, hammer-ons, palm mutes): emerging in 2025 (TART, 2024 electric-guitar tones work) but very much research-grade.
- **Solo detection** (boundary detection of where a solo starts/ends in a mix): exists as a published task with a Georgia Tech dataset; SOTA precision around 60-65%, recall around 80%. Heuristic vocal-silence + melodic-density gating in our pipeline will likely match or beat that for our specific setup because we have stems from htdemucs.

For Titan ChordPro Lib's MVP, the realistic path is: **detect solo regions heuristically from stems, run a monophonic pitch tracker (basic-pitch or CREPE) on the "other" stem during those regions, run a separate string/fret assignment, format as ASCII tab, and ship with a clear `[approximate]` watermark on the tab block.** Aim for "useful starting point for a human" rather than "ground truth tab".

## Tools / Models for Pitch Transcription

### basic-pitch (Spotify)

- **Repo**: `spotify/basic-pitch`
- **License**: Apache 2.0
- **Latest release**: v0.4.0 (Aug 2024); active community PRs into 2025; not in active feature development from Spotify but accepting community PRs.
- **Hardware**: Ships ONNX, TensorFlow Lite, CoreML, and TensorFlow weights. Default runtime is CoreML on macOS, TF Lite on Linux, ONNX on Windows. PyTorch port exists (`gudgud96/basic-pitch-torch`) for CUDA. C++ port (`sevagh/basicpitch.cpp`) for embedded.
- **Output**: MIDI with pitch bend, frame-level multipitch posteriorgram (88 keys-equivalent), note events with onsets/offsets.
- **Performance**: Designed as a *general-purpose, lightweight, instrument-agnostic* polyphonic transcriber. Trained jointly on MAESTRO, Slakh2100, GuitarSet, iKala. Note-level F1 on GuitarSet is in the 0.6-0.7 range depending on the metric (note-with-offset vs note-only). For purely monophonic pitch tracking it is **outperformed by CREPE and YAAPT** (basic-pitch was not optimised for monophonic; reports show "poor performance across all metrics" relative to dedicated monophonic trackers — see SwiftF0 paper, 2025).
- **Strengths**: Extremely small (~17 MB), runs on CPU in under realtime, no licensing friction, multi-runtime, polyphonic-capable so it handles guitar chords during a solo (double-stops, riff fragments).
- **Weaknesses**: No string/fret output (just MIDI). Vibrato/bend detection is coarse. No technique labels. Octave errors on heavily distorted or fuzz-tone guitar.

### CREPE / torchcrepe / SwiftF0

- **CREPE** (2018, ICASSP): convolutional regression on raw waveform, monophonic only. PyTorch port `maxrmorrison/torchcrepe` is the reference.
- **License**: MIT.
- **Hardware**: Pure PyTorch — CUDA, MPS, CPU. No MLX-native port but MPS is fine for inference on M-series.
- **Output**: per-frame f0 + confidence. No notes — you have to do onset/offset segmentation yourself.
- **Performance**: F1 ~88% on monophonic music, cents accuracy ~88%, octave accuracy ~92% (per SwiftF0 benchmarks).
- **Successor — SwiftF0** (2025, arXiv 2508.18440): faster and more accurate monophonic pitch detector, ONNX-shippable.
- **Why it matters for us**: CREPE is the right tool for pitch-tracking a solo *after* we've decided "this region is monophonic guitar". The combo `CREPE for f0 → onset detector → quantise to MIDI` produces cleaner monophonic transcriptions than basic-pitch on isolated guitar lines, especially for sustained bends/vibrato.

### MT3 / MR-MT3 / YourMT3+

- **MT3** (Google, 2021/2022 ICLR): T5-style transformer that emits MIDI tokens for arbitrary instrument combinations, jointly trained across multiple AMT datasets.
- **MR-MT3** (Mar 2024): adds memory retention + token shuffling to fight the "instrument leakage" failure mode.
- **YourMT3+** (Jul 2024, MLSP): hierarchical attention encoder + mixture of experts; multi-channel decoding with incomplete annotations. Best public multi-instrument note F1.
- **License**: Apache 2.0 (MT3, MR-MT3 code); YourMT3+ code public.
- **Hardware**: Heavy. T5-scale. CUDA only realistically; CPU/MPS works but slow. No MLX port.
- **Why it might matter**: MT3 family was one of the few approaches that meaningfully *boosted* GuitarSet-low-resource transcription via joint training. Useful as a future upgrade path. **Too heavy for MVP** (model size, GPU requirement, slow inference).

### Other 2024-2026 work worth knowing

- **High Resolution Guitar Transcription via Domain Adaptation** (Riley/Edwards/Dixon, ICASSP 2024) — adapts Kong et al.'s high-resolution piano transcriber to guitar via score alignment on 79 solo guitar tracks. Reports SOTA on GuitarSet zero-shot. Project page: `xavriley.github.io/HighResolutionGuitarTranscription`. **This is the model we'd actually use in v2** if we want to upgrade beyond basic-pitch.
- **GAPS** (Aug 2024) — 14h classical guitar audio-score dataset; new SOTA in supervised + zero-shot settings on GuitarSet.
- **SynthTab** (ICASSP 2024) — large synthesised tab dataset; pre-train on synth, fine-tune on real → consistent gains on GuitarSet.
- **Leveraging Real Electric Guitar Tones and Effects** (DAFx 2024, arXiv 2405.14679) — explicitly tackles the rock/pop-style distorted electric guitar problem. Uses synthetic + real-tone pairs for robustness.
- **GOAT** (Sep 2025, arXiv 2509.22655) — large paired audio/tab dataset; the "ImageNet moment" for tab transcription is starting.
- **TART** (Oct 2025, arXiv 2510.02597) — first end-to-end pipeline to emit tablature *with technique labels* (slides, bends, hammer-ons, taps). Four stages: piano-AMT-adapted-to-guitar → MLP technique classifier → Transformer string/fret assignment → LSTM tab serialisation. No public code yet. Most ambitious paper in the space.
- **Encoder-Decoder MIDI-to-Tablature** (Jun 2025, arXiv 2506.14223) and **T5-based MIDI-to-Tab** (Oct 2025, arXiv 2510.10619) — treat the fingering problem as symbolic translation; useful if we already have MIDI from basic-pitch.

### TabCNN successors

- **TabCNN** (Wiggins/Kim, ISMIR 2019) — original CRNN over CQT input, multi-task per-string fret prediction. Repo `andywiggins/tab-cnn`. Frame-level Tablature F-measure ~0.55 on GuitarSet.
- **TabInception** (~2023) — Inception block + Transformer encoder; outperforms TabCNN on multi-pitch precision and tab F-measure.
- **CRNN at trimplexx/music-transcription** — reports MPE F1 = 0.8736 on GuitarSet, beating prior GuitarSet-only models.
- **Vision Transformer / Swin Transformer adaptations** — best multi-pitch F-measure / tab recall variants in 2024 papers.
- **Note-level Attention Model** (Kim et al., EUSIPCO 2022 → 2025 follow-up) — beat-informed quantisation, attention for tab inference. Closest in spirit to what we'd want.

## Solo Detection

### Published prior art

- **Pati & Lerch (Georgia Tech, AES 2017)** — *A Dataset and Method for Electric Guitar Solo Detection in Rock Music*. SVM over spectral + temporal + predominant-pitch + MSAF structure features. Best macro accuracy 78.6%, solo precision 63.3%. Released annotated dataset. Repo: `ashispati/GuitarSoloDetection`. **This is essentially the only dedicated paper on solo detection** and it's nearly a decade old — the problem is unloved by the modern MIR community, mostly because nobody has a reason to ship it.
- **all-in-one Music Structure Analyzer** (`mir-aidj/all-in-one`, WASPAA 2023) — joint beat/downbeat tracking + functional structure segmentation. Output labels include `intro`, `outro`, `verse`, `chorus`, `bridge`, `inst`, `solo`, `break`. Operates on demixed stems and uses dilated neighbourhood attentions. Apache-licensed, PyTorch, runs on CUDA/MPS/CPU. **This is the most useful off-the-shelf tool for us** — it directly emits a `solo` label.
- **MSAF** (`urinieto/msaf`) — older but still useful structure analyser.
- **TENT** (TISMIR) — *Technique-Embedded Note Tracking for Real-World Guitar Solo Recordings*. Closer to transcription than detection but assumes you've already isolated the solo audio.

### Practical heuristic for our pipeline

Given that we already get stems from htdemucs (vocals / drums / bass / other), a cheap and effective solo gate is:

1. **Vocal silence**: vocals stem RMS below threshold (~-40 dBFS) for ≥ 4 s.
2. **Other-stem activity**: `other` stem RMS above a separate threshold AND high spectral flux.
3. **Melodic activity**: pitch salience or onset density on the `other` stem above threshold (CREPE confidence > 0.5 for ≥ 50% of frames is a good proxy). Alternatively, basic-pitch note count per second above threshold.
4. **Minimum duration**: ≥ 4 seconds; minimum gap between two solos: ~ 2 seconds.
5. **Optional cross-check**: feed the song through `all-in-one` and intersect its `solo`/`inst` labels with our heuristic regions. Only emit a tab block when both agree.

This combination should outperform Pati & Lerch's 2017 numbers because demucs gives us a much cleaner "other" stem than they had access to. Realistically: 80-90% precision, 70-85% recall on solos longer than 8 seconds.

## ChordPro Tab Format

### Inside `{sot}` / `{eot}`

The official spec (chordpro.org) is permissive: lines between `{start_of_tab}` and `{end_of_tab}` (or the abbreviated `{sot}` / `{eot}`) are rendered in fixed-width font and not folded, wrapped, or otherwise transformed. Markup inside is treated as literal text. The opening directive accepts an optional label, e.g. `{sot: Guitar Solo}`, which renders in the left margin.

There is **no defined schema** for what goes inside. The community convention is six lines representing the strings (high to low):

```
e|---------------------------------|
B|---------------------------------|
G|------5--7--5--------------------|
D|---7-----------7--5--------------|
A|---------------------------------|
E|---------------------------------|
```

Common conventions:

- **String letters at the left**: lowercase `e` for high E, uppercase `B G D A E` for the rest. Some files use uppercase throughout.
- **Bar separators**: `|` aligned vertically across all six lines.
- **Frets**: integer fret numbers; multi-digit frets share a column (use `--` between events).
- **Articulations** (community-standard, not enforced):
  - `h` hammer-on, `p` pull-off, `/` slide up, `\` slide down, `~` vibrato, `b` bend, `r` release, `x` muted, `()` ghost, `*` harmonic.
- **No timing**: vanilla ChordPro tab is **not time-aligned**. Spacing is purely visual — each character roughly equals an eighth or sixteenth note depending on song density. This is fine for human readers but means we cannot encode fine rhythmic information without an extension.

### Time alignment options

- **Vanilla ASCII** (recommended for MVP): emit notes left-to-right in performance order; use spacing ≈ 1 char per sixteenth at song tempo; group by bar with `|`. Some renderers will still mangle this if proportional fonts slip in, so we should refuse to break `\t` and emit only spaces.
- **Multi-bar layouts**: split tab into 4-bar systems with blank-line separators to keep terminal width manageable. Standard width: 60-80 columns.
- **ChordPro extensions**: `{sot}` blocks with embedded `[F#m]` chord directives are tolerated by some renderers (e.g., Songbook Pro, ChordPro's own renderer with `--decapo`) but break in others. **Avoid for portability.**
- **Time-aligned tab**: not part of ChordPro. If we want millisecond-accurate solos, we'd need a sidecar Guitar Pro `.gp5` or MusicXML file.

### Realistic output example

```
{start_of_tab: Solo (~2:14)}
e|--------------------|--------------------|
B|--------15b17r15----|----13--------------|
G|---14--------------14|--------14-12-------|
D|--------------------|------------14-12---|
A|--------------------|--------------------|
E|--------------------|--------------------|
{end_of_tab}
```

(One bar = 20 chars at moderate density. Bend/release shown with `b17r15`.)

## Hardware Support

| Tool | CPU | CUDA | MPS | MLX | CoreML | Notes |
|---|---|---|---|---|---|---|
| basic-pitch | yes (default) | via PyTorch port | indirectly via CoreML | no native | yes (default on macOS) | Tiny model; runs realtime on CPU. |
| CREPE / torchcrepe | yes | yes | yes | no | possible (export) | Lightweight; MPS works fine. |
| SwiftF0 (2025) | yes | yes | yes | no | yes (ONNX) | Replacement for CREPE; cheaper. |
| MT3 / YourMT3+ | yes (slow) | yes | yes (slow) | no | no | T5-scale — needs GPU for batch use. |
| High-Res Guitar (Riley 2024) | yes | yes | yes | no | no | PyTorch; piano-derived backbone. |
| TART (Oct 2025) | unknown | yes | unknown | no | no | No public code yet. |
| TabCNN / Inception variants | yes | yes | yes | no | no | Small CNN; trivial inference. |
| all-in-one (solo detection) | yes | yes | yes | no | no | PyTorch + neighbourhood attention; CPU OK. |

For Titan ChordPro Lib's RTX 5070Ti + Mac Mini M4 targets:

- **5070Ti / Linux**: basic-pitch (PyTorch port) + torchcrepe + all-in-one all run trivially on CUDA. MT3 family or High-Res Guitar are reachable for v2.
- **M4 / macOS**: basic-pitch ships with CoreML weights — fastest path. torchcrepe runs on MPS. all-in-one runs on MPS. Avoid MT3 family (no MLX, slow on MPS for transformer-scale).

## Reality Check: Is This Production-Ready?

**No, not as "ground-truth tab". Yes, as "first-draft tab to give a learner a starting point".**

Quantitative evidence:

- Best published Tablature F-measure on **GuitarSet** (clean, isolated guitar, hex-pickup-aligned) is around **0.85-0.87**. That means ~13-15% of fret/string predictions are wrong even on the cleanest data.
- Real-world recordings introduce: source-separation artefacts (htdemucs leaks bass/vocals into `other`); distortion/fuzz that confuses pitch trackers; double-stops and bends; rapid legato runs that break onset detectors. Expect a **substantial drop** off the GuitarSet number — realistically **note-level F1 in the 0.5-0.7 range** on a separated electric guitar solo from a rock track, and **string/fret accuracy lower still** (~0.4-0.6) because basic-pitch only emits MIDI, leaving us to guess strings.
- Solo *detection* is more tractable; we'll likely hit precision/recall in the 80-90% range with stem-based heuristics + all-in-one cross-checking.
- Technique transcription (bends, slides) is research-only. TART (Oct 2025) is the first credible attempt and has no public code.

For a learner reading the song in our app, a **70%-correct** tab is more useful than no tab — *as long as we mark it as machine-generated.* A 70%-correct tab presented as authoritative is worse than nothing because it actively misleads. The UX answer is: render the `{sot}` block with a `Solo (auto-transcribed, approximate)` label, and provide a one-click "report incorrect tab" affordance.

## Recommendation for Titan ChordPro Lib

**Defer full tablature to v2; ship a constrained MVP solo *detection* feature in v1.**

### MVP (v1) — solo *detection* only

1. Run htdemucs (already in pipeline) → vocals + drums + bass + other.
2. Heuristic gate: vocal RMS low + other-stem high + CREPE confidence > 0.5 + duration ≥ 4 s.
3. Cross-check against `all-in-one` structural labels (`solo` or `inst`).
4. Output: `{comment: Solo}` markers in the ChordPro at the detected boundaries — **no tab content**, just labelled regions. Chord progression continues underneath.
5. This alone is a useful feature that distinguishes us from "dump the lyrics + chords" competitors.

### v2 — first-draft tab

6. Inside detected solo regions, run `basic-pitch` (or High-Res Guitar v2024 if we package weights) on the `other` stem.
7. Apply a simple rule-based string/fret assigner: prefer the lowest-fret position, prefer staying on the same string between adjacent notes within 4 frets, prefer not crossing 12 fret without a gap. This is dumb but adequate; tab-CNN/T5-MIDI-to-tab models can replace it later.
8. Quantise to a 16th-note grid using the song's tempo (we already have it from beat tracking).
9. Render six-line ASCII; bars wrap at 60 columns; emit `{sot: Solo (~M:SS, auto-transcribed)}` ... `{eot}`.
10. Mandatory UI watermark: "Auto-transcribed - approximate."

### v3 — techniques + better assignment

11. Replace dumb fingering with a learned MIDI-to-tab model (T5 from arXiv 2510.10619 or TART once code is public).
12. Add bend/slide/vibrato detection by post-processing CREPE pitch contour for sustained pitch deviation > 50 cents.
13. Optionally export Guitar Pro / MusicXML alongside ChordPro for users who want time-aligned versions.

### What to *not* do

- Don't ship polyphonic guitar (chord-form) tab in MVP. Polyphonic tab fingering is ~2x harder and breaks instantly on layered guitars.
- Don't promise technique-accurate tab. The tech doesn't exist outside research.
- Don't try to retrain a tab model on proprietary data — GuitarSet plus the public 2024-2025 datasets (SynthTab, GAPS, GOAT, Riley's 79-track set) are sufficient if we ever do training.
- Don't put MT3 in the MVP critical path. Too heavy, marginal gain on guitar specifically.

## Open Questions

1. **Are htdemucs `other` stems clean enough for monophonic transcription?** Needs empirical test on 20-30 rock songs with known solos. Hypothesis: yes for clean/crunch tones, marginal for high-gain.
2. **Does `all-in-one`'s `solo` label fire reliably on guitar solos vs synth solos vs instrumental verses?** Likely conflates them; needs labelling experiment.
3. **Should we expose a confidence score in the ChordPro output?** E.g., `{sot: Solo (confidence: 0.62)}` — would be a novel but useful UX hint.
4. **What happens when the `other` stem has multiple instruments (lead guitar + organ)?** basic-pitch will transcribe both. Need a salience filter or per-instrument source separation (Spleeter/MDX with guitar-specific stems).
5. **License audit on training datasets if we ever fine-tune** — GuitarSet is CC BY-NC-SA, restricting commercial training. SynthTab and GAPS are friendlier.
6. **Tempo-grid accuracy**: if our beat tracker is off by 5%, our tab quantisation will look ragged. How robust is the bar/beat layout to tempo errors?

## Sources

- Spotify basic-pitch: https://github.com/spotify/basic-pitch ; PyTorch port https://github.com/gudgud96/basic-pitch-torch ; C++ port https://github.com/sevagh/basicpitch.cpp ; Hugging Face card https://huggingface.co/spotify/basic-pitch
- Basic Pitch paper: *A Lightweight Instrument-Agnostic Model for Polyphonic Note Transcription and Multipitch Estimation* — https://paperswithcode.com/paper/a-lightweight-instrument-agnostic-model-for
- CREPE: https://arxiv.org/abs/1802.06182 ; torchcrepe https://github.com/maxrmorrison/torchcrepe
- SwiftF0 (2025): https://arxiv.org/abs/2508.18440
- MT3 (ICLR 2022): https://openreview.net/pdf?id=iMSjopcOn0p ; code https://github.com/magenta/mt3
- MR-MT3 (2024): https://arxiv.org/abs/2403.10024 ; code https://github.com/gudgud96/MR-MT3
- YourMT3+ (2024): https://arxiv.org/abs/2407.04822
- TabCNN (ISMIR 2019): https://archives.ismir.net/ismir2019/paper/000033.pdf ; code https://github.com/andywiggins/tab-cnn
- High Resolution Guitar Transcription via Domain Adaptation (ICASSP 2024): https://arxiv.org/abs/2402.15258 ; demo https://xavriley.github.io/HighResolutionGuitarTranscription/
- SynthTab (ICASSP 2024): https://github.com/yongyizang/SynthTab
- Leveraging Real Electric Guitar Tones (DAFx 2024): https://arxiv.org/pdf/2405.14679
- GAPS (Aug 2024): https://arxiv.org/html/2408.08653
- GOAT (Sep 2025): https://arxiv.org/pdf/2509.22655
- TART (Oct 2025): https://arxiv.org/abs/2510.02597
- Encoder-Decoder MIDI-to-Tab (Jun 2025): https://arxiv.org/pdf/2506.14223
- T5 MIDI-to-Tab (Oct 2025): https://arxiv.org/pdf/2510.10619
- CRNN GuitarSet implementation (0.87 MPE F1): https://github.com/trimplexx/music-transcription
- TENT (TISMIR): https://transactions.ismir.net/articles/10.5334/tismir.23
- SoloLa (TENT implementation): https://github.com/srviest/SoloLa
- Pati & Lerch — Guitar Solo Detection (AES 2017): https://musicinformatics.gatech.edu/wp-content_nondefault/uploads/2017/06/Pati_Lerch_2017_A-Dataset-and-Method-for-Electric-Guitar-Solo-Detection-in-Rock-Music.pdf ; code https://github.com/ashispati/GuitarSoloDetection
- All-In-One Music Structure Analyzer (WASPAA 2023): https://arxiv.org/abs/2307.16425 ; code https://github.com/mir-aidj/all-in-one
- MSAF: https://github.com/urinieto/msaf
- ChordPro tab directive spec: https://www.chordpro.org/chordpro/directives-env_tab/
- ChordPro cheat sheet: https://www.chordpro.org/chordpro/chordpro-cheat_sheet/
- 2025 Automatic Music Transcription Challenge: https://ai4musicians.org/transcription/2025transcription.html
- Songscription review (industry reality check): https://www.musicradar.com/music-tech/humans-will-be-doing-all-the-serious-music-transcription-for-the-foreseeable-future-songscription-review
- hFT-Transformer (Sony): https://github.com/sony/hFT-Transformer
- Omnizart: https://github.com/Music-and-Culture-Technology-Lab/omnizart
- GuitarSet (ISMIR 2018): https://archives.ismir.net/ismir2018/paper/000188.pdf

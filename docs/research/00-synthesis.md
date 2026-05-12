# Research Synthesis — Titan ChordPro Lib

> Executive synthesis of 8 parallel research streams (docs `01` through `08`).
> All claims here are backed by the linked documents. No deductions without evidence.
> Last updated: 2026-05-08

---

## TL;DR

The original `roadmap.md` is **directionally right but tool-wise outdated**. Parallel research surfaced concrete replacements for nearly every module, plus two architectural decisions that the roadmap hadn't framed:

1. **The `[C] x///` rhythmic notation in the roadmap is NOT canonical ChordPro.** The standard mechanism is `{start_of_grid}`/`{eog}` blocks — but the dominant live-performance apps (OnSong, ProPresenter, SongbookPro) **don't render grids**. The library must emit dual representations behind output profiles. (See `05-chordpro-format.md`.)

2. **Dual-platform (CUDA + Apple Silicon) from day 1 is feasible AND cheaper than retrofitting.** Empirical evidence from `faster-whisper`, `demucs`, `audiocraft`, `whisper.cpp`, `basic-pitch` shows: *abstracting* on day 1 costs ~1.3-1.5× single-platform; *retrofitting* costs 3-10× and is sometimes architecturally impossible. The library should architect for dual, **implement single in MVP**, defer the second backend to v0.2. (See `06-hardware-platforms.md`.)

---

## Answer to User's Two Questions

### Q1: "Lib supporting CUDA + Apple Silicon — until what point does it pay off? Focus on one architecture and expand later?"

**Evidence-backed answer: Architect dual-platform from day 1, implement one backend in MVP, add the second in v0.2.**

The two research agents that touched this question reached apparently opposite conclusions but actually agree at different layers:

- **`06-hardware-platforms.md`** documents 5 case studies (faster-whisper, demucs, audiocraft, whisper.cpp, basic-pitch). The empirical finding: retrofitting Apple Silicon onto a CUDA-first lib is 3-10× the original effort and frequently blocked by a dependency choice (e.g., `faster-whisper` is permanently locked to CUDA because of CTranslate2). Designing for dual on day 1 is ~1.3-1.5× single-platform.
- **`07-competitive-landscape.md`** recommends single-platform (CUDA) MVP for shipping focus, with v0.2 porting to Apple Silicon.

These reconcile: **design** dual-platform, **ship** single. Specifically:

- Define `TranscriptionEngine`, `SourceSeparationEngine`, `BeatTrackingEngine`, `ChordRecognitionEngine` as Protocols from commit 1.
- The orchestrator never imports a concrete engine — only the abstraction.
- MVP wires up CUDA-fast implementations (e.g., `faster-whisper`, BS-RoFormer fine-tunes) behind the abstraction.
- v0.2 adds Apple-Silicon implementations (e.g., `mlx-whisper`, `demucs-mlx`) without touching the orchestrator.

The lock-in cost is in **dependency choices**, not in lines of code. The single decision that matters is: *"Don't make CTranslate2 / `device='cuda'` a foundational assumption."*

### Q2: "Run several research streams; tools in roadmap are suggestions, validate everything"

Done. Eight independent research streams ran in parallel, each with citation requirements and `[UNCERTAIN]` markers for unverifiable claims. Files saved to `docs/research/`:

| File | Domain | Recommendation |
|---|---|---|
| `01-source-separation.md` | Stem extraction | Pluggable: BS-RoFormer (CUDA best-quality) + `htdemucs_ft` (cross-platform default) + `demucs-mlx` (Apple fast-path). **Demucs alone is no longer SOTA.** |
| `02-transcription-and-alignment.md` | Lyrics + word timestamps | `whisper.cpp` as universal default; `faster-whisper`+WhisperX on CUDA; `mlx-whisper` on Apple. WhisperX wav2vec2 alignment is the most accurate timestamp source. |
| `03-chord-recognition.md` | Chord recognition | BTC-ISMIR19 forked + ported to PyTorch 2.x with MPS device handling; bass-stem post-correction for slash chords. ChordFormer/BACHI (2025) are SOTA but no public code. |
| `04-beat-tracking.md` | Beat / downbeat / meter | **BeatThis** (CPJKU 2024, MIT, PyTorch CUDA+MPS) replaces BeatNet/Madmom. Madmom is effectively unmaintained. |
| `05-chordpro-format.md` | Output format | `{sog}`/`{eog}` for rhythm grids + dual-emit inline `[C][C][C][C]` fallback. Pluggable output profiles per app. |
| `06-hardware-platforms.md` | Cross-platform | Backend abstraction day 1; ship via pip extras `[cuda]` / `[apple]` / universal. |
| `07-competitive-landscape.md` | Gap + MVP | Gap = open-source ChordPro generator with rhythmic grid + word alignment. No competitor does this combination. MVP = beat-grid-quantized chords + lyrics, maj/min only, ChordPro out, CLI + lib. |
| `08-tab-and-solo.md` | Solo + tablature | Defer authoritative tab. v0.1 ships solo *detection* only via `{comment: Solo}`. v0.2 adds approximate ASCII tab. v0.3 considers TART/T5-MIDI. |

---

## Major Roadmap Revisions (Tool-by-Tool)

### Module A — Source Separation (was: Demucs HT)

**Out:** `facebookresearch/demucs` (archived 2025-01-01).
**In (Tier 1, default cross-platform):** `htdemucs_ft` via `python-audio-separator` (MIT, CUDA + MPS + CPU).
**In (Tier 2, CUDA best-quality):** BS-RoFormer / Mel-RoFormer + SCNet-XL bass-specialist ensemble.
**In (Tier 3, Apple fast-path):** `demucs-mlx` (~73× realtime on M4 Max).

Bass SDR matters disproportionately for chord-root inference: SCNet-XL bass-specialist hits **13.81 dB SDR** vs HTDemucs' ~9 dB.

### Module B — Transcription (was: faster-whisper + stable-ts)

**Critical finding:** `faster-whisper` has NO MPS support (issue #911 unresolved as of 2026). CTranslate2 is permanently CUDA+CPU-only.

**Cross-platform default:** `whisper.cpp` (single binary, CUDA + Metal + CoreML, GGUF weights).
**CUDA fast-path:** `faster-whisper` + WhisperX wav2vec2 alignment (best word timestamps).
**Apple fast-path:** `mlx-whisper` or `whisper.cpp`+CoreML+ANE; `torchaudio.forced_align` for word timestamps.

**Whisper on sung lyrics:** Open-source SOTA on Jam-ALT is ~20% WER long-form. Always run a separate forced-alignment pass — Whisper's native timestamps are not chord-on-syllable accurate.

**Avoid:** `whisper-timestamped` is **AGPL-3.0** (license contagion for an MIT lib).

### Module C — Chord Recognition (was: BTC-ISM / Chordino)

Field has plateaued at ~83-86% on Isophonics majmin. ChordFormer (2025) and BACHI (2025) are SOTA but neither has public code.

**Recommended:** Fork BTC-ISMIR19 with `voca=True` (170-class vocab including slash chords), port to PyTorch 2.x with MPS device handling, layer **bass-stem post-correction** for inversions on top. Output normalized via `music21`.

**Slash chord handling:** Chordino emits the bass note natively; bass-stem post-correction is the cleanest path for any model. Document pattern published in LLM-CoT 2025 paper.

**Watch licenses:** Chordino is GPL-2.0 — VAMP plugin runtime dep is borderline OK, but bundling weights/plugin in the wheel is not.

### Module D — Beat Tracking (was: BeatNet / Madmom)

**Out:** Madmom (last release 2018, broken on Python ≥3.10 / NumPy ≥1.24).
**In:** **BeatThis** (CPJKU, ISMIR 2024, MIT). SOTA 94.5% Beatles beat F1 / 88.8% downbeat F1. Pure PyTorch — CUDA + MPS work cleanly. No DBN constraint, so 6/8 and meter changes are not corrupted.

**Time signature:** Mostly solved implicitly via downbeat-spacing voting; BeatThis emits clean downbeats. Explicit meter output requires madmom DBN or BeatNet+. 6/8 vs 3/4 still needs a hand-rule.

**Quantization tolerance:** ±70 ms for beat snap, ±150 ms for 8th-note snap. Mir_eval's perceptual benchmark.

### Module E — Fusion + Output (was: `[C] x///` slash notation)

**Critical correction:** `[C] x///` is **not standard ChordPro**. Canonical mechanism is `{sog}`/`{eog}` chord-grid blocks, where `|` is bar, `/` repeats prior chord, `.` is empty, `%` repeats prior measure. Strum patterns added v6.080 (Aug 2025).

**App support reality:** Grids render in ChordPro reference impl, Linkesoft Songbook, LivePrompter — but **NOT in OnSong, ProPresenter 7, SongbookPro** (the dominant live-performance apps).

**Strategy:** Pluggable output profiles (`chordpro-ref` / `onsong` / `propresenter` / `songbookpro`). Default emits BOTH a `{sog}` block AND an inline `[C][C][C][C]` fallback line so every reader gets *something* renderable.

**Time signature:** `{time: 6/8}` directives can repeat mid-song per spec. For 6/8 grids, `shape="1+Mx6+1"` maps cells to eighth notes.

**Provenance metadata:** Use `{meta: titan_version 0.1}`, `{meta: titan_confidence_chord 0.92}` etc. Spec-compliant, round-trip safe.

### Solo & Tab (was: GuitarSet-based tabs in MVP)

**Reality check:** Best Tablature F-measure on clean GuitarSet is ~0.85-0.87, dropping to 0.4-0.6 string/fret accuracy on a separated rock guitar stem. **Not production-ready in 2026.**

**v0.1:** Detect solos only (vocal-stem silence + `other`-stem activity + CREPE confidence + cross-check with `mir-aidj/all-in-one` solo/inst labels). Mark with `{comment: Solo}`.
**v0.2:** First-draft ASCII tab inside `{sot}` with rule-based fingering, watermarked "approximate."
**v0.3+:** Consider TART / T5-MIDI-to-tab once code is public.

---

## Revised Architectural Blueprint

```
┌─────────────────────────────────────────────────────┐
│              titan_chordpro.transcribe()             │
│  (orchestrator — depends ONLY on engine Protocols)   │
└─────────────────────────────────────────────────────┘
       │            │             │            │
       ▼            ▼             ▼            ▼
  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
  │ Source   │ │ Trans-   │ │ Chord    │ │ Beat     │
  │ Sep.     │ │ cription │ │ Recog.   │ │ Track    │
  │ Engine   │ │ Engine   │ │ Engine   │ │ Engine   │
  └──────────┘ └──────────┘ └──────────┘ └──────────┘
       │            │             │            │
       │            │             │            │
   Implementations (MVP wires one each, abstraction allows more):
       │            │             │            │
   • htdemucs_ft   • whisper.cpp  • BTC-ISMIR19 • BeatThis
     (default)       (universal)    fork+ porting (PyTorch
   • BS-RoFormer   • faster-       to PyTorch 2.x   CUDA+MPS)
     (CUDA)          whisper                       
   • demucs-mlx      (CUDA)
     (Apple v0.2)  • mlx-whisper
                     (Apple v0.2)
                                   │
                                   ▼
                        ┌─────────────────────┐
                        │   ChordPro Writer    │
                        │   (output profiles:  │
                        │   chordpro-ref /     │
                        │   onsong /           │
                        │   propresenter /     │
                        │   songbookpro)       │
                        └─────────────────────┘
```

---

## MVP Scope (v0.1)

**Hardware target:** CUDA only (RTX 5070Ti). Apple Silicon support architected but not implemented.

**Pipeline:**
1. `htdemucs_ft` separates audio → vocals/bass/drums/other.
2. `faster-whisper` large-v3 transcribes vocals → words with timestamps.
3. WhisperX wav2vec2 aligns words → precise timestamps.
4. BTC-ISMIR19 fork detects chords on `other`+`bass` mix → chord events.
5. Bass-stem post-correction adds inversions where confident.
6. BeatThis on full mix → beat grid + downbeats.
7. Fusion engine: snap chords to beats (±70ms), interpolate words within measures, mark instrumental sections.
8. ChordPro writer emits dual-profile output (`chordpro-ref` default).

**Out of scope for v0.1 (deferred):**

| Feature | Defer to | Why |
|---|---|---|
| Apple Silicon implementations | v0.2 | Halves test matrix; abstraction allows clean addition later |
| Solo → ASCII tab | v0.3 | Hardest module; ship harmony first |
| Extended chord vocab (7ths, sus, add9) | v0.2 | Maj/min is industry baseline |
| Variable BPM | v0.2 | Locally-stable tempo + global BPM warning |
| GUI / web demo | v0.2+ | `gradio.Interface` is a 50-line bonus |
| MusicXML / GuitarPro export | Never | ChordPro is the niche |

**Definition of Done:**
- `titan-chordpro` CLI takes one audio file, emits a valid `.chordpro`.
- Library API: `transcribe(path) → ChordProDocument`.
- Test corpus of 5-10 known songs, subjective accuracy review.
- README with single-line install + invocation.
- License: **MIT** or **Apache-2.0** (avoid GPL deps).
- README demo GIF: audio → `.chordpro` → rendered PDF.

---

## Risks Flagged

1. **Chordino GPL contagion.** If used at runtime, OK for MIT lib (separate process). Bundling weights/plugin in wheel is not. **Avoid Chordino unless we ship a separate binary.**
2. **whisper-timestamped AGPL.** Hard avoid.
3. **Mac M4 base 16GB ceiling.** Demucs + Whisper + BeatThis simultaneously may not fit in 16GB unified memory. Pipeline may need to be sequential rather than parallel on Apple. Validate empirically when v0.2 ships.
4. **faster-whisper #1287.** RTX 5070Ti regression issue. Verify before relying on faster-whisper as the CUDA fast-path.
5. **BTC-ISMIR19 fork maintenance.** We become the maintainers of a research-grade codebase. Budget time for porting to PyTorch 2.x and maintaining MPS compatibility.
6. **ChordPro grid app support gap.** Until OnSong/ProPresenter add grid rendering, our flagship feature is invisible to dominant apps. Mitigation: dual-emit fallback.
7. **Whisper hallucinations on isolated vocal stems.** Source separation can introduce artifacts that Whisper transcribes as nonsense. Counter-intuitively, sometimes raw mix transcription is more accurate than separated-vocal transcription.

---

## What I Did NOT Validate (Open)

1. **Empirical performance** of the proposed stack on actual songs. All numbers in research docs are from public benchmarks; real-world performance on the user's music library is unknown.
2. **License of every individual community RoFormer fine-tune checkpoint.** Some are MIT, some unclear. Per-checkpoint verification needed.
3. **Mac Mini M4 specific benchmarks.** Most public benchmarks compare M4 Pro/Max vs RTX 4090. Base M4 16GB unified is less benchmarked.
4. **whisper.cpp Python binding maturity.** `pywhispercpp` may lag the upstream CLI on word-level timestamps and large-v3-turbo support. Validate before committing.
5. **All-In-One model (Yamaha 2024) integration cost.** It promises joint beat+structure+chord but has NATTEN dep that blocks Apple Silicon. May replace several modules at once on CUDA-only path — worth a deeper look later.

---

## Next Steps (Pending User Approval)

1. **User reviews this synthesis + research files.**
2. **Decide v0.1 platform:** CUDA-only (recommended) vs dual.
3. **Decide ChordPro output profile default:** `chordpro-ref` (renders grids) vs `onsong`-compatible (drops grids for inline chord lines).
4. **Decide chord recognition path:** BTC-ISMIR19 fork (best quality, maintenance burden) vs `chord-extractor`+Chordino (faster start, GPL caveat).
5. **Update `roadmap.md`** to reflect findings, OR keep roadmap as historical "initial research" document and let `00-synthesis.md` be the new source-of-truth.
6. **Move from research to design:** invoke `superpowers:writing-plans` to draft the formal v0.1 implementation plan.

---

## File Index

- [`01-source-separation.md`](./01-source-separation.md) — Demucs / RoFormer / SCNet survey
- [`02-transcription-and-alignment.md`](./02-transcription-and-alignment.md) — Whisper variants + alignment
- [`03-chord-recognition.md`](./03-chord-recognition.md) — Chord recognition SOTA
- [`04-beat-tracking.md`](./04-beat-tracking.md) — Beat / downbeat / meter
- [`05-chordpro-format.md`](./05-chordpro-format.md) — ChordPro spec deep dive
- [`06-hardware-platforms.md`](./06-hardware-platforms.md) — CUDA vs Apple Silicon strategy
- [`07-competitive-landscape.md`](./07-competitive-landscape.md) — Competitive landscape + MVP
- [`08-tab-and-solo.md`](./08-tab-and-solo.md) — Tablature + solo transcription
- [`09-chord-on-syllable.md`](./09-chord-on-syllable.md) — Chord-on-syllable placement algorithm

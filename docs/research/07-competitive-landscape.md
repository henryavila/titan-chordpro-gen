# Competitive Landscape and MVP Strategy

> Research conducted for Titan ChordPro Lib. Goal: understand what already exists, identify the gap, and define a viable MVP.
> Last updated: 2026-05-08

## Executive Summary

The audio-to-chord-chart space is crowded with commercial products (Chordify, ChordAI, Moises, Klangio, AnthemScore) and a handful of open-source pieces (Demucs, Whisper, Spleeter, basic-pitch, autochord, chord-extractor, Polymath). After surveying twelve commercial tools and seven open-source projects, the central finding is this: **no tool, commercial or open-source, currently produces a true ChordPro file with quantised rhythmic grids, word-aligned lyrics, AND inline solo tablature, all generated locally from a single audio input.** Every player in the market either (a) emits chord-with-timestamp lists trapped behind a web player, (b) emits MIDI/MusicXML for sheet-music workflows but skips lyrics, or (c) does great stem separation but stops short of harmonic transcription. Titan ChordPro Lib has a defensible niche, but only if the MVP is ruthlessly narrow. The recommended MVP is a **single-platform CLI + library** (CUDA-first) that ingests one audio file and emits a ChordPro file with majmin chords on a quantised beat grid plus word-aligned lyrics — no solos, no Apple Silicon, no GUI in v0.1.

---

## Part 1 — Existing Tools

### Commercial / SaaS

#### Chordify
- **URL:** https://chordify.net
- **Pricing (2026):** Free tier (4 songs/day, ads). Premium ~$8.99/month adds transposition, tempo control, capo, PDF export, MIDI download. Premium+Toolkit adds chord trainer and chord detector.
- **What it does well:** Massive catalogue (>36M songs), instant chord detection from YouTube or upload, synced playback. Hybrid AI + human curation. Web, iOS, Android.
- **What it doesn't do:** No ChordPro export. No lyrics alignment in chord chart (lyrics shown separately or via add-on). No rhythmic grid — chords float on a horizontal timeline. No solo tabs. No local processing — everything is uploaded. No public API.
- **ChordPro support:** No.
- **Local processing:** No.

#### ChordAI
- **URL:** https://chordai.net
- **Pricing (2026):** Free tier with basics. Pro ~$9/month or ~$69/year.
- **What it does well:** Real-time chord detection via mic, offline processing on-device, four-stem separation built in (vocals/bass/drums/others), audio→MIDI, lyrics recognition, multiple instruments (piano, guitar, ukulele, bass, mandolin, banjo). Privacy-preserving (works offline).
- **What it doesn't do:** No ChordPro export. Output is locked inside the mobile app — no scriptable workflow. No quantised rhythmic grid (chords are timestamps). No solo transcription.
- **ChordPro support:** No.
- **Local processing:** Yes (mobile-only).

#### Klangio (Transcription Studio)
- **URL:** https://klang.io
- **Pricing (2026):** £4/month entry. Free preview limited to 20-second snippet. Annual unlimited around $11.99/month equivalent.
- **What it does well:** Instrument-specific transcription (piano, guitar, vocals, drums, violin, winds). Output to PDF, MusicXML, MIDI, GuitarPro. Has DAW plugin (VST3/AU) for drag-out MIDI workflow. Edit mode for fine-tuning.
- **What it doesn't do:** No ChordPro. Outputs notation, not lead sheets — the philosophy is "transcribe to score," not "produce a chord chart for a guitarist." No lyrics. No rhythmic-grid-with-slash notation. Cloud-based; uploads required.
- **ChordPro support:** No.
- **Local processing:** No (DAW plugin still calls cloud).

#### Soundslice
- **URL:** https://www.soundslice.com
- **Pricing (2026):** Free tier (basic notation/tab editor, unlimited songs). Plus $5/month or $50/year. +$5/month to upload your own audio/video. Note: Soundslice is the Hindenburg-Research-grade tool that **Anthropic itself** integrated into Claude.ai docs.
- **What it does well:** Living sheet music — sync notation to MP3/YouTube. Strong tab + notation editor. PDF/photo OCR import. Chord-chart view available. Excellent for pedagogy.
- **What it doesn't do:** Chord and tab content is **manually entered or imported** — Soundslice does not automatically transcribe audio to chords or tabs. It is the *display surface*, not the transcription engine. No ChordPro export (it has its own format).
- **ChordPro support:** No.
- **Local processing:** No.

#### AnthemScore (Lunaverus)
- **URL:** https://www.lunaverus.com
- **Pricing (2026):** One-time. Lite ~$26, Professional ~$34, Studio ~$92. No subscription. Windows/Mac/Linux. 30-second free trial.
- **What it does well:** Local desktop transcription. Audio (MP3/WAV) → sheet music + MIDI + MusicXML + PDF. One of the few truly local commercial tools.
- **What it doesn't do:** No ChordPro. Targets piano/melodic transcription, not chord-chart workflow. No lyrics. No quantised slash-chord rhythm notation.
- **ChordPro support:** No.
- **Local processing:** Yes.

#### Yalp (yalp.io)
- **URL:** https://www.yalp.io
- **Pricing (2026):** Freemium. Premium pricing not publicly visible at search time.
- **What it does well:** Chord transcription from YouTube + MP3 with built-in stem separation (voice/guitar/bass/drums). Tempo and loop controls, transposition.
- **What it doesn't do:** Web-only. No ChordPro export. No quantised grid. Accuracy admittedly imperfect. No solo tabs.
- **ChordPro support:** No.
- **Local processing:** No.

#### Moises AI
- **URL:** https://moises.ai
- **Pricing (2026):** Free (5 stems/month, 1-min chord detection). Premium $3.99/month. Pro ~$95/year. Mobile + web.
- **What it does well:** Best-in-class stem separation + the heaviest "musician toolkit" stack: pitch shift, tempo shift, chord detection (Easy/Medium/Advanced), key detection, lyric transcription, click/metronome alignment. iOS/Android native.
- **What it doesn't do:** Chord output is for in-app practice, not export to lead sheet. No ChordPro. No solo tab. Cloud-based. Reported accuracy: ~85-90% on pop/rock, drops to 40-50% on jazz with extensions.
- **ChordPro support:** No.
- **Local processing:** No.

#### Hookpad / Hooktheory
- **URL:** https://www.hooktheory.com/hookpad
- **Pricing (2026):** $4.99/month or $49/year subscription, $149 one-time. Aria AI add-on $14.99/month. Education tier available.
- **What it does well:** Composition / songwriting sketchpad with music-theory guidance, chord palette by mood, AI melody generation. TheoryTab database has 30k+ analysed songs.
- **What it doesn't do:** **Not a transcription tool.** Hookpad takes user input and helps them compose. It doesn't ingest audio. Different category entirely.
- **ChordPro support:** No.
- **Local processing:** No.

#### Scaler 2 (Plugin Boutique)
- **URL:** https://www.scalermusic.com
- **Pricing (2026):** ~$59-79 one-time (frequent sales). VST3/AU/AAX plugin.
- **What it does well:** Real-time chord detection from incoming MIDI **and audio** (single-instrument), inside a DAW. Huge chord-preset library by genre/artist. Strong creative tool for composers.
- **What it doesn't do:** Not designed for full-song chord-sheet output. No lyrics, no time-grid, no ChordPro. Audio detection works best with mono single-instrument input.
- **ChordPro support:** No.
- **Local processing:** Yes (plugin).

#### BandLab (Smart Chords / Smart Scales)
- **URL:** https://bandlab.com
- **Pricing:** Free (the headline feature).
- **What it does well:** Smart Scales detects key from project audio; Smart Chords lets one-finger trigger full chords. Zero cost, web-based DAW.
- **What it doesn't do:** Not a transcription tool — these are *generation* aids inside the DAW. No chord chart from a finished recording. No lyrics, no ChordPro.
- **ChordPro support:** No.
- **Local processing:** No.

#### Riffstation (DEFUNCT — verified)
- **Status:** Acquired by Fender, made free in late 2018, then **discontinued and removed** (server taken down). The product is no longer available. Song Surgeon is sometimes referenced as a spiritual successor but is a different codebase.
- **Lesson:** Even a beloved tool with real-time chord detection and an active user base can be killed when its parent company shifts strategy. Important context for the open-source value proposition.

#### Honorable mentions
- **Song Surgeon** — desktop slow-downer with chord detection. Niche, paid.
- **Capo (Mac)** — $40 one-time, audio slowdown + manual chord entry with detection assist. Not automated end-to-end.
- **Ultimate Guitar Tabs Pro** — community-curated chord tabs. Not transcription; it's a database.

### Open-source / Hackable

#### autochord (cjbayron)
- **URL:** https://github.com/cjbayron/autochord
- **License:** Apache-2.0. ~160 stars. ISMIR 2021 Late-Breaking Demo.
- **Architecture:** Bi-LSTM-CRF over chroma features (VAMP plugin). 25 classes (12 maj, 12 min, no-chord). 67.33% test accuracy.
- **Output:** MIREX-style LAB file `(start_sec, end_sec, label)`. Not ChordPro.
- **What it does well:** Pip-installable, simple API, runs locally on CPU.
- **What it doesn't do:** No lyrics. No beat tracking. No rhythmic grid. No tabs. Single-author, low activity, narrow accuracy ceiling. Maj/min only.

#### Polymath (samim23)
- **URL:** https://github.com/samim23/polymath
- **License:** MIT. Designed for sample-library production, not lead-sheet output.
- **Architecture:** Demucs (separation) + sf_segmenter (structure) + Crepe (pitch) + Basic Pitch (audio→MIDI) + pyrubberband (quantize) + librosa.
- **What it does well:** **Closest existing pipeline architecturally to Titan ChordPro Lib.** Same Demucs+ML stack. Cleanly orchestrates SOTA components.
- **What it doesn't do:** No ChordPro output. No word-level lyric alignment. No solo tab. Goal is producing sample loops, not lead sheets. No quantised slash-chord notation.

#### lyrics-and-chords-extractor / similar repos
- A sparse cluster of small Python repos and React Native apps exists that *parse* ChordPro or *display* chords + lyrics, but **none of them transcribe audio to ChordPro**. They are downstream consumers of ChordPro files. Examples: ChordPro/chordpro (reference parser), Desbeers/Chord-Provider (Linux editor), artutra/OpenChord (RN viewer), xilefmusics/chordlib (Rust library).
- **Implication:** A healthy ChordPro consumption ecosystem exists. There is no automated producer.

#### chord-extractor (ohollo)
- **URL:** https://github.com/ohollo/chord-extractor
- **License:** Permissive. Wraps Chordino (VAMP).
- **What it does well:** Extracts ChordChange events with multiprocessing, file-format-agnostic. Clean, extensible base class.
- **What it doesn't do:** Wraps a single backend (Chordino). No lyrics, no grid, no ChordPro. It's a thin convenience layer.

#### Magenta — Onsets and Frames (Google)
- **URL:** https://github.com/magenta/magenta/tree/main/magenta/models/onsets_frames_transcription
- **License:** Apache-2.0. Active research project, but the MAIN magenta repo is in maintenance mode for many components.
- **What it does well:** Best-in-class **piano** transcription to MIDI/NoteSequences. Web demo "Piano Scribe."
- **What it doesn't do:** Piano-only. Not chord recognition (note-level transcription). No lyrics. Not a chord-chart workflow.

#### basic-pitch (Spotify)
- **URL:** https://github.com/spotify/basic-pitch
- **License:** Apache-2.0. ~5,000 stars. Last activity August 2024.
- **What it does well:** Lightweight, polyphonic, instrument-agnostic audio→MIDI with pitch bend. Pip-installable, also npm (basic-pitch-ts) and ICASSP 2022 paper. Strong multi-channel rollout (open source + web demo + artist partnership).
- **What it doesn't do:** Notes only — no chord recognition, no harmonic analysis, no lyrics. Output is MIDI/CSV/NPZ.

#### Demucs (Meta / facebookresearch)
- **URL:** https://github.com/facebookresearch/demucs
- **License:** MIT. v4 Hybrid Transformer Demucs (Nov 2022) is current SOTA for many music separation benchmarks. Active.
- **Use in Titan stack:** Source separation only — Module A in our roadmap.

#### Whisper (OpenAI)
- **URL:** https://github.com/openai/whisper
- **License:** MIT. Released 21 Sep 2022.
- **Use in Titan stack:** Lyrics ASR — Module B. Combined with `faster-whisper` + `stable-ts` / `whisper-timestamped` for word-level timestamps.

#### Spleeter (Deezer)
- **URL:** https://github.com/deezer/spleeter
- **License:** MIT. Released 29 Oct 2019. ≥5000 stars in first week.
- **Status:** Effectively superseded by Demucs in quality, but historically and pedagogically important. Deezer now offers a paid "Spleeter Pro" API alongside.

### The Gap Titan ChordPro Lib Fills

Putting the matrix together:

| Capability                              | Chordify | Moises | ChordAI | Klangio | AnthemScore | Polymath | autochord | **Titan target** |
|-----------------------------------------|:--------:|:------:|:-------:|:-------:|:-----------:|:--------:|:---------:|:----------------:|
| Audio → chord recognition               | Yes      | Yes    | Yes     | Partial | Partial     | No       | Yes       | Yes              |
| Word-level lyric alignment              | No       | Lyrics | Lyrics  | No      | No          | No       | No        | Yes              |
| Quantised beat/measure grid             | No       | No     | No      | No      | Notation    | Beats only| No       | Yes              |
| Slash-chord rhythmic notation (`x///`)  | No       | No     | No      | No      | No          | No       | No        | Yes              |
| Solo → inline tab                       | No       | No     | No      | Tab-instrument | No   | No       | No        | Yes (later)      |
| ChordPro file output                    | **No**   | **No** | **No**  | **No**  | **No**      | **No**   | **No**    | **Yes**          |
| Local / offline processing              | No       | No     | Yes     | No      | Yes         | Yes      | Yes       | Yes              |
| Open source                             | No       | No     | No      | No      | No          | Yes      | Yes       | Yes              |
| Scriptable / library API                | No       | No     | No      | DAW plugin | API   | Yes      | Yes       | Yes              |

**Three-sentence niche statement:** Titan ChordPro Lib is the only project that targets the intersection of (a) ChordPro output, (b) local processing on a developer's GPU, and (c) musically-meaningful rhythmic structure (downbeats, quantised slash chords). Every commercial competitor traps the chord output behind a player UI; every open-source competitor stops at one stage of the pipeline. **The defensibility is integration + ChordPro + locality, not raw chord-detection accuracy.**

The risk: someone (Spotify, Moises, an enterprising researcher) ships a competing pipeline first. Mitigation: get an MVP out fast, stay narrow, integrate cleanly.

---

## Part 2 — Case Studies of Successful Music ML Lib MVPs

### librosa
- **Initial scope (2015, v0.4):** Direct ports of common MIR routines (STFT, mel, MFCC, chroma, beat tracking, onset detection, harmonic-percussive separation). MATLAB users were the primary persona — McFee et al. explicitly designed for "low barrier to entry for researchers familiar with MATLAB."
- **What was deferred:** ML models. Visualisation came later. End-to-end pipelines never came (and that's the point — it stays a building block).
- **Lib vs CLI:** Pure library. No CLI. Composable functions, scipy-style.
- **Key lessons:**
  - **Stay infrastructure, not app.** librosa never tried to be a "music analysis app." It's the lego brick everyone else builds with — including Polymath, basic-pitch tooling, and even chord-extractor.
  - **Flat namespace, NumPy types.** Don't invent a domain object hierarchy when arrays + sample rate suffices.
  - **Cite the paper.** The SciPy paper gave it academic legitimacy and a single canonical citation, which drove adoption in graduate labs.

### Spleeter
- **Initial scope (Oct 2019):** Three pretrained checkpoints (2-stems, 4-stems, 5-stems). One job: separate. CLI + Python API. TensorFlow.
- **What was deferred:** Realtime processing. Custom training. GUI (left to community forks). Mobile.
- **Lib vs CLI:** Both, equally weighted. The CLI was explicitly the headline (`spleeter separate -i in.mp3 -o out/`) and is what drove the viral GitHub-trending moment.
- **Key lessons:**
  - **One headline command.** A new user can copy-paste a single line and get value in 30 seconds. That single-line demo went viral on Twitter and HN.
  - **Pretrained checkpoints are the product.** Open-sourcing the architecture without weights would have been useless. Weights = product.
  - **Abandonment is OK.** Deezer's R&D moved on; community forks (Demucs comparisons, GUIs, web wrappers) kept it relevant. The MIT license made this resilient.
  - **Pro tier as monetisation.** Spleeter Pro API is the commercial layer — open source seeded the brand.

### Demucs
- **Initial scope (2019, v1):** Single research codebase tied to a single paper ("Music Source Separation in the Waveform Domain"). Waveform-domain separation. Drums/bass/vocals/other.
- **What was deferred:** Hybrid (spectrogram + waveform) came in v3. Transformer architecture in v4. Quantization (DiffQ) in v2. Each version one focused architectural change.
- **Lib vs CLI:** Both. `python -m demucs` CLI for users; clean module API for researchers.
- **Key lessons:**
  - **Iterate the model, not the surface.** v1→v4 over 3+ years kept the same input/output contract. Users of v1 could swap to v4 with one config change. That contract stability is what made Demucs the de-facto choice for downstream pipelines (Polymath, Moises rumored, countless web wrappers).
  - **Research-first, but ship.** Each version came with a paper and a release. The release wasn't an afterthought.

### basic-pitch
- **Initial scope (June 2022):** One model, polyphonic, instrument-agnostic, audio→MIDI with pitch bend. Lightweight (small enough for browser via tfjs).
- **What was deferred:** Chord recognition. Multi-track separation. Real-time. Drum transcription.
- **Lib vs CLI:** Three surfaces: Python pip, npm (basic-pitch-ts), web demo at basicpitch.spotify.com. The web demo is the marketing — most users discover via the demo, then `pip install`.
- **Key lessons:**
  - **The demo is the doc.** A free, no-signup web demo converts curiosity into adoption faster than any README.
  - **Lightweight beats accurate.** Basic Pitch is not the most accurate transcriber — it's the most *deployable*. Runs in a browser. That's its moat.
  - **Artist partnership for legitimacy.** Spotify partnered with Bad Snacks to use Basic Pitch on a real track. This is hard for a solo open-source project to replicate, but the principle — "show it being used in anger by a real musician" — translates to YouTube demos and Reddit posts.

### autochord
- **Initial scope (2021):** Single Python lib, one Bi-LSTM-CRF model, 25 chord classes, LAB file output. Single author.
- **What was deferred:** Everything. There is no "v2" really. The repo is essentially feature-complete by design.
- **Lib vs CLI:** Library only.
- **Key lessons:**
  - **Narrow scope is shippable.** A solo dev can ship an ISMIR demo and a pip package with 67% accuracy. The community will use it because it exists, not because it's perfect.
  - **MIREX/LAB format is a research convention, not a user format.** This is exactly the gap autochord did *not* fill — it stops at the academic output. Titan should not.
  - **160 stars, low activity = niche but useful.** A library can have a long tail of value even without virality.

### Whisper
- **Initial scope (Sep 2022):** ASR only. Five model sizes (tiny→large). Multilingual. Translate-to-English. CLI + Python API. MIT license.
- **What was deferred:** Word-level timestamps (community filled this with `whisper-timestamped`, `stable-ts`, `WhisperX`, `faster-whisper`). Speaker diarization. Streaming/realtime. Fine-tuning tooling.
- **Lib vs CLI:** Both. CLI dominated early (`whisper audio.mp3`).
- **Key lessons:**
  - **Strategic openness.** OpenAI hadn't open-sourced anything substantial in years. Releasing Whisper bought immense goodwill and forced the entire ASR market to rebase on it.
  - **The community fills the holes.** OpenAI never shipped word-level timestamps officially; the community shipped 4+ implementations. **Plan for downstream community modifications.** A clean checkpoint + clean interface is a force-multiplier.
  - **Five model sizes = serves every hardware tier.** From tiny on a laptop to large-v3 on a workstation. This range strategy is replicable for Titan if it ever ships its own models.

### Cross-cutting Lessons

1. **Ship one headline command.** `spleeter separate`, `whisper audio.mp3`, `demucs file.wav` — these are mnemonic. Titan must ship `titan-chordpro song.mp3 > song.chordpro`.
2. **Pretrained weights are the product.** Open-sourcing architectures without weights does not produce viral adoption.
3. **Stay narrow at v0.1, grow architecturally not surface-area-wise.** Demucs went v1→v4 changing the core model, not adding lyrics or chord recognition. Resist scope creep.
4. **Both CLI and library, equally weighted.** Users discover via CLI, integrate via library.
5. **A web demo accelerates adoption disproportionately.** Even a Hugging Face Space with 30-second uploads counts. (Out of MVP scope for Titan, but plan for v0.2.)
6. **Permissive license (MIT or Apache-2.0) is non-negotiable** for ML libs to be used in commercial pipelines. Lessons from Spleeter (MIT) being forked into commercial products.
7. **Research paper or technical writeup at launch.** Even a Medium post like Deezer's "Releasing Spleeter" gives the project a citation anchor. Titan should publish a `docs/method.md` describing the pipeline.
8. **Stable input/output contract from day one.** If `extract(audio_path) -> ChordProDocument` works in v0.1, never break it.

---

## Part 3 — MVP Recommendation for Titan ChordPro Lib

### Candidate MVPs

#### MVP-A: "Skinny Chordify clone, but local + ChordPro"
- Single platform (CUDA). Whisper for lyrics. A pretrained chord recogniser (Chordino via chord-extractor, or autochord) — no in-house training. Maj/min only. Word-level lyric alignment via stable-ts. **No** beat grid; chords output at raw timestamps. **No** solo tab. Output: ChordPro with `[C]word [G]word` style, no `x///`.
- Lines of code estimate: small (<2k Python).
- **Trade-off:** Loses the rhythmic-grid differentiator. Easy to build. Easy to be made obsolete by a smarter Polymath.

#### MVP-B: "Skinny clone + the unique differentiator"
- Same as MVP-A but **adds beat tracking (BeatNet or madmom) and chord-to-beat quantisation**, and emits slash notation (`[C] x///` for instrumental measures). Still no solos, still maj/min, still single-platform.
- Lines of code estimate: medium (~3-5k Python). One extra ML dep.
- **Trade-off:** This is the actual product. The grid is the moat.

#### MVP-C: "Dual-platform from day one"
- MVP-A or MVP-B but supporting both CUDA and Apple Silicon (MPS / Core ML where weights aren't available).
- **Trade-off:** Doubles the testing matrix and the dep-conflict surface (faster-whisper on MPS is a particular pain). Demucs v4 on MPS works but is slower; some sub-models don't have MPS kernels. **High risk of "works on neither rather than both."**

#### MVP-D: "CLI + library API, narrow features"
- Identical to MVP-B in features, but explicit attention to two surfaces from day one: a `titan-chordpro` CLI binary and a `from titan_chordpro import transcribe` library API. Locked stable contract.
- **Trade-off:** Modest extra design work; high payoff in adoption.

### Recommended MVP: **MVP-B + MVP-D** ("MVP-BD")

**Single-platform (CUDA) + beat-grid + ChordPro output + dual surfaces (CLI + library), and nothing else.**

#### Concretely, the v0.1 contract:

```bash
$ titan-chordpro song.mp3 -o song.chordpro
```

```python
from titan_chordpro import transcribe
doc = transcribe("song.mp3")
doc.write("song.chordpro")
```

Output: a valid ChordPro file with:
- `{title:}` / `{artist:}` if extractable from filename or ID3
- BPM tag `{tempo: 120}`
- Time signature tag `{time: 4/4}` (assume 4/4 if confidence low; document the limitation)
- Word-aligned chord-over-lyric lines: `[C]A[Am]ll a-[F]long the [G]wat-cher`
- For instrumental measures detected as such: slash notation `[C] x///` or `[C] x/ [G] x/`
- Maj/min chord vocabulary (24 + N for no-chord)
- Bass-aware inversion is a STRETCH GOAL inside MVP — keep it gated behind a flag if it slips

#### What to defer (explicitly):

| Feature                            | Defer to | Rationale |
|------------------------------------|----------|-----------|
| Apple Silicon support              | v0.2     | Halves the testing matrix; CUDA is the user's primary box (RTX 5070Ti). |
| Solo → tab transcription           | v0.3     | The hardest module (GuitarSet-class models, monophonic-vs-polyphonic detection, fingering inference). Ship harmony first. |
| Extended chord vocab (7ths, sus, add9, slash inversions) | v0.2 | Maj/min is industry baseline. 7th/sus is a one-line model swap later. |
| GUI / web demo                     | v0.2+    | A `gradio.Interface` wrapper is a 50-line bonus, not the MVP. |
| Streaming / real-time              | Never    | Out of scope. Different product. |
| Custom model training              | Never (or plugin) | Use SOTA pretrained models. Don't compete on training. |
| Multi-track export (separate stems persisted) | v0.2 | Demucs already does this; expose `--keep-stems` later. |
| MusicXML / GuitarPro export        | Never    | ChordPro is the niche. Klangio owns notation. Don't fight on their turf. |
| Variable BPM / tempo curves        | v0.2     | MVP assumes locally-stable tempo; emit one global BPM, drop a warning if confidence low. |
| Lyrics in non-English languages    | v0.1 supported (Whisper handles it for free) but unstested |
| Multi-instrument tab beyond solos  | Never    | Out of niche. |

#### CLI vs library API

**Both, with the library being the trunk.** The CLI is a 50-line wrapper (`argparse` + `transcribe()` + `write()`). Treat the library as the supported surface and document the CLI as a convenience. Pattern: copy what `whisper` does (CLI calls `whisper.transcribe()` directly).

Rationale: every successful music ML project ships both. Solo devs/musicians use the CLI; downstream pipelines (Polymath-style integrators, plugin authors, music-school tooling) use the library. Privileging the library prevents the CLI from accreting business logic.

#### Single-platform-first vs dual-platform-first

**Single-platform first (CUDA).** Reasons:

1. The user's primary production target is the RTX 5070Ti. Mac Mini M4 is a secondary inference target.
2. The dependency graph (Demucs v4 + faster-whisper + BeatNet + ML chord recognizer) is fragile on Apple Silicon today. Demucs v4 works on MPS but with caveats; `faster-whisper` (CTranslate2) had MPS support land relatively recently and is less battle-tested than CUDA. BeatNet/madmom are less Apple-Silicon-aware.
3. Single-platform v0.1 builds confidence in the architecture. v0.2 ports to Apple Silicon as a focused effort with its own test matrix.
4. The "works on neither" failure mode of dual-platform-first is far more damaging than a tagged release labelled "CUDA only — Apple Silicon coming in v0.2."

#### Definition of Done for v0.1

- `titan-chordpro` CLI exists, takes one audio file, emits a valid ChordPro file readable by the chordpro reference parser (https://github.com/ChordPro/chordpro).
- Library API: `transcribe(path) -> ChordProDocument` with stable signature.
- Test corpus of 5-10 known songs across genres (folk, pop, rock — skip jazz/classical for now). Subjective accuracy review by the project owner; no formal metrics yet.
- README with single-line install + single-line invocation example.
- `docs/method.md` describing the pipeline (Demucs → Whisper+stable-ts → chord recognizer → BeatNet → fusion → ChordPro writer).
- Apache-2.0 or MIT license.
- One headline GitHub README GIF/video showing input audio → output `.chordpro` file → rendered PDF via `chordpro` CLI.

---

## Open Questions

1. **Which chord recognizer for v0.1?** Options: Chordino (via chord-extractor — VAMP plugin dep is painful on some platforms), autochord (TF1-era TF, may have Python version constraints), BTC-ISM (PyTorch but research-grade, may need adaptation). **Need a decision in research doc 03 (chord & harmonic analysis).**
2. **BeatNet vs madmom for downbeats?** madmom is older and Cython-heavy, sometimes flaky on modern Pythons. BeatNet is newer PyTorch. **Need a decision in research doc 04 (beat tracking).**
3. **How to handle Whisper's known weakness on sung lyrics?** Whisper is trained mostly on speech. There's `Whisper-AT` and music-tuned variants (some on HuggingFace) that may be relevant. **Open research question.**
4. **Time signature detection.** Roadmap mentions 4/4 vs 6/8 patterns. madmom can do this but accuracy varies. **Open: do we ship with assumed 4/4 in v0.1, or attempt detection?**
5. **Inversion handling.** Roadmap says use bass stem to inform `C/E` notation. **Open: defer to v0.2 or include behind `--inversions` flag in v0.1?**
6. **Licensing of upstream models.** Demucs (MIT, fine), Whisper (MIT, fine), BeatNet (Apache-2.0 typically, verify), Chordino (GPL-2.0 — **this is a problem if we want a permissive license downstream; Chordino as a runtime dep is borderline okay, but bundling weights or VAMP plugin in the wheel is not**). **Verify and document.**
7. **Distribution.** Pure pip wheel? Conda? Docker image? VAMP plugin makes pip-only awkward. **Decide before v0.1 release.**
8. **ChordPro spec edge cases.** Does the reference parser accept `[C] x///` in the middle of a line? What about multi-line tab blocks (`{sot}/{eot}`)? **Cross-link to research doc 06 (ChordPro spec).**

---

## Sources

### Commercial tools
- [Chordify Premium pricing](https://chordify.net/premium)
- [Chordify Review (2026) — Guitar Chalk](https://www.guitarchalk.com/chordify-review/)
- [Chord AI FAQ](https://chordai.net/faq/)
- [Klangio Transcription Studio](https://klang.io/transcription-studio/)
- [Klangio launch — Sound on Sound](https://www.soundonsound.com/news/klangio-launch-transcription-studio)
- [Soundslice plans](https://www.soundslice.com/plans/)
- [Soundslice features](https://www.soundslice.com/features/)
- [AnthemScore homepage (Lunaverus)](https://www.lunaverus.com/)
- [Yalp.io](https://www.yalp.io/)
- [Moises advanced chord detection blog](https://moises.ai/blog/latest/advanced-chord-detection/)
- [Moises Review — StemSplit](https://stemsplit.io/blog/moises-ai-review)
- [Hookpad pricing](https://www.hooktheory.com/hookpad/pricing)
- [Plugin Boutique Scaler 2 review — Sound on Sound](https://www.soundonsound.com/reviews/plugin-boutique-scaler-2)
- [BandLab Smart Scales blog](https://blog.bandlab.com/smart-scales/)
- [Riffstation chord detection now free — TechRadar](https://www.techradar.com/news/fenders-riffstation-pro-is-now-free-get-the-chords-for-any-song-on-your-desktop)

### Open-source projects
- [autochord on GitHub](https://github.com/cjbayron/autochord)
- [autochord ISMIR 2021 paper](https://archives.ismir.net/ismir2021/latebreaking/000008.pdf)
- [Polymath on GitHub](https://github.com/samim23/polymath)
- [chord-extractor on GitHub](https://github.com/ohollo/chord-extractor)
- [Magenta Onsets and Frames](https://github.com/magenta/magenta/tree/main/magenta/models/onsets_frames_transcription)
- [basic-pitch on GitHub](https://github.com/spotify/basic-pitch)
- [basic-pitch announcement — Spotify Engineering](https://engineering.atspotify.com/2022/06/meet-basic-pitch)
- [Demucs on GitHub](https://github.com/facebookresearch/demucs)
- [Whisper on GitHub](https://github.com/openai/whisper)
- [Introducing Whisper — OpenAI](https://openai.com/index/whisper/)
- [Spleeter on GitHub](https://github.com/deezer/spleeter)
- [Releasing Spleeter — Deezer I/O](https://deezer.io/releasing-spleeter-deezer-r-d-source-separation-engine-2b88985e797e)
- [librosa on GitHub](https://github.com/librosa/librosa)
- [librosa SciPy paper (PDF)](https://proceedings.scipy.org/articles/Majora-7b98e3ed-003.pdf)
- [ChordPro reference implementation](https://github.com/ChordPro/chordpro)
- [chordpro.org](https://www.chordpro.org/)

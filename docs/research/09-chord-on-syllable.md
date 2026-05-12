# Chord-on-Syllable Placement (2024-2026)

> Research conducted for Titan ChordPro Lib. Goal: define algorithm and tooling for placing chord markers at the correct syllable (ideally the tonic/stressed syllable) within lyric lines, given word-level forced alignment timestamps.
> Last updated: 2026-05-08

## Why This Matters

ChordPro syntax allows chord markers to be embedded mid-word: chords are placed in square brackets immediately before the syllable they sound on, and a chord is allowed in the middle of a word when the chord changes at one of its syllables (e.g., `[G]char-i-[D]ot`). Tools like OnSong and Planning Center anchor chords to specific character positions and rely on those positions surviving transposition. Putting the chord on the wrong syllable produces a chart that is at best confusing and at worst musically wrong.

Take a lyric line `"hello world"` sung from t=1.000s to t=2.000s, with a chord change at t_c=1.450s:

- `[C]hello world` — chord rendered at line start. Wrong by ~450 ms; reads as if the chord starts the phrase.
- `hel[C]lo world` — chord on the second syllable of *hello*. Correct if the singer's *-lo* falls at 1.45s.
- `hello [C]world` — chord on the downbeat of *world*. Correct only if *world* starts at 1.45s.

The 70 ms tolerance for beat snap from `mir_eval` and the ~30 ms median timestamp error from WhisperX wav2vec2 mean we are operating well below the resolution of a syllable in fast-sung English (~150–250 ms per syllable) and within the resolution of a typical sustained syllable (300 ms+). So the alignment data is good enough — *if* we can decompose the word into syllables and pick the right one.

The roadmap targets placement on the **stressed (tonic) syllable** because that is where singers naturally land chord changes and where listeners parse the harmonic event. Cross-linguistically, stressed syllables coincide with note attacks and carry the longer duration / higher pitch / greater intensity that a singer uses to "hit" a chord. This is the linguistic anchor that turns a transcription into a usable chart.

## 1. Phoneme → Syllable Mapping

WhisperX produces phoneme-level alignment internally (via wav2vec2 CTC) and aggregates phoneme spans into word spans. The aggregation step throws away the syllable structure that exists implicitly in the phoneme sequence. To recover it we need a syllabification rule on top of the phonemic transcription.

### Sonority Hierarchy / Maximum Onset Principle

The classical algorithm has three stages:

1. **Identify nuclei** — every vowel (or syllabic consonant) is a syllable nucleus.
2. **Maximum Onset Principle (MOP)** — given a consonant cluster between two vowels, assign as many consonants as possible to the *onset* of the following syllable, subject to the *Sonority Sequencing Principle* (consonants in an onset must rise in sonority toward the nucleus) and *language-specific phonotactic legality* (e.g., English allows `/str-/` onsets but not `/tl-/`).
3. **Coda assignment** — any leftover consonants attach to the coda of the preceding syllable.

For `pe-tro-leum` (CMU `P EH1 T R OW0 L IY0 AH0 M`), MOP places `/tr-/` as the onset of the second syllable because `/tr/` is a legal English onset, yielding `pe.tro.leum` rather than `pet.ro.leum`.

The Maximum Onset Principle is the dominant default in computational syllabification for English and the major Romance languages and is the basis of `cainesap/syllabify`, `repp/big-phoney`, and the festival backend's syllable tokenizer.

### Language-Specific Rules

English and Portuguese diverge at several points:

- **Portuguese tolerates fewer onset clusters.** It accepts /pl-/, /pr-/, /tr-/, /kr-/, /fl-/ etc. but rejects most three-consonant onsets that English allows.
- **Portuguese is highly regular.** Brazilian Portuguese (pt-BR) has 99% syllabification accuracy from rule-based systems, and the syllable inventory is dominated by CV (60%) followed by CVC (15%) and V (8%) — a much simpler distribution than English.
- **Portuguese stress is mostly predictable** from orthography: words with a written accent are stressed on the marked syllable; unmarked words ending in `r/l/z/x/i/u/im/um/om` are *oxítonas* (stressed on the last syllable); everything else is *paroxítonas* (stressed on the second-to-last). This means stress detection in Portuguese can be *purely orthographic* with very high accuracy — a major win for our pipeline.
- **English stress is lexical** and not predictable from orthography. We need a dictionary lookup (CMU dict via `g2p_en`) or a learned model for OOV.

### MFA Syllable Output

The Montreal Forced Aligner (Kaldi-based, GPL) does not natively expose syllable boundaries in its standard TextGrid output. Its frame rate is fixed at 10 ms, so resolution is fine, but the tier output is `phones` and `words`. Practitioners fake syllable alignment in MFA by either inserting whitespace into the input transcript (e.g., separating Chinese characters) or post-processing the phone tier with an external syllabifier. For our pipeline, MFA is a heavy-weight option (Kaldi acoustic models, language-specific training data, GPL licensing), and the value-add over WhisperX wav2vec2 + post-hoc syllabification is small. Skip.

### Direct Syllable-Level Models

There are no published wav2vec2 syllable-CTC checkpoints with broad language coverage as of 2026. Singing-trained models (SongTrans, STARS) align *phonemes* to audio for singing voice synthesis but are research artefacts (Apache-2.0 / non-commercial) without a stable Python API. For lyrics-to-chord placement, the practical approach in 2026 remains:

```
audio → wav2vec2 phoneme alignment → rule-based syllabification → stress labelling
```

There is no shortcut.

## 2. Stress Detection (Tonic Syllable)

### Lexical Stress Dictionaries

- **CMU Pronouncing Dictionary** (English; Apache/BSD-style permissive): every vowel is annotated with a stress level: `0` (no stress), `1` (primary), `2` (secondary). 134k word entries. Out-of-vocabulary words are predicted by `g2p_en`'s neural net at ~75% phoneme-level accuracy and ~98% syllable-count accuracy. This is the single most authoritative resource for English stress.
- **Léxico do Português Brasileiro** and CETENFolha-derived lexicons exist but are not packaged as a Python library with stress markers per syllable. For Portuguese, orthographic rules carry most of the load, and an explicit lexicon is a backup for irregular cases (homographs like *secretária* vs *secretaria*).

### G2P Tools with Stress

| Tool | License | Stress | Languages |
|------|---------|--------|-----------|
| `g2p_en` | Apache-2.0 | Yes (CMU 0/1/2) | English only |
| `epitran` | MIT | **No explicit stress markers** in its rule files for most languages including pt-BR | 100+ languages |
| `phonemizer` (espeak backend) | GPL-3.0 | Stress in IPA output (ˈ primary, ˌ secondary) | espeak-ng's full set |
| `gruut` | MIT | Yes (in IPA output) | en, pt, fr, de, es, it, ru, sv, nl, ar, fa, cs, lb |

`g2p_en` is the gold standard for English. For Portuguese, `gruut` and `phonemizer`/espeak both carry IPA stress marks in their output; `epitran` produces IPA without stress. **The licensing matter is significant**: `phonemizer` is GPL-3.0 and links to `espeak-ng`; using it in a permissively licensed library forces our library to GPL or to keep `phonemizer` as an optional plugin behind a process boundary. `gruut` (MIT) is the cleaner choice for a permissive library.

### Acoustic Prosody-Based Stress Detection

When the lexicon disagrees or for ambiguous cases (e.g., emphasised function words, melisma extending an unstressed syllable), acoustic prosody can override or confirm the lexical guess. The principle auditory cues are:

- **F0 (pitch)** — strongest single cue; stressed syllables have higher F0.
- **Duration** — stressed syllables are longer (in absolute or vowel-relative terms).
- **Intensity (energy)** — stressed syllables have higher RMS energy.
- **Vowel quality** — unstressed English vowels reduce to schwa; full vowels signal stress.

A simple acoustic stress score per syllable (sum of z-scored F0, duration, RMS over phoneme spans within the syllable) is computable directly from the wav2vec2 phoneme spans plus a `librosa.pyin` F0 contour and `librosa.feature.rms` envelope.

### Singing vs Speech Stress

Singing distorts speech prosody: F0 is dictated by melody (not stress), duration is dictated by rhythm (long sustained syllables on weak beats are common), and intensity is shaped by the producer's mix. The lexical stress remains stable — singers do not generally re-stress words against their lexical pattern, except for stylistic emphasis or rap. For our purposes:

- **Lexical stress is the prior.** Use CMU/`g2p_en` for English, orthographic rules + `gruut` IPA for Portuguese.
- **Acoustic prosody is a tiebreaker** for phrasal stress (which word in a multi-word interval gets the chord, when several share a beat) — not for syllable stress within a word.

## 3. Syllabification Libraries

| Lib | License | PT-BR | EN | Stress | Last release | Notes |
|-----|---------|-------|----|--------|--------------|-------|
| `pyphen` | GPL-2.0+ / LGPL-2.1+ / MPL-1.1 (tri-license) | Yes (pt_BR + pt_PT Hunspell dicts) | Yes (en_US, en_GB) | No | Active 2025 | **Hyphenation, not phonetic syllabification.** Splits on orthographic boundaries, not phonemic ones — close but not identical. The MPL 1.1 leg of the tri-license makes it usable in permissive projects. |
| `g2p_en` | Apache-2.0 | No | Yes | Yes (CMU 0/1/2) | Stable | Pure-Python, ships its own model + CMU dict. Returns ARPABET phones with stress digits. Syllabification post-hoc via MOP. |
| `epitran` | MIT | Yes (`por-Latn`) | Yes (`eng-Latn`) | **No** | Active | IPA only; no stress marks; English requires `flite` system binary; the rule files for `por-Latn` are based on European Portuguese with documented gaps for pt-BR-specific phenomena (nasal vowels, vowel reduction). |
| `phonemizer` | GPL-3.0 | Yes (via espeak-ng) | Yes | Yes (IPA) | Active | espeak-ng is broadly tested; festival backend gives syllable tokens but is English-only. **GPL-3.0 propagates** — major constraint. |
| `nltk.corpus.cmudict` | Apache-2.0 (corpus) | No | Yes | Yes | Stable | Just the CMU dict, no neural OOV fallback; equivalent to `g2p_en` minus the model. |
| `gruut` | MIT | **Yes** (`pt`) | Yes | Yes (IPA) | 2.4.0 (mature, lower activity 2024-2025) | Pure Python, multi-language, ships models, exposes word/phoneme/sentence with IPA stress marks. **Best fit for Titan**: permissive license, native pt-BR support, no system binary dependency. |
| `cainesap/syllabify` | MIT | No | Yes | No | Stable, low activity | Implements MOP on CMU dict output. Useful as a reference implementation we can adapt. |
| `repp/big-phoney` | MIT | No | Yes | Yes (CMU) | Stable | Predicts syllable counts and stress for OOV English words via a neural model trained on CMU; 98.1% syllable count accuracy on OOV. Pulls in TensorFlow — heavyweight. |
| `Aquila-Resolve` | MIT | No | Yes | Yes | 2024 | Modern wrapper that combines `g2p_en` with disambiguation for homographs. English only. |

**Recommendation for Titan:**

- **English:** `g2p_en` (Apache-2.0, ARPABET with CMU stress). Apply MOP-based syllable grouping to the phoneme output ourselves (50 lines of code, same logic as `cainesap/syllabify`). For OOV words, `g2p_en`'s neural fallback covers it.
- **Portuguese (pt-BR):** `gruut` (MIT, IPA with stress marks) for phonemes + stress. For syllabification, either parse `gruut`'s IPA output with MOP or run `pyphen` (`pt_BR`) for orthographic syllables and align to the phoneme spans. Orthographic-stress rule (oxítona / paroxítona / proparoxítona) implemented as 30 lines of code provides a deterministic fallback.
- **Avoid `phonemizer` in core** because of GPL-3.0; expose it as an optional `[phonemizer]` extra for users who want espeak's coverage and accept the licence.

## 4. Lyrics-to-Audio Alignment — MIR Papers 2023-2026

Lyrics alignment is a distinct subfield from speech ASR + alignment. The dedicated lyrics-alignment line of work has been steadily eclipsed by Whisper-family pipelines, but a few directly relevant 2024–2025 contributions exist.

- **Jam-ALT (ISMIR 2024 / extended to ICME 2025).** Cífka et al. introduced a readability-aware lyrics transcription benchmark with a corresponding evaluation toolkit (`alt-eval`). Line-level timings were added in the 2025 ICME workshop paper *Exploiting Music Source Separation for Automatic Lyrics Transcription with Whisper*. AudioShake's commercial system reported a 57% reduction in WER versus Whisper v2 on Jam-ALT — the most credible commercial-vs-open-source delta we have. The *Evaluating Lyrics Alignment under Source Separated Conditions* paper at ISMIR 2025 specifically studies how different separators (Demucs vs MDX-Net) shift alignment errors.
- **ChordSync (Cífka et al., 2024).** A conformer-based aligner that maps chord annotations to audio without a weak-alignment pre-step. Library and pre-trained model published. Directly relevant: the same model pattern (conformer over CQT) could in principle be adapted to syllable-level lyric alignment, but the released checkpoint is for chords only.
- **SongTrans (2024).** Builds on Whisper with a hybrid AR/non-AR head for joint phoneme and note prediction, trained on DALI-derived data. Aligns phonemes to audio for singing voice synthesis. Phoneme outputs are usable as syllable inputs after rule-based grouping.
- **STARS (ACL 2025 Findings).** Hierarchical acoustic feature processing across frame, word, phoneme, note, and sentence levels with non-AR local acoustic encoders. Predicts phonemes, MIDI, technique, and style jointly. Research code at `gwx314/STARS`. SOTA in 2025 for joint singing transcription + alignment but not yet a drop-in tool.
- **DALI dataset.** 7,756 commercial songs with synchronised audio, lyrics, and notes at four granularity levels — *the* training set for syllable-level singing alignment because at the lowest level "syllables correspond to the vocal note." Not directly distributable due to copyright; researchers ship audio fingerprints + URLs.
- **Demucs + WhisperX is still SOTA in open-source.** No 2024-2026 specialised lyrics aligner has consistently beaten the htdemucs_ft → wav2vec2 phoneme alignment pipeline on Jam-ALT line-timing — the biggest gains are from improving the input (better separation, better VAD) rather than replacing the aligner.

## 5. Multi-Evidence Onset Fusion

Robust chord-on-syllable timing benefits from fusing several independent evidence signals because each individual signal has known failure modes:

| Signal | Source | Failure mode |
|--------|--------|--------------|
| Chord-event boundary | Chord recognizer (BTC, ChordSync) | Smoothed by HMM/CRF — boundaries can drift ±200 ms |
| Beat / downbeat | BeatThis | Tempo drift, swing — boundary at most ±70 ms typical |
| Bass-note attack | `librosa.onset.onset_detect` on bass stem | Misses sustained bass notes; false onsets on harmonic content |
| Vocal onset | Onset detection on vocal stem (consonant attack) | Misses vowel-initial words; smeared by reverb |
| Drum onset (kick/snare) | Onset detection on drum stem | Polyrhythms create extras; off-beats common |

There is no canonical published Bayesian fusion model for this exact problem. The closest published approach is ChordSync's joint conformer over CQT + chord embedding (it implicitly fuses harmonic and timing evidence) and the broader MIR tradition of weighted-evidence beat tracking (madmom's RNN beat tracker fuses several feature streams internally). For our use, a weighted-mean fusion with confidence-aware weighting suffices for v0.1, with a Bayesian extension as v0.3 work.

A practical fusion rule:

```
T_final = weighted_mean([
    (T_chord, w_chord = 0.4),
    (T_beat,  w_beat  = 0.25 if |T_chord - T_beat| < 70 ms else 0),
    (T_bass,  w_bass  = 0.2  if bass_onset within ±100 ms of T_chord else 0),
    (T_voc,   w_voc   = 0.15 if syllable consonant onset within ±100 ms else 0),
])
```

Then *snap* `T_final` to the nearest beat/downbeat if within 70 ms (the `mir_eval` beat tolerance). The snap step is critical: musicians read charts on the beat grid, not on the absolute timeline, and a chord change drawn 50 ms before a downbeat *reads* as on the downbeat to a player.

## 6. Melisma Handling

A melisma — one syllable sustained over multiple notes (e.g., gospel/pop ad-libs, sustained ballad vowels) — is a known stable-ts and DTW failure mode: the alignment "smears" the syllable across the entire vocal arc, and any chord change during the sustain ends up attached to the syllable boundary rather than the chord boundary.

### Detection

A syllable is a melisma candidate if any of:

- **Long duration**: vowel span > 600 ms (a normal sung syllable is 150–400 ms; >600 ms is a sustain).
- **Pitch variance**: std-dev of `pyin` F0 over the vowel span > 50 cents (a single note has near-flat pitch, modulo vibrato).
- **Multiple beat crossings**: vowel span covers more than 1 beat at the song tempo.

When two of three trigger, treat the syllable as a melisma.

### Placement Strategy

The right behaviour is to **break the melisma into pseudo-syllables** anchored at note boundaries within the sustain, and place chord changes against those pseudo-boundaries rather than against the original syllable.

```
melisma "Whoooooa" from t=10.0 to t=12.5 with chord changes at 10.5, 11.0, 11.7
→ render as "Whoo[C]oo[F]oo[G]oa" or "Whoa~~[C]~~[F]~~[G]"
```

The `~` continuation glyph is non-standard ChordPro but several renderers (OnSong) accept it. Falling back to standard ChordPro, the chord can be placed at the melisma start with the others attached to subsequent syllables — but if there are no subsequent syllables before the next one, drop subsequent chords to the next chord change boundary or annotate them in a `{comment: }` directive.

### Published Work

- The 2019 Chitra et al. ICASSP paper on *Automatic Lyrics-to-Audio Alignment on Polyphonic Music Using Singing-adapted Acoustic Models* explicitly notes that mistakenly recognised melisma portions can be confused with silence in the audio.
- *Phoneme Level Lyrics Alignment* (Telecom-Paris, 2021) introduced DTW-attention to handle non-syllabic singing. Soft-DTW (Cuturi & Blondel) is a differentiable replacement that some recent singing-alignment models adopt.

For a v0.1 implementation, melisma detection + a fallback rule is sufficient. The DTW-attention models are research code only.

## 7. Commercial Approaches

### AudioShake

Their lyrics-transcription product reports −57% WER vs Whisper v2 on Jam-ALT. AudioShake also runs Jam-ALT as the public benchmark, which puts them in a strong position. Public technical breadcrumbs:

- They run their own source separation (proprietary, distinct from Demucs).
- They publish `alt-eval`, the formatting-aware WER toolkit underlying Jam-ALT.
- Job listings and conference talks have referenced phoneme CTC heads on top of conformer encoders trained on internal labelled data, plus a forced-alignment post-step. They have explicitly *not* claimed to be a Whisper fine-tune.
- Their syllable-level timing for karaoke export is a separate post-process on top of word-level output — the same architecture pattern we are proposing.

### Apple Music (Sing)

- TTML (W3C XML) is the delivery format for word-by-word and syllable-by-syllable highlighting. Public TTML files from Apple Music show explicit syllable spans for high-profile catalog tracks; mid-tail tracks frequently show only word spans.
- For high-profile releases, alignment is human-verified. For long-tail catalog, an internal automated pipeline is used; the *How Apple Music Maps Audio to Lyrics* engineering write-up and Apple's 2026 patent on lyrics/karaoke UI describe a forced-alignment workflow (ASR + acoustic alignment) but do not disclose model details.
- Apple Sing's vocal-attenuation slider runs on-device and is independent of the alignment pipeline.

### Klangio

- Karlsruhe-based, cloud-only inference, Transcription Studio ships VST3/AU plugins as front-ends.
- Marketing copy mentions "instrument-specific AI models" but no model architecture is disclosed.
- User reviews note lyrics placement quality is the weak point — chord and note transcription is the strength. Suggests their lyrics path is a Whisper/wav2vec2 wrapper without serious music-domain adaptation.

### Moises

- AI Lyrics Transcription with auto language detection in <5 s. Chord detection with three difficulty levels and a synced chord/lyrics view ("Grid Mode").
- They publicly use Demucs-derived separation. Their lyrics path is widely believed to be Whisper-family with custom post-processing — the speed (<5 s for a 3-minute song) is consistent with `faster-whisper` large-v3 on GPU.
- Like Klangio, no explicit syllable-level alignment is exposed.

### LyricFind / LyricsGenius / Musixmatch

These are primarily *content distribution* networks, not alignment R&D shops. Musixmatch operates a substantial community-curated time-sync layer with internal QA tooling, but the alignment is an editorial product, not an algorithm.

### Reverse-Engineering Conclusion

The best-funded commercial systems (AudioShake, Apple Music) appear to use a similar pipeline to what Titan is targeting — source separation → phoneme-CTC alignment → post-hoc syllabification — with the major gain being **proprietary training data on singing**. For an open-source library targeting ChordPro output, our differentiator is the **chord-event fusion step** that commercial karaoke products do not need.

## 8. Recommended Algorithm — Pseudocode

```python
from dataclasses import dataclass
from typing import Literal

Language = Literal["en", "pt"]

@dataclass
class WordEvent:
    text: str               # surface form, e.g. "petroleum"
    t_start: float
    t_end: float
    confidence: float       # from wav2vec2

@dataclass
class PhonemeEvent:
    phone: str              # ARPABET ("EH1") or IPA ("e")
    t_start: float
    t_end: float
    word_idx: int           # parent word

@dataclass
class Syllable:
    nucleus: str            # the vowel phoneme
    onset: list[str]
    coda: list[str]
    t_start: float
    t_end: float
    is_stressed: bool
    char_start: int         # position in the surface word
    char_end: int

@dataclass
class ChordEvent:
    symbol: str             # "Cmaj7"
    t_change: float
    confidence: float

@dataclass
class BeatGrid:
    beats: list[float]
    downbeats: list[float]
    tempo_bpm: float


def syllabify_word(
    word: WordEvent,
    phonemes: list[PhonemeEvent],
    language: Language,
) -> list[Syllable]:
    """
    Segment phoneme sequence into syllables and label stress.
    Apply Maximum Onset Principle subject to language phonotactics.
    """
    if language == "en":
        nuclei = [p for p in phonemes if p.phone[-1].isdigit()]  # CMU stress digits
        return group_phonemes_mop(phonemes, nuclei, lang="en", word=word)
    elif language == "pt":
        ipa_phones = phonemes  # gruut output, IPA with ˈ/ˌ stress marks
        nuclei = [p for p in ipa_phones if is_vowel_ipa(p.phone)]
        syllables = group_phonemes_mop(ipa_phones, nuclei, lang="pt", word=word)
        # Override stress with orthographic rule if the IPA has none
        if not any(s.is_stressed for s in syllables):
            apply_orthographic_pt_stress(word.text, syllables)
        return syllables
    raise NotImplementedError(language)


def acoustic_stress_score(
    syllable: Syllable,
    f0_contour: np.ndarray,
    rms: np.ndarray,
    sr: int,
) -> float:
    """z-scored sum of mean F0 + duration + mean RMS over the syllable's nucleus span."""
    ...


def fuse_chord_onset(
    chord: ChordEvent,
    beat_grid: BeatGrid,
    bass_onsets: np.ndarray,
    vocal_onsets: np.ndarray,
    snap_tolerance_s: float = 0.070,    # mir_eval beat tolerance
    near_window_s: float = 0.100,
) -> float:
    """Weighted-mean fusion with optional beat snap."""
    candidates: list[tuple[float, float]] = [(chord.t_change, 0.4 * chord.confidence)]
    nearest_beat = min(beat_grid.beats, key=lambda b: abs(b - chord.t_change))
    if abs(nearest_beat - chord.t_change) < snap_tolerance_s:
        candidates.append((nearest_beat, 0.25))
    for t_b in bass_onsets:
        if abs(t_b - chord.t_change) < near_window_s:
            candidates.append((t_b, 0.2))
            break
    for t_v in vocal_onsets:
        if abs(t_v - chord.t_change) < near_window_s:
            candidates.append((t_v, 0.15))
            break
    total_w = sum(w for _, w in candidates)
    t_fused = sum(t * w for t, w in candidates) / total_w
    if abs(nearest_beat - t_fused) < snap_tolerance_s:
        return nearest_beat
    return t_fused


def detect_melisma(syllable: Syllable, f0_contour, beat_grid) -> bool:
    long_duration = (syllable.t_end - syllable.t_start) > 0.6
    f0_seg = f0_contour_segment(syllable, f0_contour)
    pitch_var = float(np.nanstd(cents(f0_seg))) if len(f0_seg) else 0.0
    high_variance = pitch_var > 50.0
    beats_crossed = sum(syllable.t_start <= b <= syllable.t_end for b in beat_grid.beats)
    multi_beat = beats_crossed > 1
    return sum([long_duration, high_variance, multi_beat]) >= 2


def place_chord_in_lyrics(
    chord_events: list[ChordEvent],
    word_alignments: list[WordEvent],
    phoneme_alignments: list[PhonemeEvent] | None,
    beat_grid: BeatGrid,
    bass_onsets: np.ndarray,
    vocal_onsets: np.ndarray,
    f0_contour: np.ndarray,
    rms: np.ndarray,
    language: Language,
    sr: int = 44100,
) -> str:
    # 1. Build syllable list per word
    syllable_seq: list[tuple[WordEvent, list[Syllable]]] = []
    for w in word_alignments:
        if phoneme_alignments is None:
            # Degenerate to whole-word placement
            syllable_seq.append((w, [_pseudo_syllable_from_word(w)]))
            continue
        ph_w = [p for p in phoneme_alignments if p.word_idx == w_idx(w)]
        sylls = syllabify_word(w, ph_w, language)
        # Acoustic re-rank: if no lexical stress, pick max acoustic score
        if not any(s.is_stressed for s in sylls):
            scores = [acoustic_stress_score(s, f0_contour, rms, sr) for s in sylls]
            sylls[int(np.argmax(scores))].is_stressed = True
        syllable_seq.append((w, sylls))

    # 2. For each chord event, find target syllable
    placements: list[tuple[int, int, str]] = []   # (word_idx, char_offset, chord_symbol)
    for ch in chord_events:
        t_target = fuse_chord_onset(ch, beat_grid, bass_onsets, vocal_onsets)

        # Hierarchical fallback search
        target = _find_stressed_syllable_at(syllable_seq, t_target, tol=0.150)
        if target is None:
            target = _find_any_syllable_at(syllable_seq, t_target, tol=0.150)
        if target is None:
            # Place before the next word that starts after t_target
            target = _next_word_start(syllable_seq, t_target)
        if target is None:
            # Defer to nearest beat: emit as a beat-anchored chord directive
            placements.append((-1, -1, f"{{comment: {ch.symbol} @ "
                                       f"{t_target:.2f}s}}"))
            continue

        word_i, syll_i, syll = target
        # Melisma override: if the syllable is a melisma and the chord lands
        # mid-melisma, attach to a pseudo-position past the syllable nucleus
        if detect_melisma(syll, f0_contour, beat_grid):
            char_offset = _melisma_char_offset(
                syll, t_target, syllable_seq[word_i][0]
            )
        else:
            char_offset = syll.char_start
        placements.append((word_i, char_offset, ch.symbol))

    # 3. Render ChordPro line
    return render_chordpro_line(word_alignments, placements)
```

Concrete walk-through. Suppose we have the line *"It's been a long, long time"* (Sam Smith, *Stay With Me*-style ballad), with WhisperX yielding word spans and phoneme spans for English, and a chord change to G at t_c = 4.18 s while the singer holds *long* (vowel) from 3.9 to 4.6 s and the next downbeat is at 4.20 s.

1. Syllabify *long* → single syllable `[L,AO1,NG]`, stressed.
2. Detect melisma on *long* — duration 700 ms, pitch variance 65 cents → yes.
3. Fuse: `t_chord=4.18`, nearest beat=4.20 (within 70 ms → snap), `T_final=4.20`.
4. Find stressed syllable at t=4.20 → first *long* (3.9–4.6).
5. Melisma override: chord lands ~300 ms into the vowel, place chord *before* "long" rather than mid-vowel because there is no later syllable in the same word to attach to.
6. Output: `It's been a [G]long, long time`.

Now consider the same line with a chord change at t_c = 4.55 s (mid-melisma, no near beat). Steps 3–5 still pick *long*, but the chord is well past the syllable's char_start. Two options:

- Conservative: still attach to *long* (slightly wrong but within ChordPro's expressive limits).
- Aggressive: emit a `{comment: G @ 4.55s}` directive between `long, long`. This preserves timing fidelity but is ChordPro-extension behaviour.

Default to conservative (option 1) for v0.1; expose option 2 behind a `melisma_strategy="annotate"` flag.

## Recommendations for Titan ChordPro Lib

### v0.1 (minimal viable — Mac-first)

- **English path:** `g2p_en` (Apache-2.0) for ARPABET + CMU stress, in-house MOP syllabifier (~50 LOC, port of `cainesap/syllabify` logic). Word-level alignment from WhisperX wav2vec2.
- **Portuguese path:** `gruut` (MIT) for IPA + stress; orthographic stress rule (oxítona / paroxítona / proparoxítona) as deterministic backup; `pyphen` (`pt_BR`) for orthographic syllable boundaries when IPA-to-grapheme alignment is needed.
- **Onset fusion:** chord boundary + beat snap only (no bass / vocal onset yet). 70 ms beat-snap tolerance.
- **Hierarchical fallback:** stressed syllable → any syllable → before word → defer-to-next-beat.
- **Melisma:** detect by duration + pitch variance; attach chord to syllable start (conservative).
- **No direct phoneme-level data:** if WhisperX phoneme output is unavailable, fall back to whole-word chord placement (still beats no placement).

### v0.2 enhancements

- Add bass-onset evidence (`librosa.onset.onset_detect` on Demucs bass stem with HPSS pre-filter).
- Add vocal consonant-onset evidence on the vocal stem.
- Acoustic prosody rerank when lexical stress is ambiguous (homographs, reduced English function words).
- Soft-DTW melisma re-segmentation for held vowels with multiple chord events inside.
- Optional `phonemizer`+espeak path as `[phonemizer]` extra (GPL boundary documented in `LICENSE-EXTRAS.md`).

### v0.3+ ambitions

- Replace WhisperX phoneme alignment with a singing-trained model when STARS-class checkpoints stabilise.
- Bayesian fusion model for chord-event timing trained on a small annotated subset of Jam-ALT-style data.
- Active-learning loop: store per-song confidence and let users correct in a GUI; feed corrections back into a fine-tuning set.
- Direct ChordSync-style joint chord + lyric alignment, conditioned on pre-extracted chord candidates.

## Open Questions

- How well does `gruut`'s pt-BR IPA model handle nasal vowels (ã, õ) and the /ɾ/ vs /h/ rhotic split — these matter for syllable boundaries and we have no quantitative benchmark.
- Does the wav2vec2 phoneme model used by WhisperX produce reliable stress-bearing phoneme labels for Portuguese, or only canonical phones? If only canonical, all stress detection must come from `gruut` / orthography.
- For melismas longer than two beats, is "split into pseudo-syllables and emit ChordPro extensions" preferred over "attach all chords to the original syllable in order"? This is a UX decision to validate with users.
- What are realistic licence expectations from the user community — is Apache-2.0 / MIT only acceptable, or is GPL-via-`phonemizer` tolerable as an opt-in?

## Sources

- [2024:Lyrics-to-Audio Alignment - MIREX Wiki](https://music-ir.org/mirex/wiki/2024:Lyrics-to-Audio_Alignment)
- [STARS: A Unified Framework for Singing Transcription, Alignment, and Refined Style Annotation (arXiv 2507.06670)](https://arxiv.org/abs/2507.06670)
- [STARS - ACL 2025 Findings PDF](https://aclanthology.org/2025.findings-acl.781.pdf)
- [STARS GitHub](https://github.com/gwx314/STARS)
- [SongTrans (arXiv 2409.14619)](https://arxiv.org/abs/2409.14619)
- [Creating DALI - TISMIR](https://transactions.ismir.net/articles/10.5334/tismir.30)
- [DALI GitHub](https://github.com/gabolsgabs/DALI)
- [Jam-ALT site](https://audioshake.github.io/jam-alt/)
- [Jam-ALT paper (arXiv 2311.13987)](https://arxiv.org/pdf/2311.13987)
- [Exploiting Music Source Separation for ALT with Whisper (arXiv 2506.15514)](https://arxiv.org/html/2506.15514v1)
- [AudioShake Jam-ALT benchmark blog](https://www.audioshake.ai/post/new-benchmark-for-higher-quality-lyrics-transcription-from-audioshake-research)
- [AudioShake Lyric Transcription product](https://www.audioshake.ai/products/lyric-transcription-alignment)
- [alt-eval toolkit](https://github.com/audioshake/alt-eval)
- [ChordSync (arXiv 2408.00674)](https://arxiv.org/abs/2408.00674)
- [BACHI: Boundary-Aware Symbolic Chord Recognition (arXiv 2510.06528)](https://arxiv.org/abs/2510.06528)
- [Phoneme Level Lyrics Alignment - HAL](https://telecom-paris.hal.science/hal-03255334v1/file/2021_Phoneme_level_lyrics_alignment_and_text-informed_singing_voice_separation.pdf)
- [Real-Time Lyrics Alignment Using Chroma and Phonetic Features (arXiv 2401.09200)](https://ar5iv.labs.arxiv.org/html/2401.09200)
- [ISMIR 2025: Evaluating Lyrics Alignment under Source Separated Conditions](https://ismir2025program.ismir.net/lbd_412.html)
- [Maximal Onset Principle - Glottopedia](http://glottopedia.org/index.php/Maximal_Onset_Principle)
- [cainesap/syllabify](https://github.com/cainesap/syllabify)
- [repp/big-phoney](https://github.com/repp/big-phoney)
- [g2p-en on PyPI](https://pypi.org/project/g2p-en/)
- [g2p_en source](https://github.com/Kyubyong/g2p/blob/master/g2p_en/g2p.py)
- [Aquila-Resolve on PyPI](https://pypi.org/project/Aquila-Resolve/)
- [phonemizer on PyPI](https://pypi.org/project/phonemizer/)
- [phonemizer documentation](https://bootphon.github.io/phonemizer/)
- [bootphon/phonemizer GitHub](https://github.com/bootphon/phonemizer)
- [gruut GitHub](https://github.com/rhasspy/gruut)
- [gruut documentation](https://rhasspy.github.io/gruut/)
- [gruut-ipa](https://github.com/rhasspy/gruut-ipa)
- [Pyphen homepage](https://pyphen.org/)
- [Pyphen GitHub (Kozea)](https://github.com/Kozea/Pyphen)
- [epitran GitHub](https://github.com/dmort27/epitran)
- [Epitran: Precision G2P for Many Languages (LREC 2018)](http://www.lrec-conf.org/proceedings/lrec2018/pdf/890.pdf)
- [CMU Pronouncing Dictionary - Wikipedia](https://en.wikipedia.org/wiki/CMU_Pronouncing_Dictionary)
- [The CMU Pronouncing Dictionary site](http://www.speech.cs.cmu.edu/cgi-bin/cmudict)
- [Montreal Forced Aligner GitHub](https://github.com/MontrealCorpusTools/Montreal-Forced-Aligner)
- [MFA Multilingual paper (arXiv 2504.07315)](https://arxiv.org/html/2504.07315)
- [stable-ts GitHub](https://github.com/jianfch/stable-ts)
- [whisper-timestamped GitHub](https://github.com/linto-ai/whisper-timestamped)
- [whisperX GitHub](https://github.com/m-bain/whisperX)
- [CrisperWhisper Interspeech 2024](https://www.isca-archive.org/interspeech_2024/zusag24_interspeech.pdf)
- [librosa.onset.onset_detect docs](https://librosa.org/doc/main/generated/librosa.onset.onset_detect.html)
- [madmom paper - ACMMM 2016](https://dl.acm.org/doi/10.1145/2964284.2973795)
- [madmom on arXiv](https://arxiv.org/pdf/1605.07008)
- [Spotify Research: End-to-End Lyrics Alignment for Polyphonic Music](https://research.atspotify.com/publications/end-to-end-lyrics-alignment-for-polyphonic-music-using-an-audio-to-character-recognition-model)
- [Apple Music lyrics-sync engineering write-up - Medium](https://medium.com/@ethchor/how-apple-music-maps-audio-to-lyrics-the-engineering-behind-real-time-lyric-sync-a2485385c9a9)
- [Apple Lyrics & Karaoke patent (2026)](https://appleworld.today/2026/03/apple-granted-patent-for-lyrics-and-karaoke-user-interfaces-methods-and-systems/)
- [Apple Music Sing announcement - TechCrunch](https://techcrunch.com/2022/12/06/apple-music-is-getting-a-new-karaoke-like-feature-apple-sing/)
- [Klangio Transcription Studio](https://klang.io/transcription-studio/)
- [Klangio Sound on Sound coverage](https://www.soundonsound.com/news/klangio-launch-transcription-studio)
- [Moises Lyrics Transcription help](https://help.moises.ai/hc/en-us/articles/8684044378780-How-do-I-use-the-transcription-and-edit-the-lyrics)
- [Moises Chords Grid Mode help](https://help.moises.ai/hc/en-us/articles/9570133423772-How-to-use-the-new-Chords-view-Grid-Mode)
- [ChordPro Implementation: Chords](https://www.chordpro.org/chordpro/chordpro-chords/)
- [ChordPro Wikipedia](https://en.wikipedia.org/wiki/ChordPro)
- [An open-source rule-based syllabification tool for Brazilian Portuguese - Journal of the Brazilian Computer Society](https://journal-bcs.springeropen.com/articles/10.1186/s13173-014-0021-9)
- [A Word Prosodic Algorithm for Brazilian Portuguese (Academia.edu)](https://www.academia.edu/73068065/A_Word_Prosodic_Algorithm_for_Brazilian_Portuguese)
- [An Automatic Phonetic Aligner for Brazilian Portuguese with a Praat Interface](https://link.springer.com/chapter/10.1007/978-3-319-41552-9_38)
- [Comparison of rule-based and data-driven approaches for syllabification (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S0885230821000401)
- [Phonetics of European Portuguese stress - Cambridge Core](https://www.cambridge.org/core/journals/journal-of-the-international-phonetic-association/article/phonetics-of-european-portuguese-stress-a-nonce-word-experiment/812DC040F6261A4A4AD14D0FFB76A711)
- [Acoustic correlates of stress in speech perception - ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0749596X24000123)
- [Acoustic Cues to Perception of Word Stress - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC5503100/)
- [A New Method for Detecting Onset and Offset for Singing - MDPI](https://www.mdpi.com/2076-3417/12/15/7391)
- [datasets-br/unitex-pt-br](https://github.com/datasets-br/unitex-pt-br)
- [pythonprobr/palavras](https://github.com/pythonprobr/palavras)
- [alvelvis/fonetizador](https://github.com/alvelvis/fonetizador)

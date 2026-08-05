# Chord explore lane — report (2026-08-05)

**Branch:** `impl/chord-explore`  
**Contract preserved:** `ChordRecognitionEngine.detect(harmonic_mix, bass_stem?) → list[ChordEvent]`  
**Eval set:** 3 operator songs (corpus `chordpros.csv`), majmin soft match vs human ChordPro brackets.

## Baseline H0 (Chordino + reseg v5 + bass)

| youtube_id | Título | match_rate | lcs_rate | max_hold | notes |
|------------|--------|------------|----------|----------|-------|
| `9yZt5ekdceI` | Ao olhar pra cruz | **0.933** | 0.943 | F 14.7s (outro) | Already strong |
| `LvoYT0loqLQ` | Teu santo nome | **0.857** | 0.857 | G 31.7s (outro) | Strong |
| `LL5Pak4zcuA` | Jesus Tu És a Minha Vida | **0.505** | 0.577 | G 11.3s | Hard case |
| **mean** | | **0.765** | 0.792 | | score≈0.771 |

Ablations already known / reconfirmed:

- Detect on **other+bass** best; other-only and bass-only worse on song 3.
- Raw Chordino on song 3 ≈0.37; postprocess/key-snap helps to ≈0.50 — acoustic ceiling for Chordino on that track, not a wiring bug.
- Long holds at end of songs 1–2 are mostly **true pads** (chroma Viterbi also keeps one chord).

## Hypotheses tested

| ID | What | Mean match | vs H0 | Verdict |
|----|------|------------|-------|---------|
| H0 | Chordino baseline | 0.765 | — | control |
| H1 | Multi-pass reseg + force Viterbi on holds >10s | 0.765 | 0 | Neutral-neutral; outros still long |
| H3 | Stem mix variants | ≤ H0 | ≤0 | other+bass remains best |
| H5 | Pure CQT template + Viterbi (no Chordino) | ~0.54–0.63 | −13–22pp | worse; do not replace |
| H6 | **BTC majmin** (Park et al. ISMIR 2019, MPS) | 0.758 | −0.7pp mean | **wins song1/2, loses song3** |

### H6 per-song (BTC engine with reseg + bass)

| song | BTC | H0 | Δ |
|------|-----|----|---|
| Ao olhar | 0.952 | 0.933 | **+1.9pp** |
| Teu santo nome | 0.929 | 0.857 | **+7.1pp** |
| Jesus Tu És… | 0.392 | 0.505 | **−11.3pp** (catastrophic under promote rule) |

Promote rule (handoff): mean ≥ H0 +2pp **and** no song −10pp → **BTC cannot become default**.

Pure BTC labs (no reseg) similar: song1/2 even better (~0.96/0.93), song3 ~0.38.

Frame-vote BTC-prefer mean 0.785 but song3 still −4pp; not enough to flip default without broader set.

## Research notes (ACR / Mac)

1. **Chordino** (NNLS + HMM, Mauch & Dixon): solid CPU baseline; struggles on some worship pads / non-diatonic GT choices.
2. **BTC** (Bi-directional Transformer, ISMIR 2019): still the most practical open majmin ML stack with public weights; runs on Apple MPS after `map_location` + numpy alias fixes.
3. **Template chroma + Viterbi**: underperforms Chordino on this set — acoustic features alone without NNLS / trained priors are weaker on dense pads.
4. **Source-separation-aware ACR**: other+bass (htdemucs) already matches literature tip; full mix previously worse.
5. **Glass ceiling / GT noise**: human ChordPro is lyric-bracket dense (repeats under same harmony) and not absolute truth — sequence match_rate is a guide, not WCSR.

Refs: project `docs/research/03-chord-recognition.md`; BTC [jayg996/BTC-ISMIR19](https://github.com/jayg996/BTC-ISMIR19); Chordino/nnls-chroma; MIREX WCSR.

## Code delivered (this branch)

| Path | Role |
|------|------|
| `titan_chordpro/engines/chord/btc.py` | `BtcEngine` (ChordRecognitionEngine) |
| `titan_chordpro/engines/chord/_btc/**` | Vendored BTC model code + config (MIT) |
| `titan_chordpro/engines/chord/chroma_viterbi.py` | Template Viterbi (eval + force-hold helper) |
| `titan_chordpro/engines/chord/chordino.py` | Multi-pass reseg + optional force-decode of long holds |
| `titan_chordpro/factory.py` | `TITAN_CHORD_BACKEND=chordino\|btc` (default chordino) |
| `scripts/compare_chordpro_to_gt.py` | Sequence / hold metrics vs corpus |
| `scripts/redetect_chords_from_cache.py` | Re-run detect only on cached harmonic_mix |
| `tests/unit/engines/chord/test_btc.py` | Unit tests |

**Weights:** not in git (~12MB). Place at  
`~/.cache/titan-chordpro/models/btc_model.pt`  
or set `TITAN_BTC_MODEL`. Source: BTC-ISMIR19 `test/btc_model.pt`.

## Winner / promote recommendation

- **Default product path:** keep **Chordino** (H0 metrics). Multi-pass reseg is safe to merge (no regression on sample).
- **Optional ML path:** merge **BtcEngine** behind `TITAN_CHORD_BACKEND=btc` for operators who want better C–G–Am–F worship charts and accept risk on hard tracks.
- **Do not** switch factory default to BTC until a larger sample (≥10 songs) shows mean gain without −10pp disasters, or an unsupervised selector is validated.
- **Song 3 residual:** Chordino acoustic ceiling ~0.50 vs this GT; may need GT review, arrangement-specific harmony, or a larger-vocab / fine-tuned model later (v0.2).

## What did not work

- Pure chroma Viterbi as primary detector.
- Stem mix tweaks beyond other+bass.
- Force-splitting outro pads (chroma agrees they are one chord).
- BTC as unconditional default (song 3).

## Metrics artifacts

`/tmp/titan-chord-explore/hyp-H0/`, `hyp-H1-reseg/`, `hyp-H6-btc/`.

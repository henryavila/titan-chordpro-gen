"""Tests for engines.chord.bass_chroma — librosa bass-note class extractor."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

pytest.importorskip("librosa")


SR = 22050


def _synthesize_tone(freq: float, duration: float, sr: int = SR) -> np.ndarray:
    t = np.linspace(0.0, duration, int(sr * duration), endpoint=False)
    return 0.4 * np.sin(2.0 * np.pi * freq * t).astype(np.float32)


@pytest.fixture
def bass_a2_wav(tmp_path: Path) -> Path:
    """2s of A2 (110 Hz) bass tone."""
    audio = _synthesize_tone(freq=110.0, duration=2.0)
    p = tmp_path / "bass_a2.wav"
    sf.write(str(p), audio, SR)
    return p


@pytest.fixture
def bass_c2_wav(tmp_path: Path) -> Path:
    """2s of C2 (65.4 Hz) bass tone."""
    audio = _synthesize_tone(freq=65.4, duration=2.0)
    p = tmp_path / "bass_c2.wav"
    sf.write(str(p), audio, SR)
    return p


@pytest.fixture
def silent_wav(tmp_path: Path) -> Path:
    audio = np.zeros(int(SR * 1.0), dtype=np.float32)
    p = tmp_path / "silent.wav"
    sf.write(str(p), audio, SR)
    return p


class TestPitchClassLetter:
    @pytest.mark.parametrize(
        "idx,letter",
        [
            (0, "C"),
            (1, "C#"),
            (2, "D"),
            (3, "D#"),
            (4, "E"),
            (5, "F"),
            (6, "F#"),
            (7, "G"),
            (8, "G#"),
            (9, "A"),
            (10, "A#"),
            (11, "B"),
        ],
    )
    def test_pitch_class_letter(self, idx: int, letter: str) -> None:
        from titan_chordpro.engines.chord.bass_chroma import pitch_class_letter

        assert pitch_class_letter(idx) == letter

    def test_invalid_index(self) -> None:
        from titan_chordpro.engines.chord.bass_chroma import pitch_class_letter

        with pytest.raises(ValueError, match="0..11"):
            pitch_class_letter(12)


class TestExtractBassNote:
    def test_a2_returns_a(self, bass_a2_wav: Path) -> None:
        from titan_chordpro.engines.chord.bass_chroma import extract_bass_note

        letter, confidence = extract_bass_note(bass_a2_wav, start=0.1, end=1.9)
        assert letter == "A"
        assert confidence > 0.5

    def test_c2_returns_c(self, bass_c2_wav: Path) -> None:
        from titan_chordpro.engines.chord.bass_chroma import extract_bass_note

        letter, confidence = extract_bass_note(bass_c2_wav, start=0.1, end=1.9)
        assert letter == "C"
        assert confidence > 0.5

    def test_silent_returns_none_low_confidence(self, silent_wav: Path) -> None:
        from titan_chordpro.engines.chord.bass_chroma import extract_bass_note

        letter, confidence = extract_bass_note(silent_wav, start=0.0, end=1.0)
        assert letter is None
        assert confidence < 0.5

    def test_too_short_interval_returns_none(self, bass_a2_wav: Path) -> None:
        from titan_chordpro.engines.chord.bass_chroma import extract_bass_note

        letter, confidence = extract_bass_note(bass_a2_wav, start=0.0, end=0.005)
        assert letter is None

    def test_interval_beyond_file_clamps(self, bass_a2_wav: Path) -> None:
        from titan_chordpro.engines.chord.bass_chroma import extract_bass_note

        letter, _ = extract_bass_note(bass_a2_wav, start=1.5, end=10.0)
        assert letter == "A"

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        from titan_chordpro.engines.chord.bass_chroma import extract_bass_note

        with pytest.raises(FileNotFoundError):
            extract_bass_note(tmp_path / "nope.wav", start=0.0, end=1.0)

    def test_short_interval_after_split_uses_local_energy(self, tmp_path: Path) -> None:
        """Bass on a reseg prefix must reflect that slice, not a later note.

        Synthesize E for 0–2s then G for 2–4s. Querying [0, 2) must return E
        (not G from the suffix that a sticky pre-split pass would pick up).
        """
        from titan_chordpro.engines.chord.bass_chroma import extract_bass_note

        # E2 ≈ 82.4 Hz, G2 ≈ 98.0 Hz
        e = _synthesize_tone(freq=82.4, duration=2.0)
        g = _synthesize_tone(freq=98.0, duration=2.0)
        audio = np.concatenate([e, g])
        p = tmp_path / "e_then_g.wav"
        sf.write(str(p), audio, SR)

        letter_prefix, conf_p = extract_bass_note(p, start=0.1, end=1.9)
        letter_suffix, conf_s = extract_bass_note(p, start=2.1, end=3.9)
        assert letter_prefix == "E", f"prefix expected E, got {letter_prefix} conf={conf_p}"
        assert letter_suffix == "G", f"suffix expected G, got {letter_suffix} conf={conf_s}"

    def test_chord_tone_gate_rejects_non_triad_bass(self) -> None:
        """Optional chord-tone filter: D is not a C major triad tone."""
        from titan_chordpro.engines.chord.bass_chroma import filter_bass_to_chord_tones

        assert filter_bass_to_chord_tones("D", chord_symbol="C") is None
        assert filter_bass_to_chord_tones("E", chord_symbol="C") == "E"
        assert filter_bass_to_chord_tones("G", chord_symbol="C") == "G"
        assert filter_bass_to_chord_tones("C", chord_symbol="C") == "C"
        assert filter_bass_to_chord_tones("E", chord_symbol="Am") == "E"
        assert filter_bass_to_chord_tones("B", chord_symbol="G") == "B"


class TestBassEmissionThresholds:
    """H2: duration-scaled conf / vote floors suppress false short slashes."""

    def test_short_interval_stricter_than_long(self) -> None:
        from titan_chordpro.engines.chord.bass_chroma import bass_emission_thresholds

        short_conf, short_vote = bass_emission_thresholds(0.5)
        mid_conf, mid_vote = bass_emission_thresholds(1.5)
        long_conf, long_vote = bass_emission_thresholds(4.0)
        assert short_conf > long_conf
        assert mid_conf > long_conf
        assert short_vote >= mid_vote >= long_vote
        # Mid-length pads (common false-inversion window) still need high conf.
        assert mid_conf >= 0.65
        assert mid_vote >= 0.55

    def test_resolve_rejects_mean_vote_disagreement(self) -> None:
        """Slash emission requires mean argmax to agree with majority vote."""
        from titan_chordpro.engines.chord.bass_chroma import resolve_bass_pc

        # Mean energy peaks at A (9); frames majority-vote to E (4).
        weights = np.zeros(12, dtype=np.float64)
        weights[9] = 1.0  # A
        weights[4] = 0.7  # E
        weights[0] = 0.2
        frame_winners = np.array([4, 4, 4, 4, 9, 9], dtype=np.int64)
        pc, conf = resolve_bass_pc(weights, frame_winners, duration=3.0)
        assert pc is None
        assert conf > 0.0  # confidence still reported for diagnostics

    def test_resolve_rejects_low_vote_share_on_mid_interval(self) -> None:
        """Weak majority on mid-duration slice → no bass letter (false slash guard)."""
        from titan_chordpro.engines.chord.bass_chroma import resolve_bass_pc

        weights = np.zeros(12, dtype=np.float64)
        weights[11] = 0.70  # B
        weights[2] = 0.48  # D residual
        weights[0] = 0.22
        # Agree on B but only ~50% of frames — below mid vote floor.
        frame_winners = np.array([11, 11, 11, 2, 2, 0], dtype=np.int64)
        pc, conf = resolve_bass_pc(weights, frame_winners, duration=1.8)
        assert conf >= 0.5  # raw peakiness ok
        assert pc is None

    def test_resolve_accepts_decisive_long_interval(self) -> None:
        from titan_chordpro.engines.chord.bass_chroma import (
            pitch_class_letter,
            resolve_bass_pc,
        )

        weights = np.zeros(12, dtype=np.float64)
        weights[4] = 0.90  # E under C → true inversion
        weights[0] = 0.25
        weights[2] = 0.20
        frame_winners = np.array([4] * 8 + [0, 2], dtype=np.int64)
        pc, conf = resolve_bass_pc(weights, frame_winners, duration=3.5)
        assert pc is not None
        assert pitch_class_letter(pc) == "E"
        assert conf >= 0.5

    def test_resolve_rejects_mid_conf_below_raised_floor(self) -> None:
        """conf in (0.5, mid_floor) on a mid-length slice must not emit."""
        from titan_chordpro.engines.chord.bass_chroma import resolve_bass_pc

        # max=0.55, median of zeros+peak ≈ 0 → conf ≈ 1.0 if only one peak.
        # Need conf just above 0.5 but below mid floor (~0.70): peak only slightly
        # above median of a flatter distribution.
        weights = np.full(12, 0.40, dtype=np.float64)
        weights[2] = 0.85  # D — conf = (0.85-0.40)/0.85 ≈ 0.529
        frame_winners = np.array([2] * 10, dtype=np.int64)  # decisive vote
        pc, conf = resolve_bass_pc(weights, frame_winners, duration=1.3)
        assert 0.5 <= conf < 0.70
        assert pc is None

    def test_short_pure_tone_still_emits_when_decisive(self, tmp_path: Path) -> None:
        """Raised short floor must not kill clean short bass (true reseg slice)."""
        from titan_chordpro.engines.chord.bass_chroma import extract_bass_note

        audio = _synthesize_tone(freq=110.0, duration=0.8)
        p = tmp_path / "short_a.wav"
        sf.write(str(p), audio, SR)
        letter, conf = extract_bass_note(p, start=0.05, end=0.75)
        assert letter == "A"
        assert conf >= 0.70

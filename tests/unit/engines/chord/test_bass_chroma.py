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

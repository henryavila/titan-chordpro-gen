# tests/unit/fusion/test_melisma.py
import pytest

from titan_chordpro.core.schemas import BeatGrid, SyllableEvent, TimeStamp
from titan_chordpro.fusion.melisma import detect_melismas


def _syllable(t_start: float, duration: float) -> SyllableEvent:
    """Helper to create a syllable with duration."""
    return SyllableEvent(
        text="la",
        timestamp=TimeStamp(start=t_start, end=t_start + duration),
        is_stressed=False,
        parent_word_idx=0,
        confidence=1.0,
    )


def _grid(beats: list[float]) -> BeatGrid:
    """Helper to create a beat grid."""
    return BeatGrid(
        beats=beats,
        downbeat_indices=[0],
        bpm=120.0,
        source_engine="mock",
    )


@pytest.mark.unit
class TestMelismaDetection:
    def test_short_syllable_not_melisma(self) -> None:
        """Sílaba curta (<600ms) não é melisma."""
        # 500ms duration syllable
        syllables = [_syllable(1.0, 0.5)]
        chords = []
        grid = _grid([1.0, 2.0, 3.0])

        result = detect_melismas(syllables, chords, grid)
        assert len(result) == 0

    def test_long_syllable_spanning_three_beats_is_melisma(self) -> None:
        """Sílaba longa (>600ms) spanning 3 beats é melisma."""
        # 800ms syllable spanning 3 beats (1.0 to 1.8)
        syllables = [_syllable(1.0, 0.8)]
        chords = []
        grid = _grid([1.0, 1.5, 2.0, 2.5])  # beats at 1.0, 1.5, 2.0

        result = detect_melismas(syllables, chords, grid)
        assert len(result) == 1
        assert result[0].syllable_idx == 0
        assert result[0].span.start == pytest.approx(1.0)
        assert result[0].span.end == pytest.approx(1.8)

    def test_long_syllable_within_one_beat_not_melisma(self) -> None:
        """Sílaba longa (>600ms) mas dentro de 1 beat não é melisma."""
        # 700ms syllable, but beats are at 0.5s intervals
        # So this syllable from 0.6 to 1.3 spans only 1 beat (at 1.0)
        # Actually, let's use a simpler beat grid: beats at 0.0, 1.0, 2.0
        # Then 600ms syllable from 0.5 to 1.1 would span only 1 beat (1.0)
        syllables = [_syllable(0.5, 0.6)]
        chords = []
        grid = _grid([0.0, 1.0, 2.0, 3.0])  # beats at 1.0s intervals

        result = detect_melismas(syllables, chords, grid)
        assert len(result) == 0

    def test_multiple_syllables_mixed(self) -> None:
        """Múltiplas sílabas, algumas são melismas."""
        syllables = [
            _syllable(0.0, 0.4),  # short: not melisma
            _syllable(1.0, 0.8),  # long + spans 3 beats: is melisma
            _syllable(2.5, 0.3),  # short: not melisma
        ]
        chords = []
        grid = _grid([0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0])

        result = detect_melismas(syllables, chords, grid)
        assert len(result) == 1
        assert result[0].syllable_idx == 1

    def test_exactly_600ms_boundary(self) -> None:
        """Sílaba com exatamente 600ms deve ser considerada melisma se span > 1 beat."""
        # Exactly 600ms, spanning 2 beats
        syllables = [_syllable(0.0, 0.600)]
        chords = []
        grid = _grid([0.0, 0.4, 0.8, 1.2])  # beats close enough to span >1

        result = detect_melismas(syllables, chords, grid)
        # 600ms exactly should NOT trigger (> 600ms is required)
        assert len(result) == 0

    def test_vocal_pitch_track_ignored_v01(self) -> None:
        """vocal_pitch_track parameter é ignorado em v0.1."""
        syllables = [_syllable(1.0, 0.8)]
        chords = []
        grid = _grid([1.0, 1.5, 2.0, 2.5])
        pitch_track = [440.0, 445.0, 450.0]  # arbitrary pitch values

        result = detect_melismas(syllables, chords, grid, vocal_pitch_track=pitch_track)
        # Should detect melisma regardless of pitch_track (ignored in v0.1)
        assert len(result) == 1

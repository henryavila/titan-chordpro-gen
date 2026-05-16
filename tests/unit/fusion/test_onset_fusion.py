# tests/unit/fusion/test_onset_fusion.py
import pytest

from titan_chordpro.core.schemas import BeatGrid, ChordEvent, TimeStamp
from titan_chordpro.fusion.onset_fusion import fuse_onsets_v01


def _chord(t_start: float, t_end: float = 4.0) -> ChordEvent:
    return ChordEvent(
        symbol="C",
        timestamp=TimeStamp(start=t_start, end=t_end),
        source_engine="mock",
    )


def _grid(beats: list[float]) -> BeatGrid:
    return BeatGrid(
        beats=beats,
        downbeat_indices=[0],
        bpm=120.0,
        source_engine="mock",
    )


@pytest.mark.unit
class TestOnsetFusionV01:
    def test_chord_aligned_to_beat(self) -> None:
        """Chord alinhado ao beat retorna timestamp do beat."""
        chord = _chord(1.04)  # 40ms past beat at 1.0
        grid = _grid([0.5, 1.0, 1.5, 2.0])
        result = fuse_onsets_v01(chord, grid)
        # Should snap to 1.0 beat
        assert result == pytest.approx(1.0)

    def test_chord_snapped_to_8th_note(self) -> None:
        """Chord próximo a 8th-note retorna timestamp da 8th-note."""
        chord = _chord(1.28)  # near 8th-note midpoint 1.25 (between 1.0 and 1.5)
        grid = _grid([0.5, 1.0, 1.5, 2.0])
        result = fuse_onsets_v01(chord, grid)
        # Should snap to 1.25 (8th-note)
        assert result == pytest.approx(1.25)

    def test_chord_unsnapped_returns_original(self) -> None:
        """Chord longe de qualquer grid retorna timestamp original."""
        chord = _chord(1.41)  # 150ms+ past both 8th at 1.25 and beat at 1.5
        grid = _grid([0.5, 1.0, 1.5, 2.0])
        result = fuse_onsets_v01(chord, grid)
        # Should remain unsnapped
        assert result == pytest.approx(1.41)

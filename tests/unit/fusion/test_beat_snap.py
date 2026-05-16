# tests/unit/fusion/test_beat_snap.py
import pytest

from titan_chordpro.core.schemas import BeatGrid, ChordEvent, TimeStamp
from titan_chordpro.fusion.beat_snap import (
    SNAP_TO_8TH_TOLERANCE,
    SNAP_TO_BEAT_TOLERANCE,
    snap_chord_to_grid,
)


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
class TestBeatSnap:
    def test_constants_match_spec(self) -> None:
        assert SNAP_TO_BEAT_TOLERANCE == 0.070
        assert SNAP_TO_8TH_TOLERANCE == 0.150

    def test_snap_to_nearest_beat(self) -> None:
        chord = _chord(1.04)  # 40ms past beat at 1.0
        grid = _grid([0.5, 1.0, 1.5, 2.0])
        snapped, level = snap_chord_to_grid(chord, grid)
        assert level == "beat"
        assert snapped.timestamp.start == pytest.approx(1.0)

    def test_no_snap_too_far(self) -> None:
        chord = _chord(1.41)  # 150ms+ past both 8th at 1.25 and beat at 1.5
        grid = _grid([0.5, 1.0, 1.5, 2.0])
        snapped, level = snap_chord_to_grid(chord, grid)
        assert level == "unsnapped"
        assert snapped.timestamp.start == pytest.approx(1.41)

    def test_snap_to_8th_between_beats(self) -> None:
        chord = _chord(1.28)  # near 8th-note midpoint 1.25 (between 1.0 and 1.5)
        grid = _grid([0.5, 1.0, 1.5, 2.0])
        snapped, level = snap_chord_to_grid(chord, grid)
        assert level == "8th"
        assert snapped.timestamp.start == pytest.approx(1.25)

    def test_beat_priority_over_8th(self) -> None:
        chord = _chord(1.05)  # closer to beat 1.0 than to 8th 1.25
        grid = _grid([0.5, 1.0, 1.5, 2.0])
        snapped, level = snap_chord_to_grid(chord, grid)
        assert level == "beat"

    def test_empty_grid_unsnapped(self) -> None:
        chord = _chord(1.0)
        # single-beat grid where chord is 500ms away → unsnapped
        grid = BeatGrid(
            beats=[0.5],
            downbeat_indices=[0],
            bpm=120.0,
            source_engine="mock",
        )
        snapped, level = snap_chord_to_grid(chord, grid)
        # 0.5s vs 1.0s = 500ms diff → unsnapped
        assert level == "unsnapped"

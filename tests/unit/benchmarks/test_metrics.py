"""Tests for benchmarks.metrics."""

from __future__ import annotations

import pytest

pytest.importorskip("mir_eval")


class TestToMirEvalChord:
    @pytest.mark.parametrize(
        "titan,expected",
        [
            ("C", "C:maj"),
            ("G", "G:maj"),
            ("Am", "A:min"),
            ("Gm", "G:min"),
            ("Cm7", "C:min7"),
            ("Cmaj7", "C:maj7"),
            ("F#", "F#:maj"),
            ("Bbm", "Bb:min"),
            ("F/A", "F:maj/A"),
            ("Gm/Bb", "G:min/Bb"),
            ("N", "N"),
        ],
    )
    def test_to_mir_eval_chord(self, titan: str, expected: str) -> None:
        from benchmarks.metrics import to_mir_eval_chord

        assert to_mir_eval_chord(titan) == expected


class TestComputeWcsrMajmin:
    def test_perfect_match(self) -> None:
        from benchmarks.metrics import compute_wcsr_majmin

        intervals = [(0.0, 1.0), (1.0, 2.0)]
        ref = ["C:maj", "G:maj"]
        score = compute_wcsr_majmin(intervals, ref, intervals, ref)
        assert score == pytest.approx(1.0)

    def test_total_mismatch(self) -> None:
        from benchmarks.metrics import compute_wcsr_majmin

        intervals = [(0.0, 1.0), (1.0, 2.0)]
        ref = ["C:maj", "G:maj"]
        est = ["F:maj", "A:min"]
        score = compute_wcsr_majmin(intervals, ref, intervals, est)
        assert score < 0.1


class TestChordEventsToIntervals:
    def test_basic(self) -> None:
        from benchmarks.metrics import chord_events_to_intervals
        from titan_chordpro.core.schemas import ChordEvent, TimeStamp

        evts = [
            ChordEvent(
                symbol="C",
                timestamp=TimeStamp(start=0.0, end=2.0),
                confidence=1.0,
                source_engine="t",
            ),
            ChordEvent(
                symbol="G",
                timestamp=TimeStamp(start=2.0, end=4.0),
                bass_note="B",
                confidence=1.0,
                source_engine="t",
            ),
        ]
        intervals, labels = chord_events_to_intervals(evts)
        assert intervals == [(0.0, 2.0), (2.0, 4.0)]
        assert labels == ["C:maj", "G:maj/B"]

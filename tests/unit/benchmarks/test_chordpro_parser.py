"""Tests for benchmarks.chordpro_parser."""

from __future__ import annotations

import pytest


class TestExtractChordSequence:
    def test_simple_progression(self) -> None:
        from benchmarks.chordpro_parser import extract_chord_sequence

        cp = "[C]Hello [G]world [Am]now [F]end"
        seq = extract_chord_sequence(cp)
        assert seq == ["C", "G", "Am", "F"]

    def test_ignores_directives(self) -> None:
        from benchmarks.chordpro_parser import extract_chord_sequence

        cp = "{t: Title}\n{key: C}\n[C]Hello [G]world"
        seq = extract_chord_sequence(cp)
        assert seq == ["C", "G"]

    def test_handles_slash_chords(self) -> None:
        from benchmarks.chordpro_parser import extract_chord_sequence

        cp = "[F/A]Down [G/B]up [C]home"
        seq = extract_chord_sequence(cp)
        assert seq == ["F/A", "G/B", "C"]

    def test_handles_qualities(self) -> None:
        from benchmarks.chordpro_parser import extract_chord_sequence

        cp = "[Cmaj7]hi [Gm7]you [F#dim]end"
        seq = extract_chord_sequence(cp)
        assert seq == ["Cmaj7", "Gm7", "F#dim"]

    def test_empty_input(self) -> None:
        from benchmarks.chordpro_parser import extract_chord_sequence

        assert extract_chord_sequence("") == []

    def test_no_chords(self) -> None:
        from benchmarks.chordpro_parser import extract_chord_sequence

        assert extract_chord_sequence("Just lyrics, no brackets") == []


class TestToIntervalsLabels:
    def test_assigns_equal_intervals(self) -> None:
        from benchmarks.chordpro_parser import to_intervals_labels

        seq = ["C", "G", "Am", "F"]
        intervals, labels = to_intervals_labels(seq, duration=12.0)
        assert labels == ["C", "G", "Am", "F"]
        assert len(intervals) == 4
        assert intervals[0] == pytest.approx((0.0, 3.0))
        assert intervals[1] == pytest.approx((3.0, 6.0))
        assert intervals[3] == pytest.approx((9.0, 12.0))

    def test_empty_sequence(self) -> None:
        from benchmarks.chordpro_parser import to_intervals_labels

        intervals, labels = to_intervals_labels([], duration=10.0)
        assert intervals == []
        assert labels == []

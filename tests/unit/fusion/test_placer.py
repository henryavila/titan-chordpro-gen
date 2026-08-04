# tests/unit/fusion/test_placer.py
"""Tests for placer (5-strategy hierarchical chord placement).

Covers each strategy exactly + orphan flow + helper unit tests:
- melisma_start: chord falls inside a detected melisma span
- stressed_syllable: stressed syllable within ±150ms
- any_syllable: closest syllable within ±300ms
- before_word: closest word within ±500ms (no syllable in window)
- orphan: nothing in any window → returned as leftover
"""

import pytest

from titan_chordpro.core.schemas import (
    BeatGrid,
    ChordEvent,
    ChordMarker,
    SyllableEvent,
    TimeStamp,
    WordEvent,
)
from titan_chordpro.fusion.melisma import Melisma
from titan_chordpro.fusion.placer import (
    _aggregate_confidence,
    _build_word_char_positions,
    _char_pos_of_syllable,
    _closest_word,
    _destack_markers,
    _find_any_syllable_within,
    _find_melisma_at,
    _find_stressed_syllable_within,
    place_chords_in_line,
)


def _word(text: str, start: float, end: float, conf: float = 1.0) -> WordEvent:
    return WordEvent(
        text=text,
        timestamp=TimeStamp(start=start, end=end),
        confidence=conf,
        source_engine="mock",
    )


def _syl(
    text: str,
    start: float,
    end: float,
    parent: int = 0,
    stressed: bool = False,
) -> SyllableEvent:
    return SyllableEvent(
        text=text,
        timestamp=TimeStamp(start=start, end=end),
        is_stressed=stressed,
        parent_word_idx=parent,
    )


def _chord(symbol: str, start: float, conf: float = 1.0) -> ChordEvent:
    return ChordEvent(
        symbol=symbol,
        timestamp=TimeStamp(start=start, end=start + 0.5),
        confidence=conf,
        source_engine="mock",
    )


def _trivial_beats(t: float) -> BeatGrid:
    """Beat grid with a single beat exactly at t (so snap is a no-op for t-aligned chords)."""
    return BeatGrid(
        beats=[t],
        downbeat_indices=[0],
        bpm=120.0,
        meter=(4, 4),
        source_engine="mock",
    )


# ───────────────────── Helper unit tests ─────────────────────


@pytest.mark.unit
class TestFindMelismaAt:
    def test_match_inside_span(self) -> None:
        m = Melisma(syllable_idx=0, span=TimeStamp(start=1.0, end=2.0))
        assert _find_melisma_at([m], 1.5) is m

    def test_no_match_outside_span(self) -> None:
        m = Melisma(syllable_idx=0, span=TimeStamp(start=1.0, end=2.0))
        assert _find_melisma_at([m], 3.0) is None

    def test_boundary_inclusive(self) -> None:
        m = Melisma(syllable_idx=0, span=TimeStamp(start=1.0, end=2.0))
        assert _find_melisma_at([m], 1.0) is m
        assert _find_melisma_at([m], 2.0) is m

    def test_empty_list(self) -> None:
        assert _find_melisma_at([], 1.0) is None


@pytest.mark.unit
class TestFindStressedSyllableWithin:
    def test_picks_stressed_in_window(self) -> None:
        s = [
            _syl("a", 0.0, 0.2, stressed=False),
            _syl("mi", 0.2, 0.4, stressed=True),
            _syl("go", 0.4, 0.6, stressed=False),
        ]
        # t_anchor=0.25, tol=0.15 → window [0.10, 0.40]. 'mi' starts at 0.20 → matches.
        assert _find_stressed_syllable_within(s, 0.25, 0.15) is s[1]

    def test_returns_none_when_no_stressed_in_window(self) -> None:
        s = [_syl("a", 0.0, 0.2, stressed=True)]
        # t_anchor far away
        assert _find_stressed_syllable_within(s, 5.0, 0.15) is None

    def test_ignores_unstressed_even_when_closer(self) -> None:
        s = [
            _syl("a", 0.28, 0.32, stressed=False),  # very close, but unstressed
            _syl("b", 0.50, 0.60, stressed=True),
        ]
        # t_anchor=0.30, tol=0.15 → window [0.15, 0.45]. 'b' at 0.50 is OUT of window.
        # 'a' is unstressed → ignored. Result: None.
        assert _find_stressed_syllable_within(s, 0.30, 0.15) is None


@pytest.mark.unit
class TestFindAnySyllableWithin:
    def test_picks_closest_by_start(self) -> None:
        s = [_syl("a", 0.0, 0.2), _syl("b", 0.5, 0.7)]
        assert _find_any_syllable_within(s, 0.55, 0.3) is s[1]

    def test_returns_none_outside_tolerance(self) -> None:
        s = [_syl("a", 0.0, 0.2)]
        assert _find_any_syllable_within(s, 1.0, 0.3) is None

    def test_includes_exact_tolerance_boundary(self) -> None:
        # dist == tol must match (inclusive <=), not only strict <
        s = [_syl("a", 0.0, 0.2)]
        assert _find_any_syllable_within(s, 0.3, 0.3) is s[0]

    def test_empty_list(self) -> None:
        assert _find_any_syllable_within([], 1.0, 0.3) is None


@pytest.mark.unit
class TestClosestWord:
    def test_picks_closest_by_start_time(self) -> None:
        words = [_word("a", 0.0, 0.5), _word("b", 1.0, 1.5)]
        assert _closest_word(words, 0.9) == 1

    def test_empty_returns_none(self) -> None:
        assert _closest_word([], 1.0) is None

    def test_single_word(self) -> None:
        assert _closest_word([_word("a", 0, 1)], 100.0) == 0


@pytest.mark.unit
class TestBuildWordCharPositions:
    def test_simple_two_words(self) -> None:
        words = [_word("hello", 0, 1), _word("world", 1, 2)]
        positions = _build_word_char_positions("hello world", words)
        assert positions[0] == 0
        assert positions[1] == 6

    def test_case_insensitive(self) -> None:
        words = [_word("hello", 0, 1)]
        positions = _build_word_char_positions("Hello", words)
        assert positions[0] == 0

    def test_missing_word_uses_cursor_fallback(self) -> None:
        words = [_word("xyz", 0, 1)]
        positions = _build_word_char_positions("abc", words)
        # Not found; falls back to cursor=0
        assert positions[0] == 0

    def test_repeated_word_picks_sequential_occurrence(self) -> None:
        words = [_word("la", 0, 1), _word("la", 1, 2)]
        positions = _build_word_char_positions("la la", words)
        assert positions[0] == 0
        assert positions[1] == 3


@pytest.mark.unit
class TestCharPosOfSyllable:
    def test_first_syllable_at_word_start(self) -> None:
        words = [_word("amigo", 0.0, 0.6)]
        syllables = [
            _syl("a", 0.0, 0.2, parent=0),
            _syl("mi", 0.2, 0.4, parent=0),
            _syl("go", 0.4, 0.6, parent=0),
        ]
        positions = _build_word_char_positions("amigo", words)
        assert _char_pos_of_syllable("amigo", syllables[0], syllables, words, positions) == 0

    def test_middle_syllable_linear_distribution(self) -> None:
        # word_len=5, n_syllables=3 → syl[1] offset = (1*5)//3 = 1
        words = [_word("amigo", 0.0, 0.6)]
        syllables = [
            _syl("a", 0.0, 0.2, parent=0),
            _syl("mi", 0.2, 0.4, parent=0),
            _syl("go", 0.4, 0.6, parent=0),
        ]
        positions = _build_word_char_positions("amigo", words)
        assert _char_pos_of_syllable("amigo", syllables[1], syllables, words, positions) == 1

    def test_syllable_in_second_word(self) -> None:
        words = [_word("hello", 0.0, 0.5), _word("world", 0.5, 1.0)]
        syllables = [
            _syl("hel", 0.0, 0.3, parent=0),
            _syl("lo", 0.3, 0.5, parent=0),
            _syl("world", 0.5, 1.0, parent=1),
        ]
        positions = _build_word_char_positions("hello world", words)
        assert (
            _char_pos_of_syllable(
                "hello world",
                syllables[2],
                syllables,
                words,
                positions,
            )
            == 6
        )


@pytest.mark.unit
class TestAggregateConfidence:
    def test_average_of_words_and_chords(self) -> None:
        words = [_word("a", 0, 0.5, conf=0.8)]
        chords = [_chord("C", 0, conf=0.6)]
        assert _aggregate_confidence(words, chords) == pytest.approx(0.7)

    def test_empty_inputs_returns_one(self) -> None:
        assert _aggregate_confidence([], []) == 1.0


# ───────────────────── End-to-end placer tests ─────────────────────


@pytest.mark.unit
class TestPlaceChordsInLineStrategies:
    def test_strategy_1_melisma_start_wins_over_stressed(self) -> None:
        # Melisma covers the chord position even though there's a stressed syllable
        words = [_word("oh", 0.0, 1.0)]
        syllables = [_syl("oh", 0.0, 1.0, parent=0, stressed=True)]
        chord = _chord("C", 0.5)
        melismas = [Melisma(syllable_idx=0, span=TimeStamp(start=0.0, end=1.0))]
        line, orphans = place_chords_in_line(
            line_text="oh",
            words=words,
            syllables=syllables,
            chords_in_line=[chord],
            beat_grid=_trivial_beats(0.5),
            melismas=melismas,
            language="en",
        )
        assert len(line.chord_markers) == 1
        assert line.chord_markers[0].placement_strategy == "melisma_start"
        assert orphans == []

    def test_strategy_2_stressed_syllable(self) -> None:
        # Chord at 0.2 hits stressed syllable "mi" (0.2-0.4) exactly.
        words = [_word("amigo", 0.0, 0.6)]
        syllables = [
            _syl("a", 0.0, 0.2, parent=0, stressed=False),
            _syl("mi", 0.2, 0.4, parent=0, stressed=True),
            _syl("go", 0.4, 0.6, parent=0, stressed=False),
        ]
        chord = _chord("C", 0.2)
        line, orphans = place_chords_in_line(
            line_text="amigo",
            words=words,
            syllables=syllables,
            chords_in_line=[chord],
            beat_grid=_trivial_beats(0.2),
            melismas=[],
            language="pt",
        )
        assert len(line.chord_markers) == 1
        assert line.chord_markers[0].placement_strategy == "stressed_syllable"
        assert orphans == []

    def test_strategy_3_any_syllable_when_no_stressed_in_window(self) -> None:
        # All syllables unstressed → any_syllable strategy
        words = [_word("foo", 0.0, 0.6)]
        syllables = [
            _syl("foo", 0.0, 0.6, parent=0, stressed=False),
        ]
        chord = _chord("C", 0.1)  # within 300ms of 'foo' start
        line, orphans = place_chords_in_line(
            line_text="foo",
            words=words,
            syllables=syllables,
            chords_in_line=[chord],
            beat_grid=_trivial_beats(0.1),
            melismas=[],
            language="en",
        )
        assert len(line.chord_markers) == 1
        assert line.chord_markers[0].placement_strategy == "any_syllable"

    def test_strategy_4_before_word_when_no_close_syllable(self) -> None:
        # Word at 1.0, chord at 0.55 (450ms before) — outside ±300ms syllable
        # window but inside ±500ms before-word window.
        words = [_word("word", 1.0, 1.5)]
        syllables = [_syl("word", 1.0, 1.5, parent=0, stressed=False)]
        chord = _chord("C", 0.55)
        line, orphans = place_chords_in_line(
            line_text="word",
            words=words,
            syllables=syllables,
            chords_in_line=[chord],
            beat_grid=_trivial_beats(0.55),
            melismas=[],
            language="en",
        )
        assert len(line.chord_markers) == 1
        assert line.chord_markers[0].placement_strategy == "before_word"

    def test_strategy_5_orphan_when_nothing_close(self) -> None:
        words = [_word("word", 1.0, 1.5)]
        syllables = [_syl("word", 1.0, 1.5, parent=0, stressed=False)]
        # Chord very far from any word/syllable
        chord = _chord("C", 5.0)
        line, orphans = place_chords_in_line(
            line_text="word",
            words=words,
            syllables=syllables,
            chords_in_line=[chord],
            beat_grid=_trivial_beats(5.0),
            melismas=[],
            language="en",
        )
        assert line.chord_markers == []
        assert len(orphans) == 1
        assert orphans[0].symbol == "C"


@pytest.mark.unit
class TestPlaceChordsInLineMulti:
    def test_multiple_chords_mix_strategies(self) -> None:
        words = [_word("amigo", 0.0, 0.6)]
        syllables = [
            _syl("a", 0.0, 0.2, parent=0, stressed=False),
            _syl("mi", 0.2, 0.4, parent=0, stressed=True),
            _syl("go", 0.4, 0.6, parent=0, stressed=False),
        ]
        chords = [
            _chord("C", 0.2),  # hits stressed 'mi' → stressed_syllable
            _chord("F", 5.0),  # far away → orphan
        ]
        beats = BeatGrid(
            beats=[0.2, 5.0],
            downbeat_indices=[0],
            bpm=120.0,
            meter=(4, 4),
            source_engine="mock",
        )
        line, orphans = place_chords_in_line(
            "amigo",
            words,
            syllables,
            chords,
            beats,
            [],
            "pt",
        )
        assert len(line.chord_markers) == 1
        assert line.chord_markers[0].chord.symbol == "C"
        assert len(orphans) == 1
        assert orphans[0].symbol == "F"

    def test_markers_sorted_by_char_position(self) -> None:
        # Two chords landing on different syllables — markers must come out sorted
        words = [_word("amigo", 0.0, 0.6)]
        syllables = [
            _syl("a", 0.0, 0.2, parent=0, stressed=True),
            _syl("mi", 0.2, 0.4, parent=0, stressed=False),
            _syl("go", 0.4, 0.6, parent=0, stressed=True),
        ]
        chords = [
            _chord("G", 0.4),  # hits 'go' (later in line)
            _chord("C", 0.0),  # hits 'a' (earlier in line)
        ]
        beats = BeatGrid(
            beats=[0.0, 0.4],
            downbeat_indices=[0],
            bpm=120.0,
            meter=(4, 4),
            source_engine="mock",
        )
        line, _ = place_chords_in_line(
            "amigo",
            words,
            syllables,
            chords,
            beats,
            [],
            "pt",
        )
        positions = [m.char_position for m in line.chord_markers]
        assert positions == sorted(positions)

    def test_empty_chord_list_returns_line_with_no_markers(self) -> None:
        words = [_word("hi", 0.0, 0.5)]
        syllables = [_syl("hi", 0.0, 0.5, parent=0)]
        line, orphans = place_chords_in_line(
            "hi",
            words,
            syllables,
            [],
            _trivial_beats(0.0),
            [],
            "en",
        )
        assert line.chord_markers == []
        assert orphans == []
        assert line.text == "hi"

    def test_line_carries_traceability_fields(self) -> None:
        words = [_word("hi", 0.0, 0.5)]
        syllables = [_syl("hi", 0.0, 0.5, parent=0)]
        line, _ = place_chords_in_line(
            "hi",
            words,
            syllables,
            [],
            _trivial_beats(0.0),
            [],
            "en",
        )
        assert line.word_alignments == words
        assert line.syllable_alignments == syllables


@pytest.mark.unit
class TestDestackMarkers:
    """Phase C T70: no two chord markers share a char_position."""

    def test_destack_spreads_same_position_forward(self) -> None:
        markers = [
            ChordMarker(
                chord=_chord("F", 1.0),
                char_position=0,
                placement_strategy="before_word",
            ),
            ChordMarker(
                chord=_chord("G", 1.1),
                char_position=0,
                placement_strategy="before_word",
            ),
        ]
        kept, orphans = _destack_markers(markers, "meus olhos")
        assert orphans == []
        positions = sorted(m.char_position for m in kept)
        assert positions == [0, 1]
        assert {m.chord.symbol for m in kept} == {"F", "G"}

    def test_destack_orphans_when_line_exhausted(self) -> None:
        # line_text length 1 → only positions 0 and 1 available (max_pos = 1).
        markers = [
            ChordMarker(
                chord=_chord("C", 0.0),
                char_position=0,
                placement_strategy="before_word",
            ),
            ChordMarker(
                chord=_chord("F", 0.1),
                char_position=0,
                placement_strategy="before_word",
            ),
            ChordMarker(
                chord=_chord("G", 0.2),
                char_position=0,
                placement_strategy="before_word",
            ),
        ]
        kept, orphans = _destack_markers(markers, "a")
        assert len(kept) == 2  # positions 0 and 1
        assert len(orphans) == 1
        assert orphans[0].symbol == "G"

    def test_place_chords_destacks_stacked_onsets(self) -> None:
        # Two chords both snap onto the single word start → must not stack.
        words = [_word("meus", 1.0, 1.4)]
        syllables = [_syl("meus", 1.0, 1.4, parent=0, stressed=True)]
        chords = [_chord("F", 0.95), _chord("G", 1.05)]
        beats = BeatGrid(
            beats=[0.95, 1.05],
            downbeat_indices=[0],
            bpm=120.0,
            meter=(4, 4),
            source_engine="mock",
        )
        line, orphans = place_chords_in_line(
            "meus",
            words,
            syllables,
            chords,
            beats,
            [],
            "pt",
        )
        positions = [m.char_position for m in line.chord_markers]
        assert len(positions) == len(set(positions)), "stacked markers after destack"
        assert len(line.chord_markers) + len(orphans) == 2


# ───────────────────── RC5: span distance + beat-aware windows ─────────────────────


@pytest.mark.unit
class TestEventTemporalDistance:
    """Distance to event span (0 inside), not only to start time."""

    def test_inside_span_is_zero(self) -> None:
        from titan_chordpro.fusion.placer import _event_temporal_distance

        assert _event_temporal_distance(1.0, 2.0, 1.5) == 0.0

    def test_before_start(self) -> None:
        from titan_chordpro.fusion.placer import _event_temporal_distance

        assert _event_temporal_distance(1.0, 2.0, 0.7) == pytest.approx(0.3)

    def test_after_end(self) -> None:
        from titan_chordpro.fusion.placer import _event_temporal_distance

        assert _event_temporal_distance(1.0, 2.0, 2.4) == pytest.approx(0.4)

    def test_on_boundaries_zero(self) -> None:
        from titan_chordpro.fusion.placer import _event_temporal_distance

        assert _event_temporal_distance(1.0, 2.0, 1.0) == 0.0
        assert _event_temporal_distance(1.0, 2.0, 2.0) == 0.0


@pytest.mark.unit
class TestBeatAwareTolerances:
    def test_slow_tempo_widens_windows(self) -> None:
        from titan_chordpro.fusion.placer import _placement_tolerances

        # ~70 BPM → beat period ≈ 0.86s
        beats = BeatGrid(
            beats=[0.0, 0.86, 1.72, 2.58],
            downbeat_indices=[0],
            bpm=70.0,
            meter=(4, 4),
            source_engine="mock",
        )
        stressed, any_syl, before_word = _placement_tolerances(beats)
        assert any_syl > 0.300
        assert before_word >= 0.500
        assert stressed >= 0.150

    def test_fast_tempo_keeps_floor(self) -> None:
        from titan_chordpro.fusion.placer import (
            ANY_SYLLABLE_TOL_S,
            BEFORE_WORD_TOL_S,
            STRESSED_TOL_S,
            _placement_tolerances,
        )

        # 200 BPM → beat 0.3s; floors dominate
        beats = BeatGrid(
            beats=[0.0, 0.3, 0.6],
            downbeat_indices=[0],
            bpm=200.0,
            meter=(4, 4),
            source_engine="mock",
        )
        stressed, any_syl, before_word = _placement_tolerances(beats)
        assert stressed == pytest.approx(STRESSED_TOL_S)
        assert any_syl == pytest.approx(ANY_SYLLABLE_TOL_S)
        assert before_word == pytest.approx(BEFORE_WORD_TOL_S)


@pytest.mark.unit
class TestSpanBasedAttachment:
    """Mid-word / post-word chords must attach when near the word span."""

    def test_chord_inside_long_word_span_far_from_start(self) -> None:
        """Chord mid-hold inside a multi-second word must not orphan.

        Classic failure: word [0.0, 2.0], syllable starts at 0.0 only, chord at
        1.6s → old start-only distance (1.6s) exceeded ±500ms before_word.
        """
        words = [_word("descanso", 0.0, 2.0)]
        syllables = [
            _syl("des", 0.0, 0.4, parent=0, stressed=True),
            _syl("can", 0.4, 0.8, parent=0, stressed=False),
            _syl("so", 0.8, 2.0, parent=0, stressed=False),
        ]
        # Chord lands on the long final syllable well after its *start*, but
        # inside its span (and the word span).
        chord = _chord("C", 1.5)
        line, orphans = place_chords_in_line(
            "descanso",
            words,
            syllables,
            [chord],
            _trivial_beats(1.5),
            [],
            "pt",
        )
        assert orphans == []
        assert len(line.chord_markers) == 1
        assert line.chord_markers[0].chord.symbol == "C"

    def test_chord_just_after_word_end_attaches_to_nearest(self) -> None:
        """Inter-word gap: chord 40ms after word end must attach, not orphan.

        Mirrors worship charts where a change lands slightly after the lyric
        alignment end of the previous word and before the next word start.
        """
        words = [
            _word("amor", 0.0, 0.66),
            _word("derramado", 1.2, 2.0),
        ]
        syllables = [
            _syl("a", 0.0, 0.33, parent=0, stressed=False),
            _syl("mor", 0.33, 0.66, parent=0, stressed=True),
            _syl("der", 1.2, 1.4, parent=1, stressed=False),
            _syl("ra", 1.4, 1.6, parent=1, stressed=False),
            _syl("ma", 1.6, 1.8, parent=1, stressed=True),
            _syl("do", 1.8, 2.0, parent=1, stressed=False),
        ]
        # 40ms after "amor" ends; old start-distance to "amor" = 0.70s > 500ms,
        # start-distance to "derramado" = 0.50s fails strict < 0.5.
        chord = _chord("G", 0.70)
        line, orphans = place_chords_in_line(
            "amor derramado",
            words,
            syllables,
            [chord],
            _trivial_beats(0.70),
            [],
            "pt",
        )
        assert orphans == []
        assert len(line.chord_markers) == 1

    def test_chord_near_next_word_at_slow_tempo_uses_beat_window(self) -> None:
        """At ~70 BPM, a chord ~0.65s before the first word still attaches."""
        words = [_word("buscando", 1.0, 1.8)]
        syllables = [
            _syl("bus", 1.0, 1.25, parent=0, stressed=True),
            _syl("can", 1.25, 1.5, parent=0, stressed=False),
            _syl("do", 1.5, 1.8, parent=0, stressed=False),
        ]
        chord = _chord("Am", 0.35)  # 650ms before word start
        beats = BeatGrid(
            beats=[0.0, 0.86, 1.72, 2.58],
            downbeat_indices=[0],
            bpm=70.0,
            meter=(4, 4),
            source_engine="mock",
        )
        line, orphans = place_chords_in_line(
            "buscando",
            words,
            syllables,
            [chord],
            beats,
            [],
            "pt",
        )
        assert orphans == []
        assert len(line.chord_markers) == 1
        assert line.chord_markers[0].placement_strategy in {
            "before_word",
            "any_syllable",
            "stressed_syllable",
        }

    def test_true_far_orphan_still_orphans(self) -> None:
        """Chords seconds away from any lyric must remain orphans."""
        words = [_word("hi", 0.0, 0.4)]
        syllables = [_syl("hi", 0.0, 0.4, parent=0)]
        chord = _chord("C", 5.0)
        line, orphans = place_chords_in_line(
            "hi",
            words,
            syllables,
            [chord],
            _trivial_beats(5.0),
            [],
            "en",
        )
        assert line.chord_markers == []
        assert len(orphans) == 1


@pytest.mark.unit
class TestMelismaDefersToNearerSyllable:
    """With multi-syllable restore, melisma must not steal nearer syllables."""

    def test_nearer_syllable_beats_melisma_span(self) -> None:
        # Long melisma on syllable 0 spanning the whole word; chord is much
        # closer to syllable 2's onset than to syllable 0.
        words = [_word("gloria", 0.0, 2.0)]
        syllables = [
            _syl("glo", 0.0, 0.8, parent=0, stressed=True),
            _syl("ri", 0.8, 1.2, parent=0, stressed=False),
            _syl("a", 1.2, 2.0, parent=0, stressed=False),
        ]
        melismas = [Melisma(syllable_idx=0, span=TimeStamp(start=0.0, end=2.0))]
        chord = _chord("F", 1.25)  # nearest to "a"@1.2
        line, orphans = place_chords_in_line(
            "gloria",
            words,
            syllables,
            [chord],
            _trivial_beats(1.25),
            melismas,
            "pt",
        )
        assert orphans == []
        assert len(line.chord_markers) == 1
        # Must NOT pin to melisma_start (char 0); "a" is last of 3 syls →
        # char offset (2*6)//3 = 4.
        assert line.chord_markers[0].placement_strategy != "melisma_start"
        assert line.chord_markers[0].char_position == 4

    def test_melisma_still_used_when_no_closer_syllable(self) -> None:
        words = [_word("oh", 0.0, 1.5)]
        syllables = [_syl("oh", 0.0, 1.5, parent=0, stressed=True)]
        melismas = [Melisma(syllable_idx=0, span=TimeStamp(start=0.0, end=1.5))]
        chord = _chord("C", 0.7)
        line, orphans = place_chords_in_line(
            "oh",
            words,
            syllables,
            [chord],
            _trivial_beats(0.7),
            melismas,
            "en",
        )
        assert orphans == []
        assert line.chord_markers[0].placement_strategy == "melisma_start"

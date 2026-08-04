"""Tests for orchestrator._place_all_chords placement wiring.

Covers T70 placement blockers:
- Multi-line local reindex of parent_word_idx (global → line-local)
- Melisma syllable_idx remapped to line-local syllables
- Orphan chords materialised as InstrumentalLine siblings
- Inter-line gap chords retained via midpoint-expanded spans
"""

from __future__ import annotations

import pytest

from titan_chordpro.core.schemas import (
    BeatGrid,
    ChordEvent,
    InstrumentalLine,
    LyricLine,
    Section,
    SyllableEvent,
    TimeStamp,
    WordEvent,
)
from titan_chordpro.fusion.melisma import Melisma
from titan_chordpro.orchestrator import _place_all_chords


def _word(text: str, start: float, end: float) -> WordEvent:
    return WordEvent(
        text=text,
        timestamp=TimeStamp(start=start, end=end),
        source_engine="mock",
    )


def _syl(
    text: str,
    start: float,
    end: float,
    parent: int,
    *,
    stressed: bool = True,
) -> SyllableEvent:
    return SyllableEvent(
        text=text,
        timestamp=TimeStamp(start=start, end=end),
        is_stressed=stressed,
        parent_word_idx=parent,
    )


def _chord(symbol: str, start: float, end: float | None = None) -> ChordEvent:
    return ChordEvent(
        symbol=symbol,
        timestamp=TimeStamp(start=start, end=end if end is not None else start + 0.5),
        source_engine="mock",
    )


def _beats(*positions: float) -> BeatGrid:
    return BeatGrid(
        beats=list(positions),
        downbeat_indices=[0],
        bpm=120.0,
        meter=(4, 4),
        source_engine="mock",
    )


@pytest.mark.unit
class TestPlaceAllChordsLocalReindex:
    def test_multiline_chord_lands_on_second_line_second_word(self) -> None:
        """Global parent_word_idx must be reindexed to line-local words.

        Line 1: "hello" (global word 0)
        Line 2: "beautiful world" (global words 1, 2)

        Without reindex, syllable for "world" keeps parent_word_idx=2 which is
        OOB for line-local words → char position falls back to word 0 ("beautiful").
        With reindex, parent becomes local 1 → chord at start of "world".
        """
        w0 = _word("hello", 0.0, 0.5)
        w1 = _word("beautiful", 2.0, 2.6)
        w2 = _word("world", 2.7, 3.2)
        # Same object identities in global list and line.word_alignments
        words = [w0, w1, w2]
        syllables = [
            _syl("hello", 0.0, 0.5, parent=0),
            _syl("beau", 2.0, 2.3, parent=1),
            _syl("ti", 2.3, 2.5, parent=1),
            _syl("ful", 2.5, 2.6, parent=1),
            _syl("world", 2.7, 3.2, parent=2),
        ]
        line1 = LyricLine(text="hello", word_alignments=[w0])
        line2 = LyricLine(text="beautiful world", word_alignments=[w1, w2])
        section = Section(
            type="verse",
            label="Verse 1",
            lines=[line1, line2],
            timestamp=TimeStamp(start=0.0, end=3.5),
        )
        chord = _chord("G", 2.7)  # on "world"
        result = _place_all_chords(
            [section],
            words,
            syllables,
            [chord],
            _beats(0.0, 2.0, 2.7),
            melismas=[],
            language="en",
        )
        lyric_lines = [ln for ln in result[0].lines if isinstance(ln, LyricLine)]
        assert len(lyric_lines) == 2
        markers = lyric_lines[1].chord_markers
        assert len(markers) == 1
        assert markers[0].chord.symbol == "G"
        # "beautiful world" → "world" starts at char 10
        assert markers[0].char_position == 10
        # Must NOT land on "beautiful" (char 0)
        assert markers[0].char_position != 0


@pytest.mark.unit
class TestPlaceAllChordsMelismaRemap:
    def test_global_melisma_syllable_idx_remapped_to_local(self) -> None:
        """Melisma.syllable_idx is global into full syllables; must remap per line.

        Global syllables: [hello@0, oh@1]. Melisma points at global index 1.
        Line 2 only has the local "oh" syllable (local index 0). Without remap,
        placer sees syllable_idx=1 as OOB on a 1-element local list and skips
        melisma_start.
        """
        w0 = _word("hello", 0.0, 0.5)
        w1 = _word("oh", 2.0, 3.0)
        words = [w0, w1]
        syllables = [
            _syl("hello", 0.0, 0.5, parent=0),
            _syl("oh", 2.0, 3.0, parent=1, stressed=True),
        ]
        line1 = LyricLine(text="hello", word_alignments=[w0])
        line2 = LyricLine(text="oh", word_alignments=[w1])
        section = Section(
            type="verse",
            label="Verse 1",
            lines=[line1, line2],
            timestamp=TimeStamp(start=0.0, end=3.5),
        )
        # Melisma targets global syllable index 1 ("oh")
        melismas = [Melisma(syllable_idx=1, span=TimeStamp(start=2.0, end=3.0))]
        chord = _chord("C", 2.5)  # inside melisma span
        result = _place_all_chords(
            [section],
            words,
            syllables,
            [chord],
            _beats(2.0, 2.5),
            melismas=melismas,
            language="en",
        )
        lyric_lines = [ln for ln in result[0].lines if isinstance(ln, LyricLine)]
        assert len(lyric_lines[1].chord_markers) == 1
        assert lyric_lines[1].chord_markers[0].placement_strategy == "melisma_start"
        assert lyric_lines[1].chord_markers[0].chord.symbol == "C"


@pytest.mark.unit
class TestPlaceAllChordsOrphans:
    def test_orphans_become_instrumental_line(self) -> None:
        """Orphans returned by placer must be appended as InstrumentalLine.

        Chord must still fall inside the line time span (else orchestrator
        never sends it to the placer) but outside all placement windows
        (±300ms syllable / ±500ms word-start) so strategy 5 fires.
        """
        # Long word span [0.0, 2.0] so a late chord at 1.6 is in-span but
        # far from syllable/word start at 0.0 → orphan.
        w0 = _word("hi", 0.0, 2.0)
        words = [w0]
        syllables = [_syl("hi", 0.0, 0.4, parent=0)]
        line = LyricLine(text="hi", word_alignments=[w0])
        section = Section(
            type="verse",
            label="Verse 1",
            lines=[line],
            timestamp=TimeStamp(start=0.0, end=10.0),
        )
        orphan_chord = _chord("F", 1.6)
        on_word = _chord("C", 0.0)
        result = _place_all_chords(
            [section],
            words,
            syllables,
            [on_word, orphan_chord],
            _beats(0.0, 1.6),
            melismas=[],
            language="en",
        )
        lines = result[0].lines
        assert any(isinstance(ln, LyricLine) for ln in lines)
        instr = [ln for ln in lines if isinstance(ln, InstrumentalLine)]
        assert len(instr) == 1
        assert {c.symbol for c in instr[0].chords} == {"F"}
        assert instr[0].measures >= 1
        # Orphan instrumental sits after its parent lyric line
        lyric_idx = next(i for i, ln in enumerate(lines) if isinstance(ln, LyricLine))
        instr_idx = next(i for i, ln in enumerate(lines) if isinstance(ln, InstrumentalLine))
        assert instr_idx == lyric_idx + 1


@pytest.mark.unit
class TestPlaceAllChordsMidpointExpansion:
    def test_gap_chord_between_lines_is_not_dropped(self) -> None:
        """Chords in short gaps between phrases must stay (via expanded spans).

        Line1 ends at 1.0, line2 starts at 2.0, chord at 1.3 sits in the gap.
        Without midpoint expansion the chord matches neither line span and vanishes.
        With expansion, mid=1.5 so chord belongs to line1 and is at least retained
        (as before_word or orphan InstrumentalLine).
        """
        w0 = _word("first", 0.0, 1.0)
        w1 = _word("second", 2.0, 2.5)
        words = [w0, w1]
        syllables = [
            _syl("first", 0.0, 1.0, parent=0),
            _syl("second", 2.0, 2.5, parent=1),
        ]
        line1 = LyricLine(text="first", word_alignments=[w0])
        line2 = LyricLine(text="second", word_alignments=[w1])
        section = Section(
            type="verse",
            label="Verse 1",
            lines=[line1, line2],
            timestamp=TimeStamp(start=0.0, end=3.0),
        )
        gap_chord = _chord("Am", 1.3, 1.6)
        result = _place_all_chords(
            [section],
            words,
            syllables,
            [gap_chord],
            _beats(0.0, 1.0, 1.3, 2.0),
            melismas=[],
            language="en",
        )
        all_symbols: list[str] = []
        for ln in result[0].lines:
            if isinstance(ln, LyricLine):
                all_symbols.extend(m.chord.symbol for m in ln.chord_markers)
            elif isinstance(ln, InstrumentalLine):
                all_symbols.extend(c.symbol for c in ln.chords)
        assert "Am" in all_symbols

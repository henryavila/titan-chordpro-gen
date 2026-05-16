# tests/unit/fusion/test_sectioner.py
"""Tests for sectioner (heuristic section inference from word gaps).

Covers:
- Instrumental-only audio (no words) → single Instrumental section
- Verse-only audio (contiguous words) → single Verse 1
- Intro + verse + outro detection from leading/trailing chord-only spans
- Multi-section alternation (verse 1 → chorus → verse 2 → chorus 2)
- Short gaps within a verse don't fragment the section
- Chord events partitioned across sections by timestamp
"""

import pytest

from titan_chordpro.core.schemas import (
    BeatGrid,
    ChordEvent,
    InstrumentalLine,
    LyricLine,
    TimeStamp,
    WordEvent,
)
from titan_chordpro.fusion.sectioner import infer_sections


def _word(text: str, start: float, end: float) -> WordEvent:
    return WordEvent(
        text=text,
        timestamp=TimeStamp(start=start, end=end),
        source_engine="mock",
    )


def _chord(symbol: str, start: float, end: float) -> ChordEvent:
    return ChordEvent(
        symbol=symbol,
        timestamp=TimeStamp(start=start, end=end),
        source_engine="mock",
    )


def _beat_grid(bpm: float = 120.0, duration: float = 30.0) -> BeatGrid:
    """Build a uniform beat grid covering [0, duration]."""
    period = 60.0 / bpm
    beats: list[float] = []
    t = 0.0
    while t < duration:
        beats.append(round(t, 6))
        t += period
    return BeatGrid(
        beats=beats,
        downbeat_indices=list(range(0, len(beats), 4)),
        bpm=bpm,
        meter=(4, 4),
        source_engine="mock",
    )


@pytest.mark.unit
class TestInferSectionsInstrumentalOnly:
    def test_no_words_produces_single_instrumental(self) -> None:
        chords = [_chord("C", 0.0, 2.0), _chord("F", 2.0, 4.0)]
        sections = infer_sections(
            words=[],
            chords=chords,
            beat_grid=_beat_grid(bpm=120.0, duration=10.0),
            duration=10.0,
        )
        assert len(sections) == 1
        assert sections[0].type == "instrumental"
        assert sections[0].timestamp.start == 0.0
        assert sections[0].timestamp.end == 10.0
        assert isinstance(sections[0].lines[0], InstrumentalLine)
        # All chords assigned to this section
        line = sections[0].lines[0]
        assert {c.symbol for c in line.chords} == {"C", "F"}

    def test_empty_audio_returns_empty_list(self) -> None:
        sections = infer_sections(
            words=[],
            chords=[],
            beat_grid=_beat_grid(),
            duration=0.0,
        )
        assert sections == []


@pytest.mark.unit
class TestInferSectionsVerseOnly:
    def test_contiguous_words_one_verse(self) -> None:
        words = [_word("hello", 0.0, 0.5), _word("world", 0.5, 1.0)]
        chords = [_chord("C", 0.0, 1.0)]
        sections = infer_sections(
            words,
            chords,
            _beat_grid(bpm=120.0, duration=1.0),
            duration=1.0,
        )
        assert len(sections) == 1
        assert sections[0].type == "verse"
        assert sections[0].label == "Verse 1"
        assert any(isinstance(ln, LyricLine) for ln in sections[0].lines)

    def test_short_gap_does_not_split_section(self) -> None:
        # At 120bpm, 4 beats = 2.0s. A 1.5s gap is sub-threshold → same section.
        words = [
            _word("a", 0.0, 0.3),
            _word("b", 1.8, 2.1),  # 1.5s gap = 3 beats < 4-beat threshold
        ]
        sections = infer_sections(
            words,
            [],
            _beat_grid(bpm=120.0, duration=3.0),
            duration=3.0,
        )
        # Single verse (no intro because words start at 0)
        verse_sections = [s for s in sections if s.type == "verse"]
        assert len(verse_sections) == 1


@pytest.mark.unit
class TestInferSectionsIntroVerseOutro:
    def test_intro_detected_from_leading_chord_gap(self) -> None:
        # Words start at 5.0s in a 12s song → 5s intro gap > 4-beat threshold
        words = [_word("the", 5.0, 5.3), _word("song", 5.3, 6.0)]
        chords = [
            _chord("C", 0.0, 5.0),
            _chord("F", 5.0, 6.0),
            _chord("G", 6.0, 12.0),
        ]
        sections = infer_sections(
            words,
            chords,
            _beat_grid(bpm=120.0, duration=12.0),
            duration=12.0,
        )
        types = [s.type for s in sections]
        assert types == ["intro", "verse", "outro"]
        intro = sections[0]
        assert intro.timestamp.start == 0.0
        assert intro.timestamp.end == 5.0
        assert isinstance(intro.lines[0], InstrumentalLine)
        # Intro chord 'C' assigned to intro section
        assert {c.symbol for c in intro.lines[0].chords} == {"C"}

    def test_outro_detected_from_trailing_chord_gap(self) -> None:
        words = [_word("hi", 0.0, 0.5)]
        chords = [_chord("C", 0.0, 0.5), _chord("G", 6.0, 10.0)]
        sections = infer_sections(
            words,
            chords,
            _beat_grid(bpm=120.0, duration=10.0),
            duration=10.0,
        )
        types = [s.type for s in sections]
        # No intro (words start at 0), verse, outro (long trailing gap)
        assert "outro" in types
        outro = next(s for s in sections if s.type == "outro")
        assert outro.timestamp.end == pytest.approx(10.0)
        outro_line = outro.lines[0]
        assert isinstance(outro_line, InstrumentalLine)
        assert any(c.symbol == "G" for c in outro_line.chords)

    def test_no_intro_when_first_word_near_start(self) -> None:
        # Words start at 0.5s — under 4-beat threshold at 120bpm (2.0s)
        words = [_word("hi", 0.5, 1.0)]
        sections = infer_sections(
            words,
            [],
            _beat_grid(bpm=120.0, duration=1.5),
            duration=1.5,
        )
        assert sections[0].type == "verse"  # no intro


@pytest.mark.unit
class TestInferSectionsAlternation:
    def test_two_lyric_blocks_alternate_verse_chorus(self) -> None:
        # 120bpm → 4 beats = 2s. Use a 3s gap (6 beats > threshold) between blocks.
        words = [
            _word("verse", 0.0, 0.5),
            _word("one", 0.5, 1.0),
            _word("the", 4.0, 4.3),  # 3s gap from prev
            _word("chorus", 4.3, 5.0),
        ]
        sections = infer_sections(
            words,
            [],
            _beat_grid(bpm=120.0, duration=5.0),
            duration=5.0,
        )
        lyric_sections = [s for s in sections if s.type in ("verse", "chorus")]
        assert [s.type for s in lyric_sections] == ["verse", "chorus"]
        assert [s.label for s in lyric_sections] == ["Verse 1", "Chorus"]

    def test_three_blocks_verse_chorus_verse(self) -> None:
        words = [
            _word("a", 0.0, 0.5),
            _word("b", 4.0, 4.5),
            _word("c", 8.0, 8.5),
        ]
        sections = infer_sections(
            words,
            [],
            _beat_grid(bpm=120.0, duration=9.0),
            duration=9.0,
        )
        lyric_sections = [s for s in sections if s.type in ("verse", "chorus")]
        assert [s.type for s in lyric_sections] == ["verse", "chorus", "verse"]
        assert [s.label for s in lyric_sections] == ["Verse 1", "Chorus", "Verse 2"]

    def test_instrumental_break_between_lyric_blocks(self) -> None:
        # Long gap between blocks → an Instrumental section appears between them
        words = [
            _word("a", 0.0, 0.5),
            _word("b", 5.0, 5.5),  # 4.5s gap = 9 beats at 120bpm
        ]
        chords = [_chord("X", 1.0, 4.5)]  # chord in the gap
        sections = infer_sections(
            words,
            chords,
            _beat_grid(bpm=120.0, duration=6.0),
            duration=6.0,
        )
        types = [s.type for s in sections]
        assert "instrumental" in types
        instr = next(s for s in sections if s.type == "instrumental")
        # The mid-gap chord X is assigned to the instrumental section
        instr_line = instr.lines[0]
        assert isinstance(instr_line, InstrumentalLine)
        assert any(c.symbol == "X" for c in instr_line.chords)


@pytest.mark.unit
class TestInferSectionsChordPartitioning:
    def test_chords_assigned_to_section_by_timestamp(self) -> None:
        words = [_word("hi", 5.0, 6.0)]
        chords = [
            _chord("C", 0.0, 5.0),  # intro
            _chord("F", 5.0, 6.0),  # verse
            _chord("G", 6.0, 12.0),  # outro
        ]
        sections = infer_sections(
            words,
            chords,
            _beat_grid(bpm=120.0, duration=12.0),
            duration=12.0,
        )
        intro = next(s for s in sections if s.type == "intro")
        outro = next(s for s in sections if s.type == "outro")
        intro_line = intro.lines[0]
        outro_line = outro.lines[0]
        assert isinstance(intro_line, InstrumentalLine)
        assert isinstance(outro_line, InstrumentalLine)
        assert any(c.symbol == "C" for c in intro_line.chords)
        assert any(c.symbol == "G" for c in outro_line.chords)


@pytest.mark.unit
class TestInferSectionsTempoSensitivity:
    def test_threshold_scales_with_bpm(self) -> None:
        # At 60bpm, 4 beats = 4s. A 3s gap is SUB-threshold → same section.
        # Same 3s gap at 180bpm = 9 beats → OVER threshold → split.
        words = [_word("a", 0.0, 0.5), _word("b", 3.5, 4.0)]
        # 60bpm: should be ONE verse (no split)
        sections_slow = infer_sections(
            words,
            [],
            _beat_grid(bpm=60.0, duration=4.0),
            duration=4.0,
        )
        verse_sections_slow = [s for s in sections_slow if s.type == "verse"]
        assert len(verse_sections_slow) == 1
        # 180bpm: should split into verse + chorus
        sections_fast = infer_sections(
            words,
            [],
            _beat_grid(bpm=180.0, duration=4.0),
            duration=4.0,
        )
        lyric_sections_fast = [s for s in sections_fast if s.type in ("verse", "chorus")]
        assert len(lyric_sections_fast) == 2

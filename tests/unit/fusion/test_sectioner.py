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

    def test_any_words_present_produces_at_least_one_lyric_section(self) -> None:
        """Phase C T70-iter2 Gap 3 regression — when transcription yields
        words (even very sparse ones), the sectioner must produce >= 1
        non-instrumental section. The 'Tua vontade' all-Instrumental render
        was misdiagnosed as a sectioner bug; the real cause was whisper
        'base' tagging everything as [Música] (filtered → zero words). This
        test pins down the sectioner contract so the same misdiagnosis
        can't recur silently."""
        words = [
            _word("entrega", 30.0, 30.5),
            _word("tudo", 60.0, 60.4),
            _word("vontade", 90.0, 90.6),
        ]
        chords = [_chord("C", 0.0, 30.0), _chord("F", 30.0, 120.0)]
        sections = infer_sections(
            words=words,
            chords=chords,
            beat_grid=_beat_grid(bpm=120.0, duration=120.0),
            duration=120.0,
        )
        lyric_sections = [s for s in sections if s.type not in ("instrumental", "intro", "outro")]
        assert lyric_sections, (
            f"sectioner produced no lyric sections despite words present; "
            f"all sections: {[(s.type, s.label) for s in sections]}"
        )

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
    """Phase C T70-iter2: thresholds are now adaptive to inter-word gap
    statistics (median × multiplier, floored at MIN_INSTRUMENTAL_GAP_SEC =
    4.0s). These fixtures use dense word streams (small gaps) and a single
    long gap that exceeds the floor to trigger a block boundary."""

    def test_two_lyric_blocks_alternate_verse_chorus(self) -> None:
        # Verse block (small gaps ~0.1s) → 10s gap (well above 4s floor) → chorus block.
        words = [
            _word("v", 0.0, 0.4),
            _word("e", 0.5, 0.9),
            _word("r", 1.0, 1.4),
            _word("s", 1.5, 1.9),
            _word("e", 2.0, 2.4),
            # 10s gap here
            _word("c", 12.4, 12.8),
            _word("h", 12.9, 13.3),
            _word("o", 13.4, 13.8),
            _word("r", 13.9, 14.3),
        ]
        sections = infer_sections(
            words,
            [],
            _beat_grid(bpm=120.0, duration=15.0),
            duration=15.0,
        )
        lyric_sections = [s for s in sections if s.type in ("verse", "chorus")]
        assert [s.type for s in lyric_sections] == ["verse", "chorus"]
        assert [s.label for s in lyric_sections] == ["Verse 1", "Chorus"]

    def test_three_blocks_verse_chorus_verse(self) -> None:
        # Three dense blocks separated by 10s gaps.
        def block(start: float) -> list:
            return [
                _word("a", start, start + 0.4),
                _word("b", start + 0.5, start + 0.9),
                _word("c", start + 1.0, start + 1.4),
            ]

        words = block(0.0) + block(11.4) + block(22.8)
        sections = infer_sections(
            words,
            [],
            _beat_grid(bpm=120.0, duration=25.0),
            duration=25.0,
        )
        lyric_sections = [s for s in sections if s.type in ("verse", "chorus")]
        assert [s.type for s in lyric_sections] == ["verse", "chorus", "verse"]
        assert [s.label for s in lyric_sections] == ["Verse 1", "Chorus", "Verse 2"]

    def test_instrumental_break_between_lyric_blocks(self) -> None:
        # Two dense blocks with a long gap → an Instrumental section appears between.
        words = [
            _word("a", 0.0, 0.4),
            _word("b", 0.5, 0.9),
            _word("c", 1.0, 1.4),
            # 10s gap
            _word("d", 11.4, 11.8),
            _word("e", 11.9, 12.3),
        ]
        chords = [_chord("X", 2.0, 10.0)]  # chord in the gap
        sections = infer_sections(
            words,
            chords,
            _beat_grid(bpm=120.0, duration=13.0),
            duration=13.0,
        )
        types = [s.type for s in sections]
        assert "instrumental" in types
        instr = next(s for s in sections if s.type == "instrumental")
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
class TestInferSectionsAdaptiveThreshold:
    """Phase C T70-iter2: thresholds derive from inter-word gap median
    with an absolute floor (MIN_INSTRUMENTAL_GAP_SEC=4.0). BPM no longer
    directly drives the threshold — a fast (often mis-detected) BPM does
    not over-fragment songs into instrumentals.
    """

    def test_threshold_floor_holds_under_fast_bpm(self) -> None:
        """A 3s gap should NOT trigger a break even at 180 BPM
        (regression for the Phase C "Jesus tu és a minha vida" case
        where BeatThis detected BPM=187 and old formula split on every
        breath pause)."""
        words = [
            _word("a", 0.0, 0.4),
            _word("b", 0.5, 0.9),
            _word("c", 1.0, 1.4),
            _word("d", 4.4, 4.8),  # 3.0s gap — under the 4.0s floor
            _word("e", 4.9, 5.3),
        ]
        sections = infer_sections(
            words,
            [],
            _beat_grid(bpm=180.0, duration=6.0),
            duration=6.0,
        )
        lyric_sections = [s for s in sections if s.type in ("verse", "chorus")]
        # Under old beat-based logic: 4 × 60/180 = 1.33s threshold → 2 sections.
        # Under adaptive floor: 3s gap < 4s floor → 1 section.
        assert len(lyric_sections) == 1, (
            f"3s gap with median ~0.1s should stay below 4s floor; "
            f"got sections {[(s.type, s.label) for s in sections]}"
        )

    def test_long_gap_triggers_break_regardless_of_bpm(self) -> None:
        """A clearly-instrumental gap (10s) breaks the section at any BPM."""
        words = [
            _word("a", 0.0, 0.4),
            _word("b", 0.5, 0.9),
            _word("c", 11.0, 11.4),  # 10.1s gap — well above any floor
            _word("d", 11.5, 11.9),
        ]
        for bpm in (60.0, 120.0, 180.0):
            sections = infer_sections(
                words,
                [],
                _beat_grid(bpm=bpm, duration=12.5),
                duration=12.5,
            )
            lyric_sections = [s for s in sections if s.type in ("verse", "chorus")]
            assert len(lyric_sections) >= 2, (
                f"10s gap should split at BPM={bpm}; got {[(s.type, s.label) for s in sections]}"
            )

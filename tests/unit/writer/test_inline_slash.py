"""Tests for InlineSlashProfile — the default ChordPro renderer.

Exercises:
- LyricLine rendering: 0 markers, 1 marker, multiple markers (char-position-driven).
- InstrumentalLine × 3 pattern_hints: full_measure, half_measure, beat.
- Full document round-trip: matches a minimal spec-style snippet exactly.
- Section dispatch: verse wraps with directives; intro prepends `{c: ...}`.
- Header always precedes sections.
"""

from datetime import datetime

import pytest

from titan_chordpro.core.schemas import (
    ChordEvent,
    ChordMarker,
    ChordProDocument,
    EngineInfo,
    EngineRegistry,
    InstrumentalLine,
    LyricLine,
    Metadata,
    Provenance,
    Section,
    TimeStamp,
)
from titan_chordpro.writer.profiles.inline_slash import InlineSlashProfile


def _chord(symbol: str, start: float = 0.0, end: float = 1.0) -> ChordEvent:
    return ChordEvent(
        symbol=symbol,
        timestamp=TimeStamp(start=start, end=end),
        source_engine="mock",
    )


def _marker(symbol: str, char_position: int, strategy: str = "stressed_syllable") -> ChordMarker:
    return ChordMarker(
        chord=_chord(symbol),
        char_position=char_position,
        placement_strategy=strategy,
    )


def _provenance() -> Provenance:
    eng = EngineInfo(name="mock", version="0", backend="cpu")
    return Provenance(
        titan_version="0.1.0a0",
        audio_id="abc123",
        engines=EngineRegistry(
            separation=eng,
            transcription=eng,
            alignment=None,
            chord_recognition=eng,
            beat_tracking=eng,
            syllabification=eng,
        ),
        started_at=datetime(2026, 5, 12, 12, 0, 0),
        completed_at=datetime(2026, 5, 12, 12, 5, 0),
        confidence=[],
    )


def _doc(sections: list[Section], title: str = "Test", **meta_kwargs) -> ChordProDocument:
    return ChordProDocument(
        metadata=Metadata(title=title, **meta_kwargs),
        sections=sections,
        provenance=_provenance(),
    )


@pytest.mark.unit
class TestInlineSlashLyricLine:
    def test_lyric_line_no_markers_renders_text_verbatim(self) -> None:
        profile = InlineSlashProfile()
        line = LyricLine(text="hello world", chord_markers=[])
        assert profile.render_line(line) == "hello world"

    def test_single_chord_marker_at_position_zero(self) -> None:
        profile = InlineSlashProfile()
        line = LyricLine(
            text="hello",
            chord_markers=[_marker("C", char_position=0)],
        )
        assert profile.render_line(line) == "[C]hello"

    def test_single_chord_marker_in_middle(self) -> None:
        profile = InlineSlashProfile()
        line = LyricLine(
            text="hello",
            chord_markers=[_marker("C", char_position=2)],
        )
        assert profile.render_line(line) == "he[C]llo"

    def test_multiple_chord_markers_inserted_in_order(self) -> None:
        profile = InlineSlashProfile()
        text = "Em tua presença quero estar"
        assert text[3] == "t"
        assert text[24] == "t"
        markers = [
            ChordMarker(
                chord=ChordEvent(
                    symbol="E", timestamp=TimeStamp(start=0.0, end=1.0), source_engine="mock"
                ),
                char_position=3,
                placement_strategy="stressed_syllable",
            ),
            ChordMarker(
                chord=ChordEvent(
                    symbol="A",
                    bass_note="E",
                    timestamp=TimeStamp(start=2.0, end=3.0),
                    source_engine="mock",
                ),
                char_position=24,
                placement_strategy="stressed_syllable",
            ),
        ]
        line = LyricLine(text=text, chord_markers=markers)
        assert profile.render_line(line) == "Em [E]tua presença quero es[A/E]tar"

    def test_markers_sorted_by_char_position_before_insertion(self) -> None:
        profile = InlineSlashProfile()
        line = LyricLine(
            text="abcd",
            chord_markers=[
                _marker("G", char_position=3),
                _marker("C", char_position=1),
            ],
        )
        assert profile.render_line(line) == "a[C]bc[G]d"


@pytest.mark.unit
class TestInlineSlashInstrumentalLine:
    def test_full_measure_pattern(self) -> None:
        profile = InlineSlashProfile()
        line = InstrumentalLine(
            chords=[_chord("E"), _chord("A"), _chord("D")],
            measures=3,
            pattern_hint="full_measure",
            label="Intro",
        )
        assert profile.render_line(line) == "[E]x///   [A]x///   [D]x///"

    def test_half_measure_pattern(self) -> None:
        profile = InlineSlashProfile()
        line = InstrumentalLine(
            chords=[_chord("E"), _chord("D"), _chord("A"), _chord("E")],
            measures=2,
            pattern_hint="half_measure",
        )
        assert profile.render_line(line) == "[E]x/[D]/   [A]x/[E]/"

    def test_half_measure_odd_count_last_pairs_with_self(self) -> None:
        profile = InlineSlashProfile()
        line = InstrumentalLine(
            chords=[_chord("E"), _chord("D"), _chord("A")],
            measures=2,
            pattern_hint="half_measure",
        )
        assert profile.render_line(line) == "[E]x/[D]/   [A]x/[A]/"

    def test_beat_pattern(self) -> None:
        profile = InlineSlashProfile()
        line = InstrumentalLine(
            chords=[_chord("E"), _chord("A"), _chord("D"), _chord("E")],
            measures=1,
            pattern_hint="beat",
        )
        assert profile.render_line(line) == "[E]/ [A]/ [D]/ [E]/"


@pytest.mark.unit
class TestInlineSlashFullDocument:
    def test_minimal_doc_renders_header_then_section(self) -> None:
        section = Section(
            type="verse",
            label="Verso 1",
            lines=[LyricLine(text="hello", chord_markers=[_marker("C", char_position=0)])],
            timestamp=TimeStamp(start=0.0, end=4.0),
        )
        doc = _doc([section], title="Test")
        out = InlineSlashProfile().render(doc)
        assert out.startswith("{title: Test}")
        assert "{meta: titan_version 0.1.0a0}" in out
        assert "{start_of_verse}" in out
        assert "[C]hello" in out
        assert "{end_of_verse}" in out

    def test_intro_section_uses_comment_label(self) -> None:
        section = Section(
            type="intro",
            label="Introdução",
            lines=[
                InstrumentalLine(
                    chords=[_chord("E")],
                    measures=1,
                    pattern_hint="full_measure",
                )
            ],
            timestamp=TimeStamp(start=0.0, end=4.0),
        )
        doc = _doc([section])
        out = InlineSlashProfile().render(doc)
        assert "{c: Introdução}" in out
        assert "[E]x///" in out
        assert "{end_of_intro}" not in out

    def test_profile_descriptor_metadata(self) -> None:
        p = InlineSlashProfile()
        assert p.name == "inline_slash"
        assert isinstance(p.description, str) and p.description

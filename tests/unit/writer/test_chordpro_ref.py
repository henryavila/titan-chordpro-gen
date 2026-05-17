"""Tests for ChordProReferenceProfile.

Exercises:
- LyricLine render: byte-identical to inline_slash (same _render_lyric_line).
- InstrumentalLine: emits `{start_of_grid}` / `{end_of_grid}` block (per spec
  line 1252-1257).
- Grid cell layout: full_measure → `| Sym . . . |`; half_measure → `| Sym . SymB . |`;
  beat → `| Sym Sym Sym Sym |` (4/4) or `| Sym Sym Sym Sym Sym Sym |` (6/8).
- Section label propagates into `{start_of_grid: <label>}`.
- Multi-measure grid lays out N measures separated by `|`.
- Mixed doc: lyric verse + instrumental intro → both render correctly.
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
from titan_chordpro.writer.profiles.chordpro_ref import ChordProReferenceProfile


def _chord(symbol: str, bass: str | None = None) -> ChordEvent:
    return ChordEvent(
        symbol=symbol,
        timestamp=TimeStamp(start=0.0, end=1.0),
        bass_note=bass,
        source_engine="mock",
    )


def _provenance() -> Provenance:
    eng = EngineInfo(name="mock", version="0", backend="cpu")
    return Provenance(
        titan_version="0.1.0a0",
        audio_id="abc",
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


def _doc(sections: list[Section], time_sig: tuple[int, int] | None = (4, 4)) -> ChordProDocument:
    return ChordProDocument(
        metadata=Metadata(title="Test", time_signature=time_sig),
        sections=sections,
        provenance=_provenance(),
    )


@pytest.mark.unit
class TestChordProRefLyricLine:
    def test_lyric_line_matches_inline_slash_format(self) -> None:
        profile = ChordProReferenceProfile()
        line = LyricLine(
            text="hello world",
            chord_markers=[
                ChordMarker(
                    chord=_chord("C"),
                    char_position=0,
                    placement_strategy="stressed_syllable",
                )
            ],
        )
        assert profile.render_line(line) == "[C]hello world"


@pytest.mark.unit
class TestChordProRefGrid:
    def test_full_measure_single_chord_in_4_4(self) -> None:
        profile = ChordProReferenceProfile()
        line = InstrumentalLine(
            chords=[_chord("E")],
            measures=1,
            pattern_hint="full_measure",
            label=None,
        )
        result = profile.render_instrumental_grid(line, meter=(4, 4))
        assert result == "| E . . . |"

    def test_full_measure_multi_measure_in_4_4(self) -> None:
        profile = ChordProReferenceProfile()
        line = InstrumentalLine(
            chords=[_chord("E"), _chord("D"), _chord("A")],
            measures=3,
            pattern_hint="full_measure",
        )
        result = profile.render_instrumental_grid(line, meter=(4, 4))
        assert result == "| E . . . | D . . . | A . . . |"

    def test_half_measure_in_4_4(self) -> None:
        profile = ChordProReferenceProfile()
        line = InstrumentalLine(
            chords=[_chord("E"), _chord("D"), _chord("A"), _chord("E")],
            measures=2,
            pattern_hint="half_measure",
        )
        result = profile.render_instrumental_grid(line, meter=(4, 4))
        assert result == "| E . D . | A . E . |"

    def test_beat_pattern_in_4_4(self) -> None:
        profile = ChordProReferenceProfile()
        line = InstrumentalLine(
            chords=[_chord("E"), _chord("A"), _chord("D"), _chord("E")],
            measures=1,
            pattern_hint="beat",
        )
        result = profile.render_instrumental_grid(line, meter=(4, 4))
        assert result == "| E A D E |"

    def test_beat_pattern_in_6_8(self) -> None:
        profile = ChordProReferenceProfile()
        line = InstrumentalLine(
            chords=[_chord("C")] * 6,
            measures=1,
            pattern_hint="beat",
        )
        result = profile.render_instrumental_grid(line, meter=(6, 8))
        assert result == "| C C C C C C |"

    def test_slash_chord_preserved_in_grid(self) -> None:
        profile = ChordProReferenceProfile()
        line = InstrumentalLine(
            chords=[_chord("A", bass="E")],
            measures=1,
            pattern_hint="full_measure",
        )
        result = profile.render_instrumental_grid(line, meter=(4, 4))
        assert result == "| A/E . . . |"


@pytest.mark.unit
class TestChordProRefFullDocument:
    def test_intro_section_wraps_grid_with_sog_eog_block(self) -> None:
        section = Section(
            type="intro",
            label="Intro",
            lines=[
                InstrumentalLine(
                    chords=[_chord("E"), _chord("D"), _chord("A")],
                    measures=3,
                    pattern_hint="full_measure",
                )
            ],
            timestamp=TimeStamp(start=0.0, end=4.0),
        )
        doc = _doc([section])
        out = ChordProReferenceProfile().render(doc)
        assert "{start_of_grid: Intro}" in out
        assert "| E . . . | D . . . | A . . . |" in out
        assert "{end_of_grid}" in out

    def test_verse_section_does_not_use_grid_block(self) -> None:
        section = Section(
            type="verse",
            label="Verso",
            lines=[
                LyricLine(
                    text="hello",
                    chord_markers=[
                        ChordMarker(
                            chord=_chord("C"),
                            char_position=0,
                            placement_strategy="stressed_syllable",
                        )
                    ],
                )
            ],
            timestamp=TimeStamp(start=0.0, end=4.0),
        )
        doc = _doc([section])
        out = ChordProReferenceProfile().render(doc)
        assert "{start_of_grid" not in out
        assert "{start_of_verse}" in out
        assert "[C]hello" in out

    def test_profile_descriptor_metadata(self) -> None:
        p = ChordProReferenceProfile()
        assert p.name == "chordpro_ref"
        assert "grid" in p.description.lower() or "canonical" in p.description.lower()


@pytest.mark.unit
class TestChordProRefDefaultMeter:
    def test_render_uses_4_4_when_metadata_time_signature_is_none(self) -> None:
        section = Section(
            type="intro",
            label="Intro",
            lines=[
                InstrumentalLine(
                    chords=[_chord("E")],
                    measures=1,
                    pattern_hint="full_measure",
                )
            ],
            timestamp=TimeStamp(start=0.0, end=4.0),
        )
        doc = _doc([section], time_sig=None)
        out = ChordProReferenceProfile().render(doc)
        assert "| E . . . |" in out

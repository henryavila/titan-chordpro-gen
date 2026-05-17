"""Tests for the shared writer serializer helpers.

Exercises:
- `_format_chord`: bass_note via slash, bass_note independent, no bass.
- `render_header`: minimal title-only doc; full metadata; extensions; multiple confidence stages.
- `_pair_chords_per_measure`: even count, odd count (last paired with itself),
  single element, empty list.
- `_format_time_signature`: standard 4/4 and uncommon 6/8.
- `SECTION_DIRECTIVES`: presence of the 7 section types per spec line 1319-1327.
- `render_section_wrapper`: verse/chorus/bridge → start/end pair; intro/outro/instrumental/
  pre-chorus → `{c: <label>}` prepend (no end directive).
"""

from datetime import datetime

import pytest

from titan_chordpro.core.schemas import (
    ChordEvent,
    EngineInfo,
    EngineRegistry,
    Metadata,
    Provenance,
    Section,
    StageConfidence,
    TimeStamp,
)
from titan_chordpro.writer.serializer import (
    SECTION_DIRECTIVES,
    _format_chord,
    _format_time_signature,
    _pair_chords_per_measure,
    render_header,
    render_section_wrapper,
)


def _chord(
    symbol: str, start: float = 0.0, end: float = 1.0, bass_note: str | None = None
) -> ChordEvent:
    return ChordEvent(
        symbol=symbol,
        timestamp=TimeStamp(start=start, end=end),
        bass_note=bass_note,
        source_engine="mock",
    )


def _engine(name: str = "mock") -> EngineInfo:
    return EngineInfo(name=name, version="0", backend="cpu")


def _engines() -> EngineRegistry:
    return EngineRegistry(
        separation=_engine("mock_sep"),
        transcription=_engine("mock_trans"),
        alignment=None,
        chord_recognition=_engine("mock_chord"),
        beat_tracking=_engine("mock_beat"),
        syllabification=_engine("mock_syl"),
    )


def _provenance(confidence: list[StageConfidence] | None = None) -> Provenance:
    return Provenance(
        titan_version="0.1.0a0",
        audio_id="abc123",
        engines=_engines(),
        started_at=datetime(2026, 5, 12, 12, 0, 0),
        completed_at=datetime(2026, 5, 12, 12, 5, 0),
        confidence=confidence or [],
    )


@pytest.mark.unit
class TestFormatChord:
    def test_no_bass_note_renders_symbol_only(self) -> None:
        assert _format_chord(_chord("C")) == "[C]"

    def test_symbol_already_has_slash_renders_as_is(self) -> None:
        chord = _chord("C/E", bass_note="E")
        assert _format_chord(chord) == "[C/E]"

    def test_independent_bass_note_inserted_with_slash(self) -> None:
        chord = _chord("Am", bass_note="C")
        assert _format_chord(chord) == "[Am/C]"

    def test_seventh_chord_no_bass(self) -> None:
        assert _format_chord(_chord("Cmaj7")) == "[Cmaj7]"


@pytest.mark.unit
class TestPairChordsPerMeasure:
    def test_empty_list(self) -> None:
        assert _pair_chords_per_measure([]) == []

    def test_single_chord_pairs_with_itself(self) -> None:
        c = _chord("C")
        result = _pair_chords_per_measure([c])
        assert result == [(c, c)]

    def test_even_count_pairs_sequentially(self) -> None:
        c1, c2, c3, c4 = _chord("C"), _chord("G"), _chord("Am"), _chord("F")
        result = _pair_chords_per_measure([c1, c2, c3, c4])
        assert result == [(c1, c2), (c3, c4)]

    def test_odd_count_last_pairs_with_itself(self) -> None:
        c1, c2, c3 = _chord("C"), _chord("G"), _chord("Am")
        result = _pair_chords_per_measure([c1, c2, c3])
        assert result == [(c1, c2), (c3, c3)]


@pytest.mark.unit
class TestFormatTimeSignature:
    def test_standard_4_4(self) -> None:
        assert _format_time_signature((4, 4)) == "4/4"

    def test_compound_6_8(self) -> None:
        assert _format_time_signature((6, 8)) == "6/8"


@pytest.mark.unit
class TestRenderHeader:
    def test_minimal_title_only(self) -> None:
        meta = Metadata(title="Test Song")
        prov = _provenance()
        result = render_header(meta, prov)
        assert result.endswith("\n\n")
        lines = [ln for ln in result.split("\n") if ln]
        assert lines == [
            "{title: Test Song}",
            "{meta: titan_version 0.1.0a0}",
        ]

    def test_full_metadata(self) -> None:
        meta = Metadata(
            title="Grande Deus",
            artist="Adoradores 2",
            key="E",
            tempo=85,
            time_signature=(4, 4),
            capo=2,
        )
        prov = _provenance()
        result = render_header(meta, prov)
        lines = [ln for ln in result.split("\n") if ln]
        assert lines == [
            "{title: Grande Deus}",
            "{artist: Adoradores 2}",
            "{key: E}",
            "{tempo: 85}",
            "{time: 4/4}",
            "{capo: 2}",
            "{meta: titan_version 0.1.0a0}",
        ]

    def test_capo_zero_is_omitted(self) -> None:
        meta = Metadata(title="X", capo=0)
        prov = _provenance()
        result = render_header(meta, prov)
        assert "{capo:" not in result

    def test_multiple_confidence_stages_rendered_in_order(self) -> None:
        meta = Metadata(title="X")
        prov = _provenance(
            confidence=[
                StageConfidence(stage="chord_recognition", mean=0.923, median=0.9, p10=0.6),
                StageConfidence(stage="beat_tracking", mean=0.88, median=0.9, p10=0.7),
            ]
        )
        result = render_header(meta, prov)
        assert "{meta: titan_confidence_chord_recognition 0.92}" in result
        assert "{meta: titan_confidence_beat_tracking 0.88}" in result
        chord_idx = result.index("titan_confidence_chord_recognition")
        beat_idx = result.index("titan_confidence_beat_tracking")
        assert chord_idx < beat_idx

    def test_metadata_extensions_appended_at_end(self) -> None:
        meta = Metadata(title="X", extensions={"ccli": "12345", "sbp_difficulty": "easy"})
        prov = _provenance()
        result = render_header(meta, prov)
        assert "{meta: ccli 12345}" in result
        assert "{meta: sbp_difficulty easy}" in result


@pytest.mark.unit
class TestSectionDirectives:
    def test_directive_keys_match_spec(self) -> None:
        assert set(SECTION_DIRECTIVES.keys()) == {
            "verse",
            "chorus",
            "bridge",
            "pre-chorus",
            "instrumental",
            "intro",
            "outro",
        }

    def test_verse_chorus_bridge_have_directives(self) -> None:
        for key in ("verse", "chorus", "bridge"):
            assert SECTION_DIRECTIVES[key] == (f"{{start_of_{key}}}", f"{{end_of_{key}}}")

    def test_intro_outro_instrumental_pre_chorus_have_no_directives(self) -> None:
        for key in ("intro", "outro", "instrumental", "pre-chorus"):
            assert SECTION_DIRECTIVES[key] is None


@pytest.mark.unit
class TestRenderSectionWrapper:
    def test_verse_wraps_body_with_start_end_directives(self) -> None:
        section = Section(
            type="verse",
            label="Verso 1",
            lines=[],
            timestamp=TimeStamp(start=0.0, end=1.0),
        )
        result = render_section_wrapper(section, "Em [E]tua presença")
        assert result == "{start_of_verse}\nEm [E]tua presença\n{end_of_verse}\n"

    def test_intro_prepends_comment_no_end_directive(self) -> None:
        section = Section(
            type="intro",
            label="Introdução",
            lines=[],
            timestamp=TimeStamp(start=0.0, end=1.0),
        )
        result = render_section_wrapper(section, "[E]x///")
        assert result == "{c: Introdução}\n[E]x///\n"

    def test_pre_chorus_prepends_comment(self) -> None:
        section = Section(
            type="pre-chorus",
            label="Pré-coro",
            lines=[],
            timestamp=TimeStamp(start=0.0, end=1.0),
        )
        result = render_section_wrapper(section, "body")
        assert result.startswith("{c: Pré-coro}\n")
        assert "{end_of_" not in result

"""Tests for ChordProDocument.to_string / write methods (T28).

Exercises:
- to_string('inline_slash') returns the correct rendered string.
- write(path) writes the same content to disk.
- to_string with an unknown profile raises ValueError.
"""

from datetime import datetime
from pathlib import Path

import pytest

from titan_chordpro.core.schemas import (
    ChordEvent,
    ChordMarker,
    ChordProDocument,
    EngineInfo,
    EngineRegistry,
    LyricLine,
    Metadata,
    Provenance,
    Section,
    TimeStamp,
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


def _simple_doc() -> ChordProDocument:
    section = Section(
        type="verse",
        label="Verso",
        lines=[
            LyricLine(
                text="hello",
                chord_markers=[
                    ChordMarker(
                        chord=ChordEvent(
                            symbol="C",
                            timestamp=TimeStamp(start=0.0, end=1.0),
                            source_engine="mock",
                        ),
                        char_position=0,
                        placement_strategy="stressed_syllable",
                    )
                ],
            )
        ],
        timestamp=TimeStamp(start=0.0, end=4.0),
    )
    return ChordProDocument(
        metadata=Metadata(title="Test Song"),
        sections=[section],
        provenance=_provenance(),
    )


@pytest.mark.unit
class TestToString:
    def test_to_string_default_profile_produces_header_and_section(self) -> None:
        doc = _simple_doc()
        out = doc.to_string()
        assert out.startswith("{title: Test Song}")
        assert "{start_of_verse}" in out
        assert "[C]hello" in out
        assert "{end_of_verse}" in out

    def test_to_string_chordpro_ref_profile(self) -> None:
        doc = _simple_doc()
        out = doc.to_string("chordpro_ref")
        assert "{title: Test Song}" in out
        assert "[C]hello" in out

    def test_to_string_unknown_profile_raises(self) -> None:
        doc = _simple_doc()
        with pytest.raises(ValueError, match="Unknown output profile"):
            doc.to_string("nonexistent_profile")


@pytest.mark.unit
class TestWrite:
    def test_write_creates_file_with_correct_content(self, tmp_path: Path) -> None:
        doc = _simple_doc()
        out_path = tmp_path / "song.chordpro"
        doc.write(out_path)
        assert out_path.exists()
        content = out_path.read_text()
        assert "{title: Test Song}" in content
        assert "[C]hello" in content

    def test_write_content_matches_to_string(self, tmp_path: Path) -> None:
        doc = _simple_doc()
        out_path = tmp_path / "song.chordpro"
        doc.write(out_path)
        assert out_path.read_text() == doc.to_string()

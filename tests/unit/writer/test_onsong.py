"""Tests for OnSongProfile — inline_slash + OnSong-specific capo directive."""

from datetime import datetime

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
from titan_chordpro.writer.profiles.onsong import OnSongProfile


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


def _trivial_section() -> Section:
    return Section(
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


@pytest.mark.unit
class TestOnSongProfileCapo:
    def test_capo_positive_renders_x_capo_not_capo(self) -> None:
        doc = ChordProDocument(
            metadata=Metadata(title="Test", capo=2),
            sections=[_trivial_section()],
            provenance=_provenance(),
        )
        out = OnSongProfile().render(doc)
        assert "{x_capo: 2}" in out
        assert "{capo: 2}" not in out

    def test_capo_zero_renders_neither_directive(self) -> None:
        doc = ChordProDocument(
            metadata=Metadata(title="Test", capo=0),
            sections=[_trivial_section()],
            provenance=_provenance(),
        )
        out = OnSongProfile().render(doc)
        assert "{x_capo:" not in out
        assert "{capo:" not in out


@pytest.mark.unit
class TestOnSongProfileBody:
    def test_body_is_identical_to_inline_slash(self) -> None:
        from titan_chordpro.writer.profiles.inline_slash import InlineSlashProfile

        doc = ChordProDocument(
            metadata=Metadata(title="Test"),
            sections=[_trivial_section()],
            provenance=_provenance(),
        )
        onsong_out = OnSongProfile().render(doc)
        inline_out = InlineSlashProfile().render(doc)
        assert onsong_out == inline_out


@pytest.mark.unit
class TestOnSongDescriptor:
    def test_metadata(self) -> None:
        p = OnSongProfile()
        assert p.name == "onsong"
        assert "onsong" in p.description.lower()

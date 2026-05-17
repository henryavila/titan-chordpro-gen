"""Tests for SongbookProProfile — inline_slash + {x_sbp_tags} aggregation."""

from datetime import datetime

import pytest

from titan_chordpro.core.schemas import (
    ChordProDocument,
    EngineInfo,
    EngineRegistry,
    Metadata,
    Provenance,
)
from titan_chordpro.writer.profiles.songbookpro import SongbookProProfile


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


def _doc(extensions: dict[str, str]) -> ChordProDocument:
    return ChordProDocument(
        metadata=Metadata(title="Test", extensions=extensions),
        sections=[],
        provenance=_provenance(),
    )


@pytest.mark.unit
class TestSongbookProSBPTags:
    def test_single_sbp_tag_aggregated(self) -> None:
        doc = _doc({"sbp_difficulty": "easy"})
        out = SongbookProProfile().render(doc)
        assert "{x_sbp_tags: difficulty=easy}" in out
        assert "{meta: sbp_difficulty easy}" not in out

    def test_multiple_sbp_tags_concatenated(self) -> None:
        doc = _doc({"sbp_difficulty": "easy", "sbp_section": "Sun"})
        out = SongbookProProfile().render(doc)
        assert "{x_sbp_tags: difficulty=easy section=Sun}" in out
        assert "{meta: sbp_difficulty" not in out
        assert "{meta: sbp_section" not in out

    def test_no_sbp_keys_emits_no_x_sbp_tags(self) -> None:
        doc = _doc({"ccli": "999", "custom": "x"})
        out = SongbookProProfile().render(doc)
        assert "{x_sbp_tags:" not in out
        assert "{meta: ccli 999}" in out
        assert "{meta: custom x}" in out

    def test_mixed_sbp_and_non_sbp_extensions(self) -> None:
        doc = _doc({"sbp_difficulty": "hard", "other": "value"})
        out = SongbookProProfile().render(doc)
        assert "{x_sbp_tags: difficulty=hard}" in out
        assert "{meta: other value}" in out
        assert "{meta: sbp_difficulty" not in out


@pytest.mark.unit
class TestSongbookProBodyIdentity:
    def test_doc_with_no_sbp_extensions_matches_inline_slash(self) -> None:
        from titan_chordpro.writer.profiles.inline_slash import InlineSlashProfile

        doc = _doc({"other": "val"})
        assert SongbookProProfile().render(doc) == InlineSlashProfile().render(doc)


@pytest.mark.unit
class TestSongbookProDescriptor:
    def test_metadata(self) -> None:
        p = SongbookProProfile()
        assert p.name == "songbookpro"
        assert "songbookpro" in p.description.lower() or "songbook" in p.description.lower()

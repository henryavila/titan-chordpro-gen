"""Tests for ProPresenterProfile — inline_slash + {ccli} promotion."""

from datetime import datetime

import pytest

from titan_chordpro.core.schemas import (
    ChordProDocument,
    EngineInfo,
    EngineRegistry,
    Metadata,
    Provenance,
)
from titan_chordpro.writer.profiles.propresenter import ProPresenterProfile


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


def _empty_doc(extensions: dict[str, str] | None = None) -> ChordProDocument:
    return ChordProDocument(
        metadata=Metadata(title="Test", extensions=extensions or {}),
        sections=[],
        provenance=_provenance(),
    )


@pytest.mark.unit
class TestProPresenterCCLI:
    def test_ccli_in_extensions_promoted_to_standalone_directive(self) -> None:
        doc = _empty_doc(extensions={"ccli": "1234567"})
        out = ProPresenterProfile().render(doc)
        assert "{ccli: 1234567}" in out
        assert "{meta: ccli 1234567}" not in out

    def test_no_ccli_renders_no_directive(self) -> None:
        doc = _empty_doc(extensions={})
        out = ProPresenterProfile().render(doc)
        assert "{ccli:" not in out

    def test_other_extensions_still_rendered_as_meta(self) -> None:
        doc = _empty_doc(extensions={"ccli": "999", "custom_key": "value"})
        out = ProPresenterProfile().render(doc)
        assert "{ccli: 999}" in out
        assert "{meta: ccli 999}" not in out
        assert "{meta: custom_key value}" in out


@pytest.mark.unit
class TestProPresenterBodyIdentity:
    def test_doc_without_ccli_matches_inline_slash(self) -> None:
        from titan_chordpro.writer.profiles.inline_slash import InlineSlashProfile

        doc = _empty_doc(extensions={"other": "stuff"})
        assert ProPresenterProfile().render(doc) == InlineSlashProfile().render(doc)


@pytest.mark.unit
class TestProPresenterDescriptor:
    def test_metadata(self) -> None:
        p = ProPresenterProfile()
        assert p.name == "propresenter"
        assert "propresenter" in p.description.lower()

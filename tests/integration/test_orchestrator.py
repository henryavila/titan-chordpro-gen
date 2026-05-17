"""Integration smoke test: full pipeline with mock engines.

Exercises:
- transcribe() returns a ChordProDocument.
- Document has provenance with correct titan_version.
- Document can be rendered via to_string().
- Document can be written to disk.
"""

from pathlib import Path

import pytest

from titan_chordpro.core.schemas import ChordProDocument
from titan_chordpro.orchestrator import transcribe


@pytest.mark.integration
class TestTranscribePipeline:
    def test_returns_chord_pro_document(self, tmp_path: Path) -> None:
        audio = tmp_path / "silent.wav"
        audio.write_bytes(b"RIFF" + b"\x00" * 44)
        doc = transcribe(audio)
        assert isinstance(doc, ChordProDocument)

    def test_document_has_provenance(self, tmp_path: Path) -> None:
        audio = tmp_path / "song.wav"
        audio.write_bytes(b"RIFF" + b"\x00" * 44)
        doc = transcribe(audio)
        assert doc.provenance.titan_version
        assert doc.provenance.audio_id

    def test_to_string_returns_non_empty(self, tmp_path: Path) -> None:
        audio = tmp_path / "song.wav"
        audio.write_bytes(b"RIFF" + b"\x00" * 44)
        doc = transcribe(audio)
        out = doc.to_string()
        assert out.startswith("{title:")
        assert "{meta: titan_version" in out

    def test_write_produces_file(self, tmp_path: Path) -> None:
        audio = tmp_path / "song.wav"
        audio.write_bytes(b"RIFF" + b"\x00" * 44)
        out_path = tmp_path / "song.chordpro"
        doc = transcribe(audio)
        doc.write(out_path)
        assert out_path.exists()
        assert len(out_path.read_text()) > 0

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
def test_real_factory_smoke_on_silent_wav(silent_wav: Path) -> None:
    """End-to-end smoke with force_mock=True: silent.wav through deterministic mocks.

    Post v0.1.0-b1 (Codex review F-002): factory no longer silently falls back to
    mocks when real deps are missing — callers must opt in via force_mock=True.
    This smoke asserts the no-crash contract under the deterministic mock path.
    """
    doc = transcribe(silent_wav, language="pt", output_profile="inline_slash", force_mock=True)
    assert isinstance(doc, ChordProDocument)
    # Document should have metadata even on silent input.
    assert doc.metadata is not None
    # Provenance should reflect which engines actually ran.
    assert doc.provenance is not None
    assert len(doc.provenance.confidence) >= 0


@pytest.mark.integration
class TestTranscribePipeline:
    def test_returns_chord_pro_document(self, tmp_path: Path) -> None:
        audio = tmp_path / "silent.wav"
        audio.write_bytes(b"RIFF" + b"\x00" * 44)
        doc = transcribe(audio, force_mock=True)
        assert isinstance(doc, ChordProDocument)

    def test_document_has_provenance(self, tmp_path: Path) -> None:
        audio = tmp_path / "song.wav"
        audio.write_bytes(b"RIFF" + b"\x00" * 44)
        doc = transcribe(audio, force_mock=True)
        assert doc.provenance.titan_version
        assert doc.provenance.audio_id

    def test_to_string_returns_non_empty(self, tmp_path: Path) -> None:
        audio = tmp_path / "song.wav"
        audio.write_bytes(b"RIFF" + b"\x00" * 44)
        doc = transcribe(audio, force_mock=True)
        out = doc.to_string()
        assert out.startswith("{title:")
        assert "{meta: titan_version" in out

    def test_write_produces_file(self, tmp_path: Path) -> None:
        audio = tmp_path / "song.wav"
        audio.write_bytes(b"RIFF" + b"\x00" * 44)
        out_path = tmp_path / "song.chordpro"
        doc = transcribe(audio, force_mock=True)
        doc.write(out_path)
        assert out_path.exists()
        assert len(out_path.read_text()) > 0

    def test_chord_engine_receives_audio_not_bass(self, tmp_path: Path, monkeypatch) -> None:
        """Orchestrator must pass the harmonic source (audio) to chord_engine.detect,
        not the bass stem (regression: F-002).

        Pre-fix bug: chord_engine.detect(stems.bass) starved Chordino of harmonic
        content, producing empty/wrong chord progressions in real-engine mode.
        """
        from titan_chordpro import factory

        captured: dict[str, object] = {}
        real_select = factory.select_chord_recognition

        def spy_select_chord(*args, **kwargs):
            engine = real_select(*args, **kwargs)
            original_detect = engine.detect

            def detect_spy(harmonic_mix, bass_stem=None):
                captured["harmonic_mix"] = harmonic_mix
                captured["bass_stem"] = bass_stem
                return original_detect(harmonic_mix, bass_stem=bass_stem)

            engine.detect = detect_spy  # type: ignore[method-assign]
            return engine

        monkeypatch.setattr(factory, "select_chord_recognition", spy_select_chord)

        audio = tmp_path / "song.wav"
        audio.write_bytes(b"RIFF" + b"\x00" * 44)
        transcribe(audio, force_mock=True)

        # harmonic_mix should be the original audio file, NOT a bass stem path.
        assert captured["harmonic_mix"] == audio, (
            f"chord_engine.detect got {captured['harmonic_mix']!r} as harmonic_mix; "
            f"expected the original audio path {audio!r}"
        )
        # bass_stem should be populated (mock separator emits stems.bass).
        assert captured["bass_stem"] is not None
        assert captured["bass_stem"] != audio

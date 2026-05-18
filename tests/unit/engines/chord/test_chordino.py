"""Unit tests for ChordinoEngine (mocked chord_extractor)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestChordinoEngineInit:
    def test_unavailable_raises(self) -> None:
        from titan_chordpro.core.exceptions import EngineUnavailableError

        with patch.dict(
            "sys.modules",
            {"chord_extractor": None, "chord_extractor.extractors": None},
        ):
            from titan_chordpro.engines.chord.chordino import ChordinoEngine

            with pytest.raises(EngineUnavailableError, match="chord_extractor"):
                ChordinoEngine()

    def test_info_and_protocol_properties(self) -> None:
        from titan_chordpro.engines.chord.chordino import ChordinoEngine

        engine = ChordinoEngine.__new__(ChordinoEngine)
        info = engine.info
        assert info.name == "chordino"
        assert info.backend == "cpu"
        assert engine.vocabulary == "majmin"
        # Chordino does NOT decode inversions natively. Bass is supplied
        # separately when the bass stem is passed; the wrapper synthesizes
        # slash chords via bass_note.
        assert engine.supports_inversions is False


@pytest.mark.unit
class TestChordinoEngineDetect:
    def test_detect_translates_chord_extractor_output(self, tmp_path: Path) -> None:
        from titan_chordpro.engines.chord.chordino import ChordinoEngine

        # Fake chord_extractor.extractors.Chordino.extract returns objects
        # with .chord (e.g. "C:maj", "G:min7") and .timestamp (float seconds).
        c1 = MagicMock(chord="C:maj", timestamp=0.0)
        c2 = MagicMock(chord="G:min", timestamp=1.5)
        c3 = MagicMock(chord="N", timestamp=3.0)  # no-chord; skipped

        fake_extractor = MagicMock()
        fake_extractor.extract = MagicMock(return_value=[c1, c2, c3])

        engine = ChordinoEngine.__new__(ChordinoEngine)
        engine._extractor = fake_extractor

        audio = tmp_path / "song.wav"
        audio.write_bytes(b"x")

        chords = engine.detect(audio)
        assert len(chords) == 2
        assert chords[0].symbol == "C"
        assert chords[0].timestamp.start == 0.0
        assert chords[0].timestamp.end == 1.5
        assert chords[1].symbol == "Gm"
        assert chords[1].timestamp.start == 1.5
        assert chords[1].source_engine == "chordino"

    def test_detect_with_bass_stem_synthesizes_slash(self, tmp_path: Path) -> None:
        """When bass_stem provided, wrapper attaches bass_note from a 2nd pass.

        For Phase B, the bass_note is simply set to None (Chordino does not
        return bass info via chord_extractor). Future Phase B bug-fix may add
        a Cepstrum-based bass detection pass — out of scope here.
        """
        from titan_chordpro.engines.chord.chordino import ChordinoEngine

        c1 = MagicMock(chord="C:maj", timestamp=0.0)
        fake_extractor = MagicMock()
        fake_extractor.extract = MagicMock(return_value=[c1])

        engine = ChordinoEngine.__new__(ChordinoEngine)
        engine._extractor = fake_extractor

        audio = tmp_path / "song.wav"
        audio.write_bytes(b"x")
        bass = tmp_path / "bass.wav"
        bass.write_bytes(b"x")

        chords = engine.detect(audio, bass_stem=bass)
        assert len(chords) == 1
        assert chords[0].bass_note is None  # Phase B baseline behavior

    def test_detect_empty_chord_list(self, tmp_path: Path) -> None:
        from titan_chordpro.engines.chord.chordino import ChordinoEngine

        fake_extractor = MagicMock()
        fake_extractor.extract = MagicMock(return_value=[])

        engine = ChordinoEngine.__new__(ChordinoEngine)
        engine._extractor = fake_extractor

        audio = tmp_path / "song.wav"
        audio.write_bytes(b"x")

        # Empty output is acceptable per spec Section 5: percussive audio
        # produces no chords; pipeline continues with LyricLines without
        # chord markers.
        chords = engine.detect(audio)
        assert chords == []

    def test_detect_native_failure_wrapped(self, tmp_path: Path) -> None:
        from titan_chordpro.core.exceptions import ChordRecognitionError
        from titan_chordpro.engines.chord.chordino import ChordinoEngine

        fake_extractor = MagicMock()
        fake_extractor.extract = MagicMock(side_effect=RuntimeError("vamp boom"))

        engine = ChordinoEngine.__new__(ChordinoEngine)
        engine._extractor = fake_extractor

        audio = tmp_path / "song.wav"
        audio.write_bytes(b"x")

        with pytest.raises(ChordRecognitionError, match="chordino"):
            engine.detect(audio)

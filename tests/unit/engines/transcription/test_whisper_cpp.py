# tests/unit/engines/transcription/test_whisper_cpp.py
"""Unit tests for WhisperCppEngine wrapper (mocked native call)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestWhisperCppEngineInit:
    def test_unavailable_raises(self) -> None:
        from titan_chordpro.core.exceptions import EngineUnavailableError

        with patch.dict("sys.modules", {"pywhispercpp": None, "pywhispercpp.model": None}):
            from titan_chordpro.engines.transcription.whisper_cpp import WhisperCppEngine

            with pytest.raises(EngineUnavailableError, match="pywhispercpp"):
                WhisperCppEngine()

    def test_info_default_backend_is_cpu(self) -> None:
        # whisper.cpp runs natively; backend in EngineInfo is always "cpu"
        # because torch is not used. MPS/CUDA backends are reserved for engines
        # that actually dispatch through torch.
        from titan_chordpro.engines.transcription.whisper_cpp import WhisperCppEngine

        engine = WhisperCppEngine.__new__(WhisperCppEngine)
        engine._model_id = "base"
        info = engine.info
        assert info.name == "whisper_cpp"
        assert info.backend == "cpu"
        assert info.model_id == "base"


@pytest.mark.unit
class TestWhisperCppEngineTranscribe:
    def test_transcribe_builds_words_only(self, tmp_path: Path) -> None:
        """whisper.cpp output → list[WordEvent], phonemes=None."""
        import numpy as np

        from titan_chordpro.engines.transcription.whisper_cpp import WhisperCppEngine

        seg = MagicMock()
        seg.t0 = 100  # 1.00s (whisper.cpp uses centiseconds)
        seg.t1 = 150  # 1.50s
        seg.text = "Hello"

        fake_model = MagicMock()
        fake_model.transcribe = MagicMock(return_value=[seg])

        engine = WhisperCppEngine.__new__(WhisperCppEngine)
        engine._model_id = "base"
        engine._model = fake_model

        # Phase C T70 iter: wrapper now resamples via librosa.load; patch it.
        with patch("librosa.load", return_value=(np.zeros(16000, dtype=np.float32), 16000)):
            result = engine.transcribe(tmp_path / "vocals.wav", language="en")

        assert result.phonemes is None
        assert len(result.words) == 1
        word = result.words[0]
        assert word.text == "Hello"
        assert word.timestamp.start == 1.0
        assert word.timestamp.end == 1.5
        assert word.source_engine == "whisper_cpp"
        assert word.language == "en"
        assert result.detected_language == "en"

    def test_transcribe_empty_audio_returns_empty_words(self, tmp_path: Path) -> None:
        """No segments returned → words=[], phonemes=None, no exception."""
        import numpy as np

        from titan_chordpro.engines.transcription.whisper_cpp import WhisperCppEngine

        fake_model = MagicMock()
        fake_model.transcribe = MagicMock(return_value=[])

        engine = WhisperCppEngine.__new__(WhisperCppEngine)
        engine._model_id = "base"
        engine._model = fake_model

        with patch("librosa.load", return_value=(np.zeros(16000, dtype=np.float32), 16000)):
            result = engine.transcribe(tmp_path / "silent.wav")

        assert result.words == []
        assert result.phonemes is None

    def test_transcribe_native_failure_wrapped(self, tmp_path: Path) -> None:
        from titan_chordpro.core.exceptions import TranscriptionError
        from titan_chordpro.engines.transcription.whisper_cpp import WhisperCppEngine

        fake_model = MagicMock()
        fake_model.transcribe = MagicMock(side_effect=RuntimeError("boom"))

        engine = WhisperCppEngine.__new__(WhisperCppEngine)
        engine._model_id = "base"
        engine._model = fake_model

        with pytest.raises(TranscriptionError, match="whisper_cpp"):
            engine.transcribe(tmp_path / "vocals.wav")


@pytest.mark.unit
class TestWhisperSpecialTokenFilter:
    """Phase C T70 iter: whisper.cpp marks instrumentals with [Música]
    etc. — those tokens crash the MMS aligner (KeyError on '['). The
    wrapper must drop them at the boundary."""

    def _make_engine(self, segments):
        import numpy as np

        from titan_chordpro.engines.transcription.whisper_cpp import WhisperCppEngine

        fake_model = MagicMock()
        fake_model.transcribe = MagicMock(return_value=segments)
        engine = WhisperCppEngine.__new__(WhisperCppEngine)
        engine._model_id = "base"
        engine._model = fake_model
        return engine, np.zeros(16000, dtype=np.float32)

    def test_drops_musica_token(self, tmp_path: Path) -> None:
        s1 = MagicMock(t0=0, t1=100, text="[Música]")
        s2 = MagicMock(t0=100, t1=200, text="Hello")
        engine, fake_audio = self._make_engine([s1, s2])
        with patch("librosa.load", return_value=(fake_audio, 16000)):
            result = engine.transcribe(tmp_path / "vocals.wav")
        assert [w.text for w in result.words] == ["Hello"]

    def test_drops_blank_audio_token(self, tmp_path: Path) -> None:
        s1 = MagicMock(t0=0, t1=100, text="[BLANK_AUDIO]")
        s2 = MagicMock(t0=100, t1=200, text="world")
        engine, fake_audio = self._make_engine([s1, s2])
        with patch("librosa.load", return_value=(fake_audio, 16000)):
            result = engine.transcribe(tmp_path / "vocals.wav")
        assert [w.text for w in result.words] == ["world"]

    def test_keeps_words_with_brackets_inside(self, tmp_path: Path) -> None:
        """Only WHOLE-segment [...] tokens are dropped; mixed text stays."""
        s1 = MagicMock(t0=0, t1=100, text="Hello [pause] world")
        engine, fake_audio = self._make_engine([s1])
        with patch("librosa.load", return_value=(fake_audio, 16000)):
            result = engine.transcribe(tmp_path / "vocals.wav")
        assert [w.text for w in result.words] == ["Hello [pause] world"]

    def test_drops_empty_brackets(self, tmp_path: Path) -> None:
        s1 = MagicMock(t0=0, t1=100, text="[]")
        s2 = MagicMock(t0=100, t1=200, text="ok")
        engine, fake_audio = self._make_engine([s1, s2])
        with patch("librosa.load", return_value=(fake_audio, 16000)):
            result = engine.transcribe(tmp_path / "vocals.wav")
        assert [w.text for w in result.words] == ["ok"]

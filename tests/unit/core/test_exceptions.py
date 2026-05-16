# tests/unit/core/test_exceptions.py
"""Tests for TitanError hierarchy."""

import pytest

from titan_chordpro.core.exceptions import (
    AlignmentError,
    BeatTrackingError,
    ChordRecognitionError,
    EngineUnavailableError,
    FusionError,
    SeparationError,
    SyllabificationError,
    TitanConfigError,
    TitanError,
    TranscriptionError,
    WriterError,
)


@pytest.mark.unit
class TestTitanError:
    def test_minimal(self) -> None:
        err = TitanError("something failed")
        assert str(err) == "something failed"

    def test_with_context(self) -> None:
        err = TitanError(
            "transcription failed",
            audio_id="abc1234567890",
            stage="transcription",
            engine="whisper_cpp",
        )
        s = str(err)
        assert "transcription failed" in s
        assert "stage=transcription" in s
        assert "engine=whisper_cpp" in s
        assert "audio_id=abc123456789" in s  # truncated to 12

    def test_with_cause(self) -> None:
        inner = RuntimeError("CUDA OOM")
        err = TranscriptionError(
            "failed",
            cause=inner,
        )
        assert "caused_by=RuntimeError" in str(err)
        assert "CUDA OOM" in str(err)


@pytest.mark.unit
class TestErrorHierarchy:
    @pytest.mark.parametrize(
        "cls",
        [
            SeparationError,
            TranscriptionError,
            AlignmentError,
            ChordRecognitionError,
            BeatTrackingError,
            SyllabificationError,
            FusionError,
            WriterError,
        ],
    )
    def test_stage_errors_inherit_from_titan_error(self, cls: type) -> None:
        assert issubclass(cls, TitanError)

    def test_config_errors_inherit(self) -> None:
        assert issubclass(TitanConfigError, TitanError)
        assert issubclass(EngineUnavailableError, TitanConfigError)

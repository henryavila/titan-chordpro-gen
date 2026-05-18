# tests/unit/engines/alignment/test_torchaudio_align.py
"""Unit tests for TorchaudioAlignEngine (mocked torch/torchaudio calls)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestTorchaudioAlignEngineInit:
    def test_unavailable_raises(self) -> None:
        from titan_chordpro.core.exceptions import EngineUnavailableError

        with patch.dict("sys.modules", {"torchaudio": None, "torchaudio.functional": None}):
            from titan_chordpro.engines.alignment.torchaudio_align import (
                TorchaudioAlignEngine,
            )

            with pytest.raises(EngineUnavailableError, match="torchaudio"):
                TorchaudioAlignEngine()

    def test_info_reports_backend(self) -> None:
        from titan_chordpro.engines.alignment.torchaudio_align import (
            TorchaudioAlignEngine,
        )

        engine = TorchaudioAlignEngine.__new__(TorchaudioAlignEngine)
        engine._backend = "cpu"
        info = engine.info
        assert info.name == "torchaudio_align"
        assert info.backend == "cpu"


@pytest.mark.unit
class TestTorchaudioAlignEngineAlign:
    def test_align_translates_frames_to_seconds(self, tmp_path: Path) -> None:
        """Mock the inner _run_forced_align call to verify shape conversion."""
        from titan_chordpro.core.schemas import TimeStamp, WordEvent
        from titan_chordpro.engines.alignment.torchaudio_align import (
            TorchaudioAlignEngine,
        )

        engine = TorchaudioAlignEngine.__new__(TorchaudioAlignEngine)
        engine._backend = "cpu"
        # Fake forced_align result: 3 tokens spanning frames 0-9, 10-19, 20-29.
        # At 16kHz sample_rate and stride 320 samples → 0.02s per frame.
        # So token spans become: [0.00, 0.20], [0.20, 0.40], [0.40, 0.60]
        engine._run_forced_align = MagicMock(
            return_value=[
                {"text": "h", "start_frame": 0, "end_frame": 9, "word_idx": 0},
                {"text": "e", "start_frame": 10, "end_frame": 19, "word_idx": 0},
                {"text": "l", "start_frame": 20, "end_frame": 29, "word_idx": 0},
            ]
        )
        engine._frame_seconds = 0.02

        vocals = tmp_path / "vocals.wav"
        vocals.write_bytes(b"x")

        words = [
            WordEvent(
                text="hel",
                timestamp=TimeStamp(start=0.0, end=1.0),
                source_engine="whisper_cpp",
            )
        ]
        result = engine.align(vocals, words, language="en")

        # 1 word with 3 phonemes.
        assert len(result.words) == 1
        assert len(result.phonemes) == 3
        # First phoneme spans frames 0-9 → 0.00-0.18s (9 * 0.02).
        assert result.phonemes[0].timestamp.start == pytest.approx(0.0)
        assert result.phonemes[0].timestamp.end == pytest.approx(0.18, abs=1e-3)
        # Word span = union of its phoneme spans → 0.00-0.58s.
        assert result.words[0].timestamp.start == pytest.approx(0.0)
        assert result.words[0].timestamp.end == pytest.approx(0.58, abs=1e-3)

    def test_align_empty_words_returns_empty_result(self, tmp_path: Path) -> None:
        from titan_chordpro.engines.alignment.torchaudio_align import (
            TorchaudioAlignEngine,
        )

        engine = TorchaudioAlignEngine.__new__(TorchaudioAlignEngine)
        engine._backend = "cpu"
        engine._run_forced_align = MagicMock(return_value=[])
        engine._frame_seconds = 0.02

        vocals = tmp_path / "vocals.wav"
        vocals.write_bytes(b"x")

        result = engine.align(vocals, words=[], language="en")
        assert result.words == []
        assert result.phonemes == []

    def test_align_native_failure_wrapped(self, tmp_path: Path) -> None:
        from titan_chordpro.core.exceptions import AlignmentError
        from titan_chordpro.core.schemas import TimeStamp, WordEvent
        from titan_chordpro.engines.alignment.torchaudio_align import (
            TorchaudioAlignEngine,
        )

        engine = TorchaudioAlignEngine.__new__(TorchaudioAlignEngine)
        engine._backend = "cpu"
        engine._run_forced_align = MagicMock(side_effect=RuntimeError("boom"))
        engine._frame_seconds = 0.02

        vocals = tmp_path / "vocals.wav"
        vocals.write_bytes(b"x")

        words = [
            WordEvent(
                text="h",
                timestamp=TimeStamp(start=0.0, end=1.0),
                source_engine="whisper_cpp",
            )
        ]
        with pytest.raises(AlignmentError, match="torchaudio_align"):
            engine.align(vocals, words, language="en")

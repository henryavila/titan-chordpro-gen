# tests/unit/engines/alignment/test_torchaudio_align.py
"""Unit tests for TorchaudioAlignEngine (mocked torch/torchaudio calls)."""

from __future__ import annotations

from pathlib import Path
from typing import Any
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
        # end_s = (end_frame + 1) * FS marks when the token finishes sounding,
        # so the spans are [0.00, 0.20), [0.20, 0.40), [0.40, 0.60).
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
        # First phoneme spans frames 0-9 → audible [0.00, 0.20) → end = 10 * 0.02.
        assert result.phonemes[0].timestamp.start == pytest.approx(0.0)
        assert result.phonemes[0].timestamp.end == pytest.approx(0.20, abs=1e-3)
        # Word span = union → frames 0-29 → audible [0.00, 0.60).
        assert result.words[0].timestamp.start == pytest.approx(0.0)
        assert result.words[0].timestamp.end == pytest.approx(0.60, abs=1e-3)

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


def _torch_available() -> bool:
    import importlib.util

    return importlib.util.find_spec("torch") is not None


@pytest.mark.unit
@pytest.mark.skipif(not _torch_available(), reason="torch not installed in this venv")
class TestChunkedEmissions:
    """Phase C T70 iter: chunked encoder forward + global emissions stitching.

    The encoder is mocked — we verify the chunking math (window/context/
    stitching/padding trim) by checking how many forward passes happen
    and the final emissions shape.
    """

    def _build_engine_with_fake_model(self, fake_model: Any) -> Any:
        from titan_chordpro.engines.alignment.torchaudio_align import TorchaudioAlignEngine

        engine = TorchaudioAlignEngine.__new__(TorchaudioAlignEngine)
        engine._device = "cpu"
        engine._model = fake_model
        engine._frame_seconds = 0.02
        engine._blank_id = 0
        return engine

    def test_short_audio_single_shot(self) -> None:
        """Audio shorter than window → bypass chunking, single forward."""
        from unittest.mock import MagicMock

        import torch

        # Audio of 10s (= 160000 samples) < 30s window → no chunking.
        fake_emissions = torch.zeros(1, 500, 32)  # ~500 frames for ~10s
        fake_model = MagicMock(return_value=(fake_emissions, None))
        engine = self._build_engine_with_fake_model(fake_model)

        wav = torch.zeros(160000, dtype=torch.float32)
        out = engine._generate_emissions(wav)

        assert fake_model.call_count == 1
        assert out.shape == (1, 500, 32)

    def test_long_audio_chunked_with_correct_chunk_count(self) -> None:
        """Audio of 90s → 3 chunks of 30s each (after pad to multiple of window)."""
        from unittest.mock import MagicMock

        import torch

        # Emissions shape per (34s) chunk = 1700 frames at 50 fps.
        # We expect the encoder to be called once per batch (batch=1 by default).
        def fake_forward(batch_in):
            n_chunks_in_batch = batch_in.shape[0]
            # 34s @ 50fps = 1700 frames per chunk.
            return (torch.zeros(n_chunks_in_batch, 1700, 32), None)

        fake_model = MagicMock(side_effect=fake_forward)
        engine = self._build_engine_with_fake_model(fake_model)

        # 90s of audio = 1_440_000 samples → 3 chunks of 30s, each with 2s
        # context on each side → encoder called 3 times (batch_size=1).
        wav = torch.zeros(90 * 16000, dtype=torch.float32)
        out = engine._generate_emissions(wav, window_sec=30, context_sec=2, batch_size=1)

        assert fake_model.call_count == 3
        # After cropping 100 frames (2s * 50fps) from each side and stitching:
        # 3 chunks * (1700 - 200) inner frames = 4500 frames. No extension.
        assert out.shape == (1, 4500, 32)

    def test_chunking_batched(self) -> None:
        """batch_size=2 should cut the forward count to ceil(num_chunks/2)."""
        from unittest.mock import MagicMock

        import torch

        def fake_forward(batch_in):
            n = batch_in.shape[0]
            return (torch.zeros(n, 1700, 32), None)

        fake_model = MagicMock(side_effect=fake_forward)
        engine = self._build_engine_with_fake_model(fake_model)

        wav = torch.zeros(90 * 16000, dtype=torch.float32)  # 3 chunks
        engine._generate_emissions(wav, window_sec=30, context_sec=2, batch_size=2)

        # 3 chunks / batch=2 → 2 forwards (one of size 2, one of size 1).
        assert fake_model.call_count == 2

    def test_extension_padding_trimmed(self) -> None:
        """Non-multiple audio length → padded then trimmed in emissions."""
        from unittest.mock import MagicMock

        import torch

        # 35s audio: pad to 60s (2 chunks of 30s).
        def fake_forward(batch_in):
            n = batch_in.shape[0]
            return (torch.zeros(n, 1700, 32), None)

        fake_model = MagicMock(side_effect=fake_forward)
        engine = self._build_engine_with_fake_model(fake_model)

        wav = torch.zeros(35 * 16000, dtype=torch.float32)
        out = engine._generate_emissions(wav, window_sec=30, context_sec=2, batch_size=1)

        # 2 chunks, each contributes 1500 inner frames after context crop.
        # Padded extension = 25s = 1250 frames → trimmed.
        # Final length ≈ 2*1500 - 1250 = 1750 frames.
        assert fake_model.call_count == 2
        assert out.shape[1] == 1750


@pytest.mark.unit
class TestSanitizeForMms:
    """Phase C T70 iter: whisper returns multi-word segments with spaces/
    punctuation that crash the MMS tokenizer. Sanitizer strips them."""

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("hello world", "helloworld"),
            ("Tudo que há de bom em mim", "Tudoquehádebomemmim"),
            ("Senhor,", "Senhor"),
            ("a-b-c", "abc"),
            ("a'b", "ab"),
            ("123 abc", "abc"),
            ("", ""),
            ("   ", ""),
            ("é à õ ç", "éàõç"),  # PT-BR accents preserved
        ],
    )
    def test_sanitize(self, raw: str, expected: str) -> None:
        from titan_chordpro.engines.alignment.torchaudio_align import _sanitize_for_mms

        assert _sanitize_for_mms(raw) == expected

"""Unit tests for HtdemucsEngine wrapper (mocked separator)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestHtdemucsEngineInit:
    def test_unavailable_raises(self) -> None:
        from titan_chordpro.core.exceptions import EngineUnavailableError

        with patch.dict(
            "sys.modules", {"audio_separator": None, "audio_separator.separator": None}
        ):
            from titan_chordpro.engines.separation.htdemucs import HtdemucsEngine

            with pytest.raises(EngineUnavailableError, match="audio_separator"):
                HtdemucsEngine()

    def test_info_reports_engine_and_backend(self) -> None:
        from titan_chordpro.engines.separation.htdemucs import HtdemucsEngine

        engine = HtdemucsEngine.__new__(HtdemucsEngine)
        engine._backend = "cpu"
        info = engine.info
        assert info.name == "htdemucs_ft"
        assert info.backend == "cpu"
        assert info.model_id == "htdemucs_ft"

    def test_load_separator_passes_use_cuda_when_backend_cuda(self, tmp_path: Path) -> None:
        """_load_separator must propagate backend to audio_separator (F-004).

        Pre-fix bug: backend was accepted by HtdemucsEngine.__init__ but never
        forwarded to Separator(), so --device cuda had no effect on separation.
        """
        from titan_chordpro.engines.separation import htdemucs as mod

        captured: dict[str, object] = {}

        class FakeSeparator:
            def __init__(self, **kwargs):
                captured.update(kwargs)

            def load_model(self, model_filename):  # noqa: D401
                captured["model_filename"] = model_filename

        with patch.object(mod, "_load_separator", wraps=mod._load_separator):
            with patch.dict(
                "sys.modules", {"audio_separator.separator": MagicMock(Separator=FakeSeparator)}
            ):
                mod._load_separator("cuda", tmp_path)
        assert (
            captured.get("use_cuda") is True
        ), f"backend='cuda' did not produce use_cuda=True kwarg; got {captured!r}"

    def test_load_separator_falls_back_on_typeerror(self, tmp_path: Path) -> None:
        """When audio_separator rejects backend kwargs (older version), the
        loader must fall back to default args without crashing."""
        from titan_chordpro.engines.separation import htdemucs as mod

        call_count = {"n": 0}

        class OldSeparator:
            def __init__(self, **kwargs):
                # First call (with use_cuda) rejected; second call (defaults) accepted.
                call_count["n"] += 1
                if "use_cuda" in kwargs or "use_cpu" in kwargs:
                    raise TypeError("unexpected keyword argument 'use_cuda'")

            def load_model(self, model_filename):
                pass

        with patch.dict(
            "sys.modules", {"audio_separator.separator": MagicMock(Separator=OldSeparator)}
        ):
            mod._load_separator("cuda", tmp_path)
        assert call_count["n"] == 2  # initial TypeError + retry with defaults


@pytest.mark.unit
class TestHtdemucsEngineSeparate:
    def test_separate_builds_stemset_from_separator_output(self, tmp_path: Path) -> None:
        """Mock the separator; verify StemSet field assembly."""
        from titan_chordpro.engines.separation.htdemucs import HtdemucsEngine

        # Fake source audio.
        audio = tmp_path / "song.wav"
        audio.write_bytes(b"FAKE_AUDIO_DATA")
        expected_sha = hashlib.sha256(b"FAKE_AUDIO_DATA").hexdigest()

        # Fake stem outputs the separator would create.
        out_dir = tmp_path / "stems"
        out_dir.mkdir()
        for stem in ("Vocals", "Bass", "Drums", "Other"):
            (out_dir / f"song_({stem})_htdemucs_ft.wav").write_bytes(b"STEM")

        # Mocked separator.
        fake_sep = MagicMock()
        fake_sep.separate.return_value = [
            "song_(Vocals)_htdemucs_ft.wav",
            "song_(Bass)_htdemucs_ft.wav",
            "song_(Drums)_htdemucs_ft.wav",
            "song_(Other)_htdemucs_ft.wav",
        ]
        fake_sep.model_file_dir = str(out_dir)
        fake_sep.output_dir = str(out_dir)

        engine = HtdemucsEngine.__new__(HtdemucsEngine)
        engine._backend = "cpu"
        engine._separator = fake_sep
        engine._output_dir = out_dir

        # Also patch soundfile reading for duration probe.
        with patch("titan_chordpro.engines.separation.htdemucs._probe_duration", return_value=30.0):
            stems = engine.separate(audio)

        assert stems.audio_id == expected_sha
        assert stems.vocals.name.endswith("(Vocals)_htdemucs_ft.wav")
        assert stems.bass.name.endswith("(Bass)_htdemucs_ft.wav")
        assert stems.drums.name.endswith("(Drums)_htdemucs_ft.wav")
        assert stems.other.name.endswith("(Other)_htdemucs_ft.wav")
        assert stems.sample_rate == 44100
        assert stems.duration == 30.0
        assert stems.source_engine == "htdemucs_ft"

    def test_separate_missing_stem_raises(self, tmp_path: Path) -> None:
        from titan_chordpro.core.exceptions import SeparationError
        from titan_chordpro.engines.separation.htdemucs import HtdemucsEngine

        audio = tmp_path / "song.wav"
        audio.write_bytes(b"x")

        fake_sep = MagicMock()
        fake_sep.separate.return_value = ["song_(Vocals)_htdemucs_ft.wav"]  # only 1 stem
        fake_sep.output_dir = str(tmp_path)

        engine = HtdemucsEngine.__new__(HtdemucsEngine)
        engine._backend = "cpu"
        engine._separator = fake_sep
        engine._output_dir = tmp_path

        with pytest.raises(SeparationError, match="expected 4 stems"):
            engine.separate(audio)

# tests/unit/engines/beat/test_beatthis.py
"""Unit tests for BeatThisEngine wrapper.

These tests do NOT load the real model — they mock the underlying call.
The integration smoke (T40) is the test that exercises model loading.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestBeatThisEngineInfo:
    def test_info_reports_engine_name_and_backend(self) -> None:
        from titan_chordpro.engines.beat.beatthis import BeatThisEngine

        engine = BeatThisEngine.__new__(BeatThisEngine)  # bypass __init__
        engine._backend = "cpu"
        info = engine.info
        assert info.name == "beat_this"
        assert info.backend == "cpu"
        assert info.version  # non-empty

    def test_supports_variable_tempo_true(self) -> None:
        from titan_chordpro.engines.beat.beatthis import BeatThisEngine

        engine = BeatThisEngine.__new__(BeatThisEngine)
        assert engine.supports_variable_tempo is True

    def test_supports_meter_detection_false(self) -> None:
        # BeatThis predicts beats + downbeats but not meter signature.
        from titan_chordpro.engines.beat.beatthis import BeatThisEngine

        engine = BeatThisEngine.__new__(BeatThisEngine)
        assert engine.supports_meter_detection is False


@pytest.mark.unit
class TestBeatThisEngineTrack:
    def test_track_unavailable_raises(self) -> None:
        """When beat_this package is not importable, __init__ raises."""
        from titan_chordpro.core.exceptions import EngineUnavailableError

        with patch.dict("sys.modules", {"beat_this": None, "beat_this.inference": None}):
            from titan_chordpro.engines.beat.beatthis import BeatThisEngine

            with pytest.raises(EngineUnavailableError, match="beat_this"):
                BeatThisEngine()

    def test_track_builds_beatgrid_from_inference(self, tmp_path: Path) -> None:
        """Mock the underlying File2Beats call and assert schema round-trip."""
        from titan_chordpro.engines.beat.beatthis import BeatThisEngine

        # Fake beat_this.inference.File2Beats — returns (beats, downbeats).
        fake_beats = [0.5, 1.0, 1.5, 2.0]
        fake_downbeats = [0.5, 2.0]

        fake_audio = tmp_path / "x.wav"
        fake_audio.write_bytes(b"RIFF")  # placeholder; never read

        engine = BeatThisEngine.__new__(BeatThisEngine)
        engine._backend = "cpu"
        engine._file2beats = MagicMock(return_value=(fake_beats, fake_downbeats))

        grid = engine.track(fake_audio)
        assert grid.beats == fake_beats
        assert grid.downbeat_indices == [0, 3]
        assert grid.bpm == pytest.approx(120.0, abs=2.0)
        assert grid.source_engine == "beat_this"

    def test_track_empty_beats_raises(self, tmp_path: Path) -> None:
        from titan_chordpro.core.exceptions import BeatTrackingError
        from titan_chordpro.engines.beat.beatthis import BeatThisEngine

        engine = BeatThisEngine.__new__(BeatThisEngine)
        engine._backend = "cpu"
        engine._file2beats = MagicMock(return_value=([], []))

        with pytest.raises(BeatTrackingError, match="empty"):
            engine.track(tmp_path / "x.wav")

"""Factory selects real engines when extras are present, mocks otherwise."""

from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.mark.integration
class TestFactoryRealSelection:
    def test_select_beat_tracking_returns_beatthis_when_available(self) -> None:
        pytest.importorskip("beat_this", reason="beat_this not installed")
        from titan_chordpro.engines.beat.beatthis import BeatThisEngine
        from titan_chordpro.factory import select_beat_tracking

        engine = select_beat_tracking()
        assert isinstance(engine, BeatThisEngine)

    def test_select_beat_tracking_raises_when_unavailable(self) -> None:
        from titan_chordpro.core.exceptions import EngineUnavailableError
        from titan_chordpro.factory import select_beat_tracking

        # Codex F-002: missing real dep without force_mock → fail-fast.
        with patch.dict("sys.modules", {"beat_this": None, "beat_this.inference": None}):
            with pytest.raises(EngineUnavailableError):
                select_beat_tracking()

    def test_select_chord_recognition_raises_when_no_vamp(self) -> None:
        from titan_chordpro.core.exceptions import EngineUnavailableError
        from titan_chordpro.factory import select_chord_recognition

        with patch.dict(
            "sys.modules",
            {"chord_extractor": None, "chord_extractor.extractors": None},
        ):
            with pytest.raises(EngineUnavailableError):
                select_chord_recognition()

    def test_select_syllabification_pt_force_mock(self) -> None:
        from titan_chordpro.factory import select_syllabification

        engine = select_syllabification(language="pt", force_mock=True)
        assert engine.language == "pt"

    def test_select_syllabification_en_force_mock(self) -> None:
        from titan_chordpro.factory import select_syllabification

        engine = select_syllabification(language="en", force_mock=True)
        assert engine.language == "en"

    def test_select_syllabification_pt_br_normalizes(self) -> None:
        """Codex F-005: pt-BR / pt_BR must normalize to the PT engine path."""
        from titan_chordpro.factory import select_syllabification

        engine = select_syllabification(language="pt-BR", force_mock=True)
        assert engine.language == "pt-BR"  # original tag preserved on the engine

    def test_explicit_override_force_mock(self) -> None:
        from titan_chordpro.factory import select_beat_tracking
        from titan_chordpro.mocks import MockBeatTrackingEngine

        engine = select_beat_tracking(force_mock=True)
        assert isinstance(engine, MockBeatTrackingEngine)

    def test_orchestrator_force_mock_reaches_syllabification(self, tmp_path) -> None:
        """force_mock=True must apply to syllabification too (regression: F-001).

        Pre-fix bug: orchestrator called select_syllabification without
        propagating force_mock, so --device mock could still load real gruut/g2p_en.
        """
        from titan_chordpro.factory import last_selection
        from titan_chordpro.orchestrator import transcribe

        audio = tmp_path / "x.wav"
        audio.write_bytes(b"RIFF")  # bytes don't matter — mocks ignore content

        transcribe(audio, force_mock=True)
        sel = last_selection()
        assert "syllabification" in sel
        assert sel["syllabification"]["real"] is False, (
            f"syllabification used real engine despite force_mock=True: {sel['syllabification']}"
        )

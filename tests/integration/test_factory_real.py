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

    def test_select_beat_tracking_falls_back_to_mock(self) -> None:
        from titan_chordpro.factory import select_beat_tracking
        from titan_chordpro.mocks import MockBeatTrackingEngine

        # Simulate beat_this missing.
        with patch.dict("sys.modules", {"beat_this": None, "beat_this.inference": None}):
            engine = select_beat_tracking()
        assert isinstance(engine, MockBeatTrackingEngine)

    def test_select_chord_recognition_falls_back_when_no_vamp(self) -> None:
        from titan_chordpro.factory import select_chord_recognition
        from titan_chordpro.mocks import MockChordRecognitionEngine

        with patch.dict(
            "sys.modules",
            {"chord_extractor": None, "chord_extractor.extractors": None},
        ):
            engine = select_chord_recognition()
        assert isinstance(engine, MockChordRecognitionEngine)

    def test_select_syllabification_pt(self) -> None:
        from titan_chordpro.factory import select_syllabification

        # gruut may or may not be installed; either way returns something that
        # conforms to the Protocol with language="pt".
        engine = select_syllabification(language="pt")
        assert engine.language == "pt"

    def test_select_syllabification_en(self) -> None:
        from titan_chordpro.factory import select_syllabification

        engine = select_syllabification(language="en")
        assert engine.language == "en"

    def test_explicit_override_force_mock(self) -> None:
        from titan_chordpro.factory import select_beat_tracking
        from titan_chordpro.mocks import MockBeatTrackingEngine

        engine = select_beat_tracking(force_mock=True)
        assert isinstance(engine, MockBeatTrackingEngine)

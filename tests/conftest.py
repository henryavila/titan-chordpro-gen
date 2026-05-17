"""Pytest fixtures wrapping plain mock classes from titan_chordpro.mocks.

Each fixture returns a fresh instance — tests must NOT share state.
Mock implementations live in `titan_chordpro/mocks.py` (importable at
runtime by `factory.py`); this file exposes them as pytest fixtures.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from titan_chordpro.mocks import (
    MockAlignmentEngine,
    MockBeatTrackingEngine,
    MockChordRecognitionEngine,
    MockSourceSeparationEngine,
    MockSyllabificationEngine,
    MockTranscriptionEngine,
)


@pytest.fixture
def mock_separation_engine(tmp_path: Path) -> MockSourceSeparationEngine:
    return MockSourceSeparationEngine(stem_dir=tmp_path)


@pytest.fixture
def mock_transcription_engine() -> MockTranscriptionEngine:
    return MockTranscriptionEngine()


@pytest.fixture
def mock_alignment_engine() -> MockAlignmentEngine:
    return MockAlignmentEngine()


@pytest.fixture
def mock_chord_engine() -> MockChordRecognitionEngine:
    return MockChordRecognitionEngine()


@pytest.fixture
def mock_beat_engine() -> MockBeatTrackingEngine:
    return MockBeatTrackingEngine()


@pytest.fixture
def mock_syllabification_engine() -> MockSyllabificationEngine:
    return MockSyllabificationEngine(language="pt")

"""Engine factory — hardware detection + user override → Protocol-typed instances.

In Phase A, all factories return mock engines (real engines come in Phase B).
The `**overrides` kwarg is where hardware detection results (e.g. backend="mps")
will feed into selection logic in Phase B.
"""

from __future__ import annotations

from titan_chordpro.core.protocols import (
    AlignmentEngine,
    BeatTrackingEngine,
    ChordRecognitionEngine,
    SourceSeparationEngine,
    SyllabificationEngine,
    TranscriptionEngine,
)
from titan_chordpro.mocks import (
    MockAlignmentEngine,
    MockBeatTrackingEngine,
    MockChordRecognitionEngine,
    MockSourceSeparationEngine,
    MockSyllabificationEngine,
    MockTranscriptionEngine,
)


def select_separation(**overrides: object) -> SourceSeparationEngine:
    return MockSourceSeparationEngine()


def select_transcription(**overrides: object) -> TranscriptionEngine:
    return MockTranscriptionEngine()


def select_alignment(**overrides: object) -> AlignmentEngine:
    return MockAlignmentEngine()


def select_chord_recognition(**overrides: object) -> ChordRecognitionEngine:
    return MockChordRecognitionEngine()


def select_beat_tracking(**overrides: object) -> BeatTrackingEngine:
    return MockBeatTrackingEngine()


def select_syllabification(language: str = "pt", **overrides: object) -> SyllabificationEngine:
    return MockSyllabificationEngine(language=language)

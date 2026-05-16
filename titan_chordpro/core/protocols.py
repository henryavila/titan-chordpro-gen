"""Engine Protocols for Titan ChordPro Lib.

The orchestrator depends EXCLUSIVELY on these interfaces. ML implementations
are in titan_chordpro/engines/ (Phase B); mocks are in tests/conftest.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

from titan_chordpro.core.schemas import (
    AlignmentResult,
    BeatGrid,
    ChordEvent,
    EngineInfo,
    PhonemeEvent,
    StemSet,
    SyllableEvent,
    TranscriptionResult,
    WordEvent,
)


@runtime_checkable
class SourceSeparationEngine(Protocol):
    """Separates a mixed audio file into 4 stems: vocals, bass, drums, other."""

    def separate(self, audio: Path) -> StemSet: ...

    @property
    def info(self) -> EngineInfo: ...


@runtime_checkable
class TranscriptionEngine(Protocol):
    """Transcribes vocal stem to words.

    Optionally returns phonemes if the engine has phoneme-level alignment
    built-in (e.g. WhisperX wav2vec2 path). The orchestrator checks
    `result.phonemes is not None` — no separate property needed.
    """

    def transcribe(
        self,
        vocals: Path,
        language: str | None = None,
    ) -> TranscriptionResult: ...

    @property
    def info(self) -> EngineInfo: ...


@runtime_checkable
class AlignmentEngine(Protocol):
    """Refines word timestamps using forced phonetic alignment.

    Used as a post-pass when the TranscriptionEngine's TranscriptionResult
    has phonemes=None.
    """

    def align(
        self,
        vocals: Path,
        words: list[WordEvent],
        language: str,
    ) -> AlignmentResult: ...

    @property
    def info(self) -> EngineInfo: ...


@runtime_checkable
class ChordRecognitionEngine(Protocol):
    """Detects chord progression from harmonic content."""

    def detect(
        self,
        harmonic_mix: Path,
        bass_stem: Path | None = None,
    ) -> list[ChordEvent]: ...

    @property
    def info(self) -> EngineInfo: ...

    @property
    def vocabulary(self) -> Literal["majmin", "sevenths", "tetrads", "extended_170"]: ...

    @property
    def supports_inversions(self) -> bool: ...


@runtime_checkable
class BeatTrackingEngine(Protocol):
    """Tracks beats, downbeats, tempo, and meter."""

    def track(self, audio: Path) -> BeatGrid: ...

    @property
    def info(self) -> EngineInfo: ...

    @property
    def supports_variable_tempo(self) -> bool: ...

    @property
    def supports_meter_detection(self) -> bool: ...


@runtime_checkable
class SyllabificationEngine(Protocol):
    """Decomposes words into syllables with stress detection.

    One implementation per language. When phonemes are provided, syllable
    timestamps are derived from phoneme spans via Maximum Onset Principle.
    When None, syllables are derived from orthography and timestamps are
    linearly interpolated within the parent word.
    """

    def syllabify(
        self,
        words: list[WordEvent],
        phonemes: list[PhonemeEvent] | None = None,
    ) -> list[SyllableEvent]: ...

    @property
    def language(self) -> str: ...

    @property
    def info(self) -> EngineInfo: ...

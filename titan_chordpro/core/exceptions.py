# titan_chordpro/core/exceptions.py
"""Exception hierarchy for Titan ChordPro Gen.

All errors carry rich context (audio_id, stage, engine, cause) so users get
debuggable messages with suggested actions, not bare stacktraces.
"""

from __future__ import annotations


class TitanError(Exception):
    """Base class for all Titan ChordPro errors."""

    def __init__(
        self,
        message: str,
        *,
        audio_id: str | None = None,
        stage: str | None = None,
        engine: str | None = None,
        cause: Exception | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.audio_id = audio_id
        self.stage = stage
        self.engine = engine
        self.cause = cause

    def __str__(self) -> str:
        parts = [self.message]
        if self.stage:
            parts.append(f"stage={self.stage}")
        if self.engine:
            parts.append(f"engine={self.engine}")
        if self.audio_id:
            parts.append(f"audio_id={self.audio_id[:12]}")
        if self.cause:
            parts.append(f"caused_by={type(self.cause).__name__}: {self.cause}")
        return " | ".join(parts)


# Stage-specific subclasses


class SeparationError(TitanError):
    """Source separation failed."""


class TranscriptionError(TitanError):
    """Transcription of vocals failed."""


class AlignmentError(TitanError):
    """Forced alignment of words failed."""


class ChordRecognitionError(TitanError):
    """Chord recognition failed."""


class BeatTrackingError(TitanError):
    """Beat tracking failed."""


class SyllabificationError(TitanError):
    """Syllabification failed."""


class FusionError(TitanError):
    """Fusion engine failed (placement, sectioning, etc.)."""


class WriterError(TitanError):
    """Output writer failed (profile rendering, file IO)."""


# Configuration / environment errors


class TitanConfigError(TitanError):
    """User-supplied configuration is invalid."""


class EngineUnavailableError(TitanConfigError):
    """Requested engine is not installed or hardware not supported."""

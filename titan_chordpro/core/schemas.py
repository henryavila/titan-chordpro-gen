# titan_chordpro/core/schemas.py
"""Pydantic v2 schemas for Titan ChordPro Lib.

All inter-module communication uses these models. Validation is fail-fast:
invalid data raises pydantic.ValidationError at construction time.
"""

from __future__ import annotations

from typing import Annotated, Self

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

# Confidence: float in [0, 1]
Confidence = Annotated[float, Field(ge=0.0, le=1.0)]


class TimeStamp(BaseModel):
    """Time interval in seconds from start of audio."""

    start: float = Field(ge=0)
    end: float = Field(ge=0)

    @field_validator("end")
    @classmethod
    def end_not_before_start(cls, v: float, info: ValidationInfo) -> float:
        # In Pydantic v2 field_validators receive ValidationInfo.
        start = info.data.get("start")
        if start is not None and v < start:
            raise ValueError("end must be >= start")
        return v

    @property
    def duration(self) -> float:
        return self.end - self.start


class WordEvent(BaseModel):
    """A transcribed word with timestamp and confidence."""

    text: str
    timestamp: TimeStamp
    confidence: Confidence = 1.0
    source_engine: str
    language: str | None = None  # ISO 639-1


class PhonemeEvent(BaseModel):
    """A phoneme (IPA or ARPABET) with timestamp and word reference."""

    symbol: str
    timestamp: TimeStamp
    parent_word_idx: int = Field(ge=0)
    confidence: Confidence = 1.0


class SyllableEvent(BaseModel):
    """A syllable derived from phonemes via Maximum Onset Principle, or from
    orthography when phonemes are unavailable."""

    text: str
    phoneme_indices: list[int] = Field(default_factory=list)
    timestamp: TimeStamp
    is_stressed: bool
    parent_word_idx: int = Field(ge=0)
    confidence: Confidence = 1.0


class ChordEvent(BaseModel):
    """A detected chord with optional bass note for slash-chord support.

    `bass_note` may be supplied independently when the engine extracted bass
    from the bass stem. When `symbol` already encodes a slash chord (e.g. "C/E"),
    `bass_note` MUST agree or be None — enforced by validator.
    """

    symbol: str
    timestamp: TimeStamp
    bass_note: str | None = None
    confidence: Confidence = 1.0
    source_engine: str

    @model_validator(mode="after")
    def validate_bass_consistency(self) -> Self:
        if "/" in self.symbol and self.bass_note is not None:
            symbol_bass = self.symbol.rsplit("/", 1)[1].strip()
            if symbol_bass != self.bass_note:
                raise ValueError(
                    f"chord symbol bass {symbol_bass!r} disagrees with "
                    f"bass_note field {self.bass_note!r}"
                )
        return self

    @property
    def is_slash(self) -> bool:
        return "/" in self.symbol or self.bass_note is not None

    @property
    def effective_bass(self) -> str | None:
        if self.bass_note:
            return self.bass_note
        if "/" in self.symbol:
            return self.symbol.rsplit("/", 1)[1].strip()
        return None

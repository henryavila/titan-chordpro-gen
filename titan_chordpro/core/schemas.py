# titan_chordpro/core/schemas.py
"""Pydantic v2 schemas for Titan ChordPro Lib.

All inter-module communication uses these models. Validation is fail-fast:
invalid data raises pydantic.ValidationError at construction time.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal, Self

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


class BeatGrid(BaseModel):
    """Beat positions, downbeats, tempo, and meter for a song."""

    beats: list[float]
    downbeat_indices: list[int]
    bpm: float = Field(gt=0)
    bpm_variable: bool = False
    meter: tuple[int, int] = (4, 4)
    confidence: Confidence = 1.0
    source_engine: str = ""

    @field_validator("beats")
    @classmethod
    def beats_monotonic(cls, v: list[float]) -> list[float]:
        for i in range(len(v) - 1):
            if v[i] >= v[i + 1]:
                raise ValueError("beats must be strictly monotonically increasing")
        return v

    @field_validator("meter")
    @classmethod
    def meter_valid(cls, v: tuple[int, int]) -> tuple[int, int]:
        if v[0] <= 0 or v[1] not in {2, 4, 8, 16}:
            raise ValueError(
                f"invalid meter {v}: numerator must be > 0, denominator in {{2,4,8,16}}"
            )
        return v


class StemSet(BaseModel):
    """Output of source separation: 4 stem files + metadata."""

    audio_id: str  # sha256 of source audio
    vocals: Path
    bass: Path
    drums: Path
    other: Path
    sample_rate: int = 44100
    duration: float = Field(gt=0)
    source_engine: str


class TranscriptionResult(BaseModel):
    """Output of a TranscriptionEngine."""

    words: list[WordEvent]
    phonemes: list[PhonemeEvent] | None = None
    detected_language: str | None = None


class AlignmentResult(BaseModel):
    """Output of an AlignmentEngine."""

    words: list[WordEvent]
    phonemes: list[PhonemeEvent]


class ChordMarker(BaseModel):
    """A chord pinned to a specific character position in a rendered line."""

    chord: ChordEvent
    char_position: int = Field(ge=0)
    placement_strategy: Literal[
        "melisma_start",
        "stressed_syllable",
        "any_syllable",
        "before_word",
        "beat_boundary",
    ]


class LyricLine(BaseModel):
    """A line of lyrics with chord markers placed at character positions."""

    line_type: Literal["lyric"] = "lyric"
    text: str
    chord_markers: list[ChordMarker] = Field(default_factory=list)
    word_alignments: list[WordEvent] = Field(default_factory=list)
    syllable_alignments: list[SyllableEvent] = Field(default_factory=list)
    confidence: Confidence = 1.0


class InstrumentalLine(BaseModel):
    """A line representing instrumental measures (intro, solo break, outro)."""

    line_type: Literal["instrumental"] = "instrumental"
    chords: list[ChordEvent]
    measures: int = Field(gt=0)
    pattern_hint: Literal["full_measure", "half_measure", "beat"] = "full_measure"
    label: str | None = None


# Discriminated union for type-safe section content
Line = Annotated[LyricLine | InstrumentalLine, Field(discriminator="line_type")]


class Section(BaseModel):
    """A song section: verse, chorus, bridge, instrumental."""

    type: Literal[
        "verse",
        "chorus",
        "bridge",
        "pre-chorus",
        "instrumental",
        "intro",
        "outro",
    ]
    label: str
    lines: list[Line]
    timestamp: TimeStamp


class Metadata(BaseModel):
    """Structured song metadata. Maps to ChordPro {directives}."""

    title: str
    artist: str | None = None
    key: str | None = None
    tempo: int | None = Field(default=None, ge=20, le=300)
    time_signature: tuple[int, int] | None = None
    capo: int = Field(default=0, ge=0, le=12)
    extensions: dict[str, str] = Field(default_factory=dict)

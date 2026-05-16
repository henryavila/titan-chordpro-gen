# titan_chordpro/core/schemas.py
"""Pydantic v2 schemas for Titan ChordPro Lib.

All inter-module communication uses these models. Validation is fail-fast:
invalid data raises pydantic.ValidationError at construction time.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, ValidationInfo, field_validator

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

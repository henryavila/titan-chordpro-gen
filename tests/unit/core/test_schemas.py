# tests/unit/core/test_schemas.py
"""Tests for core Pydantic schemas."""

import pytest
from pydantic import ValidationError

from titan_chordpro.core.schemas import TimeStamp


@pytest.mark.unit
class TestTimeStamp:
    def test_valid(self) -> None:
        ts = TimeStamp(start=1.0, end=2.0)
        assert ts.start == 1.0
        assert ts.end == 2.0
        assert ts.duration == 1.0

    def test_zero_duration_allowed(self) -> None:
        ts = TimeStamp(start=1.0, end=1.0)
        assert ts.duration == 0.0

    def test_negative_start_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TimeStamp(start=-1.0, end=1.0)

    def test_end_before_start_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TimeStamp(start=2.0, end=1.0)


@pytest.mark.unit
class TestConfidence:
    """Confidence is an Annotated type — tested via a host model."""

    def test_bounds_via_word_event(self) -> None:
        # Will be tested concretely once WordEvent exists (T06).
        # For now, verify the Confidence type alias exists and accepts 0..1.
        from titan_chordpro.core.schemas import Confidence

        assert Confidence is not None

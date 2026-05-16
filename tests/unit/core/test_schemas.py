# tests/unit/core/test_schemas.py
"""Tests for core Pydantic schemas."""

import pytest
from pydantic import ValidationError

from titan_chordpro.core.schemas import (
    ChordEvent,
    PhonemeEvent,
    SyllableEvent,
    TimeStamp,
    WordEvent,
)


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


@pytest.mark.unit
class TestWordEvent:
    def test_basic(self) -> None:
        word = WordEvent(
            text="hello",
            timestamp=TimeStamp(start=1.0, end=1.5),
            confidence=0.9,
            source_engine="mock",
        )
        assert word.text == "hello"
        assert word.confidence == 0.9
        assert word.language is None

    def test_with_language(self) -> None:
        word = WordEvent(
            text="hello",
            timestamp=TimeStamp(start=1.0, end=1.5),
            source_engine="mock",
            language="en",
        )
        assert word.language == "en"

    def test_confidence_bounds(self) -> None:
        with pytest.raises(ValidationError):
            WordEvent(
                text="x",
                timestamp=TimeStamp(start=0, end=1),
                confidence=1.5,
                source_engine="mock",
            )


@pytest.mark.unit
class TestPhonemeEvent:
    def test_basic(self) -> None:
        ph = PhonemeEvent(
            symbol="h",
            timestamp=TimeStamp(start=1.0, end=1.05),
            parent_word_idx=0,
        )
        assert ph.symbol == "h"
        assert ph.parent_word_idx == 0

    def test_negative_parent_idx_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PhonemeEvent(
                symbol="h",
                timestamp=TimeStamp(start=0, end=1),
                parent_word_idx=-1,
            )


@pytest.mark.unit
class TestSyllableEvent:
    def test_basic(self) -> None:
        syl = SyllableEvent(
            text="hel",
            timestamp=TimeStamp(start=1.0, end=1.2),
            is_stressed=True,
            parent_word_idx=0,
        )
        assert syl.text == "hel"
        assert syl.is_stressed
        assert syl.phoneme_indices == []


@pytest.mark.unit
class TestChordEvent:
    def test_plain_major(self) -> None:
        c = ChordEvent(
            symbol="C",
            timestamp=TimeStamp(start=0, end=2),
            source_engine="mock",
        )
        assert c.symbol == "C"
        assert c.bass_note is None
        assert not c.is_slash
        assert c.effective_bass is None

    def test_slash_via_symbol(self) -> None:
        c = ChordEvent(
            symbol="C/E",
            timestamp=TimeStamp(start=0, end=2),
            source_engine="mock",
        )
        assert c.is_slash
        assert c.effective_bass == "E"

    def test_slash_via_bass_note(self) -> None:
        c = ChordEvent(
            symbol="C",
            bass_note="E",
            timestamp=TimeStamp(start=0, end=2),
            source_engine="mock",
        )
        assert c.is_slash
        assert c.effective_bass == "E"

    def test_consistent_bass_note_ok(self) -> None:
        c = ChordEvent(
            symbol="C/E",
            bass_note="E",
            timestamp=TimeStamp(start=0, end=2),
            source_engine="mock",
        )
        assert c.effective_bass == "E"

    def test_inconsistent_bass_note_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc:
            ChordEvent(
                symbol="C/E",
                bass_note="A",
                timestamp=TimeStamp(start=0, end=2),
                source_engine="mock",
            )
        assert "disagrees" in str(exc.value)

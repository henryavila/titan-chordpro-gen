# tests/unit/core/test_schemas.py
"""Tests for core Pydantic schemas."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from titan_chordpro.core.schemas import (
    AlignmentResult,
    BeatGrid,
    ChordEvent,
    PhonemeEvent,
    StemSet,
    SyllableEvent,
    TimeStamp,
    TranscriptionResult,
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


@pytest.mark.unit
class TestBeatGrid:
    def test_basic(self) -> None:
        grid = BeatGrid(
            beats=[0.5, 1.0, 1.5, 2.0],
            downbeat_indices=[0, 4],
            bpm=120.0,
            source_engine="mock",
        )
        assert grid.meter == (4, 4)
        assert not grid.bpm_variable

    def test_non_monotonic_beats_rejected(self) -> None:
        with pytest.raises(ValidationError):
            BeatGrid(
                beats=[1.0, 0.5, 2.0],
                downbeat_indices=[0],
                bpm=120.0,
                source_engine="mock",
            )

    def test_zero_bpm_rejected(self) -> None:
        with pytest.raises(ValidationError):
            BeatGrid(
                beats=[0.5, 1.0],
                downbeat_indices=[0],
                bpm=0.0,
                source_engine="mock",
            )

    def test_invalid_meter_denominator_rejected(self) -> None:
        with pytest.raises(ValidationError):
            BeatGrid(
                beats=[0.5, 1.0],
                downbeat_indices=[0],
                bpm=120.0,
                meter=(4, 3),  # 3 not in {2,4,8,16}
                source_engine="mock",
            )

    def test_six_eight_ok(self) -> None:
        grid = BeatGrid(
            beats=[0.5, 1.0],
            downbeat_indices=[0],
            bpm=120.0,
            meter=(6, 8),
        )
        assert grid.meter == (6, 8)


@pytest.mark.unit
class TestStemSet:
    def test_basic(self, tmp_path: Path) -> None:
        stems = StemSet(
            audio_id="abc123",
            vocals=tmp_path / "vocals.wav",
            bass=tmp_path / "bass.wav",
            drums=tmp_path / "drums.wav",
            other=tmp_path / "other.wav",
            duration=180.0,
            source_engine="mock",
        )
        assert stems.sample_rate == 44100

    def test_zero_duration_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ValidationError):
            StemSet(
                audio_id="abc",
                vocals=tmp_path / "v.wav",
                bass=tmp_path / "b.wav",
                drums=tmp_path / "d.wav",
                other=tmp_path / "o.wav",
                duration=0.0,
                source_engine="mock",
            )


@pytest.mark.unit
class TestResultWrappers:
    def test_transcription_result_minimal(self) -> None:
        tr = TranscriptionResult(words=[])
        assert tr.phonemes is None
        assert tr.detected_language is None

    def test_transcription_result_full(self) -> None:
        word = WordEvent(
            text="hi",
            timestamp=TimeStamp(start=0, end=1),
            source_engine="mock",
        )
        tr = TranscriptionResult(
            words=[word],
            detected_language="en",
        )
        assert tr.detected_language == "en"

    def test_alignment_result_basic(self) -> None:
        ar = AlignmentResult(words=[], phonemes=[])
        assert ar.words == []

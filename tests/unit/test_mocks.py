"""Smoke tests for mock engines — verify Protocol conformance and determinism."""

from pathlib import Path

import pytest

from titan_chordpro.core.protocols import (
    AlignmentEngine,
    BeatTrackingEngine,
    ChordRecognitionEngine,
    SourceSeparationEngine,
    SyllabificationEngine,
    TranscriptionEngine,
)
from titan_chordpro.core.schemas import (
    AlignmentResult,
    BeatGrid,
    ChordEvent,
    EngineInfo,
    PhonemeEvent,
    StemSet,
    SyllableEvent,
    TimeStamp,
    TranscriptionResult,
    WordEvent,
)
from titan_chordpro.mocks import (
    MockAlignmentEngine,
    MockBeatTrackingEngine,
    MockChordRecognitionEngine,
    MockSourceSeparationEngine,
    MockSyllabificationEngine,
    MockTranscriptionEngine,
)


@pytest.mark.unit
class TestProtocolConformance:
    def test_mock_separation_satisfies_protocol(self) -> None:
        assert isinstance(MockSourceSeparationEngine(), SourceSeparationEngine)

    def test_mock_transcription_satisfies_protocol(self) -> None:
        assert isinstance(MockTranscriptionEngine(), TranscriptionEngine)

    def test_mock_alignment_satisfies_protocol(self) -> None:
        assert isinstance(MockAlignmentEngine(), AlignmentEngine)

    def test_mock_chord_satisfies_protocol(self) -> None:
        assert isinstance(MockChordRecognitionEngine(), ChordRecognitionEngine)

    def test_mock_beat_satisfies_protocol(self) -> None:
        assert isinstance(MockBeatTrackingEngine(), BeatTrackingEngine)

    def test_mock_syllabification_satisfies_protocol(self) -> None:
        assert isinstance(MockSyllabificationEngine(), SyllabificationEngine)


@pytest.mark.unit
class TestSeparation:
    def test_returns_stem_set_with_four_paths(self, tmp_path: Path) -> None:
        audio = tmp_path / "song.mp3"
        audio.write_bytes(b"")
        stems = MockSourceSeparationEngine(stem_dir=tmp_path).separate(audio)
        assert isinstance(stems, StemSet)
        assert stems.vocals.name == "vocals.wav"
        assert stems.bass.name == "bass.wav"
        assert stems.drums.name == "drums.wav"
        assert stems.other.name == "other.wav"

    def test_deterministic_audio_id(self, tmp_path: Path) -> None:
        audio = tmp_path / "song.mp3"
        audio.write_bytes(b"")
        engine = MockSourceSeparationEngine(stem_dir=tmp_path)
        assert engine.separate(audio).audio_id == engine.separate(audio).audio_id

    def test_engine_info_reports_cpu_backend(self) -> None:
        info = MockSourceSeparationEngine().info
        assert isinstance(info, EngineInfo)
        assert info.backend == "cpu"
        assert "mock" in info.name


@pytest.mark.unit
class TestTranscription:
    def test_returns_three_hardcoded_words(self, tmp_path: Path) -> None:
        result = MockTranscriptionEngine().transcribe(tmp_path / "vocals.wav")
        assert isinstance(result, TranscriptionResult)
        assert len(result.words) == 3
        assert [w.text for w in result.words] == ["hello", "world", "test"]
        assert result.detected_language == "pt"
        assert result.phonemes is None

    def test_word_timestamps_are_monotonic(self, tmp_path: Path) -> None:
        result = MockTranscriptionEngine().transcribe(tmp_path / "vocals.wav")
        ts = [w.timestamp for w in result.words]
        for prev, curr in zip(ts, ts[1:], strict=False):
            assert prev.end <= curr.start

    def test_deterministic_across_calls(self, tmp_path: Path) -> None:
        engine = MockTranscriptionEngine()
        a = engine.transcribe(tmp_path / "v.wav")
        b = engine.transcribe(tmp_path / "v.wav")
        assert [w.text for w in a.words] == [w.text for w in b.words]


@pytest.mark.unit
class TestAlignment:
    def test_returns_phonemes_per_word(self, tmp_path: Path) -> None:
        words = [
            WordEvent(
                text="hello",
                timestamp=TimeStamp(start=0.0, end=0.5),
                source_engine="mock",
            ),
            WordEvent(
                text="world",
                timestamp=TimeStamp(start=0.5, end=1.0),
                source_engine="mock",
            ),
        ]
        result = MockAlignmentEngine().align(tmp_path / "v.wav", words, language="pt")
        assert isinstance(result, AlignmentResult)
        assert len(result.words) == 2
        assert len(result.phonemes) > 0
        assert all(isinstance(p, PhonemeEvent) for p in result.phonemes)


@pytest.mark.unit
class TestChordRecognition:
    def test_returns_four_chord_events(self, tmp_path: Path) -> None:
        chords = MockChordRecognitionEngine().detect(tmp_path / "mix.wav")
        assert len(chords) == 4
        assert all(isinstance(c, ChordEvent) for c in chords)
        assert [c.symbol for c in chords] == ["C", "G", "Am", "F"]

    def test_chord_timestamps_monotonic(self, tmp_path: Path) -> None:
        chords = MockChordRecognitionEngine().detect(tmp_path / "mix.wav")
        for prev, curr in zip(chords, chords[1:], strict=False):
            assert prev.timestamp.end <= curr.timestamp.start

    def test_vocabulary_is_majmin(self) -> None:
        assert MockChordRecognitionEngine().vocabulary == "majmin"

    def test_supports_inversions_false(self) -> None:
        assert MockChordRecognitionEngine().supports_inversions is False


@pytest.mark.unit
class TestBeatTracking:
    def test_returns_60_bpm_4_4_grid(self, tmp_path: Path) -> None:
        grid = MockBeatTrackingEngine().track(tmp_path / "audio.wav")
        assert isinstance(grid, BeatGrid)
        assert grid.bpm == 60.0
        assert grid.meter == (4, 4)
        assert len(grid.beats) == 8
        assert grid.beats[0] == pytest.approx(0.0)
        assert grid.beats[-1] == pytest.approx(7.0)
        assert grid.downbeat_indices == [0, 4]

    def test_supports_variable_tempo_false(self) -> None:
        assert MockBeatTrackingEngine().supports_variable_tempo is False

    def test_supports_meter_detection_false(self) -> None:
        assert MockBeatTrackingEngine().supports_meter_detection is False


@pytest.mark.unit
class TestSyllabification:
    def test_returns_syllables_per_word(self) -> None:
        words = [
            WordEvent(
                text="amigo",
                timestamp=TimeStamp(start=0.0, end=0.6),
                source_engine="mock",
            ),
            WordEvent(
                text="hello",
                timestamp=TimeStamp(start=0.6, end=1.0),
                source_engine="mock",
            ),
        ]
        engine = MockSyllabificationEngine(language="pt")
        result = engine.syllabify(words, phonemes=None)
        assert all(isinstance(s, SyllableEvent) for s in result)
        assert len(result) >= 5

    def test_language_property(self) -> None:
        assert MockSyllabificationEngine(language="en").language == "en"


@pytest.mark.unit
class TestConftestFixtures:
    def test_fixture_separation(self, mock_separation_engine) -> None:
        assert isinstance(mock_separation_engine, MockSourceSeparationEngine)

    def test_fixture_transcription(self, mock_transcription_engine) -> None:
        assert isinstance(mock_transcription_engine, MockTranscriptionEngine)

    def test_fixture_alignment(self, mock_alignment_engine) -> None:
        assert isinstance(mock_alignment_engine, MockAlignmentEngine)

    def test_fixture_chord(self, mock_chord_engine) -> None:
        assert isinstance(mock_chord_engine, MockChordRecognitionEngine)

    def test_fixture_beat(self, mock_beat_engine) -> None:
        assert isinstance(mock_beat_engine, MockBeatTrackingEngine)

    def test_fixture_syllabification(self, mock_syllabification_engine) -> None:
        assert isinstance(mock_syllabification_engine, MockSyllabificationEngine)

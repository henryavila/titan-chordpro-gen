"""Verify all 6 Engine Protocols exist and have correct structure."""

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
    TranscriptionResult,
    WordEvent,
)


@pytest.mark.unit
class TestProtocolsRuntimeCheckable:
    """All Engine Protocols are @runtime_checkable so mocks can be verified."""

    def test_separation_protocol(self, tmp_path: Path) -> None:
        class _Sep:
            def separate(self, audio: Path) -> StemSet:
                return StemSet(
                    audio_id="x",
                    vocals=tmp_path / "v.wav",
                    bass=tmp_path / "b.wav",
                    drums=tmp_path / "d.wav",
                    other=tmp_path / "o.wav",
                    duration=1.0,
                    source_engine="mock",
                )

            @property
            def info(self) -> EngineInfo:
                return EngineInfo(name="mock", version="0", backend="cpu")

        assert isinstance(_Sep(), SourceSeparationEngine)

    def test_transcription_protocol(self) -> None:
        class _Tr:
            def transcribe(self, vocals: Path, language: str | None = None) -> TranscriptionResult:
                return TranscriptionResult(words=[])

            @property
            def info(self) -> EngineInfo:
                return EngineInfo(name="mock", version="0", backend="cpu")

        assert isinstance(_Tr(), TranscriptionEngine)

    def test_alignment_protocol(self) -> None:
        class _Al:
            def align(self, vocals: Path, words: list[WordEvent], language: str) -> AlignmentResult:
                return AlignmentResult(words=[], phonemes=[])

            @property
            def info(self) -> EngineInfo:
                return EngineInfo(name="mock", version="0", backend="cpu")

        assert isinstance(_Al(), AlignmentEngine)

    def test_chord_recognition_protocol(self) -> None:
        class _Ch:
            def detect(self, harmonic_mix: Path, bass_stem: Path | None = None) -> list[ChordEvent]:
                return []

            @property
            def info(self) -> EngineInfo:
                return EngineInfo(name="mock", version="0", backend="cpu")

            @property
            def vocabulary(self) -> str:
                return "majmin"

            @property
            def supports_inversions(self) -> bool:
                return False

        assert isinstance(_Ch(), ChordRecognitionEngine)

    def test_beat_tracking_protocol(self) -> None:
        class _Bt:
            def track(self, audio: Path) -> BeatGrid:
                return BeatGrid(
                    beats=[0.5, 1.0],
                    downbeat_indices=[0],
                    bpm=120.0,
                    source_engine="mock",
                )

            @property
            def info(self) -> EngineInfo:
                return EngineInfo(name="mock", version="0", backend="cpu")

            @property
            def supports_variable_tempo(self) -> bool:
                return False

            @property
            def supports_meter_detection(self) -> bool:
                return False

        assert isinstance(_Bt(), BeatTrackingEngine)

    def test_syllabification_protocol(self) -> None:
        class _Sy:
            def syllabify(
                self,
                words: list[WordEvent],
                phonemes: list[PhonemeEvent] | None = None,
            ) -> list[SyllableEvent]:
                return []

            @property
            def language(self) -> str:
                return "en"

            @property
            def info(self) -> EngineInfo:
                return EngineInfo(name="mock", version="0", backend="cpu")

        assert isinstance(_Sy(), SyllabificationEngine)

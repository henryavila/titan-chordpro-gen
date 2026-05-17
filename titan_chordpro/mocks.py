"""Plain (non-fixture) mock engine classes used by:

1. `factory.py` (T30) — returns these instances in Phase A so the orchestrator
   pipeline can run end-to-end without ML dependencies.
2. `tests/conftest.py` (T29) — thin pytest-fixture wrappers around these
   classes so unit/integration tests get fresh instances.

All mocks return deterministic hardcoded data so downstream fusion/writer
tests have a stable input. They are NOT random.
"""

from __future__ import annotations

from pathlib import Path

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
from titan_chordpro.fusion.syllabifier import syllabify_word_orthographic


class MockSourceSeparationEngine:
    """Returns a StemSet pointing at placeholder paths inside `stem_dir`."""

    def __init__(self, stem_dir: Path | None = None) -> None:
        self._stem_dir = stem_dir or Path("/tmp/titan-mock-stems")
        try:
            self._stem_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

    def separate(self, audio: Path) -> StemSet:
        d = self._stem_dir
        return StemSet(
            audio_id="mock-audio-id-deterministic",
            vocals=d / "vocals.wav",
            bass=d / "bass.wav",
            drums=d / "drums.wav",
            other=d / "other.wav",
            sample_rate=44100,
            duration=8.0,
            source_engine="mock_separation",
        )

    @property
    def info(self) -> EngineInfo:
        return EngineInfo(name="mock_separation", version="0", backend="cpu")


_MOCK_WORDS_HARDCODED = [
    ("hello", 0.0, 0.5),
    ("world", 0.6, 1.0),
    ("test", 1.1, 1.5),
]


class MockTranscriptionEngine:
    """Returns 3 hardcoded PT-tagged words with no phonemes (forces alignment)."""

    def transcribe(self, vocals: Path, language: str | None = None) -> TranscriptionResult:
        words = [
            WordEvent(
                text=text,
                timestamp=TimeStamp(start=start, end=end),
                source_engine="mock_transcription",
                language=language or "pt",
            )
            for text, start, end in _MOCK_WORDS_HARDCODED
        ]
        return TranscriptionResult(words=words, phonemes=None, detected_language=language or "pt")

    @property
    def info(self) -> EngineInfo:
        return EngineInfo(name="mock_transcription", version="0", backend="cpu")


class MockAlignmentEngine:
    """Returns the input words verbatim + 2 phonemes per word (deterministic)."""

    def align(self, vocals: Path, words: list[WordEvent], language: str) -> AlignmentResult:
        phonemes: list[PhonemeEvent] = []
        for idx, word in enumerate(words):
            mid = (word.timestamp.start + word.timestamp.end) / 2.0
            phonemes.append(
                PhonemeEvent(
                    symbol="m",
                    timestamp=TimeStamp(start=word.timestamp.start, end=mid),
                    parent_word_idx=idx,
                )
            )
            phonemes.append(
                PhonemeEvent(
                    symbol="ˈa",
                    timestamp=TimeStamp(start=mid, end=word.timestamp.end),
                    parent_word_idx=idx,
                )
            )
        return AlignmentResult(words=words, phonemes=phonemes)

    @property
    def info(self) -> EngineInfo:
        return EngineInfo(name="mock_alignment", version="0", backend="cpu")


_MOCK_CHORD_PROGRESSION = [
    ("C", 0.0, 2.0),
    ("G", 2.0, 4.0),
    ("Am", 4.0, 6.0),
    ("F", 6.0, 8.0),
]


class MockChordRecognitionEngine:
    """Returns a 4-chord I-V-vi-IV progression spanning 8 seconds."""

    def detect(self, harmonic_mix: Path, bass_stem: Path | None = None) -> list[ChordEvent]:
        return [
            ChordEvent(
                symbol=symbol,
                timestamp=TimeStamp(start=start, end=end),
                source_engine="mock_chord",
            )
            for symbol, start, end in _MOCK_CHORD_PROGRESSION
        ]

    @property
    def info(self) -> EngineInfo:
        return EngineInfo(name="mock_chord", version="0", backend="cpu")

    @property
    def vocabulary(self) -> str:
        return "majmin"

    @property
    def supports_inversions(self) -> bool:
        return False


class MockBeatTrackingEngine:
    """Returns a 60-BPM 4/4 BeatGrid with 8 beats and 2 downbeats."""

    def track(self, audio: Path) -> BeatGrid:
        return BeatGrid(
            beats=[float(i) for i in range(8)],
            downbeat_indices=[0, 4],
            bpm=60.0,
            bpm_variable=False,
            meter=(4, 4),
            source_engine="mock_beat",
        )

    @property
    def info(self) -> EngineInfo:
        return EngineInfo(name="mock_beat", version="0", backend="cpu")

    @property
    def supports_variable_tempo(self) -> bool:
        return False

    @property
    def supports_meter_detection(self) -> bool:
        return False


class MockSyllabificationEngine:
    """Delegates to the real T13 orthographic syllabifier."""

    def __init__(self, language: str = "pt") -> None:
        self._language = language

    def syllabify(
        self,
        words: list[WordEvent],
        phonemes: list[PhonemeEvent] | None = None,
    ) -> list[SyllableEvent]:
        result: list[SyllableEvent] = []
        for word in words:
            result.extend(syllabify_word_orthographic(word, self._language))
        return result

    @property
    def language(self) -> str:
        return self._language

    @property
    def info(self) -> EngineInfo:
        return EngineInfo(name=f"mock_syllabification_{self._language}", version="0", backend="cpu")

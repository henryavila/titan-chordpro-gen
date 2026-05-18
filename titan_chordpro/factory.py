"""Engine factory.

Phase B: prefer real engine when the optional dep is importable; fall back
to the matching mock when missing. All selections honor a `force_mock=True`
kwarg so callers (tests, CLI --device=mock) can opt out of real engines.

Selection rationale is stored in `_LAST_SELECTION` for the CLI's
`--list-engines` flag (T56).
"""

from __future__ import annotations

import importlib.util
import logging
from typing import Any

from titan_chordpro.core.exceptions import EngineUnavailableError
from titan_chordpro.core.protocols import (
    AlignmentEngine,
    BeatTrackingEngine,
    ChordRecognitionEngine,
    SourceSeparationEngine,
    SyllabificationEngine,
    TranscriptionEngine,
)
from titan_chordpro.mocks import (
    MockAlignmentEngine,
    MockBeatTrackingEngine,
    MockChordRecognitionEngine,
    MockSourceSeparationEngine,
    MockSyllabificationEngine,
    MockTranscriptionEngine,
)

_log = logging.getLogger(__name__)

# Module-level state: maps stage -> {"engine": str, "real": bool, "reason": str}
_LAST_SELECTION: dict[str, dict[str, Any]] = {}


def _have_module(module_name: str) -> bool:
    """True iff the module can be imported. Does NOT actually import it."""
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ValueError):
        return False


def _record(stage: str, engine_name: str, real: bool, reason: str) -> None:
    _LAST_SELECTION[stage] = {"engine": engine_name, "real": real, "reason": reason}
    _log.info("factory: %s -> %s (%s)", stage, engine_name, reason)


def last_selection() -> dict[str, dict[str, Any]]:
    """Return a shallow copy of the most recent selection map."""
    return {k: dict(v) for k, v in _LAST_SELECTION.items()}


def select_separation(
    *,
    force_mock: bool = False,
    backend: str | None = None,
    **_ignored: Any,
) -> SourceSeparationEngine:
    if force_mock or not _have_module("audio_separator"):
        _record(
            "separation",
            "mock",
            False,
            "audio_separator not installed" if not force_mock else "force_mock",
        )
        return MockSourceSeparationEngine()
    try:
        from titan_chordpro.engines.separation.htdemucs import HtdemucsEngine

        engine = HtdemucsEngine(backend=backend)
        _record("separation", "htdemucs_ft", True, "audio_separator importable")
        return engine
    except EngineUnavailableError as exc:
        _record("separation", "mock", False, f"htdemucs init failed: {exc}")
        return MockSourceSeparationEngine()


def select_transcription(
    *,
    force_mock: bool = False,
    model_id: str = "base",
    **_ignored: Any,
) -> TranscriptionEngine:
    if force_mock or not _have_module("pywhispercpp"):
        _record(
            "transcription",
            "mock",
            False,
            "pywhispercpp not installed" if not force_mock else "force_mock",
        )
        return MockTranscriptionEngine()
    try:
        from titan_chordpro.engines.transcription.whisper_cpp import WhisperCppEngine

        engine = WhisperCppEngine(model_id=model_id)
        _record("transcription", "whisper_cpp", True, "pywhispercpp importable")
        return engine
    except EngineUnavailableError as exc:
        _record("transcription", "mock", False, f"whisper_cpp init failed: {exc}")
        return MockTranscriptionEngine()


def select_alignment(
    *,
    force_mock: bool = False,
    backend: str | None = None,
    **_ignored: Any,
) -> AlignmentEngine:
    if force_mock or not _have_module("torchaudio"):
        _record(
            "alignment",
            "mock",
            False,
            "torchaudio not installed" if not force_mock else "force_mock",
        )
        return MockAlignmentEngine()
    try:
        from titan_chordpro.engines.alignment.torchaudio_align import TorchaudioAlignEngine

        engine = TorchaudioAlignEngine(backend=backend)
        _record("alignment", "torchaudio_align", True, "torchaudio importable")
        return engine
    except EngineUnavailableError as exc:
        _record("alignment", "mock", False, f"torchaudio_align init failed: {exc}")
        return MockAlignmentEngine()


def select_chord_recognition(
    *,
    force_mock: bool = False,
    **_ignored: Any,
) -> ChordRecognitionEngine:
    if force_mock or not _have_module("chord_extractor"):
        _record(
            "chord_recognition",
            "mock",
            False,
            "chord_extractor not installed" if not force_mock else "force_mock",
        )
        return MockChordRecognitionEngine()
    try:
        from titan_chordpro.engines.chord.chordino import ChordinoEngine

        engine = ChordinoEngine()
        _record("chord_recognition", "chordino", True, "chord_extractor importable")
        return engine
    except EngineUnavailableError as exc:
        _record("chord_recognition", "mock", False, f"chordino init failed: {exc}")
        return MockChordRecognitionEngine()


def select_beat_tracking(
    *,
    force_mock: bool = False,
    backend: str | None = None,
    **_ignored: Any,
) -> BeatTrackingEngine:
    if force_mock or not _have_module("beat_this"):
        _record(
            "beat_tracking",
            "mock",
            False,
            "beat_this not installed" if not force_mock else "force_mock",
        )
        return MockBeatTrackingEngine()
    try:
        from titan_chordpro.engines.beat.beatthis import BeatThisEngine

        engine = BeatThisEngine(backend=backend)
        _record("beat_tracking", "beat_this", True, "beat_this importable")
        return engine
    except EngineUnavailableError as exc:
        _record("beat_tracking", "mock", False, f"beatthis init failed: {exc}")
        return MockBeatTrackingEngine()


def select_syllabification(
    language: str = "pt",
    *,
    force_mock: bool = False,
    **_ignored: Any,
) -> SyllabificationEngine:
    if language == "pt":
        if force_mock or not _have_module("gruut"):
            _record(
                "syllabification",
                "mock",
                False,
                "gruut not installed" if not force_mock else "force_mock",
            )
            return MockSyllabificationEngine(language=language)
        try:
            from titan_chordpro.engines.lang.portuguese import PortugueseSyllabifierEngine

            pt_engine: SyllabificationEngine = PortugueseSyllabifierEngine()
            _record("syllabification", "gruut_pt", True, "gruut importable")
            return pt_engine
        except EngineUnavailableError as exc:
            _record("syllabification", "mock", False, f"gruut_pt init failed: {exc}")
            return MockSyllabificationEngine(language=language)

    if language == "en":
        if force_mock or not _have_module("g2p_en"):
            _record(
                "syllabification",
                "mock",
                False,
                "g2p_en not installed" if not force_mock else "force_mock",
            )
            return MockSyllabificationEngine(language=language)
        try:
            from titan_chordpro.engines.lang.english import EnglishSyllabifierEngine

            en_engine: SyllabificationEngine = EnglishSyllabifierEngine()
            _record("syllabification", "g2p_en", True, "g2p_en importable")
            return en_engine
        except EngineUnavailableError as exc:
            _record("syllabification", "mock", False, f"g2p_en init failed: {exc}")
            return MockSyllabificationEngine(language=language)

    # Unknown language → always mock with passed language for parent tracking.
    _record("syllabification", "mock", False, f"unknown language {language!r}; using mock")
    return MockSyllabificationEngine(language=language)

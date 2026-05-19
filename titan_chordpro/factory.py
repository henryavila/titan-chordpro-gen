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


def _missing_real_engine(stage: str, module: str, engine: str) -> EngineUnavailableError:
    return EngineUnavailableError(
        f"{module!r} is not installed; pass force_mock=True for explicit mock mode",
        stage=stage,
        engine=engine,
    )


def select_separation(
    *,
    force_mock: bool = False,
    backend: str | None = None,
    **_ignored: Any,
) -> SourceSeparationEngine:
    if force_mock:
        _record("separation", "mock", False, "force_mock")
        return MockSourceSeparationEngine()
    if not _have_module("audio_separator"):
        raise _missing_real_engine("separation", "audio_separator", "htdemucs_ft")
    from titan_chordpro.engines.separation.htdemucs import HtdemucsEngine

    engine = HtdemucsEngine(backend=backend)
    _record("separation", "htdemucs_ft", True, "audio_separator importable")
    return engine


def select_transcription(
    *,
    force_mock: bool = False,
    transcription_model_id: str | None = None,
    **_ignored: Any,
) -> TranscriptionEngine:
    """Build the transcription engine. `transcription_model_id` overrides
    the whisper.cpp default (env var TITAN_WHISPER_MODEL or "medium")."""
    if force_mock:
        _record("transcription", "mock", False, "force_mock")
        return MockTranscriptionEngine()
    if not _have_module("pywhispercpp"):
        raise _missing_real_engine("transcription", "pywhispercpp", "whisper_cpp")
    from titan_chordpro.engines.transcription.whisper_cpp import _DEFAULT_MODEL, WhisperCppEngine

    model_id = transcription_model_id or _DEFAULT_MODEL
    engine = WhisperCppEngine(model_id=model_id)
    _record("transcription", "whisper_cpp", True, f"pywhispercpp ({model_id})")
    return engine


def select_alignment(
    *,
    force_mock: bool = False,
    backend: str | None = None,
    **_ignored: Any,
) -> AlignmentEngine:
    if force_mock:
        _record("alignment", "mock", False, "force_mock")
        return MockAlignmentEngine()
    if not _have_module("torchaudio"):
        raise _missing_real_engine("alignment", "torchaudio", "torchaudio_align")
    from titan_chordpro.engines.alignment.torchaudio_align import TorchaudioAlignEngine

    engine = TorchaudioAlignEngine(backend=backend)
    _record("alignment", "torchaudio_align", True, "torchaudio importable")
    return engine


def select_chord_recognition(
    *,
    force_mock: bool = False,
    **_ignored: Any,
) -> ChordRecognitionEngine:
    if force_mock:
        _record("chord_recognition", "mock", False, "force_mock")
        return MockChordRecognitionEngine()
    if not _have_module("chord_extractor"):
        raise _missing_real_engine("chord_recognition", "chord_extractor", "chordino")
    from titan_chordpro.engines.chord.chordino import ChordinoEngine

    engine = ChordinoEngine()
    _record("chord_recognition", "chordino", True, "chord_extractor importable")
    return engine


def select_beat_tracking(
    *,
    force_mock: bool = False,
    backend: str | None = None,
    **_ignored: Any,
) -> BeatTrackingEngine:
    if force_mock:
        _record("beat_tracking", "mock", False, "force_mock")
        return MockBeatTrackingEngine()
    if not _have_module("beat_this"):
        raise _missing_real_engine("beat_tracking", "beat_this", "beat_this")
    from titan_chordpro.engines.beat.beatthis import BeatThisEngine

    engine = BeatThisEngine(backend=backend)
    _record("beat_tracking", "beat_this", True, "beat_this importable")
    return engine


def _normalize_lang(lang: str) -> str:
    """Strip region suffix and lowercase: pt-BR → pt, en_US → en."""
    return lang.split("-", 1)[0].split("_", 1)[0].lower()


def select_syllabification(
    language: str = "pt",
    *,
    force_mock: bool = False,
    **_ignored: Any,
) -> SyllabificationEngine:
    if force_mock:
        _record("syllabification", "mock", False, "force_mock")
        return MockSyllabificationEngine(language=language)

    base = _normalize_lang(language)
    if base == "pt":
        if not _have_module("gruut"):
            raise _missing_real_engine("syllabification", "gruut", "gruut_pt")
        from titan_chordpro.engines.lang.portuguese import PortugueseSyllabifierEngine

        pt_engine: SyllabificationEngine = PortugueseSyllabifierEngine()
        _record("syllabification", "gruut_pt", True, "gruut importable")
        return pt_engine

    if base == "en":
        if not _have_module("g2p_en"):
            raise _missing_real_engine("syllabification", "g2p_en", "g2p_en")
        from titan_chordpro.engines.lang.english import EnglishSyllabifierEngine

        en_engine: SyllabificationEngine = EnglishSyllabifierEngine()
        _record("syllabification", "g2p_en", True, "g2p_en importable")
        return en_engine

    # Unknown language → mock with passed language for parent tracking.
    # Not raising: unknown-language is a content/data classification, not a missing dependency.
    _record("syllabification", "mock", False, f"unknown language {language!r}; using mock")
    return MockSyllabificationEngine(language=language)

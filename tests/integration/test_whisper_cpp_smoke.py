# tests/integration/test_whisper_cpp_smoke.py
"""whisper.cpp integration smoke.

silent.wav should yield words=[] (Whisper learned to emit silence on
silence). tone_a4_2s.wav may or may not produce hallucinated words — we
only assert no crash and schema validity.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip(
    "pywhispercpp",
    reason="pywhispercpp not installed; install with pip install -e .[mac]",
)


@pytest.mark.integration
def test_silent_produces_empty_words(silent_wav: Path) -> None:
    from titan_chordpro.core.schemas import TranscriptionResult
    from titan_chordpro.engines.transcription.whisper_cpp import WhisperCppEngine

    engine = WhisperCppEngine()
    result = engine.transcribe(silent_wav)

    assert isinstance(result, TranscriptionResult)
    assert result.phonemes is None
    assert result.words == [] or all(w.text.strip() == "" for w in result.words)


@pytest.mark.integration
def test_tone_does_not_crash(tone_a4_2s_wav: Path) -> None:
    from titan_chordpro.engines.transcription.whisper_cpp import WhisperCppEngine

    engine = WhisperCppEngine()
    result = engine.transcribe(tone_a4_2s_wav, language="en")

    # Any number of words is OK; we just assert schema validity.
    for w in result.words:
        assert w.timestamp.end >= w.timestamp.start
        assert w.source_engine == "whisper_cpp"
        assert 0.0 <= w.confidence <= 1.0

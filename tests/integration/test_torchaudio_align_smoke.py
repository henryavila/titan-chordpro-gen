# tests/integration/test_torchaudio_align_smoke.py
"""torchaudio forced_align integration smoke.

Empty word list returns empty result deterministically — that path is the
only one we can assert without a real vocal recording. When a single word
is passed against the tone fixture, alignment may succeed or raise
AlignmentError (the model emits gibberish on a sine wave); both are
acceptable.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip(
    "torchaudio",
    reason="torchaudio not installed; install with pip install -e .[mac]",
)


@pytest.mark.integration
def test_empty_words_returns_empty(tone_a4_2s_wav: Path) -> None:
    from titan_chordpro.engines.alignment.torchaudio_align import TorchaudioAlignEngine

    engine = TorchaudioAlignEngine()
    result = engine.align(tone_a4_2s_wav, words=[], language="en")
    assert result.words == []
    assert result.phonemes == []


@pytest.mark.integration
def test_single_word_on_tone_completes_or_raises(tone_a4_2s_wav: Path) -> None:
    from titan_chordpro.core.exceptions import AlignmentError
    from titan_chordpro.core.schemas import TimeStamp, WordEvent
    from titan_chordpro.engines.alignment.torchaudio_align import TorchaudioAlignEngine

    engine = TorchaudioAlignEngine()
    words = [
        WordEvent(
            text="hello",
            timestamp=TimeStamp(start=0.0, end=2.0),
            source_engine="test",
        )
    ]
    try:
        result = engine.align(tone_a4_2s_wav, words, language="en")
    except AlignmentError as exc:
        assert exc.engine == "torchaudio_align"
        return

    # If alignment succeeded, validate schema invariants only.
    for w in result.words:
        assert w.timestamp.end >= w.timestamp.start
    for p in result.phonemes:
        assert p.timestamp.end >= p.timestamp.start

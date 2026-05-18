"""Lang wrapper integration smoke (text-only, no audio)."""

from __future__ import annotations

import pytest

from titan_chordpro.core.schemas import TimeStamp, WordEvent


@pytest.mark.integration
def test_portuguese_real_gruut_call() -> None:
    pytest.importorskip("gruut", reason="gruut not installed; pip install -e .[mac]")
    from titan_chordpro.engines.lang.portuguese import PortugueseSyllabifierEngine

    engine = PortugueseSyllabifierEngine()
    words = [
        WordEvent(
            text="coracao",  # ASCII fallback to dodge encoding edge in CI
            timestamp=TimeStamp(start=0.0, end=1.0),
            source_engine="test",
        ),
        WordEvent(
            text="amor",
            timestamp=TimeStamp(start=1.0, end=1.6),
            source_engine="test",
        ),
    ]
    syls = engine.syllabify(words, phonemes=None)
    assert len(syls) >= 2  # at least one syllable per word
    assert any(s.is_stressed for s in syls)


@pytest.mark.integration
def test_english_real_g2p_call() -> None:
    pytest.importorskip("g2p_en", reason="g2p_en not installed; pip install -e .[mac]")
    from titan_chordpro.engines.lang.english import EnglishSyllabifierEngine

    engine = EnglishSyllabifierEngine()
    words = [
        WordEvent(
            text="hello",
            timestamp=TimeStamp(start=0.0, end=1.0),
            source_engine="test",
        ),
        WordEvent(
            text="world",
            timestamp=TimeStamp(start=1.0, end=1.5),
            source_engine="test",
        ),
    ]
    syls = engine.syllabify(words, phonemes=None)
    assert len(syls) >= 2
    assert any(s.is_stressed for s in syls)

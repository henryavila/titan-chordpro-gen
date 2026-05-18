"""Unit tests for EnglishSyllabifierEngine wrapper."""

from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.mark.unit
class TestEnglishEngineInit:
    def test_unavailable_raises(self) -> None:
        from titan_chordpro.core.exceptions import EngineUnavailableError

        with patch.dict("sys.modules", {"g2p_en": None}):
            from titan_chordpro.engines.lang.english import EnglishSyllabifierEngine

            with pytest.raises(EngineUnavailableError, match="g2p_en"):
                EnglishSyllabifierEngine()

    def test_info_and_language(self) -> None:
        from titan_chordpro.engines.lang.english import EnglishSyllabifierEngine

        engine = EnglishSyllabifierEngine.__new__(EnglishSyllabifierEngine)
        engine._g2p = None  # not invoked in this test
        assert engine.language == "en"
        info = engine.info
        assert info.name == "g2p_en"
        assert info.backend == "cpu"


@pytest.mark.unit
class TestEnglishSyllabify:
    def test_syllabify_without_phonemes_uses_g2p(self) -> None:
        from titan_chordpro.core.schemas import TimeStamp, WordEvent
        from titan_chordpro.engines.lang.english import EnglishSyllabifierEngine

        engine = EnglishSyllabifierEngine.__new__(EnglishSyllabifierEngine)
        # Stub g2p: "hello" -> ["HH", "AH0", "L", "OW1"] (2 syllables: he-llo)
        engine._g2p = lambda text: ["HH", "AH0", "L", "OW1"]

        words = [
            WordEvent(
                text="hello",
                timestamp=TimeStamp(start=0.0, end=1.0),
                source_engine="whisper_cpp",
            )
        ]
        syls = engine.syllabify(words, phonemes=None)

        # 2 syllables expected from ARPABET vowel-grouping (AH0, OW1).
        assert len(syls) == 2
        assert syls[1].is_stressed is True  # OW1 has primary stress
        assert syls[0].timestamp.start == pytest.approx(0.0)
        assert syls[1].timestamp.end == pytest.approx(1.0)

    def test_syllabify_empty(self) -> None:
        from titan_chordpro.engines.lang.english import EnglishSyllabifierEngine

        engine = EnglishSyllabifierEngine.__new__(EnglishSyllabifierEngine)
        engine._g2p = lambda text: []
        assert engine.syllabify([], phonemes=None) == []

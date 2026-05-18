"""Unit tests for PortugueseSyllabifierEngine wrapper."""

from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.mark.unit
class TestPortugueseEngineInit:
    def test_unavailable_raises(self) -> None:
        from titan_chordpro.core.exceptions import EngineUnavailableError

        with patch.dict("sys.modules", {"gruut": None}):
            from titan_chordpro.engines.lang.portuguese import PortugueseSyllabifierEngine

            with pytest.raises(EngineUnavailableError, match="gruut"):
                PortugueseSyllabifierEngine()

    def test_info_and_language(self) -> None:
        from titan_chordpro.engines.lang.portuguese import PortugueseSyllabifierEngine

        engine = PortugueseSyllabifierEngine.__new__(PortugueseSyllabifierEngine)
        assert engine.language == "pt"
        info = engine.info
        assert info.name == "gruut_pt"
        assert info.backend == "cpu"


@pytest.mark.unit
class TestPortugueseSyllabify:
    def test_syllabify_without_phonemes_uses_orthographic(self) -> None:
        """A 2-syllable word over 1s should produce 2 events spanning 0.5s each."""
        from titan_chordpro.core.schemas import TimeStamp, WordEvent
        from titan_chordpro.engines.lang.portuguese import PortugueseSyllabifierEngine

        engine = PortugueseSyllabifierEngine.__new__(PortugueseSyllabifierEngine)
        words = [
            WordEvent(
                text="casa",
                timestamp=TimeStamp(start=0.0, end=1.0),
                source_engine="whisper_cpp",
            )
        ]
        syls = engine.syllabify(words, phonemes=None)

        # "casa" splits into "ca" + "sa" in PT.
        assert len(syls) == 2
        assert [s.text for s in syls] == ["ca", "sa"]
        assert syls[0].timestamp.start == pytest.approx(0.0)
        assert syls[0].timestamp.end == pytest.approx(0.5)
        assert syls[1].timestamp.start == pytest.approx(0.5)
        assert syls[1].timestamp.end == pytest.approx(1.0)
        # Stress: "casa" is paroxytone (stress on 'ca').
        assert syls[0].is_stressed is True
        assert syls[1].is_stressed is False
        # parent_word_idx aligns with input list position.
        assert all(s.parent_word_idx == 0 for s in syls)

    def test_syllabify_empty_words(self) -> None:
        from titan_chordpro.engines.lang.portuguese import PortugueseSyllabifierEngine

        engine = PortugueseSyllabifierEngine.__new__(PortugueseSyllabifierEngine)
        assert engine.syllabify([], phonemes=None) == []

    def test_syllabify_single_syllable_word(self) -> None:
        from titan_chordpro.core.schemas import TimeStamp, WordEvent
        from titan_chordpro.engines.lang.portuguese import PortugueseSyllabifierEngine

        engine = PortugueseSyllabifierEngine.__new__(PortugueseSyllabifierEngine)
        words = [
            WordEvent(
                text="sol",
                timestamp=TimeStamp(start=0.0, end=0.4),
                source_engine="whisper_cpp",
            )
        ]
        syls = engine.syllabify(words, phonemes=None)
        assert len(syls) == 1
        assert syls[0].text == "sol"
        assert syls[0].is_stressed is True  # single syllable always stressed

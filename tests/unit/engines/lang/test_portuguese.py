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

    def test_numeric_mms_phonemes_fall_back_to_orthographic(self) -> None:
        """RC1: MMS token IDs must not collapse multi-syllable PT words to 1 syl."""
        from titan_chordpro.core.schemas import PhonemeEvent, TimeStamp, WordEvent
        from titan_chordpro.engines.lang.portuguese import PortugueseSyllabifierEngine

        engine = PortugueseSyllabifierEngine.__new__(PortugueseSyllabifierEngine)
        words = [
            WordEvent(
                text="descanso",
                timestamp=TimeStamp(start=0.0, end=0.9),
                source_engine="whisper_cpp",
            ),
            WordEvent(
                text="merecedor",
                timestamp=TimeStamp(start=1.0, end=2.0),
                source_engine="whisper_cpp",
            ),
            WordEvent(
                text="sacrifício",
                timestamp=TimeStamp(start=2.0, end=3.2),
                source_engine="whisper_cpp",
            ),
        ]
        # Numeric token IDs as emitted by MMS_FA when decode fails.
        phonemes: list[PhonemeEvent] = []
        for wi, w in enumerate(words):
            n = 5
            dur = w.timestamp.end - w.timestamp.start
            for i in range(n):
                phonemes.append(
                    PhonemeEvent(
                        symbol=str(i + 1),
                        timestamp=TimeStamp(
                            start=w.timestamp.start + dur * i / n,
                            end=w.timestamp.start + dur * (i + 1) / n,
                        ),
                        parent_word_idx=wi,
                    )
                )

        syls = engine.syllabify(words, phonemes=phonemes)
        by_word: dict[int, list] = {}
        for s in syls:
            by_word.setdefault(s.parent_word_idx, []).append(s)

        assert len(by_word[0]) >= 3, [s.text for s in by_word[0]]
        assert len(by_word[1]) >= 4, [s.text for s in by_word[1]]
        assert len(by_word[2]) >= 4, [s.text for s in by_word[2]]
        # Stress still applied on the orthographic fallback path.
        for wi, events in by_word.items():
            assert sum(1 for e in events if e.is_stressed) == 1, wi

    def test_real_ipa_phonemes_still_use_mop_path(self) -> None:
        from titan_chordpro.core.schemas import PhonemeEvent, TimeStamp, WordEvent
        from titan_chordpro.engines.lang.portuguese import PortugueseSyllabifierEngine

        engine = PortugueseSyllabifierEngine.__new__(PortugueseSyllabifierEngine)
        words = [
            WordEvent(
                text="amigo",
                timestamp=TimeStamp(start=0.0, end=0.6),
                source_engine="whisper_cpp",
            )
        ]
        phonemes = [
            PhonemeEvent(
                symbol="a",
                timestamp=TimeStamp(start=0.0, end=0.1),
                parent_word_idx=0,
            ),
            PhonemeEvent(
                symbol="m",
                timestamp=TimeStamp(start=0.1, end=0.2),
                parent_word_idx=0,
            ),
            PhonemeEvent(
                symbol="ˈi",
                timestamp=TimeStamp(start=0.2, end=0.4),
                parent_word_idx=0,
            ),
            PhonemeEvent(
                symbol="ɡ",
                timestamp=TimeStamp(start=0.4, end=0.5),
                parent_word_idx=0,
            ),
            PhonemeEvent(
                symbol="u",
                timestamp=TimeStamp(start=0.5, end=0.6),
                parent_word_idx=0,
            ),
        ]
        syls = engine.syllabify(words, phonemes=phonemes)
        assert len(syls) == 3
        assert [s.is_stressed for s in syls] == [False, True, False]

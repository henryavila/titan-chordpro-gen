# tests/unit/fusion/test_stress.py
"""Tests for stress detectors and orchestrator _apply_stress."""

import pytest

from titan_chordpro.core.schemas import SyllableEvent, TimeStamp, WordEvent
from titan_chordpro.fusion.stress import EnglishStressDetector, PortugueseStressDetector
from titan_chordpro.orchestrator import _apply_stress


def _word(text: str) -> WordEvent:
    return WordEvent(
        text=text,
        timestamp=TimeStamp(start=0, end=1),
        source_engine="mock",
    )


def _syllables(*texts: str) -> list[SyllableEvent]:
    n = len(texts)
    return [
        SyllableEvent(
            text=t,
            timestamp=TimeStamp(start=i / n, end=(i + 1) / n),
            is_stressed=False,
            parent_word_idx=0,
        )
        for i, t in enumerate(texts)
    ]


@pytest.mark.unit
class TestPortugueseStressDetector:
    def setup_method(self) -> None:
        self.detector = PortugueseStressDetector()

    def test_oxitona_ending_r(self) -> None:
        # "amor" — termina em r → oxítona (última)
        idx = self.detector.detect_stressed_syllable(_word("amor"), _syllables("a", "mor"))
        assert idx == 1

    def test_oxitona_ending_l(self) -> None:
        # "papel" — oxítona
        idx = self.detector.detect_stressed_syllable(_word("papel"), _syllables("pa", "pel"))
        assert idx == 1

    def test_paroxitona_default(self) -> None:
        # "casa" — termina em "a" → paroxítona
        idx = self.detector.detect_stressed_syllable(_word("casa"), _syllables("ca", "sa"))
        assert idx == 0

    def test_acento_marcado_proparoxitona(self) -> None:
        # "música" — acento gráfico → tônica é a sílaba marcada
        idx = self.detector.detect_stressed_syllable(_word("música"), _syllables("mú", "si", "ca"))
        assert idx == 0

    def test_acento_marcado_oxitona(self) -> None:
        # "café" — acento gráfico na última
        idx = self.detector.detect_stressed_syllable(_word("café"), _syllables("ca", "fé"))
        assert idx == 1

    def test_monossilabo(self) -> None:
        idx = self.detector.detect_stressed_syllable(_word("pão"), _syllables("pão"))
        assert idx == 0

    def test_ending_im(self) -> None:
        # "ruim" — termina em "im" → oxítona
        idx = self.detector.detect_stressed_syllable(_word("ruim"), _syllables("ru", "im"))
        assert idx == 1


@pytest.mark.unit
class TestEnglishStressDetector:
    def setup_method(self) -> None:
        # Use heuristic fallback (no CMU lookup) for Phase A
        self.detector = EnglishStressDetector(use_cmu_dict=False)

    def test_monosyllable(self) -> None:
        idx = self.detector.detect_stressed_syllable(_word("cat"), _syllables("cat"))
        assert idx == 0

    def test_bisyllable_heuristic_first(self) -> None:
        # Without CMU dict, heuristic = "stress first syllable" for most EN words
        idx = self.detector.detect_stressed_syllable(_word("hello"), _syllables("hel", "lo"))
        assert idx == 0

    def test_trisyllable_heuristic_first(self) -> None:
        idx = self.detector.detect_stressed_syllable(
            _word("beautiful"), _syllables("beau", "ti", "ful")
        )
        assert idx == 0


class _FixedStressDetector:
    """Stub detector that always reports a fixed syllable index."""

    def __init__(self, index: int) -> None:
        self.index = index

    def detect_stressed_syllable(self, word: WordEvent, syllables: list[SyllableEvent]) -> int:
        return self.index


@pytest.mark.unit
class TestApplyStress:
    """orchestrator._apply_stress must leave exactly one stressed syllable per word."""

    def test_clears_preexisting_stress_sets_exactly_one(self) -> None:
        """If the engine already marked the wrong syllable, clear it and set one."""
        words = [
            WordEvent(
                text="casa",
                timestamp=TimeStamp(start=0.0, end=1.0),
                source_engine="mock",
            )
        ]
        # Engine wrongly stressed BOTH syllables (or the wrong one).
        syllables = [
            SyllableEvent(
                text="ca",
                timestamp=TimeStamp(start=0.0, end=0.5),
                is_stressed=True,  # wrong / leftover
                parent_word_idx=0,
            ),
            SyllableEvent(
                text="sa",
                timestamp=TimeStamp(start=0.5, end=1.0),
                is_stressed=True,  # double-stress bug
                parent_word_idx=0,
            ),
        ]
        # Detector says index 0 is correct ("casa" paroxítona).
        detector = _FixedStressDetector(index=0)
        result = _apply_stress(words, syllables, detector)

        assert result is not None
        stressed_flags = [s.is_stressed for s in result]
        assert stressed_flags == [True, False]
        assert sum(1 for s in result if s.is_stressed) == 1

    def test_does_not_mutate_input_syllables(self) -> None:
        words = [
            WordEvent(
                text="amor",
                timestamp=TimeStamp(start=0.0, end=1.0),
                source_engine="mock",
            )
        ]
        syllables = [
            SyllableEvent(
                text="a",
                timestamp=TimeStamp(start=0.0, end=0.4),
                is_stressed=False,
                parent_word_idx=0,
            ),
            SyllableEvent(
                text="mor",
                timestamp=TimeStamp(start=0.4, end=1.0),
                is_stressed=False,
                parent_word_idx=0,
            ),
        ]
        detector = _FixedStressDetector(index=1)
        result = _apply_stress(words, syllables, detector)
        # Input list objects must remain unchanged (immutability).
        assert syllables[0].is_stressed is False
        assert syllables[1].is_stressed is False
        assert result[0].is_stressed is False
        assert result[1].is_stressed is True

    def test_multi_word_exactly_one_each(self) -> None:
        words = [
            WordEvent(
                text="hello",
                timestamp=TimeStamp(start=0.0, end=0.5),
                source_engine="mock",
            ),
            WordEvent(
                text="world",
                timestamp=TimeStamp(start=0.5, end=1.0),
                source_engine="mock",
            ),
        ]
        syllables = [
            SyllableEvent(
                text="hel",
                timestamp=TimeStamp(start=0.0, end=0.25),
                is_stressed=True,
                parent_word_idx=0,
            ),
            SyllableEvent(
                text="lo",
                timestamp=TimeStamp(start=0.25, end=0.5),
                is_stressed=True,
                parent_word_idx=0,
            ),
            SyllableEvent(
                text="world",
                timestamp=TimeStamp(start=0.5, end=1.0),
                is_stressed=False,
                parent_word_idx=1,
            ),
        ]
        # Always stress first syllable of multi-syl words; mono stays 0.
        detector = _FixedStressDetector(index=0)
        result = _apply_stress(words, syllables, detector)
        by_word: dict[int, list[bool]] = {}
        for s in result:
            by_word.setdefault(s.parent_word_idx, []).append(s.is_stressed)
        assert by_word[0] == [True, False]
        assert by_word[1] == [True]

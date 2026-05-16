# tests/unit/fusion/test_stress.py
"""Tests for stress detectors."""

import pytest

from titan_chordpro.core.schemas import SyllableEvent, TimeStamp, WordEvent
from titan_chordpro.fusion.stress import PortugueseStressDetector


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

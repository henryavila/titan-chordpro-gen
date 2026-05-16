# tests/unit/fusion/test_syllabifier.py
"""Tests for syllabifier (Maximum Onset Principle + orthographic fallback).

Covers:
- ARPABET phonemes with CMU stress digits (AH1, AH0, AH2)
- IPA phonemes with stress markers (ˈ primary, ˌ secondary)
- Orthographic fallback for PT-BR (amigo, música) and EN (hello, beautiful)
- Hyphenated compound words (self-aware, bem-vindo)
- OOV / edge cases (empty, no vowels, single phoneme)
"""

import pytest

from titan_chordpro.core.schemas import PhonemeEvent, TimeStamp, WordEvent
from titan_chordpro.fusion.syllabifier import (
    syllabify_word,
    syllabify_word_orthographic,
)


def _word(text: str, start: float = 0.0, end: float = 1.0) -> WordEvent:
    return WordEvent(
        text=text,
        timestamp=TimeStamp(start=start, end=end),
        source_engine="mock",
    )


def _phoneme(symbol: str, start: float, end: float, word_idx: int = 0) -> PhonemeEvent:
    return PhonemeEvent(
        symbol=symbol,
        timestamp=TimeStamp(start=start, end=end),
        parent_word_idx=word_idx,
    )


@pytest.mark.unit
class TestSyllabifyWordPhonemicARPABET:
    """ARPABET phonemes from CMU dict (English). Stress digits 0/1/2."""

    def test_hello_two_syllables_stress_on_first(self) -> None:
        # CMU "hello" = HH AH1 L OW0
        word = _word("hello", 0.0, 0.5)
        phonemes = [
            _phoneme("HH", 0.00, 0.05),
            _phoneme("AH1", 0.05, 0.20),  # primary stress
            _phoneme("L", 0.20, 0.25),
            _phoneme("OW0", 0.25, 0.50),
        ]
        result = syllabify_word(word, phonemes, "en")
        assert len(result) == 2
        assert result[0].is_stressed is True
        assert result[1].is_stressed is False
        # MOP: 'L' goes to second syllable's onset
        assert result[0].timestamp.end == pytest.approx(0.20)
        assert result[1].timestamp.start == pytest.approx(0.20)

    def test_beautiful_three_syllables(self) -> None:
        # CMU "beautiful" = B Y UW1 T AH0 F AH0 L
        word = _word("beautiful", 0.0, 0.9)
        phonemes = [
            _phoneme("B", 0.00, 0.05),
            _phoneme("Y", 0.05, 0.10),
            _phoneme("UW1", 0.10, 0.30),  # primary stress
            _phoneme("T", 0.30, 0.40),
            _phoneme("AH0", 0.40, 0.55),
            _phoneme("F", 0.55, 0.65),
            _phoneme("AH0", 0.65, 0.80),
            _phoneme("L", 0.80, 0.90),
        ]
        result = syllabify_word(word, phonemes, "en")
        assert len(result) == 3
        assert [s.is_stressed for s in result] == [True, False, False]
        # MOP boundaries
        assert result[0].timestamp.end == pytest.approx(0.30)
        assert result[1].timestamp.start == pytest.approx(0.30)
        assert result[1].timestamp.end == pytest.approx(0.55)
        assert result[2].timestamp.start == pytest.approx(0.55)

    def test_stress_digit_zero_means_unstressed(self) -> None:
        word = _word("ago", 0.0, 0.3)
        phonemes = [
            _phoneme("AH0", 0.0, 0.1),  # unstressed
            _phoneme("G", 0.1, 0.2),
            _phoneme("OW1", 0.2, 0.3),  # primary
        ]
        result = syllabify_word(word, phonemes, "en")
        assert [s.is_stressed for s in result] == [False, True]


@pytest.mark.unit
class TestSyllabifyWordPhonemicIPA:
    """IPA phonemes from gruut (PT-BR + general)."""

    def test_pt_amigo_stress_on_middle(self) -> None:
        # gruut for "amigo" → [a, m, ˈi, ɡ, u] (PT-BR closes final /o/ to /u/)
        word = _word("amigo", 0.0, 0.6)
        phonemes = [
            _phoneme("a", 0.0, 0.1),
            _phoneme("m", 0.1, 0.2),
            _phoneme("ˈi", 0.2, 0.4),  # IPA primary stress marker
            _phoneme("ɡ", 0.4, 0.5),
            _phoneme("u", 0.5, 0.6),
        ]
        result = syllabify_word(word, phonemes, "pt")
        assert len(result) == 3
        assert [s.is_stressed for s in result] == [False, True, False]

    def test_diphthong_treated_as_single_nucleus(self) -> None:
        # "boy" in IPA = b ɔɪ → diphthong as single token (one nucleus)
        word = _word("boy", 0.0, 0.3)
        phonemes = [
            _phoneme("b", 0.0, 0.1),
            _phoneme("ɔɪ", 0.1, 0.3),
        ]
        result = syllabify_word(word, phonemes, "en")
        assert len(result) == 1


@pytest.mark.unit
class TestSyllabifyWordEdgeCases:
    def test_empty_phonemes_returns_word_as_single_syllable(self) -> None:
        result = syllabify_word(_word("foo", 0.0, 0.3), [], "en")
        assert len(result) == 1
        assert result[0].text == "foo"

    def test_no_vowels_returns_single_syllable(self) -> None:
        # Interjection "hmm" — no vowels
        word = _word("hmm", 0.0, 0.3)
        phonemes = [_phoneme("h", 0.0, 0.1), _phoneme("m", 0.1, 0.3)]
        result = syllabify_word(word, phonemes, "en")
        assert len(result) == 1
        assert result[0].text == "hmm"

    def test_single_vowel_phoneme(self) -> None:
        word = _word("a", 0.0, 0.2)
        phonemes = [_phoneme("AH1", 0.0, 0.2)]
        result = syllabify_word(word, phonemes, "en")
        assert len(result) == 1
        assert result[0].is_stressed is True


@pytest.mark.unit
class TestSyllabifyWordOrthographic:
    """Fallback when phonemes unavailable. Uses hybrid MOP/CVC rule."""

    def test_monosyllable(self) -> None:
        result = syllabify_word_orthographic(_word("cat", 0.0, 0.3), "en")
        assert len(result) == 1
        assert result[0].text == "cat"
        assert result[0].timestamp.end == pytest.approx(0.3)

    def test_pt_amigo(self) -> None:
        result = syllabify_word_orthographic(_word("amigo", 0.0, 0.6), "pt")
        assert [s.text for s in result] == ["a", "mi", "go"]
        # Linear time distribution
        assert result[0].timestamp.start == pytest.approx(0.0)
        assert result[0].timestamp.end == pytest.approx(0.2)
        assert result[1].timestamp.start == pytest.approx(0.2)
        assert result[2].timestamp.end == pytest.approx(0.6)

    def test_pt_musica_with_accent(self) -> None:
        # Accented 'ú' must be detected as a vowel
        result = syllabify_word_orthographic(_word("música", 0.0, 0.6), "pt")
        assert [s.text for s in result] == ["mú", "si", "ca"]

    def test_en_hello(self) -> None:
        # Hybrid rule: 'll' = 2 consoants between e/o → 1 coda + 1 onset → "hel-lo"
        result = syllabify_word_orthographic(_word("hello", 0.0, 0.4), "en")
        assert [s.text for s in result] == ["hel", "lo"]

    def test_en_beautiful(self) -> None:
        # 'eau' merged as single nucleus (orthographic limitation: not detected as 1 vowel sound),
        # then 'i' alone, 'u' alone → 3 syllables matches phonetic count.
        result = syllabify_word_orthographic(_word("beautiful", 0.0, 0.9), "en")
        assert [s.text for s in result] == ["beau", "ti", "ful"]

    def test_pt_vindo_keeps_n_as_coda(self) -> None:
        # /nd-/ is NOT a legal PT onset, hybrid rule splits: 'n' coda, 'd' onset
        result = syllabify_word_orthographic(_word("vindo", 0.0, 0.4), "pt")
        assert [s.text for s in result] == ["vin", "do"]

    def test_hyphenated_compound_en(self) -> None:
        # "self-aware" → ["self"] + ["a", "ware"] but "ware" → ["wa", "re"] due to silent-e
        # Orthographic limitation accepted: 4 syllables instead of 3 phonetic.
        # We test the structural property: hyphen acts as a split point.
        result = syllabify_word_orthographic(_word("self-aware", 0.0, 1.0), "en")
        texts = [s.text for s in result]
        # First syllable must be "self" (compound first part is monosyllabic)
        assert texts[0] == "self"
        # Second part starts a new syllable group
        assert texts[1].startswith("a") or texts[1] == "a"

    def test_hyphenated_compound_pt(self) -> None:
        # "bem-vindo" → ["bem"] + ["vin", "do"]
        result = syllabify_word_orthographic(_word("bem-vindo", 0.0, 1.0), "pt")
        assert [s.text for s in result] == ["bem", "vin", "do"]

    def test_oov_no_vowels_returns_single_syllable(self) -> None:
        result = syllabify_word_orthographic(_word("xyz", 0.0, 0.3), "en")
        assert len(result) == 1
        assert result[0].text == "xyz"

    def test_empty_word_returns_empty_list(self) -> None:
        result = syllabify_word_orthographic(_word("", 0.0, 0.1), "en")
        assert result == []

    def test_word_starting_with_vowel_keeps_leading_chars(self) -> None:
        # "open" → vowels at 0, 2. Hybrid: 1 consoant 'p' between → onset → "o-pen"
        result = syllabify_word_orthographic(_word("open", 0.0, 0.4), "en")
        assert [s.text for s in result] == ["o", "pen"]

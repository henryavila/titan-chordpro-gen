# titan_chordpro/fusion/stress.py
"""Stress detectors for syllables.

Spec reference: Section 3.2.
Portuguese: ~99% accuracy via orthographic rules.
English (T15): CMU dict via g2p_en.
"""

from __future__ import annotations

from typing import Protocol

from titan_chordpro.core.schemas import SyllableEvent, WordEvent

# Characters that indicate written accents (Portuguese tonic markers)
_ACCENTED_CHARS = set("áéíóúâêîôûãõàèìòù")

# Word endings that cause oxítona (last syllable stressed) when unaccented
_OXITONA_ENDINGS = ("r", "l", "z", "x", "i", "u", "im", "um", "om", "ins", "uns", "ons")


class StressDetector(Protocol):
    def detect_stressed_syllable(
        self,
        word: WordEvent,
        syllables: list[SyllableEvent],
    ) -> int:
        """Returns the index of the stressed syllable within the word."""
        ...


class PortugueseStressDetector:
    """PT-BR stress via orthographic rules.

    Priority:
    1. Written accent (´, `, ^, ~) → that syllable is stressed.
    2. Unmarked ending in r/l/z/x/i/u/im/um/om → oxítona.
    3. Else → paroxítona.
    """

    @property
    def language(self) -> str:
        return "pt"

    def detect_stressed_syllable(
        self,
        word: WordEvent,
        syllables: list[SyllableEvent],
    ) -> int:
        if not syllables:
            return 0

        # Rule 1: written accent — find syllable containing accented char.
        for i, syl in enumerate(syllables):
            if any(ch.lower() in _ACCENTED_CHARS for ch in syl.text):
                return i

        # Rule 2: oxítona by ending.
        text_lower = word.text.lower()
        for ending in _OXITONA_ENDINGS:
            if text_lower.endswith(ending):
                return len(syllables) - 1

        # Rule 3: paroxítona (second-to-last).
        if len(syllables) >= 2:
            return len(syllables) - 2
        return 0


class EnglishStressDetector:
    """EN stress via CMU dict (preferred) or heuristic fallback.

    Phase A uses the heuristic by default (no g2p_en dependency).
    Phase B will pass use_cmu_dict=True after installing g2p_en.
    """

    def __init__(self, use_cmu_dict: bool = True):
        self.use_cmu_dict = use_cmu_dict
        self._g2p = None
        if use_cmu_dict:
            try:
                from g2p_en import G2p

                self._g2p = G2p()
            except ImportError:
                self.use_cmu_dict = False

    @property
    def language(self) -> str:
        return "en"

    def detect_stressed_syllable(
        self,
        word: WordEvent,
        syllables: list[SyllableEvent],
    ) -> int:
        if not syllables:
            return 0
        if len(syllables) == 1:
            return 0

        if self.use_cmu_dict and self._g2p is not None:
            try:
                phonemes = self._g2p(word.text)
                # ARPABET stress markers: digits attached to vowel symbols
                # '1' = primary stress, '2' = secondary, '0' = unstressed.
                # Map phoneme stress to syllable index by counting vowels.
                vowel_count = 0
                primary_vowel = -1
                for ph in phonemes:
                    if isinstance(ph, str) and ph and ph[-1].isdigit():
                        if ph[-1] == "1":
                            primary_vowel = vowel_count
                        vowel_count += 1
                if 0 <= primary_vowel < len(syllables):
                    return primary_vowel
            except (KeyError, IndexError, AttributeError):
                pass

        # Heuristic fallback: first syllable (modal stress pattern in EN).
        return 0

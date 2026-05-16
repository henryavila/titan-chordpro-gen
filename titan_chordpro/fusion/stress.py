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

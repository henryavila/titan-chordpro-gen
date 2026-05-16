# titan_chordpro/fusion/syllabifier.py
"""Syllabifier using Maximum Onset Principle + orthographic fallback.

Two modes:
- Phonemic (preferred): consumes phoneme-level alignment from g2p_en (ARPABET)
  or gruut (IPA). Stress detection happens here when markers are present.
- Orthographic (fallback): vowel-cluster split when phonemes unavailable.
  Precision degrades from ~30ms to ~80-150ms.

Hybrid splitting rule (orthographic mode):
- 1 consonant between two vowels → onset of following syllable (CV.CV)
- 2+ consonants → 1 coda + rest onset (CVC.CV); approximates phonotactic
  legality for both PT-BR and EN without explicit phonotactic rules.

Spec reference: docs/superpowers/specs/2026-05-09-titan-v0.1-design.md → Section 3.1
"""

from __future__ import annotations

from titan_chordpro.core.schemas import (
    PhonemeEvent,
    SyllableEvent,
    TimeStamp,
    WordEvent,
)

# ARPABET vowel base symbols (CMU dict). Stress digits 0/1/2 stripped before lookup.
_ARPABET_VOWELS = frozenset(
    {
        "AA",
        "AE",
        "AH",
        "AO",
        "AW",
        "AY",
        "EH",
        "ER",
        "EY",
        "IH",
        "IY",
        "OW",
        "OY",
        "UH",
        "UW",
    }
)

# IPA vowel set (EN + PT-BR + common Romance).
_IPA_VOWELS = frozenset(
    {
        # Monophthongs
        "i",
        "ɪ",
        "e",
        "ɛ",
        "æ",
        "a",
        "ɑ",
        "ɒ",
        "ʌ",
        "ɔ",
        "o",
        "ʊ",
        "u",
        "y",
        "ø",
        "œ",
        "ɶ",
        "ɨ",
        "ʉ",
        "ɯ",
        "ə",
        "ɚ",
        "ɜ",
        "ɝ",
        "ɐ",
        # Common diphthongs (multi-char tokens from gruut/eSpeak)
        "eɪ",
        "aɪ",
        "ɔɪ",
        "aʊ",
        "oʊ",
        "ɛə",
        "ɪə",
        "ʊə",
        # Portuguese nasal vowels
        "ɐ̃",
        "ẽ",
        "ĩ",
        "õ",
        "ũ",
        "ɐ̃ʊ̃",
        "õĩ",
        "ɐ̃ĩ",
    }
)

# Orthographic vowels (Latin alphabet + diacritics, EN + PT-BR + common Romance).
# 'y' included as orthographic vowel (heuristic — works for "rhythm", "bye", "y-cluster";
# misclassifies "yes" but that's a single-syllable word so impact is minimal).
_ORTHOGRAPHIC_VOWELS = frozenset(
    "aeiouyAEIOUY" "áéíóúýÁÉÍÓÚÝ" "âêîôûÂÊÎÔÛ" "ãõÃÕ" "àèìòùÀÈÌÒÙ" "äëïöüÄËÏÖÜ"
)


def _strip_arpabet_stress(symbol: str) -> tuple[str, int]:
    """Returns (base_symbol, stress_level).

    Stress level: -1 if no marker present, otherwise 0/1/2 per CMU convention.
    Example: "AH1" → ("AH", 1); "L" → ("L", -1).
    """
    if symbol and symbol[-1] in "012":
        return symbol[:-1], int(symbol[-1])
    return symbol, -1


def _phoneme_is_vowel(symbol: str) -> bool:
    """Check if a phoneme symbol (ARPABET or IPA) represents a vowel nucleus."""
    base, _ = _strip_arpabet_stress(symbol)
    # Strip IPA stress markers (ˈ primary, ˌ secondary) before lookup
    stripped = base.lstrip("ˈˌ")
    # ARPABET symbols are always uppercase ASCII (e.g. HH, Y, AH).
    # Short-circuit to avoid the orthographic fallthrough misclassifying
    # consonants like 'Y' (palatal approximant) as vowels.
    if stripped.isascii() and stripped.isupper():
        return stripped in _ARPABET_VOWELS
    if stripped in _IPA_VOWELS:
        return True
    if len(stripped) == 1 and stripped in _ORTHOGRAPHIC_VOWELS:
        return True
    return False


def _phoneme_stress_level(symbol: str) -> int:
    """Returns -1 (no marker), 0 (unstressed), 1 (primary), 2 (secondary)."""
    base, arpa_stress = _strip_arpabet_stress(symbol)
    if arpa_stress >= 0:
        return arpa_stress
    if base.startswith("ˈ"):
        return 1
    if base.startswith("ˌ"):
        return 2
    return -1


def _orthographic_is_vowel(ch: str) -> bool:
    return ch in _ORTHOGRAPHIC_VOWELS


def syllabify_word(
    word: WordEvent,
    phonemes: list[PhonemeEvent],
    language: str,
) -> list[SyllableEvent]:
    """Apply Maximum Onset Principle to phoneme sequence.

    Algorithm:
        1. Identify nuclei (vowel phonemes) — each becomes a syllable.
        2. Between two nuclei, ALL consonants go to FOLLOWING syllable's onset (MOP).
        3. Trailing consonants of the last syllable become its coda.

    Stress is detected from phoneme markers when available:
        - ARPABET digit 1 → primary stress → is_stressed=True
        - IPA "ˈ" prefix → primary stress → is_stressed=True
        - Otherwise → is_stressed=False (T14 stress.py module fills it)

    Edge cases:
        - Empty phoneme list → 1 syllable spanning full word timestamp.
        - No vowel phonemes (e.g. "hmm") → 1 syllable.

    Note: SyllableEvent.text in phonemic mode is the concatenation of phoneme
    symbols (NOT orthographic). The placer (T20) maps syllable indices to
    orthographic char positions via linear distribution over parent word.
    """
    if not phonemes:
        return [
            SyllableEvent(
                text=word.text,
                timestamp=word.timestamp,
                is_stressed=False,
                parent_word_idx=0,
            )
        ]

    parent_idx = phonemes[0].parent_word_idx

    vowel_indices = [i for i, p in enumerate(phonemes) if _phoneme_is_vowel(p.symbol)]
    if not vowel_indices:
        return [
            SyllableEvent(
                text=word.text,
                phoneme_indices=list(range(len(phonemes))),
                timestamp=TimeStamp(
                    start=phonemes[0].timestamp.start,
                    end=phonemes[-1].timestamp.end,
                ),
                is_stressed=False,
                parent_word_idx=parent_idx,
            )
        ]

    syllables: list[SyllableEvent] = []
    for k, vi in enumerate(vowel_indices):
        # Start phoneme index for this syllable.
        # MOP: consonants between previous nucleus and this one all belong here.
        if k == 0:
            start_idx = 0
        else:
            start_idx = vowel_indices[k - 1] + 1

        # End phoneme index. Last syllable swallows trailing consonants as coda;
        # otherwise stop at the nucleus (consonants after go to next syllable's onset).
        if k == len(vowel_indices) - 1:
            end_idx = len(phonemes) - 1
        else:
            end_idx = vi

        syl_phonemes = phonemes[start_idx : end_idx + 1]
        is_stressed = any(_phoneme_stress_level(p.symbol) == 1 for p in syl_phonemes)

        syllables.append(
            SyllableEvent(
                text="".join(p.symbol for p in syl_phonemes),
                phoneme_indices=list(range(start_idx, end_idx + 1)),
                timestamp=TimeStamp(
                    start=syl_phonemes[0].timestamp.start,
                    end=syl_phonemes[-1].timestamp.end,
                ),
                is_stressed=is_stressed,
                parent_word_idx=parent_idx,
            )
        )

    return syllables


def syllabify_word_orthographic(
    word: WordEvent,
    language: str,
) -> list[SyllableEvent]:
    """Fallback syllabifier: vowel-cluster split + linear timestamps.

    Algorithm:
        1. Split on hyphen (compound words: "self-aware" → ["self", "aware"]).
        2. For each piece, find vowel-cluster nuclei (consecutive vowels = 1 nucleus).
        3. Apply hybrid MOP/CVC rule:
           - 1 consonant between nuclei → goes to next onset (CV.CV → "a-mi")
           - 2+ consonants → 1 coda + rest onset (CVC.CV → "vin-do", "in-stru")
        4. Distribute the word's time span linearly across syllables.

    Known limitations (documented in spec Section 3.1):
        - Hiatus not detected (PT "saída" rendered as 1 cluster instead of 2).
        - Silent letters not handled (EN "twelve" → 2 syllables instead of 1).
        - Complex onset clusters (EN "splash") collapse into single syllable when
          there is only one vowel cluster — that happens to be correct here.
        - is_stressed always False (T14 stress.py module fills it).
    """
    text = word.text
    if not text:
        return []

    # Compound words: recurse on each part.
    if "-" in text:
        parts = [p for p in text.split("-") if p]
        if not parts:
            return [_single_syllable(text, word.timestamp)]
        total_chars = sum(len(p) for p in parts)
        result: list[SyllableEvent] = []
        cursor = word.timestamp.start
        for i, part in enumerate(parts):
            part_dur = word.timestamp.duration * (len(part) / total_chars)
            part_end = cursor + part_dur if i < len(parts) - 1 else word.timestamp.end
            sub_word = WordEvent(
                text=part,
                timestamp=TimeStamp(start=cursor, end=part_end),
                source_engine=word.source_engine,
                language=word.language,
            )
            result.extend(syllabify_word_orthographic(sub_word, language))
            cursor = part_end
        return result

    # Find vowel-cluster spans (each cluster = one nucleus).
    nucleus_spans: list[tuple[int, int]] = []
    i = 0
    while i < len(text):
        if _orthographic_is_vowel(text[i]):
            j = i
            while j < len(text) and _orthographic_is_vowel(text[j]):
                j += 1
            nucleus_spans.append((i, j))
            i = j
        else:
            i += 1

    if not nucleus_spans:
        return [_single_syllable(text, word.timestamp)]

    # Build syllable char-spans using hybrid MOP/CVC rule.
    syllable_char_spans: list[tuple[int, int]] = []
    prev_end = 0
    for k, (_n_start, n_end) in enumerate(nucleus_spans):
        if k == len(nucleus_spans) - 1:
            syllable_char_spans.append((prev_end, len(text)))
            break

        next_n_start, _ = nucleus_spans[k + 1]
        n_consonants = next_n_start - n_end
        if n_consonants <= 1:
            # 0 or 1 consonant → all goes to following onset (CV.CV)
            syl_end = n_end
        else:
            # 2+ consonants → 1 coda for this syllable + rest to next onset (CVC.CV)
            syl_end = n_end + 1
        syllable_char_spans.append((prev_end, syl_end))
        prev_end = syl_end

    # Linear time distribution.
    n = len(syllable_char_spans)
    duration = word.timestamp.duration
    step = duration / n if n > 0 else duration
    syllables: list[SyllableEvent] = []
    for k, (cs, ce) in enumerate(syllable_char_spans):
        t_start = word.timestamp.start + k * step
        t_end = word.timestamp.start + (k + 1) * step if k < n - 1 else word.timestamp.end
        syllables.append(
            SyllableEvent(
                text=text[cs:ce],
                timestamp=TimeStamp(start=t_start, end=t_end),
                is_stressed=False,
                parent_word_idx=0,
            )
        )
    return syllables


def _single_syllable(text: str, ts: TimeStamp) -> SyllableEvent:
    return SyllableEvent(
        text=text,
        timestamp=ts,
        is_stressed=False,
        parent_word_idx=0,
    )

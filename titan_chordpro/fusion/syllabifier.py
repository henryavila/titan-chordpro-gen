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
_ORTHOGRAPHIC_VOWELS = frozenset("aeiouyAEIOUYáéíóúýÁÉÍÓÚÝâêîôûÂÊÎÔÛãõÃÕàèìòùÀÈÌÒÙäëïöüÄËÏÖÜ")


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


def _symbol_is_digit_token(symbol: str) -> bool:
    """True when *symbol* looks like a pure integer token id (e.g. MMS_FA)."""
    s = symbol.strip()
    return bool(s) and s.isdigit()


def phoneme_inventory_is_usable(phonemes: list[PhonemeEvent]) -> bool:
    """Return True only when *phonemes* look like real IPA/ARPABET symbols.

    MMS_FA forced-align often emits integer vocabulary ids as strings
    (``"1"``, ``"13"``). Those are not phonemes: MOP finds no vowels and
    every word collapses to a single syllable. Detect that inventory and
    let callers fall back to orthographic syllabification.

    Rules (generic, language-agnostic):
      - empty → unusable
      - ≥80% pure-digit symbols → unusable (token-id dump)
      - no vowel nucleus among symbols → unusable for MOP
    """
    if not phonemes:
        return False
    symbols = [p.symbol for p in phonemes]
    n = len(symbols)
    digitish = sum(1 for s in symbols if _symbol_is_digit_token(s))
    if digitish == n or digitish / n >= 0.8:
        return False
    if not any(_phoneme_is_vowel(s) for s in symbols):
        return False
    return True


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
        - No vowel phonemes but orthographic vowels present → orthographic fallback
          (covers MMS token-id "phonemes" and similar non-IPA inventories).
        - No vowel phonemes and no orthographic vowels (e.g. "hmm") → 1 syllable.

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

    # Non-phonemic inventories (digit token ids, etc.): never collapse multi-
    # syllable orthography to a single syllable via the no-vowel branch.
    if not phoneme_inventory_is_usable(phonemes):
        if any(_orthographic_is_vowel(ch) for ch in word.text):
            return syllabify_word_orthographic(word, language)
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

    vowel_indices = [i for i, p in enumerate(phonemes) if _phoneme_is_vowel(p.symbol)]
    if not vowel_indices:
        if any(_orthographic_is_vowel(ch) for ch in word.text):
            return syllabify_word_orthographic(word, language)
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


# ---------------------------------------------------------------------------
# Phase B engine adapter surface
# ---------------------------------------------------------------------------
# The T51/T52 Reference Implementations call three helpers that have slightly
# different names than the Phase A functions above.  These thin re-exports
# and adapters bridge the name gap without touching the original implementations.
# ---------------------------------------------------------------------------


def cv_split(text: str) -> list[str]:
    """Split a single word string into orthographic syllable texts.

    Adapter for Phase B engine wrappers (T51 portuguese.py, T52 english.py).
    Delegates to syllabify_word_orthographic with a dummy WordEvent and
    returns only the text labels.

    Example:
        cv_split("casa")  -> ["ca", "sa"]
        cv_split("amor")  -> ["a", "mor"]
    """
    dummy = WordEvent(
        text=text,
        timestamp=TimeStamp(start=0.0, end=1.0),
        source_engine="cv_split",
    )
    events = syllabify_word_orthographic(dummy, language="pt")
    return [e.text for e in events] if events else [text]


def syllabify_word_from_phonemes(
    word: WordEvent,
    phonemes: list[PhonemeEvent],
    word_idx: int,
    language: str,
) -> list[SyllableEvent]:
    """Syllabify one word from phonemes with parent_word_idx fixup.

    Phase B engine wrappers (T51/T52) call this instead of syllabify_word
    directly so they can pass word_idx without mutating phoneme objects.
    The returned SyllableEvent.parent_word_idx values are overridden to
    word_idx so upstream callers get consistent indexing regardless of the
    phoneme list's parent_word_idx field.

    When *phonemes* are not a usable IPA/ARPABET inventory (e.g. MMS_FA
    integer token ids), falls back to orthographic syllabification with
    linear timestamps and language-aware stress — never emits 1 syllable
    for multi-syllable orthography solely because token ids have no vowels.
    """
    if not phoneme_inventory_is_usable(phonemes):
        events = syllabify_word_orthographic(word, language)
        if not events:
            events = [
                SyllableEvent(
                    text=word.text,
                    timestamp=word.timestamp,
                    is_stressed=True,
                    parent_word_idx=word_idx,
                )
            ]
        # Lazy import avoids circular import with stress.py at module load.
        from titan_chordpro.fusion import stress as _fusion_stress

        texts = [e.text for e in events]
        stress_index = _fusion_stress.stressed_syllable_index(texts, language=language)
        fixed: list[SyllableEvent] = []
        for i, e in enumerate(events):
            fixed.append(
                e.model_copy(
                    update={
                        "parent_word_idx": word_idx,
                        "is_stressed": i == stress_index,
                    }
                )
            )
        return fixed

    events = syllabify_word(word=word, phonemes=phonemes, language=language)
    for e in events:
        object.__setattr__(e, "parent_word_idx", word_idx)
    return events


def group_arpabet_into_syllables(arpabet: list[str]) -> list[list[str]]:
    """Group a flat ARPABET token list into per-syllable token sublists.

    Each vowel nucleus (ARPABET token whose base is in _ARPABET_VOWELS)
    anchors one syllable.  Consonants before the first nucleus are prepended
    to it (onset); consonants between two nuclei go to the following onset
    (Maximum Onset Principle); trailing consonants after the last nucleus
    become its coda.

    Returns an empty list when arpabet is empty.

    Example:
        group_arpabet_into_syllables(["HH", "AH0", "L", "OW1"])
        -> [["HH", "AH0"], ["L", "OW1"]]
    """
    if not arpabet:
        return []

    vowel_positions = [i for i, tok in enumerate(arpabet) if _phoneme_is_vowel(tok)]

    if not vowel_positions:
        # No vowel found — treat the whole token list as a single syllable.
        return [list(arpabet)]

    groups: list[list[str]] = []
    for k, vi in enumerate(vowel_positions):
        # Onset: consonants from the previous nucleus+1 up to current vowel.
        if k == 0:
            onset_start = 0
        else:
            onset_start = vowel_positions[k - 1] + 1

        if k == len(vowel_positions) - 1:
            # Last nucleus: swallow trailing consonants as coda.
            groups.append(list(arpabet[onset_start:]))
        else:
            groups.append(list(arpabet[onset_start : vi + 1]))

    return groups

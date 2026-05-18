# titan_chordpro/engines/lang/portuguese.py
"""Portuguese syllabifier — SyllabificationEngine implementation.

Backed by gruut[pt-br] (MIT) for grapheme-to-phoneme + syllable split.
Stress detection delegates to fusion/stress.py (orthographic rules for PT).

Two paths:
  1. `phonemes` supplied (e.g. after torchaudio_align) → use fusion's
     Maximum Onset Principle on the phoneme spans.
  2. `phonemes` is None → use gruut's syllable split and interpolate
     timestamps linearly across each word's duration.
"""

from __future__ import annotations

import logging

from titan_chordpro.core.exceptions import EngineUnavailableError
from titan_chordpro.core.schemas import (
    EngineInfo,
    PhonemeEvent,
    SyllableEvent,
    TimeStamp,
    WordEvent,
)
from titan_chordpro.fusion import stress as _fusion_stress
from titan_chordpro.fusion import syllabifier as _fusion_syllabifier

_log = logging.getLogger(__name__)


def _check_gruut() -> None:
    try:
        import gruut  # noqa: F401
    except ImportError as exc:
        raise EngineUnavailableError(
            "gruut is not installed; install with `pip install -e .[mac]` "
            "or `pip install 'gruut[pt-br]'`",
            engine="gruut_pt",
            cause=exc,
        ) from exc


def _syllabify_pt_orthographic(word: str) -> list[str]:
    """Use gruut to split a PT word into orthographic syllables.

    Falls back to the fusion CV-split heuristic when gruut is not installed
    (e.g. in unit tests that bypass __init__ via __new__).
    """
    try:
        import gruut
    except ImportError:
        return _fusion_syllabifier.cv_split(word)

    # gruut.sentences returns Sentence objects with .words[i].text + .phonemes;
    # we ask for the orthographic syllable boundaries via .text.
    splits: list[str] = []
    for sent in gruut.sentences(word, lang="pt-br"):
        for w in sent.words:
            # gruut exposes syllable boundaries via `w.syllables` when available;
            # fall back to the existing fusion CV-split heuristic otherwise.
            syls = getattr(w, "syllables", None)
            if syls:
                splits.extend(syls)
            else:
                splits.extend(_fusion_syllabifier.cv_split(w.text))
    return splits or [word]


class PortugueseSyllabifierEngine:
    """Conforms to SyllabificationEngine Protocol."""

    def __init__(self) -> None:
        _check_gruut()

    @property
    def info(self) -> EngineInfo:
        return EngineInfo(
            name="gruut_pt",
            version="2.3",  # gruut does not expose __version__ cleanly
            backend="cpu",
        )

    @property
    def language(self) -> str:
        return "pt"

    def syllabify(
        self,
        words: list[WordEvent],
        phonemes: list[PhonemeEvent] | None = None,
    ) -> list[SyllableEvent]:
        if not words:
            return []

        syllables: list[SyllableEvent] = []
        for word_idx, word in enumerate(words):
            if phonemes is not None:
                # Path 1: phoneme-grounded; defer to fusion's MOP-aware splitter.
                word_phonemes = [p for p in phonemes if p.parent_word_idx == word_idx]
                events = _fusion_syllabifier.syllabify_word_from_phonemes(
                    word=word,
                    phonemes=word_phonemes,
                    word_idx=word_idx,
                    language="pt",
                )
                syllables.extend(events)
                continue

            # Path 2: orthographic split + linear time interpolation.
            text_parts = _syllabify_pt_orthographic(word.text)
            n = max(1, len(text_parts))
            duration = max(0.0, word.timestamp.end - word.timestamp.start)
            stress_index = _fusion_stress.stressed_syllable_index(text_parts, language="pt")
            for i, syl_text in enumerate(text_parts):
                start = word.timestamp.start + (duration * i / n)
                end = word.timestamp.start + (duration * (i + 1) / n)
                syllables.append(
                    SyllableEvent(
                        text=syl_text,
                        phoneme_indices=[],
                        timestamp=TimeStamp(start=start, end=end),
                        is_stressed=(i == stress_index),
                        parent_word_idx=word_idx,
                        confidence=1.0,
                    )
                )

        return syllables

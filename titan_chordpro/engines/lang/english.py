# titan_chordpro/engines/lang/english.py
"""English syllabifier — SyllabificationEngine implementation.

Backed by g2p_en (MIT) for grapheme-to-phoneme via the CMU dict + a
fallback seq2seq model. ARPABET output drives the fusion syllabifier's
Maximum Onset Principle path (Phase A T13). Stress markers come from the
CMU dict's 0/1/2 suffix convention (0=unstressed, 1=primary, 2=secondary).
"""

from __future__ import annotations

import logging
from typing import Any

from titan_chordpro.core.exceptions import EngineUnavailableError
from titan_chordpro.core.schemas import (
    EngineInfo,
    PhonemeEvent,
    SyllableEvent,
    TimeStamp,
    WordEvent,
)
from titan_chordpro.fusion import syllabifier as _fusion_syllabifier

_log = logging.getLogger(__name__)


def _load_g2p() -> Any:
    try:
        from g2p_en import G2p
    except ImportError as exc:
        raise EngineUnavailableError(
            "g2p_en is not installed; install with `pip install -e .[mac]` or `pip install g2p_en`",
            engine="g2p_en",
            cause=exc,
        ) from exc
    return G2p()


class EnglishSyllabifierEngine:
    """Conforms to SyllabificationEngine Protocol."""

    def __init__(self) -> None:
        self._g2p = _load_g2p()

    @property
    def info(self) -> EngineInfo:
        return EngineInfo(
            name="g2p_en",
            version="2.1",
            backend="cpu",
        )

    @property
    def language(self) -> str:
        return "en"

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
                word_phonemes = [p for p in phonemes if p.parent_word_idx == word_idx]
                events = _fusion_syllabifier.syllabify_word_from_phonemes(
                    word=word,
                    phonemes=word_phonemes,
                    word_idx=word_idx,
                    language="en",
                )
                syllables.extend(events)
                continue

            # Path 2: G2P → ARPABET → group into syllables → interpolate time.
            arpabet = [tok for tok in self._g2p(word.text) if tok.strip()]
            groups = _fusion_syllabifier.group_arpabet_into_syllables(arpabet)
            n = max(1, len(groups))
            duration = max(0.0, word.timestamp.end - word.timestamp.start)
            for i, syl_phonemes in enumerate(groups):
                start = word.timestamp.start + (duration * i / n)
                end = word.timestamp.start + (duration * (i + 1) / n)
                is_stressed = any(p.endswith("1") for p in syl_phonemes)
                syllables.append(
                    SyllableEvent(
                        text="".join(p.rstrip("012") for p in syl_phonemes).lower(),
                        phoneme_indices=[],
                        timestamp=TimeStamp(start=start, end=end),
                        is_stressed=is_stressed,
                        parent_word_idx=word_idx,
                        confidence=1.0,
                    )
                )

        return syllables

# titan_chordpro/fusion/melisma.py
"""Melisma detection.

Heuristic: syllable is melismatic if duration > 600ms AND spans more than one beat.
"""

from __future__ import annotations

from pydantic import BaseModel

from titan_chordpro.core.schemas import BeatGrid, ChordEvent, SyllableEvent, TimeStamp

MELISMA_MIN_DURATION = 0.600  # 600ms


class Melisma(BaseModel):
    """A detected melisma: a syllable spanning multiple beats."""

    syllable_idx: int
    span: TimeStamp


def detect_melismas(
    syllables: list[SyllableEvent],
    chords: list[ChordEvent],
    beat_grid: BeatGrid,
    vocal_pitch_track: list[float] | None = None,
) -> list[Melisma]:
    """Detect melismas in syllables.

    v0.1: simple heuristic — duration > 600ms AND spans > 1 beat.
    v0.2: will add pitch_variance > 50 cents check using vocal_pitch_track.

    Args:
        syllables: List of syllable events.
        chords: List of chord events (unused in v0.1).
        beat_grid: Beat grid for finding beat boundaries.
        vocal_pitch_track: Optional pitch track (ignored in v0.1).

    Returns:
        List of detected melismas.
    """
    result: list[Melisma] = []

    for i, syl in enumerate(syllables):
        # Filter 1: duration must be > 600ms
        if syl.timestamp.duration <= MELISMA_MIN_DURATION:
            continue

        # Filter 2: must span more than one beat
        beats_in_span = [
            b for b in beat_grid.beats if syl.timestamp.start <= b <= syl.timestamp.end
        ]

        if len(beats_in_span) <= 1:
            continue

        # v0.2 will add: pitch_variance > 50 cents check
        result.append(Melisma(syllable_idx=i, span=syl.timestamp))

    return result

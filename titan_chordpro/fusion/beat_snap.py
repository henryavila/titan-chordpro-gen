# titan_chordpro/fusion/beat_snap.py
"""Quantization of chord events to beat grid.

Spec reference: Section 3.3. Uses mir_eval-calibrated tolerances:
±70ms for beat snap, ±150ms for 8th-note snap.
"""

from __future__ import annotations

from typing import Literal

from titan_chordpro.core.schemas import BeatGrid, ChordEvent, TimeStamp

SNAP_TO_BEAT_TOLERANCE = 0.070  # ±70ms — mir_eval beat tolerance
SNAP_TO_8TH_TOLERANCE = 0.150  # ±150ms — 8th-note tolerance


SnapLevel = Literal["beat", "8th", "unsnapped"]


def snap_chord_to_grid(
    chord: ChordEvent,
    beat_grid: BeatGrid,
) -> tuple[ChordEvent, SnapLevel]:
    """Snap chord.timestamp.start to nearest beat or 8th-note within tolerance.

    Returns (possibly-modified ChordEvent, which grid level it snapped to).
    """
    if not beat_grid.beats:
        return chord, "unsnapped"

    t = chord.timestamp.start

    # Find nearest beat
    nearest_beat = min(beat_grid.beats, key=lambda b: abs(b - t))
    beat_diff = abs(nearest_beat - t)

    if beat_diff <= SNAP_TO_BEAT_TOLERANCE:
        new_ts = TimeStamp(start=nearest_beat, end=chord.timestamp.end)
        return chord.model_copy(update={"timestamp": new_ts}), "beat"

    # Find nearest 8th-note (midpoint between consecutive beats)
    eighths: list[float] = []
    for i in range(len(beat_grid.beats) - 1):
        eighths.append((beat_grid.beats[i] + beat_grid.beats[i + 1]) / 2)

    if eighths:
        nearest_8th = min(eighths, key=lambda e: abs(e - t))
        eighth_diff = abs(nearest_8th - t)
        if eighth_diff <= SNAP_TO_8TH_TOLERANCE:
            new_ts = TimeStamp(start=nearest_8th, end=chord.timestamp.end)
            return chord.model_copy(update={"timestamp": new_ts}), "8th"

    return chord, "unsnapped"

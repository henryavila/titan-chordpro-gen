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


def _timestamp_with_snapped_start(
    original: TimeStamp,
    new_start: float,
) -> TimeStamp:
    """Build a TimeStamp after snapping start, clamping end so end >= start.

    Preserves original duration when possible: if the snap moves start past the
    original end, end becomes new_start + original duration (or at least
    new_start when duration was zero).
    """
    original_start = original.start
    original_end = original.end
    duration = max(0.0, original_end - original_start)
    if new_start <= original_end:
        # Snap stayed within/before original end — keep original end (and
        # duration may grow slightly when start moves earlier; that is fine).
        new_end = max(original_end, new_start)
    else:
        # Snap moved start past original end — preserve duration.
        new_end = new_start + duration
    return TimeStamp(start=new_start, end=new_end)


def snap_chord_to_grid(
    chord: ChordEvent,
    beat_grid: BeatGrid,
) -> tuple[ChordEvent, SnapLevel]:
    """Snap chord.timestamp.start to nearest beat or 8th-note within tolerance.

    Returns (possibly-modified ChordEvent, which grid level it snapped to).
    When the snap target is past the original end, end is clamped so
    ``end >= start`` (duration preserved when possible) to avoid
    ``TimeStamp`` ValidationError on short chords.
    """
    if not beat_grid.beats:
        return chord, "unsnapped"

    t = chord.timestamp.start

    # Find nearest beat
    nearest_beat = min(beat_grid.beats, key=lambda b: abs(b - t))
    beat_diff = abs(nearest_beat - t)

    if beat_diff <= SNAP_TO_BEAT_TOLERANCE:
        new_ts = _timestamp_with_snapped_start(chord.timestamp, nearest_beat)
        return chord.model_copy(update={"timestamp": new_ts}), "beat"

    # Find nearest 8th-note (midpoint between consecutive beats)
    eighths: list[float] = []
    for i in range(len(beat_grid.beats) - 1):
        eighths.append((beat_grid.beats[i] + beat_grid.beats[i + 1]) / 2)

    if eighths:
        nearest_8th = min(eighths, key=lambda e: abs(e - t))
        eighth_diff = abs(nearest_8th - t)
        if eighth_diff <= SNAP_TO_8TH_TOLERANCE:
            new_ts = _timestamp_with_snapped_start(chord.timestamp, nearest_8th)
            return chord.model_copy(update={"timestamp": new_ts}), "8th"

    return chord, "unsnapped"

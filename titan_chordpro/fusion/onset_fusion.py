# titan_chordpro/fusion/onset_fusion.py
"""Multi-evidence chord onset fusion.

v0.1: simple — snap via beat_snap and return.
v0.2: weighted average of chord_recognizer + beat + bass_attack + vocal_consonant.
"""

from __future__ import annotations

from titan_chordpro.core.schemas import BeatGrid, ChordEvent
from titan_chordpro.fusion.beat_snap import snap_chord_to_grid


def fuse_onsets_v01(chord: ChordEvent, beats: BeatGrid) -> float:
    """Snap chord to beat grid and return onset timestamp.

    Args:
        chord: The chord event to fuse.
        beats: The beat grid for snapping.

    Returns:
        The snapped (or original) onset timestamp in seconds.
    """
    snapped, _level = snap_chord_to_grid(chord, beats)
    return snapped.timestamp.start

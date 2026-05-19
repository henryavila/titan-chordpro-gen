"""mir_eval adapters for the validation harness.

Converts Titan symbol form (`C`, `Gm7`, `F/A`) to mir_eval form
(`C:maj`, `G:min7`, `F:maj/A`). Computes WCSR-majmin per spec §1526.
"""

from __future__ import annotations

import re
from typing import Any

_TITAN_TO_MIR: tuple[tuple[re.Pattern[str], str], ...] = (
    # Slash chord with min7 quality: "Cm7/Eb" → "C:min7/Eb"
    (re.compile(r"^([A-G][#b]?)m7/([A-G][#b]?)$"), r"\1:min7/\2"),
    # Slash chord with maj7 quality: "Cmaj7/E" → "C:maj7/E"
    (re.compile(r"^([A-G][#b]?)maj7/([A-G][#b]?)$"), r"\1:maj7/\2"),
    # Brazilian "7M" notation for maj7 (e.g., F7M = Fmaj7); slash variant first
    (re.compile(r"^([A-G][#b]?)7M/([A-G][#b]?)$"), r"\1:maj7/\2"),
    # Slash chord with min quality: "Am/C" → "A:min/C"
    (re.compile(r"^([A-G][#b]?)m/([A-G][#b]?)$"), r"\1:min/\2"),
    # Slash chord plain major: "F/A" → "F:maj/A"
    (re.compile(r"^([A-G][#b]?)/([A-G][#b]?)$"), r"\1:maj/\2"),
    # Quality min7: "Gm7" → "G:min7"
    (re.compile(r"^([A-G][#b]?)m7$"), r"\1:min7"),
    # Quality maj7: "Cmaj7" → "C:maj7"
    (re.compile(r"^([A-G][#b]?)maj7$"), r"\1:maj7"),
    # Brazilian "7M" notation for maj7 (e.g., F7M, C7M)
    (re.compile(r"^([A-G][#b]?)7M$"), r"\1:maj7"),
    # Suspended chords — mir_eval majmin rejects sus2/sus4; collapse to
    # root major for majmin-vocabulary scoring (suspended ≈ major in coarse
    # comparison). Handle slash variant first.
    (re.compile(r"^([A-G][#b]?)sus[24]?/([A-G][#b]?)$"), r"\1:maj/\2"),
    (re.compile(r"^([A-G][#b]?)sus[24]?$"), r"\1:maj"),
    # Quality dim: "F#dim" → "F#:dim"
    (re.compile(r"^([A-G][#b]?)dim$"), r"\1:dim"),
    # Quality min: "Gm" → "G:min"
    (re.compile(r"^([A-G][#b]?)m$"), r"\1:min"),
    # Quality 7: "C7" → "C:7"
    (re.compile(r"^([A-G][#b]?)7$"), r"\1:7"),
    # Plain major: "C" → "C:maj"
    (re.compile(r"^([A-G][#b]?)$"), r"\1:maj"),
)


def to_mir_eval_chord(symbol: str) -> str:
    """Convert a Titan chord symbol to mir_eval's vocabulary.

    No-chord ("N") is returned as-is. Unknown shapes are returned as-is
    too — mir_eval will treat them as a single unique class (not crash).
    """
    if symbol == "N":
        return "N"
    for pat, repl in _TITAN_TO_MIR:
        new = pat.sub(repl, symbol)
        if new != symbol:
            return new
    return symbol


def chord_events_to_intervals(
    events: list[Any],
) -> tuple[list[tuple[float, float]], list[str]]:
    """Convert Titan ChordEvent list → (intervals, mir_eval-format labels).

    bass_note is appended as a slash-chord component to the mir_eval label.
    """
    intervals: list[tuple[float, float]] = []
    labels: list[str] = []
    for evt in events:
        base = to_mir_eval_chord(evt.symbol)
        if getattr(evt, "bass_note", None):
            base = f"{base}/{evt.bass_note}"
        intervals.append((evt.timestamp.start, evt.timestamp.end))
        labels.append(base)
    return intervals, labels


def compute_wcsr_majmin(
    ref_intervals: list[tuple[float, float]],
    ref_labels: list[str],
    est_intervals: list[tuple[float, float]],
    est_labels: list[str],
) -> float:
    """Weighted chord symbol recall at majmin vocabulary.

    Returns score in [0.0, 1.0]. 0.0 on empty inputs.
    """
    import mir_eval
    import numpy as np

    if not ref_intervals or not est_intervals:
        return 0.0

    ref_intervals_np = np.array(ref_intervals)
    est_intervals_np = np.array(est_intervals)

    end = float(ref_intervals_np[-1, 1])
    est_intervals_np, est_labels_clipped = mir_eval.util.adjust_intervals(
        est_intervals_np,
        list(est_labels),
        t_min=0.0,
        t_max=end,
        start_label="N",
        end_label="N",
    )

    merged_intervals, ref_aligned, est_aligned = mir_eval.util.merge_labeled_intervals(
        ref_intervals_np, list(ref_labels), est_intervals_np, est_labels_clipped
    )
    durations = mir_eval.util.intervals_to_durations(merged_intervals)
    scores = mir_eval.chord.majmin(ref_aligned, est_aligned)
    return float(mir_eval.chord.weighted_accuracy(scores, durations))

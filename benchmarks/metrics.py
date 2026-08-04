"""mir_eval adapters for the validation harness.

Converts Titan symbol form (`C`, `Gm7`, `F/A`) to mir_eval form
(`C:maj`, `G:min7`, `F:maj/A`). Computes WCSR-majmin per spec §1526.
"""

from __future__ import annotations

import re
from typing import Any

_TITAN_TO_MIR: tuple[tuple[re.Pattern[str], str], ...] = (
    # === Slash-chord variants (most specific first) ===
    # Slash with min7 quality: "Cm7/Eb" → "C:min7/Eb"
    (re.compile(r"^([A-G][#b]?)m7/([A-G][#b]?)$"), r"\1:min7/\2"),
    # Slash with maj7 quality: "Cmaj7/E" → "C:maj7/E"
    (re.compile(r"^([A-G][#b]?)maj7/([A-G][#b]?)$"), r"\1:maj7/\2"),
    # Brazilian "7M" notation for maj7 — slash variant
    (re.compile(r"^([A-G][#b]?)7M/([A-G][#b]?)$"), r"\1:maj7/\2"),
    # Slash with min: "Am/C" → "A:min/C"
    (re.compile(r"^([A-G][#b]?)m/([A-G][#b]?)$"), r"\1:min/\2"),
    # Slash plain major: "F/A" → "F:maj/A"
    (re.compile(r"^([A-G][#b]?)/([A-G][#b]?)$"), r"\1:maj/\2"),
    # === Non-slash qualities ===
    (re.compile(r"^([A-G][#b]?)m7$"), r"\1:min7"),
    (re.compile(r"^([A-G][#b]?)maj7$"), r"\1:maj7"),
    # Brazilian "7M" notation
    (re.compile(r"^([A-G][#b]?)7M$"), r"\1:maj7"),
    # Suspended chords collapse to root major in majmin vocab.
    (re.compile(r"^([A-G][#b]?)sus[24]?/([A-G][#b]?)$"), r"\1:maj/\2"),
    (re.compile(r"^([A-G][#b]?)sus[24]?$"), r"\1:maj"),
    # Diminished
    (re.compile(r"^([A-G][#b]?)dim$"), r"\1:dim"),
    (re.compile(r"^([A-G][#b]?)°$"), r"\1:dim"),
    # Augmented
    (re.compile(r"^([A-G][#b]?)aug$"), r"\1:aug"),
    (re.compile(r"^([A-G][#b]?)\+$"), r"\1:aug"),
    # Minor (must come before "m9"/"m6")
    (re.compile(r"^([A-G][#b]?)m9$"), r"\1:min"),
    (re.compile(r"^([A-G][#b]?)m6$"), r"\1:min"),
    (re.compile(r"^([A-G][#b]?)m$"), r"\1:min"),
    # Dominant 7th
    (re.compile(r"^([A-G][#b]?)7$"), r"\1:7"),
    # Brazilian "9" / "6" extensions — collapse to root major in majmin vocab.
    # Phase C T70 iter: corpus song "Tua vontade" had 'D9' which the spec's
    # majmin scorer rejects; treat add9 ≈ major (lossy but consistent).
    (re.compile(r"^([A-G][#b]?)9$"), r"\1:maj"),
    (re.compile(r"^([A-G][#b]?)6$"), r"\1:maj"),
    # Plain major: "C" → "C:maj"
    (re.compile(r"^([A-G][#b]?)$"), r"\1:maj"),
)


# Catch-all fallback: when no specific pattern matches but the symbol
# starts with a recognizable root letter (e.g., 'Bm7b5', 'C7sus4', exotic
# Brazilian extensions), extract the root and collapse to major. This
# preserves WCSR-majmin coarse comparison without letting one unknown
# suffix kill the whole song's metric.
_ROOT_PREFIX_RE = re.compile(r"^([A-G][#b]?)")


def to_mir_eval_chord(symbol: str) -> str:
    """Convert a Titan chord symbol to mir_eval's vocabulary.

    No-chord ("N") is returned as-is.

    Catch-all (Phase C T70 iter): when no pattern matches, extract the
    root letter and collapse to major. This handles exotic suffixes
    (Brazilian 11, 13, m7b5, etc.) gracefully without crashing
    mir_eval — at the cost of lossy comparison in majmin vocab (which
    is the right tradeoff: an add-tone chord IS a major chord in coarse
    comparison).
    """
    if symbol == "N":
        return "N"
    for pat, repl in _TITAN_TO_MIR:
        new = pat.sub(repl, symbol)
        if new != symbol:
            return new
    # No regex matched. Try the catch-all root-prefix extraction.
    m = _ROOT_PREFIX_RE.match(symbol)
    if m:
        # Heuristic: if 'm' immediately follows the root and is followed by
        # a digit (e.g., 'Bm7b5'), classify as minor; otherwise major.
        root = m.group(1)
        remainder = symbol[len(root) :]
        if remainder.startswith("m") and not remainder.startswith("maj"):
            return f"{root}:min"
        return f"{root}:maj"
    return symbol


def chord_events_to_intervals(
    events: list[Any],
) -> tuple[list[tuple[float, float]], list[str]]:
    """Convert Titan ChordEvent list → (intervals, mir_eval-format labels).

    bass_note is appended as a slash-chord component to the mir_eval label.

    Events are sorted by onset so collecting chords from interleaved
    LyricLine/InstrumentalLine order (post orphan materialization) still
    yields monotonic intervals for mir_eval.
    """
    intervals: list[tuple[float, float]] = []
    labels: list[str] = []
    ordered = sorted(events, key=lambda e: (e.timestamp.start, e.timestamp.end))
    for evt in ordered:
        base = to_mir_eval_chord(evt.symbol)
        if getattr(evt, "bass_note", None):
            base = f"{base}/{evt.bass_note}"
        intervals.append((evt.timestamp.start, evt.timestamp.end))
        labels.append(base)
    return intervals, labels


_SLASH_BASS_RE = re.compile(r"/[A-G][#b]?$")


def _strip_slash_for_majmin(label: str) -> str:
    """mir_eval.chord.majmin treats slash bass as out-of-vocabulary when
    the bass is an absolute pitch class (e.g., 'E:maj/G#'). Strip the
    bass for the scoring pass — bass info is preserved in the original
    label trail and can be re-introduced when v0.2 supports inversions.

    Phase C T70 iter (corpus 'Tua vontade': 'E/G#' / 'G/B' etc).
    """
    return _SLASH_BASS_RE.sub("", label)


def compute_beat_consistency_vs_librosa(
    audio_path: Any,
    titan_beats: list[float],
    *,
    sr: int = 22050,
    f_measure_threshold: float = 0.07,
) -> dict[str, float]:
    """Cross-detector beat consistency against librosa.beat.beat_track.

    Spec §1683 originally asked for "Beat F ≥ 0.85" against ground-truth
    beat times. The iasdermelinda corpus does NOT carry beat timestamps,
    so a true F-measure against ground truth is impossible in Phase C.

    What we compute instead: agreement between Titan's beat output and
    librosa.beat.beat_track (a classical detector run on the same audio).
    This is a CROSS-DETECTOR CONSISTENCY signal — useful for detecting
    catastrophic regressions in the Titan beat engine, but it is NOT a
    ground-truth gate. Octave errors (one detector at 2x tempo) drive
    F-measure down even when both detectors are individually sensible;
    AMLt (Allowed Metrical Level, total accuracy) is the octave-invariant
    companion metric and is more robust for cross-detector comparison.

    Returns dict with keys `f_measure` and `amlt` (both in [0.0, 1.0]).
    Returns zeros on empty input or load failure (caller decides whether
    to record or skip).

    Phase D should replace this with mir_eval.beat.f_measure against a
    labeled subset (DALI / RWC-Pop / hand-annotated) and apply the spec's
    ≥ 0.85 gate properly.
    """
    import librosa
    import mir_eval
    import numpy as np

    if not titan_beats:
        return {"f_measure": 0.0, "amlt": 0.0}

    try:
        y, sr_loaded = librosa.load(str(audio_path), sr=sr, mono=True)
        _, librosa_beats = librosa.beat.beat_track(y=y, sr=sr_loaded, units="time")
    except Exception:  # noqa: BLE001
        return {"f_measure": 0.0, "amlt": 0.0}

    ref = mir_eval.beat.trim_beats(np.asarray(librosa_beats, dtype=float))
    est = mir_eval.beat.trim_beats(np.asarray(titan_beats, dtype=float))
    if ref.size == 0 or est.size == 0:
        return {"f_measure": 0.0, "amlt": 0.0}

    f = float(mir_eval.beat.f_measure(ref, est, f_measure_threshold=f_measure_threshold))
    _cml_c, _cml_t, _aml_c, aml_t = mir_eval.beat.continuity(ref, est)
    return {"f_measure": f, "amlt": float(aml_t)}


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

    # Strip slash-bass from labels for majmin scoring (mir_eval rejects
    # E:maj/G# etc — majmin vocab is root+quality only).
    ref_labels_majmin = [_strip_slash_for_majmin(lbl) for lbl in ref_labels]
    est_labels_majmin = [_strip_slash_for_majmin(lbl) for lbl in est_labels]

    ref_intervals_np = np.array(ref_intervals)
    est_intervals_np = np.array(est_intervals)

    end = float(ref_intervals_np[-1, 1])
    est_intervals_np, est_labels_clipped = mir_eval.util.adjust_intervals(
        est_intervals_np,
        list(est_labels_majmin),
        t_min=0.0,
        t_max=end,
        start_label="N",
        end_label="N",
    )

    merged_intervals, ref_aligned, est_aligned = mir_eval.util.merge_labeled_intervals(
        ref_intervals_np, list(ref_labels_majmin), est_intervals_np, est_labels_clipped
    )
    durations = mir_eval.util.intervals_to_durations(merged_intervals)
    scores = mir_eval.chord.majmin(ref_aligned, est_aligned)
    return float(mir_eval.chord.weighted_accuracy(scores, durations))

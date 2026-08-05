# titan_chordpro/engines/chord/chordino.py
"""Chordino via chord-extractor — ChordRecognitionEngine implementation.

Chordino is a VAMP plugin (GPL-2.0). It must be installed via
`scripts/install_vamp.sh` (T49). chord-extractor (MIT-licensed Python
wrapper) calls Chordino as a subprocess; runtime separation means the
GPL contagion does not extend to titan-chordpro-lib (which stays MIT).

Output format:
  - chord_extractor returns objects with `.chord` (e.g. "C:maj", "G:min7",
    "N" for no-chord) and `.timestamp` (start time in seconds).
  - Chord intervals are derived by pairing each onset with the next one;
    the last chord runs to the end of the audio (Chordino does not emit
    an explicit "end" marker — we use a sentinel from soundfile).

F-004 (Phase C): when a bass stem is provided, per-interval bass-note
chroma is computed via `bass_chroma.extract_bass_note`. The detected
note is emitted as `ChordEvent.bass_note` ONLY when it differs from the
chord root (no spurious "F/F" slash chords) AND chroma confidence ≥ 0.5
(asymmetric — root position is the safer default).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Literal

from titan_chordpro.core.exceptions import ChordRecognitionError, EngineUnavailableError
from titan_chordpro.core.schemas import ChordEvent, EngineInfo, TimeStamp
from titan_chordpro.engines.chord.bass_chroma import (
    extract_bass_note,
    filter_bass_to_chord_tones,
)

_MAJ_QUAL = ":maj"
_MIN_QUAL = ":min"
_CHORD_ROOT_RE = re.compile(r"^[A-G][#b]?")
_log = logging.getLogger(__name__)

# Pitch-class order used by key estimation / out-of-key snap.
_PC: tuple[str, ...] = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
_FLAT_TO_SHARP: dict[str, str] = {
    "Db": "C#",
    "Eb": "D#",
    "Gb": "F#",
    "Ab": "G#",
    "Bb": "A#",
}

# Minimum chord duration (seconds). Shorter "flutter" detections are merged
# into the longer neighbour — Chordino occasionally emits sub-beat noise on
# dense worship mixes that destroys both placement and WCSR.
MIN_CHORD_DURATION_S = 0.60

# RC3 — long-hold resegmentation: multi-bar holds are re-checked with
# beat-sized chroma windows against the diatonic triad set. Defaults are
# relative to ``beat_period`` when the caller does not override absolute
# seconds. No song-specific thresholds.
DEFAULT_BEAT_PERIOD_S = 0.75  # ~80 BPM fallback when onsets are sparse
MIN_HOLD_BEATS = 3.0  # ~1.5 half-bars / short multi-beat tonic pads
MIN_ALT_BEATS = 1.0  # alternate root must dominate ≥1 beat to split
# H1: peel multi-change pads. One pass inserts only the first alternate and
# suffix-commits it; further passes re-scan long pieces so a 30s hold can
# surface 2–3 harmonic changes without recursive window flutter inside one split.
RESEG_MAX_PASSES = 6
# Holds at/above this duration use full beat-window relabel (run merge) instead
# of single first-alt split — fixes wrong-onset pads (e.g. F labeled for a span
# that opens on C) and multi-change outros without song-specific thresholds.
LONG_HOLD_FORCE_RELABEL_S = 12.0
CHROMA_SCORE_MARGIN = 0.01  # baseline edge over current-label score
# Primary harmonic functions (I/IV/V/vi) get the baseline or easier margin;
# secondary (ii/iii/dim) need a larger edge to suppress pad-overtone FPs.
CHROMA_SCORE_MARGIN_DOMINANT = 0.004  # V under pads is systematically weak
CHROMA_SCORE_MARGIN_SECONDARY = 0.08  # iii/ii almost never inserted without huge edge
# Additive score prior for the key dominant so weak V under tonic pads can
# surface for ≥1 beat without lowering the bar for iii/ii.
CHROMA_DOMINANT_SCORE_PRIOR = 0.02
# When True (default), reseg inserts only primary functions + dominant + bVII.
# Secondary diatonic triads (ii/iii/dim) are excluded from change-point
# candidates — they remain available only via the extreme secondary path
# if RESEG_ALLOW_SECONDARY is enabled.
RESEG_PRIMARY_ONLY = True
RESEG_ALLOW_SECONDARY = False
CHROMA_HOP_LENGTH = 512  # finer hop than bass_chroma (change-point recall)
# Bass confidence floor for slash emission (matches bass_chroma default).
BASS_NOTE_MIN_CONFIDENCE = 0.5


def _load_extractor() -> Any:
    try:
        from chord_extractor.extractors import Chordino
    except ImportError as exc:
        raise EngineUnavailableError(
            "chord_extractor (with Chordino VAMP plugin) is not installed; "
            "run scripts/install_vamp.sh and see docs/setup-vamp.md",
            engine="chordino",
            cause=exc,
        ) from exc
    return Chordino()


def _normalize_chord_symbol(raw: str) -> str | None:
    """Convert chord_extractor output to ChordEvent.symbol format."""
    if not raw or raw == "N":
        return None
    if _MAJ_QUAL in raw:
        root, _, suffix = raw.partition(_MAJ_QUAL)
        return root if not suffix else f"{root}maj{suffix}"
    if _MIN_QUAL in raw:
        root, _, suffix = raw.partition(_MIN_QUAL)
        return f"{root}m{suffix}" if suffix else f"{root}m"
    return raw.replace(":", "")


def _chord_root(symbol: str) -> str:
    """Extract the root letter (sharp form) from a chord symbol.

    Phase C operates on sharp form internally; rendering layer handles
    enharmonic preferences. Flat-to-sharp mapping ensures bass_chroma
    (sharp-only) compares correctly to chord symbols that may carry flats.
    """
    m = _CHORD_ROOT_RE.match(symbol)
    if not m:
        return symbol
    root = m.group(0)
    return _FLAT_TO_SHARP.get(root, root)


def _majmin_quality(symbol: str) -> str:
    """Return 'min' if the symbol is a minor triad/quality, else 'maj'.

    Slash bass and extensions are ignored — only the triad quality matters
    for key estimation and out-of-key snap (majmin vocabulary).
    """
    # Strip slash bass first so "Am/C" still reads as minor.
    base = symbol.split("/", 1)[0]
    m = _CHORD_ROOT_RE.match(base)
    if not m:
        return "maj"
    remainder = base[len(m.group(0)) :]
    if remainder.startswith("m") and not remainder.startswith("maj"):
        return "min"
    return "maj"


def _diatonic_set(key_root: str, mode: str) -> set[tuple[str, str]]:
    """Return {(root, quality)} for the diatonic triad set of key_root/mode.

    Worship charts frequently use bVII (major) as a secondary colour, so
    major-key sets include the flat-7 major triad as a soft allowance.
    """
    key_root = _FLAT_TO_SHARP.get(key_root, key_root)
    i = _PC.index(key_root) if key_root in _PC else 0
    if mode == "minor":
        steps = (0, 2, 3, 5, 7, 8, 10)
        quals = ("min", "dim", "maj", "min", "min", "maj", "maj")
    else:
        steps = (0, 2, 4, 5, 7, 9, 10)  # include bVII major (worship colour)
        quals = ("maj", "min", "min", "maj", "maj", "min", "maj")
    return {(_PC[(i + s) % 12], q) for s, q in zip(steps, quals, strict=True)}


def estimate_key(events: list[ChordEvent]) -> tuple[str, str]:
    """Estimate (key_root, mode) from a chord histogram (duration-weighted).

    Tries all 24 major/minor keys and returns the one whose diatonic set
    covers the most event duration. Falls back to ("C", "major") on empty.
    """
    if not events:
        return "C", "major"

    # Duration-weighted bag of (root, quality).
    bag: dict[tuple[str, str], float] = {}
    for e in events:
        root = _chord_root(e.symbol)
        if root not in _PC:
            continue
        qual = _majmin_quality(e.symbol)
        dur = max(0.0, e.timestamp.end - e.timestamp.start)
        bag[(root, qual)] = bag.get((root, qual), 0.0) + dur

    if not bag:
        return "C", "major"

    best_key = "C"
    best_mode = "major"
    best_cov = -1.0
    for root in _PC:
        for mode in ("major", "minor"):
            dia = _diatonic_set(root, mode)
            cov = sum(w for k, w in bag.items() if k in dia)
            if cov > best_cov:
                best_cov = cov
                best_key = root
                best_mode = mode
    return best_key, best_mode


def _nearest_diatonic(root: str, quality: str, dia: set[tuple[str, str]]) -> tuple[str, str]:
    """Map an out-of-key (root, quality) onto the closest diatonic triad."""
    if (root, quality) in dia:
        return root, quality
    if root not in _PC:
        return next(iter(dia))
    ri = _PC.index(root)
    best: tuple[str, str] | None = None
    best_dist = 99.0
    for dr, dq in dia:
        di = _PC.index(dr)
        dist = float(min((di - ri) % 12, (ri - di) % 12))
        if dq == quality:
            dist -= 0.5  # prefer keeping the same quality when possible
        if dist < best_dist:
            best_dist = dist
            best = (dr, dq)
    return best if best is not None else (root, quality)


def _rewrite_symbol_root_quality(symbol: str, new_root: str, new_quality: str) -> str:
    """Rewrite symbol keeping slash bass / extensions where possible.

    Extensions (7, maj7, …) are dropped on quality flips so we never emit
    nonsense like "Cm maj7". Slash bass is preserved when present.
    """
    bass = None
    base = symbol
    if "/" in symbol:
        base, bass = symbol.split("/", 1)
    # Keep simple extensions only when quality matches the original.
    orig_q = _majmin_quality(symbol)
    m = _CHORD_ROOT_RE.match(base)
    remainder = base[len(m.group(0)) :] if m else ""
    if new_quality == orig_q and remainder:
        # Preserve original suffix (m7, maj7, 7, …) but swap the root letter.
        # Normalise leading 'm' so "Am7" → root A + "m7"; if new_root is C
        # and quality min → "Cm7".
        if remainder.startswith("maj"):
            new_sym = f"{new_root}{remainder}"
        elif remainder.startswith("m"):
            new_sym = (
                f"{new_root}{remainder}" if new_quality == "min" else f"{new_root}{remainder[1:]}"
            )
        else:
            new_sym = f"{new_root}{remainder}"
    else:
        new_sym = new_root if new_quality == "maj" else f"{new_root}m"
    if bass:
        new_sym = f"{new_sym}/{bass}"
    return new_sym


def snap_events_to_key(events: list[ChordEvent], key_root: str, mode: str) -> list[ChordEvent]:
    """Snap out-of-key chord roots onto the estimated diatonic set.

    In-key events are returned unchanged (new object only when rewritten).
    """
    dia = _diatonic_set(key_root, mode)
    out: list[ChordEvent] = []
    for e in events:
        root = _chord_root(e.symbol)
        if root not in _PC:
            out.append(e)
            continue
        qual = _majmin_quality(e.symbol)
        if (root, qual) in dia:
            out.append(e)
            continue
        new_root, new_qual = _nearest_diatonic(root, qual, dia)
        if new_root == root and new_qual == qual:
            out.append(e)
            continue
        new_symbol = _rewrite_symbol_root_quality(e.symbol, new_root, new_qual)
        # Drop bass_note when it collides with the rewritten root.
        bass = e.bass_note
        if bass is not None and bass == new_root:
            bass = None
        # If symbol already encodes a slash and bass disagrees after rewrite,
        # clear the field — schema validator rejects mismatches.
        if "/" in new_symbol:
            bass = None
        out.append(e.model_copy(update={"symbol": new_symbol, "bass_note": bass}))
    return out


def merge_short_chords(
    events: list[ChordEvent],
    min_duration: float = MIN_CHORD_DURATION_S,
) -> list[ChordEvent]:
    """Absorb chords shorter than ``min_duration`` into a neighbour.

    Preference order: merge into the longer adjacent chord (by duration);
    ties go to the previous chord. Preserves chronological coverage of
    [first.start, last.end]. Empty input returns empty.
    """
    if len(events) <= 1:
        return list(events)

    # Work on a mutable copy of (symbol, bass, conf, source, start, end).
    work: list[ChordEvent] = list(events)
    changed = True
    while changed and len(work) > 1:
        changed = False
        for i, e in enumerate(work):
            dur = e.timestamp.end - e.timestamp.start
            if dur >= min_duration:
                continue
            # Choose neighbour to absorb into.
            prev = work[i - 1] if i > 0 else None
            nxt = work[i + 1] if i + 1 < len(work) else None
            if prev is None and nxt is None:
                continue
            if prev is None:
                target_i = i + 1
            elif nxt is None:
                target_i = i - 1
            else:
                prev_dur = prev.timestamp.end - prev.timestamp.start
                next_dur = nxt.timestamp.end - nxt.timestamp.start
                target_i = i - 1 if prev_dur >= next_dur else i + 1
            target = work[target_i]
            if target_i < i:
                # Absorb short into previous: extend previous end.
                new_ts = TimeStamp(start=target.timestamp.start, end=e.timestamp.end)
                work[target_i] = target.model_copy(update={"timestamp": new_ts})
            else:
                # Absorb short into next: pull next start earlier.
                new_ts = TimeStamp(start=e.timestamp.start, end=target.timestamp.end)
                work[target_i] = target.model_copy(update={"timestamp": new_ts})
            del work[i]
            changed = True
            break
    return work


def collapse_adjacent_same_root(events: list[ChordEvent]) -> list[ChordEvent]:
    """Merge consecutive events that share the same majmin root+quality.

    Chordino often re-emits "Am" → "Am7" → "Am" as three segments; for
    majmin scoring and placement these are one harmonic region. Keeps the
    first event's symbol (richer extensions usually come later — we prefer
    the longer-duration spelling when durations differ).
    """
    if not events:
        return []
    out: list[ChordEvent] = []
    for e in events:
        if not out:
            out.append(e)
            continue
        prev = out[-1]
        same = _chord_root(prev.symbol) == _chord_root(e.symbol) and _majmin_quality(
            prev.symbol
        ) == _majmin_quality(e.symbol)
        if not same:
            out.append(e)
            continue
        # Merge: pick symbol from the longer segment; extend span.
        prev_dur = prev.timestamp.end - prev.timestamp.start
        cur_dur = e.timestamp.end - e.timestamp.start
        keep_symbol = e.symbol if cur_dur > prev_dur else prev.symbol
        keep_bass = e.bass_note if cur_dur > prev_dur else prev.bass_note
        # Slash in symbol ⇒ clear separate bass_note to satisfy validator.
        if "/" in keep_symbol:
            keep_bass = None
        elif keep_bass is not None and keep_bass == _chord_root(keep_symbol):
            keep_bass = None
        new_ts = TimeStamp(start=prev.timestamp.start, end=e.timestamp.end)
        out[-1] = prev.model_copy(
            update={"symbol": keep_symbol, "bass_note": keep_bass, "timestamp": new_ts}
        )
    return out


def _triad_pitch_classes(root: str, quality: str) -> tuple[int, int, int]:
    """Return pitch-class indices for a major/minor triad (sharp spellings)."""
    root = _FLAT_TO_SHARP.get(root, root)
    if root not in _PC:
        return (0, 4, 7)
    ri = _PC.index(root)
    third = 3 if quality == "min" else 4
    return (ri, (ri + third) % 12, (ri + 7) % 12)


def _symbol_for_root_quality(root: str, quality: str) -> str:
    """Plain majmin spelling (no extensions) for inserted change-points."""
    return root if quality == "maj" else f"{root}m"


def _relative_triad(root: str, quality: str) -> tuple[str, str] | None:
    """Relative major/minor pair (shares two pitch classes — chroma-ambiguous)."""
    root = _FLAT_TO_SHARP.get(root, root)
    if root not in _PC:
        return None
    i = _PC.index(root)
    if quality == "maj":
        return _PC[(i + 9) % 12], "min"  # vi of I
    if quality == "min":
        return _PC[(i + 3) % 12], "maj"  # I of vi
    return None


def _mediant_triad(root: str, quality: str) -> tuple[str, str] | None:
    """iii of a major triad (or I of a minor iii) — shares two pitch classes.

    C maj = C E G; Em = E G B → share E,G. Under pad-heavy "other" stems the
    mediant often outscores weak V; treat like relative for exclusion unless
    strong secondary evidence clears the elevated margin.
    """
    root = _FLAT_TO_SHARP.get(root, root)
    if root not in _PC:
        return None
    i = _PC.index(root)
    if quality == "maj":
        return _PC[(i + 4) % 12], "min"  # iii of I
    if quality == "min":
        return _PC[(i + 8) % 12], "maj"  # I when current is iii
    return None


def _scale_degree(root: str, key_root: str) -> int | None:
    """Semitone offset of ``root`` above ``key_root`` in 0..11, or None."""
    root = _FLAT_TO_SHARP.get(root, root)
    key_root = _FLAT_TO_SHARP.get(key_root, key_root)
    if root not in _PC or key_root not in _PC:
        return None
    return (_PC.index(root) - _PC.index(key_root)) % 12


def _function_class(
    root: str,
    quality: str,
    key_root: str,
    mode: str,
) -> Literal["dominant", "primary", "secondary"]:
    """Classify a diatonic triad for reseg insert margins.

    major: I/IV/V/vi primary (V specially dominant); bVII treated as primary
    worship colour; ii/iii/dim secondary.
    minor: i/iv/V(or v)/VI primary; others secondary.
    """
    deg = _scale_degree(root, key_root)
    if deg is None:
        return "secondary"
    if mode == "minor":
        # i, III/VI colours, iv, v/V
        if deg == 7 and quality in ("maj", "min"):
            return "dominant"
        if deg in (0, 3, 5, 8):
            return "primary"
        return "secondary"
    # major key
    if deg == 7 and quality == "maj":
        return "dominant"
    if (deg, quality) in {(0, "maj"), (5, "maj"), (9, "min"), (10, "maj")}:
        # I, IV, vi, bVII (worship flat-7 colour)
        return "primary"
    return "secondary"


def _margin_for_candidate(
    root: str,
    quality: str,
    key_root: str,
    mode: str,
    base_margin: float,
) -> float:
    """Required score edge for an alternate, by harmonic function."""
    cls = _function_class(root, quality, key_root, mode)
    if cls == "dominant":
        return min(base_margin, CHROMA_SCORE_MARGIN_DOMINANT)
    if cls == "secondary":
        return max(base_margin, CHROMA_SCORE_MARGIN_SECONDARY)
    return base_margin


def _score_with_priors(
    raw_score: float,
    root: str,
    quality: str,
    key_root: str,
    mode: str,
) -> float:
    """Apply function-aware score priors (dominant boost under pads)."""
    if _function_class(root, quality, key_root, mode) == "dominant":
        return raw_score + CHROMA_DOMINANT_SCORE_PRIOR
    return raw_score


def _reseg_candidate_pool(
    key_root: str,
    mode: str,
    *,
    primary_only: bool = RESEG_PRIMARY_ONLY,
    allow_secondary: bool = RESEG_ALLOW_SECONDARY,
) -> list[tuple[str, str]]:
    """Diatonic candidates allowed as *inserted* change-points.

    By default only primary functions + dominant (and bVII in major) so
    pad overtones cannot promote iii/ii into the chart. Secondary triads
    remain in the full diatonic set used by key-snap, not reseg inserts.
    """
    pool = _candidates_for_key(key_root, mode)
    if not primary_only:
        return pool
    out: list[tuple[str, str]] = []
    for r, q in pool:
        cls = _function_class(r, q, key_root, mode)
        if cls in ("dominant", "primary"):
            out.append((r, q))
        elif allow_secondary and cls == "secondary":
            out.append((r, q))
    return out


def _shared_pitch_class_count(r1: str, q1: str, r2: str, q2: str) -> int:
    """How many triad pitch classes two chords share (0–3)."""
    a = set(_triad_pitch_classes(r1, q1))
    b = set(_triad_pitch_classes(r2, q2))
    return len(a & b)


def _triad_score(chroma_vec: Any, root: str, quality: str) -> float:
    """Contrastive triad score with root emphasis.

    L1-normalizes the 12-d column, then returns
    ``mean(on) − mean(off) + ROOT_WEIGHT * root_bin``. Root emphasis helps
    surface V under tonic pads (shared G between C and G triads) without
    relying on song-specific progressions.
    """
    import numpy as np

    v = np.asarray(chroma_vec, dtype=float).reshape(-1)
    if v.size != 12:
        return 0.0
    s = float(v.sum())
    if s <= 0.0:
        return 0.0
    v = v / s
    root = _FLAT_TO_SHARP.get(root, root)
    on_pcs = set(_triad_pitch_classes(root, quality))
    on_vals = [float(v[p]) for p in on_pcs]
    off_vals = [float(v[i]) for i in range(12) if i not in on_pcs]
    on_mean = sum(on_vals) / max(1, len(on_vals))
    off_mean = sum(off_vals) / max(1, len(off_vals))
    root_bin = float(v[_PC.index(root)]) if root in _PC else 0.0
    return on_mean - off_mean + 0.35 * root_bin


def estimate_beat_period(events: list[ChordEvent]) -> float:
    """Heuristic beat period from chord-onset gaps (no BeatThis required).

    Chord changes in worship material often land on bar or half-bar
    boundaries. We take the median positive onset gap and map it to a beat:
    long gaps (≈1 bar) → /4, medium (≈2 beats) → /2, short → as-is.
    Falls back to ``DEFAULT_BEAT_PERIOD_S`` when evidence is thin.
    """
    if len(events) < 2:
        return DEFAULT_BEAT_PERIOD_S
    gaps: list[float] = []
    for a, b in zip(events, events[1:], strict=False):
        g = b.timestamp.start - a.timestamp.start
        if 0.4 < g < 10.0:
            gaps.append(g)
    if not gaps:
        return DEFAULT_BEAT_PERIOD_S
    gaps_sorted = sorted(gaps)
    med = gaps_sorted[len(gaps_sorted) // 2]
    if med >= 2.5:
        return med / 4.0
    if med >= 1.2:
        return med / 2.0
    return med


def _window_mean_chroma(
    chroma: Any,
    frame_times: Any,
    start: float,
    end: float,
) -> Any | None:
    """Average chroma columns whose frame times fall in [start, end)."""
    import numpy as np

    c = np.asarray(chroma, dtype=float)
    t = np.asarray(frame_times, dtype=float)
    if c.ndim != 2 or c.shape[0] != 12 or t.ndim != 1 or c.shape[1] != t.shape[0]:
        return None
    if end <= start:
        return None
    mask = (t >= start) & (t < end)
    if not np.any(mask):
        # Fall back to nearest frame if window fell between hops.
        if t.size == 0:
            return None
        mid = 0.5 * (start + end)
        idx = int(np.argmin(np.abs(t - mid)))
        return c[:, idx].copy()
    return c[:, mask].mean(axis=1)


def _candidates_for_key(key_root: str, mode: str) -> list[tuple[str, str]]:
    """Ordered diatonic (root, quality) candidates for template matching."""
    dia = _diatonic_set(key_root, mode)
    # Prefer tonic / dominant / submediant / subdominant order for stability
    # when scores tie — pure sort by root index is fine and generic.
    return sorted(dia, key=lambda rq: _PC.index(rq[0]) if rq[0] in _PC else 99)


def resegment_long_holds(
    events: list[ChordEvent],
    *,
    chroma: Any,
    frame_times: Any,
    beat_period: float,
    key_root: str = "C",
    mode: str = "major",
    min_hold_s: float | None = None,
    min_alt_s: float | None = None,
    score_margin: float = CHROMA_SCORE_MARGIN,
    max_passes: int = RESEG_MAX_PASSES,
) -> list[ChordEvent]:
    """Split multi-beat chord holds when chroma favors another diatonic triad.

    Chordino often sustains I across bars where V is audible under pads
    (I–V–vi–IV loops). For each event longer than ``min_hold_s`` (default
    ``MIN_HOLD_BEATS * beat_period``), scan beat-aligned windows and label
    each with the best-scoring diatonic triad. An alternate label is only
    committed when it wins by a *function-aware* margin over the current
    event's majmin label for a contiguous span ≥ ``min_alt_s`` (default 1
    beat): dominant (V) is easier, secondary (ii/iii) harder.

    Each pass inserts at most one alternate per long hold (suffix-commit).
    Multiple passes (``max_passes``, default ``RESEG_MAX_PASSES``) re-scan
    newly created long pieces so multi-change pads (C→G→F under one Chordino
    event) peel progressively without recursive window flutter inside a single
    split. Stops early when a pass produces no new events.

    Pure w.r.t. audio: callers supply a precomputed chromagram. Empty
    input and short events pass through unchanged. Coverage of
    [first.start, last.end] is preserved. Both split pieces clear
    ``bass_note`` — callers must recompute bass on final intervals.
    """
    if not events:
        return []
    if beat_period <= 0:
        beat_period = DEFAULT_BEAT_PERIOD_S
    hold_floor = min_hold_s if min_hold_s is not None else MIN_HOLD_BEATS * beat_period
    alt_floor = min_alt_s if min_alt_s is not None else MIN_ALT_BEATS * beat_period
    candidates = _reseg_candidate_pool(key_root, mode)
    if not candidates:
        return list(events)

    passes = max(1, int(max_passes))
    current = list(events)
    for _ in range(passes):
        out: list[ChordEvent] = []
        changed = False
        for ev in current:
            dur = ev.timestamp.end - ev.timestamp.start
            if dur < hold_floor:
                out.append(ev)
                continue
            if dur >= LONG_HOLD_FORCE_RELABEL_S - 1e-9:
                pieces = _relabel_long_hold(
                    ev,
                    chroma=chroma,
                    frame_times=frame_times,
                    beat_period=beat_period,
                    candidates=candidates,
                    alt_floor=alt_floor,
                    score_margin=score_margin,
                    key_root=key_root,
                    mode=mode,
                )
            else:
                pieces = _split_one_hold(
                    ev,
                    chroma=chroma,
                    frame_times=frame_times,
                    beat_period=beat_period,
                    candidates=candidates,
                    alt_floor=alt_floor,
                    score_margin=score_margin,
                    key_root=key_root,
                    mode=mode,
                )
            if len(pieces) > 1:
                changed = True
            out.extend(pieces)
        current = out
        if not changed:
            break
    return current


def _relabel_long_hold(
    ev: ChordEvent,
    *,
    chroma: Any,
    frame_times: Any,
    beat_period: float,
    candidates: list[tuple[str, str]],
    alt_floor: float,
    score_margin: float,
    key_root: str = "C",
    mode: str = "major",
) -> list[ChordEvent]:
    """Full beat-window relabel for very long holds (H1b).

    Unlike ``_split_one_hold`` (keeps Chordino onset, one mid-hold alternate),
    this path rewrites the entire span from window-best primary labels and
    merges runs shorter than ``alt_floor`` into neighbours. Used only when the
    hold is ≥ ``LONG_HOLD_FORCE_RELABEL_S`` so ordinary multi-beat pads still
    use the conservative single-split path.
    """
    t0 = ev.timestamp.start
    t1 = ev.timestamp.end
    cur_root = _chord_root(ev.symbol)
    cur_qual = _majmin_quality(ev.symbol)
    # Pool includes current label so stable pads stay put.
    pool: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for r, q in [(cur_root, cur_qual), *candidates]:
        if not r or (r, q) in seen:
            continue
        seen.add((r, q))
        pool.append((r, q))

    windows: list[tuple[float, float, str, str]] = []
    t = t0
    while t < t1 - 1e-9:
        w_end = min(t + beat_period, t1)
        vec = _window_mean_chroma(chroma, frame_times, t, w_end)
        label_r, label_q = cur_root, cur_qual
        if vec is not None:
            import numpy as np

            v = np.asarray(vec, dtype=float).reshape(-1)
            vs = float(v.sum())
            if vs > 0:
                v = v / vs
            cur_s = _triad_score(vec, cur_root, cur_qual)
            best_s = cur_s
            # Score-first ranking (class rank is only a tie-break). Preferring
            # dominant-over-primary by rank alone would rewrite C pads as G.
            best_cls_rank = 1
            cur_pc = _PC.index(cur_root) if cur_root in _PC else None
            cur_root_e = float(v[cur_pc]) if cur_pc is not None else 0.0
            for r, q in pool:
                if r not in _PC:
                    continue
                raw_s = _triad_score(vec, r, q)
                s = _score_with_priors(raw_s, r, q, key_root, mode)
                if r == cur_root and q == cur_qual:
                    # Current label: no margin; win ties to avoid flutter.
                    if s >= best_s - 1e-12:
                        best_s = max(best_s, s)
                        label_r, label_q = r, q
                        best_cls_rank = 1
                    continue
                alt_root_e = float(v[_PC.index(r)])
                margin = _margin_for_candidate(r, q, key_root, mode, score_margin)
                # Long holds: slightly easier primary/dominant inserts.
                cls = _function_class(r, q, key_root, mode)
                if cls in ("dominant", "primary"):
                    margin = min(margin, score_margin * 0.5)
                cls_rank = 0 if cls == "dominant" else (1 if cls == "primary" else 2)
                if cls == "secondary":
                    root_ok = alt_root_e >= cur_root_e + 0.02
                else:
                    root_ok = alt_root_e >= cur_root_e - (0.03 if cls == "dominant" else 0.0)
                if not root_ok or s <= cur_s + margin:
                    continue
                if s > best_s + 1e-12 or (abs(s - best_s) <= 1e-9 and cls_rank < best_cls_rank):
                    best_s = s
                    best_cls_rank = cls_rank
                    label_r, label_q = r, q
        windows.append((t, w_end, label_r, label_q))
        t = w_end

    if not windows:
        return [ev]

    # Compress consecutive same labels into runs.
    runs: list[tuple[float, float, str, str]] = []
    for wt0, wt1, wr, wq in windows:
        if runs and runs[-1][2] == wr and runs[-1][3] == wq:
            prev = runs[-1]
            runs[-1] = (prev[0], wt1, wr, wq)
        else:
            runs.append((wt0, wt1, wr, wq))

    # Absorb short runs (< alt_floor) into the longer neighbour.
    if len(runs) > 1:
        merged: list[tuple[float, float, str, str]] = []
        for run in runs:
            dur = run[1] - run[0]
            if merged and dur < alt_floor - 1e-9:
                prev = merged[-1]
                merged[-1] = (prev[0], run[1], prev[2], prev[3])
            else:
                merged.append(run)
        # Trailing short run: fold into previous if any.
        if len(merged) >= 2:
            last = merged[-1]
            if last[1] - last[0] < alt_floor - 1e-9:
                prev = merged[-2]
                merged[-2] = (prev[0], last[1], prev[2], prev[3])
                merged.pop()
        runs = merged

    if len(runs) <= 1:
        # Possibly only a full rewrite of the symbol with same span.
        if not runs:
            return [ev]
        wr, wq = runs[0][2], runs[0][3]
        if wr != cur_root or wq != cur_qual:
            return [
                ev.model_copy(
                    update={
                        "symbol": _symbol_for_root_quality(wr, wq),
                        "bass_note": None,
                    }
                )
            ]
        return [ev]

    pieces: list[ChordEvent] = []
    for rt0, rt1, wr, wq in runs:
        pieces.append(
            ev.model_copy(
                update={
                    "symbol": _symbol_for_root_quality(wr, wq),
                    "bass_note": None,
                    "timestamp": TimeStamp(start=rt0, end=rt1),
                }
            )
        )
    return pieces


def _split_one_hold(
    ev: ChordEvent,
    *,
    chroma: Any,
    frame_times: Any,
    beat_period: float,
    candidates: list[tuple[str, str]],
    alt_floor: float,
    score_margin: float,
    key_root: str = "C",
    mode: str = "major",
) -> list[ChordEvent]:
    """Insert the first sustained non-confusable alternate, then commit the suffix.

    Chordino under-segmentation usually keeps a correct onset and swallows the
    next chord under a multi-beat pad. Relative major/minor pairs (I↔vi) share
    two pitch classes and are excluded from the alternate set. The mediant
    (I↔iii) is also excluded from easy inserts — E-rich pads make Em score
    explode under C while true V often fails a flat margin. Secondary
    functions (ii/iii/dim) require ``CHROMA_SCORE_MARGIN_SECONDARY``; the
    dominant of the estimated key uses ``CHROMA_SCORE_MARGIN_DOMINANT``.

    When a non-confusable diatonic triad beats the current label for ≥
    ``alt_floor`` contiguous beat windows, we split once at that run's start
    and keep the alternate through the end of the hold (suffix commit avoids
    C–G–C flutter). Both pieces clear ``bass_note`` so sticky pre-reseg slash
    bass cannot label the wrong half.
    """
    t0 = ev.timestamp.start
    t1 = ev.timestamp.end
    cur_root = _chord_root(ev.symbol)
    cur_qual = _majmin_quality(ev.symbol)
    rel = _relative_triad(cur_root, cur_qual)
    med = _mediant_triad(cur_root, cur_qual)
    # Hard-exclude relative (I↔vi). Mediant (I↔iii) stays in the candidate
    # set but only with the elevated secondary margin + extra root-bin gate.
    cand = [
        (r, q)
        for r, q in candidates
        if not (r == cur_root and q == cur_qual) and (rel is None or (r, q) != rel)
    ]
    if not cand:
        return [ev]

    # Prefer primary functions when scanning (V/I/IV/vi before ii/iii).
    def _cand_rank(rq: tuple[str, str]) -> tuple[int, int]:
        r, q = rq
        cls = _function_class(r, q, key_root, mode)
        pri = 0 if cls == "dominant" else (1 if cls == "primary" else 2)
        return (pri, _PC.index(r) if r in _PC else 99)

    cand = sorted(cand, key=_cand_rank)

    windows: list[tuple[float, float, str, str]] = []
    cur_pc = _PC.index(cur_root) if cur_root in _PC else None
    t = t0
    while t < t1 - 1e-9:
        w_end = min(t + beat_period, t1)
        vec = _window_mean_chroma(chroma, frame_times, t, w_end)
        label_r, label_q = cur_root, cur_qual
        if vec is not None:
            import numpy as np

            v = np.asarray(vec, dtype=float).reshape(-1)
            vs = float(v.sum())
            if vs > 0:
                v = v / vs
            cur_s = _triad_score(vec, cur_root, cur_qual)
            cur_root_e = float(v[cur_pc]) if cur_pc is not None else 0.0
            best_s = cur_s
            best_cls_rank = 99
            for r, q in cand:
                if r not in _PC:
                    continue
                raw_s = _triad_score(vec, r, q)
                s = _score_with_priors(raw_s, r, q, key_root, mode)
                alt_root_e = float(v[_PC.index(r)])
                margin = _margin_for_candidate(r, q, key_root, mode, score_margin)
                cls = _function_class(r, q, key_root, mode)
                cls_rank = 0 if cls == "dominant" else (1 if cls == "primary" else 2)

                # Root-bin gate: primary/dominant may be slightly below current
                # root (shared tones under pads); secondary must clearly lead.
                if cls == "secondary":
                    root_ok = alt_root_e >= cur_root_e + 0.02
                    # Mediant under major I: require even stronger root lead.
                    if med is not None and (r, q) == med:
                        root_ok = alt_root_e >= cur_root_e + 0.05
                else:
                    # V under I: G bin often ≈ C bin; allow small deficit.
                    root_ok = alt_root_e >= cur_root_e - (0.03 if cls == "dominant" else 0.0)

                # Compare prior-adjusted alt score against raw current score.
                if not root_ok or s <= cur_s + margin:
                    continue

                # Prefer dominant/primary over secondary when both clear gates.
                # Also prefer higher score within the same class rank.
                if cls_rank < best_cls_rank or (cls_rank == best_cls_rank and s > best_s + 1e-12):
                    best_s = s
                    best_cls_rank = cls_rank
                    label_r, label_q = r, q
                elif (
                    cls_rank == best_cls_rank
                    and abs(s - best_s) <= 1e-9
                    and _shared_pitch_class_count(r, q, cur_root, cur_qual)
                    < _shared_pitch_class_count(label_r, label_q, cur_root, cur_qual)
                ):
                    # Tie-break: fewer shared PCs with current (V over iii under I).
                    label_r, label_q = r, q
        windows.append((t, w_end, label_r, label_q))
        t = w_end

    if not windows:
        return [ev]

    # First contiguous alternate run (same root+qual) of duration ≥ alt_floor.
    # Single split only (no recursive re-label of the suffix): under-seg almost
    # always hides one missing chord, and recursion re-introduces C–G–C flutter.
    i = 0
    n = len(windows)
    split_at: float | None = None
    alt_r = cur_root
    alt_q = cur_qual
    while i < n:
        wr, wq = windows[i][2], windows[i][3]
        if wr == cur_root and wq == cur_qual:
            i += 1
            continue
        j = i
        while j < n and windows[j][2] == wr and windows[j][3] == wq:
            j += 1
        run_start = windows[i][0]
        run_end = windows[j - 1][1]
        if run_end - run_start >= alt_floor - 1e-9:
            # Need a non-empty original prefix so we do not rewrite the onset.
            if run_start > t0 + 1e-9:
                split_at = float(run_start)
                alt_r, alt_q = wr, wq
                break
        i = j

    if split_at is None:
        return [ev]

    # Clear bass on BOTH pieces — pre-reseg bass_note is for the full span
    # and must not stick to the prefix as a false slash (e.g. C/G).
    left = ev.model_copy(
        update={
            "timestamp": TimeStamp(start=t0, end=split_at),
            "bass_note": None,
        }
    )
    # Suffix commit: keep the alternate through the end of the hold so a
    # mid-hold V that only weakly outscores I on later beats still surfaces.
    right = ev.model_copy(
        update={
            "symbol": _symbol_for_root_quality(alt_r, alt_q),
            "bass_note": None,
            "timestamp": TimeStamp(start=split_at, end=t1),
        }
    )
    return [left, right]


def load_harmonic_chroma(harmonic_mix: Path) -> tuple[Any, Any]:
    """Load a CQT chromagram and frame times from a harmonic-mix WAV.

    Returns ``(chroma[12, n], frame_times[n])``. Used by long-hold
    resegmentation; hop is finer than bass_chroma for change-point recall.
    """
    import librosa
    import numpy as np

    y, sr = librosa.load(str(harmonic_mix), sr=22050, mono=True)
    if y.size == 0:
        return np.zeros((12, 0)), np.zeros((0,))
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=CHROMA_HOP_LENGTH, n_chroma=12)
    times = librosa.frames_to_time(np.arange(chroma.shape[1]), sr=sr, hop_length=CHROMA_HOP_LENGTH)
    return chroma, times


def postprocess_chords(events: list[ChordEvent]) -> list[ChordEvent]:
    """Quality-loop post-processing for Chordino output (Phase C T70).

    Pipeline:
      1. Merge sub-``MIN_CHORD_DURATION_S`` flutter chords into neighbours.
      2. Collapse adjacent same majmin root+quality.
      3. Estimate key from the cleaned histogram.
      4. Snap out-of-key chords onto the diatonic set.
      5. Collapse again (snap may create new adjacent twins).
    """
    if not events:
        return []
    cleaned = merge_short_chords(events)
    cleaned = collapse_adjacent_same_root(cleaned)
    key_root, mode = estimate_key(cleaned)
    snapped = snap_events_to_key(cleaned, key_root, mode)
    return collapse_adjacent_same_root(snapped)


def _probe_duration(path: Path) -> float:
    import soundfile as sf

    return float(sf.info(str(path)).duration)


class ChordinoEngine:
    """Conforms to ChordRecognitionEngine Protocol."""

    def __init__(self) -> None:
        self._extractor = _load_extractor()

    @property
    def info(self) -> EngineInfo:
        return EngineInfo(
            name="chordino",
            version="1.0",
            backend="cpu",
            model_id="chordino",
        )

    @property
    def vocabulary(self) -> Literal["majmin", "sevenths", "tetrads", "extended_170"]:
        return "majmin"

    @property
    def supports_inversions(self) -> bool:
        # Phase C T64 / Codex F-004: bass-stem chroma analysis now active
        # when a bass_stem is provided to detect(). Slash chords F/A, G/B,
        # C/E in the PT-BR corpus emit as inversions when bass-stem chroma
        # confidence ≥ 0.5 and the detected note differs from the chord
        # root. See engines/chord/bass_chroma.py for the chroma extractor.
        return True

    def detect(
        self,
        harmonic_mix: Path,
        bass_stem: Path | None = None,
    ) -> list[ChordEvent]:
        try:
            raw_chords = self._extractor.extract(str(harmonic_mix))
        except Exception as exc:  # noqa: BLE001
            raise ChordRecognitionError(
                f"chordino extraction failed on {harmonic_mix.name}",
                engine="chordino",
                cause=exc,
            ) from exc

        all_events: list[tuple[str | None, float]] = []
        for c in raw_chords:
            symbol = _normalize_chord_symbol(str(c.chord))
            all_events.append((symbol, float(c.timestamp)))

        if not any(sym is not None for sym, _ in all_events):
            return []

        try:
            duration = _probe_duration(harmonic_mix)
        except Exception:  # noqa: BLE001
            duration = all_events[-1][1] + 1.0

        # Build raw intervals WITHOUT bass first. Reseg splits rewrite spans;
        # attaching bass pre-reseg leaves sticky slash on the wrong half
        # (e.g. long C with later G energy → C/G on the C prefix).
        events: list[ChordEvent] = []
        for i, (symbol, start) in enumerate(all_events):
            if symbol is None:
                continue
            end = all_events[i + 1][1] if i + 1 < len(all_events) else duration
            if end < start:
                end = start

            events.append(
                ChordEvent(
                    symbol=symbol,
                    timestamp=TimeStamp(start=start, end=end),
                    bass_note=None,
                    confidence=1.0,
                    source_engine="chordino",
                )
            )

        raw = [e for e in events if e.timestamp.end > e.timestamp.start]
        # RC3: re-check multi-beat holds against beat-window chroma so looping
        # I–V–vi–IV progressions emit mid-hold V (etc.) instead of long I pads.
        # Failures are non-fatal — fall back to raw Chordino intervals.
        if raw:
            try:
                pre = collapse_adjacent_same_root(merge_short_chords(raw))
                key_root, mode = estimate_key(pre)
                beat_period = estimate_beat_period(pre)
                chroma, frame_times = load_harmonic_chroma(harmonic_mix)
                if getattr(chroma, "shape", (12, 0))[1] > 0:
                    raw = resegment_long_holds(
                        raw,
                        chroma=chroma,
                        frame_times=frame_times,
                        beat_period=beat_period,
                        key_root=key_root,
                        mode=mode,
                    )
            except Exception as exc:  # noqa: BLE001
                _log.warning("chroma long-hold resegment skipped: %s", exc)
        # Phase C T70 quality loop: flutter merge + key snap + collapse.
        final = postprocess_chords(raw)
        # F-004 / P1: attach bass on *final* intervals only.
        if bass_stem is not None and final:
            final = _attach_bass_notes(final, bass_stem)
        return final


def _attach_bass_notes(events: list[ChordEvent], bass_stem: Path) -> list[ChordEvent]:
    """Recompute ``bass_note`` per event on its final [start, end) interval.

    Skips events whose symbol already encodes a slash (native Chordino slash
    spelling). Applies triad-tone gate so non-chord-tone pedals do not emit
    random slashes. Root-position bass is suppressed (no F/F).
    """
    out: list[ChordEvent] = []
    for e in events:
        if "/" in e.symbol:
            out.append(e.model_copy(update={"bass_note": None}))
            continue
        start = e.timestamp.start
        end = e.timestamp.end
        letter: str | None = None
        conf = 0.0
        try:
            letter, conf = extract_bass_note(bass_stem, start=start, end=end)
        except FileNotFoundError:
            _log.warning("bass_stem path %s vanished mid-detection; skipping", bass_stem)
        except Exception as exc:  # noqa: BLE001
            _log.warning("bass_chroma failed on interval %.3f-%.3f: %s", start, end, exc)
        if letter is None or conf < BASS_NOTE_MIN_CONFIDENCE:
            out.append(e.model_copy(update={"bass_note": None}))
            continue
        letter = filter_bass_to_chord_tones(letter, e.symbol)
        if letter is None or letter == _chord_root(e.symbol):
            out.append(e.model_copy(update={"bass_note": None}))
            continue
        out.append(e.model_copy(update={"bass_note": letter}))
    return out

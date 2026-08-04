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
from titan_chordpro.engines.chord.bass_chroma import extract_bass_note

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
CHROMA_SCORE_MARGIN = 0.01  # required edge over current-label score
CHROMA_HOP_LENGTH = 512  # finer hop than bass_chroma (change-point recall)


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
) -> list[ChordEvent]:
    """Split multi-beat chord holds when chroma favors another diatonic triad.

    Chordino often sustains I across bars where V is audible under pads
    (I–V–vi–IV loops). For each event longer than ``min_hold_s`` (default
    ``MIN_HOLD_BEATS * beat_period``), scan beat-aligned windows and label
    each with the best-scoring diatonic triad. An alternate label is only
    committed when it wins by ``score_margin`` over the current event's
    majmin label for a contiguous span ≥ ``min_alt_s`` (default 1 beat).

    Pure w.r.t. audio: callers supply a precomputed chromagram. Empty
    input and short events pass through unchanged. Coverage of
    [first.start, last.end] is preserved.
    """
    if not events:
        return []
    if beat_period <= 0:
        beat_period = DEFAULT_BEAT_PERIOD_S
    hold_floor = min_hold_s if min_hold_s is not None else MIN_HOLD_BEATS * beat_period
    alt_floor = min_alt_s if min_alt_s is not None else MIN_ALT_BEATS * beat_period
    candidates = _candidates_for_key(key_root, mode)
    if not candidates:
        return list(events)

    out: list[ChordEvent] = []
    for ev in events:
        dur = ev.timestamp.end - ev.timestamp.start
        if dur < hold_floor:
            out.append(ev)
            continue
        pieces = _split_one_hold(
            ev,
            chroma=chroma,
            frame_times=frame_times,
            beat_period=beat_period,
            candidates=candidates,
            alt_floor=alt_floor,
            score_margin=score_margin,
        )
        out.extend(pieces)
    return out


def _split_one_hold(
    ev: ChordEvent,
    *,
    chroma: Any,
    frame_times: Any,
    beat_period: float,
    candidates: list[tuple[str, str]],
    alt_floor: float,
    score_margin: float,
) -> list[ChordEvent]:
    """Insert the first sustained non-relative alternate, then commit the suffix.

    Chordino under-segmentation usually keeps a correct onset and swallows the
    next chord under a multi-beat pad. Relative major/minor pairs (I↔vi) share
    two pitch classes and are excluded from the alternate set — rewriting a
    correct vi as I (or vice versa) from chroma alone is unreliable. When a
    non-relative diatonic triad beats the current label for ≥ ``alt_floor``
    contiguous beat windows, we split once at that run's start and keep the
    alternate through the end of the hold (suffix commit avoids C–G–C flutter
    when V is only intermittently stronger than I under pads). Recurses on the
    suffix for multi-step pads.
    """
    t0 = ev.timestamp.start
    t1 = ev.timestamp.end
    cur_root = _chord_root(ev.symbol)
    cur_qual = _majmin_quality(ev.symbol)
    rel = _relative_triad(cur_root, cur_qual)
    cand = [
        (r, q)
        for r, q in candidates
        if not (r == cur_root and q == cur_qual) and (rel is None or (r, q) != rel)
    ]
    if not cand:
        return [ev]

    # Beat-window labels: stick with original until a non-relative alternate
    # wins by ``score_margin`` *and* its root bin meets/exceeds the current
    # root bin (blocks weak iii/etc. substitutions under tonic pads).
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
            for r, q in cand:
                if r not in _PC:
                    continue
                s = _triad_score(vec, r, q)
                alt_root_e = float(v[_PC.index(r)])
                if s > best_s + score_margin and alt_root_e >= cur_root_e - 1e-9:
                    best_s = s
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

    left = ev.model_copy(update={"timestamp": TimeStamp(start=t0, end=split_at)})
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

        events: list[ChordEvent] = []
        for i, (symbol, start) in enumerate(all_events):
            if symbol is None:
                continue
            end = all_events[i + 1][1] if i + 1 < len(all_events) else duration
            if end < start:
                end = start

            # F-004: derive bass_note from the bass stem if one was provided.
            # Phase C T70-iter2 follow-up: when chordino itself emits a slash
            # chord (e.g. 'C#/E#'), the bass is already encoded in symbol —
            # do NOT also set bass_note. Otherwise ChordEvent.validate_bass_consistency
            # rejects the event when bass_chroma picks the enharmonic spelling
            # (E# vs F) chordino didn't use.
            bass_note: str | None = None
            if bass_stem is not None and "/" not in symbol:
                try:
                    letter, _ = extract_bass_note(bass_stem, start=start, end=end)
                except FileNotFoundError:
                    _log.warning("bass_stem path %s vanished mid-detection; skipping", bass_stem)
                    letter = None
                except Exception as exc:  # noqa: BLE001
                    _log.warning("bass_chroma failed on interval %.3f-%.3f: %s", start, end, exc)
                    letter = None
                if letter is not None and letter != _chord_root(symbol):
                    bass_note = letter

            events.append(
                ChordEvent(
                    symbol=symbol,
                    timestamp=TimeStamp(start=start, end=end),
                    bass_note=bass_note,
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
        return postprocess_chords(raw)

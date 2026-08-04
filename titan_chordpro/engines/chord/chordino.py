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
        # Phase C T70 quality loop: flutter merge + key snap + collapse.
        return postprocess_chords(raw)

# titan_chordpro/engines/chord/bass_chroma.py
"""F-004 — bass-note class extraction from a bass stem via librosa chroma.

The chordino wrapper provides chord intervals + a bass stem. For each
interval, this module:
  1. Loads the bass-stem slice via librosa (CQT-friendly mono signal).
  2. Computes a CQT-based chromagram (chroma_cqt — log-frequency,
     bass-aware vs STFT-based chroma_stft).
  3. Combines mean weights with per-frame argmax majority vote for
     stability on intervals that reseg may have shortened.
  4. Picks the dominant pitch-class → bass-note class.
  5. Applies duration-scaled confidence + vote-share floors (H2): short
     and mid post-reseg slices need higher agreement before emitting a
     letter; long pads keep the baseline 0.5 conf / 0.5 vote floors.
  6. Optional ``filter_bass_to_chord_tones`` keeps only triad tones {1,3,5}.

Thresholds are asymmetric on purpose: a wrong slash-chord (e.g.,
emitting `F/A` when the chord is just `F`) is visually disruptive to the
chart reader, while omitting an inversion just renders root-position —
which is the Phase B baseline anyway.

This module is the only place in Titan that calls librosa for bass. The
chordino wrapper imports `extract_bass_note` and calls it per final chord
interval (after resegmentation) so slash bass is not sticky across splits.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np

_PITCH_CLASS_LETTERS: tuple[str, ...] = (
    "C",
    "C#",
    "D",
    "D#",
    "E",
    "F",
    "F#",
    "G",
    "G#",
    "A",
    "A#",
    "B",
)
_FLAT_TO_SHARP: dict[str, str] = {
    "Db": "C#",
    "Eb": "D#",
    "Gb": "F#",
    "Ab": "G#",
    "Bb": "A#",
}
_CHORD_ROOT_RE = re.compile(r"^[A-G][#b]?")
_MIN_INTERVAL_SEC = 0.05  # 50ms — below this, chroma is unreliable
_BASS_CHROMA_THRESHOLD = 0.5  # long-interval confidence floor; below → None
# Duration bands for H2 slash stability (post-reseg false-inversion guard).
_SHORT_INTERVAL_SEC = 1.0
_MID_INTERVAL_SEC = 2.5
_SHORT_MIN_CONF = 0.70
_SHORT_MIN_VOTE_SHARE = 0.70
_MID_MIN_CONF = 0.70
_MID_MIN_VOTE_SHARE = 0.60
_LONG_MIN_VOTE_SHARE = 0.50


def pitch_class_letter(idx: int) -> str:
    """Map pitch-class index 0..11 → letter (sharp form)."""
    if not 0 <= idx <= 11:
        raise ValueError(f"pitch class index out of 0..11: {idx}")
    return _PITCH_CLASS_LETTERS[idx]


def bass_emission_thresholds(duration: float) -> tuple[float, float]:
    """Return ``(min_confidence, min_vote_share)`` for an interval duration.

    Short / mid slices (common after reseg) need higher peakiness and a
    more decisive majority vote before a bass letter is emitted. Long
    pads keep the baseline 0.5 conf floor so true held inversions survive.
    """
    if duration < _SHORT_INTERVAL_SEC:
        return _SHORT_MIN_CONF, _SHORT_MIN_VOTE_SHARE
    if duration < _MID_INTERVAL_SEC:
        return _MID_MIN_CONF, _MID_MIN_VOTE_SHARE
    return _BASS_CHROMA_THRESHOLD, _LONG_MIN_VOTE_SHARE


def resolve_bass_pc(
    weights: np.ndarray,
    frame_winners: np.ndarray,
    duration: float,
) -> tuple[int | None, float]:
    """Decide pitch-class index from mean chroma + per-frame winners.

    Emits only when:
      * confidence = (max - median) / max clears the duration-scaled floor
      * mean argmax agrees with majority-vote argmax
      * vote share clears the duration-scaled floor

    Returns ``(pc_idx_or_None, confidence)``. Confidence is always the
    raw peakiness score so callers can log near-misses.
    """
    import numpy as np

    weights = np.asarray(weights, dtype=float).reshape(-1)
    if weights.size != 12:
        raise ValueError(f"weights must have 12 pitch classes, got {weights.size}")
    max_w = float(weights.max())
    if max_w <= 0.0:
        return None, 0.0
    median_w = float(np.median(weights))
    confidence = max(0.0, (max_w - median_w) / max_w)
    min_conf, min_vote = bass_emission_thresholds(duration)
    if confidence < min_conf:
        return None, confidence

    mean_idx = int(weights.argmax())
    winners = np.asarray(frame_winners).reshape(-1)
    if winners.size == 0:
        # No frame votes — only accept on long intervals where mean alone
        # is historically trusted; still require conf floor (already passed).
        if duration >= _MID_INTERVAL_SEC:
            return mean_idx, confidence
        return None, confidence

    counts = np.bincount(winners.astype(int), minlength=12).astype(float)
    vote_idx = int(counts.argmax())
    vote_share = float(counts[vote_idx] / counts.sum()) if counts.sum() > 0 else 0.0

    # H2: require mean/vote agreement — disagreeing modes are unstable slashes.
    if vote_idx != mean_idx:
        return None, confidence
    if vote_share < min_vote:
        return None, confidence

    # Slight boost when vote is decisive and agrees (diagnostic only).
    if vote_share >= 0.45:
        confidence = max(confidence, min(0.99, confidence + 0.05))
    return mean_idx, confidence


def _triad_tone_letters(chord_symbol: str) -> set[str]:
    """Pitch-class letters for the triad tones of ``chord_symbol`` (root/3/5)."""
    base = chord_symbol.split("/", 1)[0]
    m = _CHORD_ROOT_RE.match(base)
    if not m:
        return set()
    root = _FLAT_TO_SHARP.get(m.group(0), m.group(0))
    if root not in _PITCH_CLASS_LETTERS:
        return set()
    ri = _PITCH_CLASS_LETTERS.index(root)
    remainder = base[len(m.group(0)) :]
    is_min = remainder.startswith("m") and not remainder.startswith("maj")
    third = 3 if is_min else 4
    pcs = {ri, (ri + third) % 12, (ri + 7) % 12}
    return {pitch_class_letter(p) for p in pcs}


def filter_bass_to_chord_tones(bass_letter: str | None, chord_symbol: str) -> str | None:
    """Keep bass only when it is a triad tone of ``chord_symbol``; else None.

    Root-position (bass == root) is still returned so callers can suppress
    slash emission with their usual root-match check. Non-chord-tone bass
    (pedals, wrong PC) is rejected for slash honesty.
    """
    if bass_letter is None:
        return None
    letter = _FLAT_TO_SHARP.get(bass_letter, bass_letter)
    tones = _triad_tone_letters(chord_symbol)
    if not tones:
        return letter
    return letter if letter in tones else None


def extract_bass_note(
    bass_stem: Path,
    start: float,
    end: float,
) -> tuple[str | None, float]:
    """Extract the dominant bass-note class from a bass-stem interval.

    Uses mean chroma weights with per-frame argmax majority vote, gated by
    duration-scaled confidence and vote-share floors so short/mid reseg
    slices do not emit unstable slash bass.

    Returns:
        (letter, confidence) — letter is None when thresholds fail or
        the interval is shorter than 50ms.

    Raises FileNotFoundError if bass_stem does not exist.
    """
    import librosa

    if not bass_stem.exists():
        raise FileNotFoundError(f"bass_stem not found: {bass_stem}")

    if end - start < _MIN_INTERVAL_SEC:
        return None, 0.0

    duration = end - start
    y, sr = librosa.load(
        str(bass_stem), sr=22050, mono=True, offset=max(0.0, start), duration=duration
    )
    if y.size == 0:
        return None, 0.0

    # CQT chroma is bass-friendly (log-frequency). hop_length=2048 keeps
    # the per-frame window large enough to resolve low pitches.
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=2048, n_chroma=12)
    if chroma.size == 0:
        return None, 0.0

    weights = chroma.mean(axis=1)
    frame_winners = chroma.argmax(axis=0)
    pc_idx, confidence = resolve_bass_pc(weights, frame_winners, duration)
    if pc_idx is None:
        return None, confidence
    return pitch_class_letter(pc_idx), confidence

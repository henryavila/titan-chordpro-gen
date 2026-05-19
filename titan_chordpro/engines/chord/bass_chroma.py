# titan_chordpro/engines/chord/bass_chroma.py
"""F-004 — bass-note class extraction from a bass stem via librosa chroma.

The chordino wrapper provides chord intervals + a bass stem. For each
interval, this module:
  1. Loads the bass-stem slice via librosa (CQT-friendly mono signal).
  2. Computes a CQT-based chromagram (chroma_cqt — log-frequency,
     bass-aware vs STFT-based chroma_stft).
  3. Averages across time → 12-d pitch-class weight vector.
  4. Picks argmax → bass-note class.
  5. Computes confidence = (max - median) / max. Returns None when below 0.5.

The 0.5 threshold is asymmetric on purpose: a wrong slash-chord (e.g.,
emitting `F/A` when the chord is just `F`) is visually disruptive to the
chart reader, while omitting an inversion just renders root-position —
which is the Phase B baseline anyway.

This module is the only place in Titan that calls librosa. The chordino
wrapper imports `extract_bass_note` and calls it per chord interval.
"""

from __future__ import annotations

from pathlib import Path

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
_MIN_INTERVAL_SEC = 0.05  # 50ms — below this, chroma is unreliable
_BASS_CHROMA_THRESHOLD = 0.5  # confidence floor; below → None


def pitch_class_letter(idx: int) -> str:
    """Map pitch-class index 0..11 → letter (sharp form)."""
    if not 0 <= idx <= 11:
        raise ValueError(f"pitch class index out of 0..11: {idx}")
    return _PITCH_CLASS_LETTERS[idx]


def extract_bass_note(
    bass_stem: Path,
    start: float,
    end: float,
) -> tuple[str | None, float]:
    """Extract the dominant bass-note class from a bass-stem interval.

    Returns:
        (letter, confidence) — letter is None when confidence < 0.5 or
        the interval is shorter than 50ms.

    Raises FileNotFoundError if bass_stem does not exist.
    """
    import librosa
    import numpy as np

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
    max_w = float(weights.max())
    if max_w <= 0.0:
        return None, 0.0
    median_w = float(np.median(weights))
    confidence = max(0.0, (max_w - median_w) / max_w)

    if confidence < _BASS_CHROMA_THRESHOLD:
        return None, confidence

    pc_idx = int(weights.argmax())
    return pitch_class_letter(pc_idx), confidence

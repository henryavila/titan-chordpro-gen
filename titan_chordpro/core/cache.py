"""Opt-in cache helpers.

Layout (when `cache=True` is passed to transcribe()):

    <root>/<audio_id>/
        stems.json
        transcription.json
        alignment.json
        chords.json
        beats.json
        syllables.json

Phase B exposes only the path helpers — actual serialization wiring lands
in Phase C alongside the validation harness.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

_MIN_AUDIO_ID_LEN = 4

Stage = Literal[
    "stems",
    "transcription",
    "alignment",
    "chords",
    "beats",
    "syllables",
]
_VALID_STAGES: frozenset[str] = frozenset(
    {"stems", "transcription", "alignment", "chords", "beats", "syllables"}
)


def cache_dir(audio_id: str, root: Path | None = None) -> Path:
    """Return (and create) the per-audio cache directory.

    Args:
        audio_id: sha256-hex string identifying the source audio.
        root: cache root; defaults to `./.titan-cache` (relative to cwd).

    Raises ValueError when audio_id is shorter than 4 chars (likely typo).
    """
    if len(audio_id) < _MIN_AUDIO_ID_LEN:
        raise ValueError(
            f"audio_id too short ({len(audio_id)} chars); expected >= {_MIN_AUDIO_ID_LEN}"
        )
    base = root if root is not None else Path.cwd() / ".titan-cache"
    d = base / audio_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def stage_file(audio_id: str, stage: Stage, root: Path | None = None) -> Path:
    """Return the per-audio per-stage JSON file path (not created)."""
    if stage not in _VALID_STAGES:
        raise ValueError(f"unknown stage {stage!r}; expected one of {sorted(_VALID_STAGES)}")
    base = root if root is not None else Path.cwd() / ".titan-cache"
    return base / audio_id / f"{stage}.json"

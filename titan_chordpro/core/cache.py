"""Opt-in cache helpers.

Layout (when `cache=True` is passed to transcribe()):

    <root>/<audio_id>/
        stems.json
        transcription.json
        alignment.json
        chords.json
        beats.json
        syllables.json
        document.json       (Phase C — full ChordProDocument round-trip)
        provenance.json     (Phase C — engine registry + confidence)

Phase C adds dump_stage / load_stage. Writes are atomic (tmp + rename).
Loads return None on missing OR corrupted file — the caller decides
cache-miss behavior (orchestrator falls back to re-running the engine).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Literal

_MIN_AUDIO_ID_LEN = 4
_log = logging.getLogger(__name__)

Stage = Literal[
    "stems",
    "transcription",
    "alignment",
    "chords",
    "beats",
    "syllables",
    "document",
    "provenance",
]
_VALID_STAGES: frozenset[str] = frozenset(
    {
        "stems",
        "transcription",
        "alignment",
        "chords",
        "beats",
        "syllables",
        "document",
        "provenance",
    }
)


def cache_dir(audio_id: str, root: Path | None = None) -> Path:
    """Return (and create) the per-audio cache directory.

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
    if len(audio_id) < _MIN_AUDIO_ID_LEN:
        raise ValueError(
            f"audio_id too short ({len(audio_id)} chars); expected >= {_MIN_AUDIO_ID_LEN}"
        )
    base = root if root is not None else Path.cwd() / ".titan-cache"
    return base / audio_id / f"{stage}.json"


def dump_stage(
    audio_id: str,
    stage: Stage,
    payload: Any,
    root: Path | None = None,
) -> Path:
    """Write a stage payload atomically. Returns the final file path.

    Atomicity: payload is written to `<stage>.json.tmp` then renamed to
    `<stage>.json`. A half-written tmp is never visible as a valid cache
    file (load_stage looks at the canonical name only).
    """
    if stage not in _VALID_STAGES:
        raise ValueError(f"unknown stage {stage!r}; expected one of {sorted(_VALID_STAGES)}")
    d = cache_dir(audio_id, root=root)
    final = d / f"{stage}.json"
    tmp = d / f"{stage}.json.tmp"
    tmp.write_text(json.dumps(payload, ensure_ascii=False, default=str))
    os.replace(tmp, final)
    return final


def load_stage(
    audio_id: str,
    stage: Stage,
    root: Path | None = None,
) -> dict[str, Any] | None:
    """Read a stage payload, or return None on missing / corrupted file.

    Corruption is treated as cache-miss (not raised) so a future
    dump_stage overwrites it cleanly. A WARNING is logged for visibility.
    """
    if stage not in _VALID_STAGES:
        raise ValueError(f"unknown stage {stage!r}; expected one of {sorted(_VALID_STAGES)}")
    if len(audio_id) < _MIN_AUDIO_ID_LEN:
        raise ValueError(
            f"audio_id too short ({len(audio_id)} chars); expected >= {_MIN_AUDIO_ID_LEN}"
        )
    base = root if root is not None else Path.cwd() / ".titan-cache"
    path = base / audio_id / f"{stage}.json"
    if not path.exists():
        return None
    try:
        data: dict[str, Any] = json.loads(path.read_text())
        return data
    except json.JSONDecodeError:
        _log.warning("cache file %s is corrupted; treating as miss", path)
        return None

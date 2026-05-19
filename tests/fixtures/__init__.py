"""Test fixture helpers (Phase C+)."""

from __future__ import annotations

from pathlib import Path


def silent_audio_path() -> Path:
    """Path to the checked-in silent.wav fixture (Phase A T05)."""
    return Path(__file__).parent / "silent.wav"

# tests/integration/test_beatthis_smoke.py
"""BeatThis integration smoke — real model, synthetic input.

Skipped automatically when `beat_this` is not installed (CI without [mac]
extras, dev machine without ML deps, etc.). The test is intentionally
permissive: a 2s sine tone is musically degenerate, so BeatThis may either
produce a degenerate grid (low confidence) or raise BeatTrackingError. Both
outcomes are acceptable; what we verify is that schema validation passes
when a grid is returned, and that any failure is a domain exception.
"""

from __future__ import annotations

from pathlib import Path

import pytest

beat_this = pytest.importorskip(
    "beat_this",
    reason="beat_this not installed; install with pip install -e .[mac]",
)


@pytest.mark.integration
def test_beatthis_returns_valid_grid_on_tone(tone_a4_2s_wav: Path) -> None:
    from titan_chordpro.core.exceptions import BeatTrackingError
    from titan_chordpro.core.schemas import BeatGrid
    from titan_chordpro.engines.beat.beatthis import BeatThisEngine

    engine = BeatThisEngine()
    try:
        grid = engine.track(tone_a4_2s_wav)
    except BeatTrackingError as exc:
        # Acceptable: 2s tone has no actual rhythm; engine may raise.
        assert exc.engine == "beat_this"
        return

    assert isinstance(grid, BeatGrid)
    assert grid.source_engine == "beat_this"
    assert all(0 <= b for b in grid.beats)
    assert all(0 <= idx < len(grid.beats) for idx in grid.downbeat_indices)


@pytest.mark.integration
def test_beatthis_silent_wav_handled(silent_wav: Path) -> None:
    """silent.wav should NOT crash the engine; either valid grid or
    BeatTrackingError (no other exception types)."""
    from titan_chordpro.core.exceptions import BeatTrackingError
    from titan_chordpro.engines.beat.beatthis import BeatThisEngine

    engine = BeatThisEngine()
    try:
        engine.track(silent_wav)
    except BeatTrackingError:
        pass  # acceptable


@pytest.mark.integration
def test_beatthis_info_reports_real_version() -> None:
    from titan_chordpro.engines.beat.beatthis import BeatThisEngine

    engine = BeatThisEngine()
    info = engine.info
    assert info.name == "beat_this"
    assert info.backend in ("mps", "cuda", "cpu")
    assert info.version  # non-empty

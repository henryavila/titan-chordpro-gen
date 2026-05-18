"""htdemucs_ft integration smoke — real model on synthetic tone.

The tone is a degenerate input (no actual instruments to separate) but
htdemucs_ft is robust to non-musical signals; it will produce 4 stems
that mostly contain silence/noise. We only assert shape, not audibility.
Real corpus validation happens in Phase C.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip(
    "audio_separator",
    reason="python-audio-separator not installed; install with pip install -e .[mac]",
)


@pytest.mark.integration
def test_htdemucs_produces_four_stems(tone_a4_2s_wav: Path, tmp_path: Path) -> None:
    from titan_chordpro.core.schemas import StemSet
    from titan_chordpro.engines.separation.htdemucs import HtdemucsEngine

    engine = HtdemucsEngine(output_dir=tmp_path)
    stems = engine.separate(tone_a4_2s_wav)

    assert isinstance(stems, StemSet)
    assert stems.vocals.exists()
    assert stems.bass.exists()
    assert stems.drums.exists()
    assert stems.other.exists()
    assert stems.sample_rate == 44100
    assert stems.duration == pytest.approx(2.0, abs=0.2)
    assert stems.source_engine == "htdemucs_ft"
    assert stems.audio_id  # non-empty sha256

"""Chordino integration smoke — skipped when chord_extractor or VAMP missing.

The tone fixture is harmonically degenerate (single sine wave); Chordino
will likely emit "N" (no-chord) repeatedly or return an empty list. Both
outcomes pass the smoke. Real harmonic content is validated in Phase C.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip(
    "chord_extractor",
    reason="chord_extractor not installed; install with pip install -e .[mac]",
)


def _chordino_plugin_present() -> bool:
    try:
        import vampyhost
    except ImportError:
        return False
    return "nnls-chroma:chordino" in vampyhost.list_plugins()


pytestmark = pytest.mark.skipif(
    not _chordino_plugin_present(),
    reason="nnls-chroma:chordino VAMP plugin not installed; run scripts/install_vamp.sh",
)


@pytest.mark.integration
def test_chordino_returns_schema_valid_list(tone_a4_2s_wav: Path) -> None:
    from titan_chordpro.core.schemas import ChordEvent
    from titan_chordpro.engines.chord.chordino import ChordinoEngine

    engine = ChordinoEngine()
    chords = engine.detect(tone_a4_2s_wav)

    assert isinstance(chords, list)
    for c in chords:
        assert isinstance(c, ChordEvent)
        assert c.timestamp.end >= c.timestamp.start
        assert c.source_engine == "chordino"
        # bass_note may be None or letter; depends on whether a bass stem
        # was passed (this smoke calls detect() without one — F-004 path
        # is exercised in test_bass_note_smoke_with_synthetic_bass below).
        assert c.bass_note is None


@pytest.mark.integration
def test_chordino_info_reports_majmin_vocab() -> None:
    from titan_chordpro.engines.chord.chordino import ChordinoEngine

    engine = ChordinoEngine()
    info = engine.info
    assert info.name == "chordino"
    assert engine.vocabulary == "majmin"
    # Phase C T64: F-004 active when a bass_stem is provided to detect().
    assert engine.supports_inversions is True


def test_bass_note_smoke_with_synthetic_bass(tmp_path: Path) -> None:
    """End-to-end smoke: a chord interval with a known-bass synthetic stem
    should emit bass_note (or None if librosa is absent / chroma weak)."""
    pytest.importorskip("librosa")
    import numpy as np
    import soundfile as sf

    from titan_chordpro.engines.chord.bass_chroma import extract_bass_note

    sr = 22050
    t = np.linspace(0.0, 2.0, int(sr * 2.0), endpoint=False)
    audio = 0.4 * np.sin(2.0 * np.pi * 110.0 * t).astype(np.float32)  # A2
    bass = tmp_path / "bass_synth.wav"
    sf.write(str(bass), audio, sr)

    letter, conf = extract_bass_note(bass, start=0.2, end=1.8)
    assert letter == "A"
    assert conf > 0.5

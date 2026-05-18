"""Chordino integration smoke — skipped when chord_extractor or VAMP missing.

The tone fixture is harmonically degenerate (single sine wave); Chordino
will likely emit "N" (no-chord) repeatedly or return an empty list. Both
outcomes pass the smoke. Real harmonic content is validated in Phase C.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

pytest.importorskip(
    "chord_extractor",
    reason="chord_extractor not installed; install with pip install -e .[mac]",
)


def _vamp_host_present() -> bool:
    return shutil.which("sonic-annotator") is not None


pytestmark = pytest.mark.skipif(
    not _vamp_host_present(),
    reason="sonic-annotator (VAMP host) not installed; run scripts/install_vamp.sh",
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
        assert c.bass_note is None  # Phase B baseline


@pytest.mark.integration
def test_chordino_info_reports_majmin_vocab() -> None:
    from titan_chordpro.engines.chord.chordino import ChordinoEngine

    engine = ChordinoEngine()
    info = engine.info
    assert info.name == "chordino"
    assert engine.vocabulary == "majmin"
    assert engine.supports_inversions is False

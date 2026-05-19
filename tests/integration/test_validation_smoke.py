"""Integration smoke for validation_runner — no yt-dlp, no real audio."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("mir_eval")


def test_validation_smoke_with_mocked_transcribe(tmp_path: Path) -> None:
    """Smoke test using REAL schema objects (not a fake Line attribute).

    F-003 review note: the previous smoke test invented a `chord_events`
    attribute that doesn't exist on any Line subtype. The runner now
    extracts from `LyricLine.chord_markers[*].chord` and
    `InstrumentalLine.chords`, so the smoke must build those real shapes.
    """
    import numpy as np
    import soundfile as sf

    from benchmarks.corpus import Song
    from benchmarks.validation_runner import run_validation
    from titan_chordpro.core.schemas import (
        ChordEvent,
        ChordMarker,
        ChordProDocument,
        LyricLine,
        Section,
        TimeStamp,
    )

    # F-004 duration probe needs a real audio file.
    audio_path = tmp_path / "fake.wav"
    sf.write(str(audio_path), np.zeros(int(22050 * 4.0), dtype=np.float32), 22050)

    chord_events = [
        ChordEvent(
            symbol=s,
            timestamp=TimeStamp(start=i * 1.0, end=(i + 1) * 1.0),
            confidence=1.0,
            source_engine="t",
        )
        for i, s in enumerate(["C", "G", "Am", "F"])
    ]
    markers = [
        ChordMarker(chord=evt, char_position=i * 5, placement_strategy="any_syllable")
        for i, evt in enumerate(chord_events)
    ]
    line = LyricLine(text="Hello world now end", chord_markers=markers)
    section = Section(
        type="verse",
        label="Verse 1",
        lines=[line],
        timestamp=TimeStamp(start=0.0, end=4.0),
    )

    fake_doc = MagicMock(spec=ChordProDocument)
    fake_doc.sections = [section]

    def fake_transcribe(audio: Path, **kwargs: object) -> ChordProDocument:
        return fake_doc

    songs = [
        Song(
            title="Test",
            external_link="https://youtu.be/aaaaaaaaaaa",
            chordpro="[C]Hello [G]world [Am]now [F]end",
            youtube_id="aaaaaaaaaaa",
        )
    ]

    with patch("benchmarks.validation_runner.download_audio", return_value=audio_path):
        report = run_validation(
            songs,
            transcribe_fn=fake_transcribe,
            audio_cache_root=tmp_path,
            titan_cache_root=tmp_path / "cache",
        )

    assert report.total_attempted == 1
    assert len(report.metrics) == 1
    assert report.metrics[0].wcsr_majmin > 0.9
    assert report.failures == []


def test_validation_captures_failure_per_song(tmp_path: Path) -> None:
    from benchmarks.corpus import Song
    from benchmarks.validation_runner import run_validation

    songs = [
        Song(
            title="Bad",
            external_link="https://youtu.be/bbbbbbbbbbb",
            chordpro="[C]Hi",
            youtube_id="bbbbbbbbbbb",
        )
    ]

    def failing_transcribe(audio: Path, **kwargs: object) -> None:
        raise RuntimeError("simulated engine crash")

    with patch("benchmarks.validation_runner.download_audio", return_value=tmp_path / "fake.m4a"):
        report = run_validation(
            songs,
            transcribe_fn=failing_transcribe,
            audio_cache_root=tmp_path,
            titan_cache_root=tmp_path,
        )

    assert len(report.failures) == 1
    assert "simulated engine crash" in report.failures[0].error
    assert report.metrics == []

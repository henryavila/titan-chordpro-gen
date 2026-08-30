"""Integration tests for orchestrator.transcribe(cache=True)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch


def test_cache_off_no_cache_files_created(tmp_path: Path) -> None:
    from tests.fixtures import silent_audio_path
    from titan_chordpro.orchestrator import transcribe

    audio = silent_audio_path()
    doc = transcribe(audio, force_mock=True, cache=False, cache_root=tmp_path)
    # Stage JSON cache must stay empty when cache=False. Harmonic-mix scratch
    # may still mkdir under cache_root (orchestrator writes other+bass WAV there).
    assert list(tmp_path.rglob("*.json")) == []
    assert doc is not None


def test_cache_on_writes_all_stages(tmp_path: Path) -> None:
    from tests.fixtures import silent_audio_path
    from titan_chordpro.orchestrator import transcribe

    audio = silent_audio_path()
    transcribe(audio, force_mock=True, cache=True, cache_root=tmp_path)
    audio_dirs = list(tmp_path.iterdir())
    assert len(audio_dirs) == 1
    files = sorted(p.name for p in audio_dirs[0].iterdir())
    for expected in (
        "alignment.json",
        "beats.json",
        "chords.json",
        "document.json",
        "provenance.json",
        "stems.json",
        "syllables.json",
        "transcription.json",
    ):
        assert expected in files, f"missing {expected} (got: {files})"


def test_cache_on_second_run_skips_engines(tmp_path: Path) -> None:
    """On a cache hit, engines must NOT be invoked."""
    from tests.fixtures import silent_audio_path
    from titan_chordpro import factory
    from titan_chordpro.orchestrator import transcribe

    audio = silent_audio_path()
    transcribe(audio, force_mock=True, cache=True, cache_root=tmp_path)

    with patch.object(factory, "select_separation") as mock_sep:
        transcribe(audio, force_mock=True, cache=True, cache_root=tmp_path)
        mock_sep.assert_not_called()


def test_corrupted_cache_falls_back_gracefully(tmp_path: Path) -> None:
    """A corrupted stems.json must NOT raise — cache treated as miss.

    Note: with the document.json fast path, the second call returns from
    the cached document BEFORE looking at stems.json. To exercise the
    stems-miss path we delete document.json after the first run.
    """
    from tests.fixtures import silent_audio_path
    from titan_chordpro.orchestrator import transcribe

    audio = silent_audio_path()
    transcribe(audio, force_mock=True, cache=True, cache_root=tmp_path)
    audio_dirs = list(tmp_path.iterdir())
    (audio_dirs[0] / "document.json").unlink()
    (audio_dirs[0] / "stems.json").write_text("{not json")

    doc = transcribe(audio, force_mock=True, cache=True, cache_root=tmp_path)
    assert doc is not None

"""CLI integration tests — Phase B extensions."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.integration
def test_cli_list_engines_prints_selections(
    capsys: pytest.CaptureFixture[str], silent_wav: Path, tmp_path: Path
) -> None:
    """--list-engines prints stage -> engine map after running the pipeline.

    Implemented as a side-effect of a real transcribe run because the
    selection map is populated by select_*() calls inside the pipeline.
    """
    from titan_chordpro.cli import main

    out_path = tmp_path / "out.chordpro"
    code = main([str(silent_wav), "--output", str(out_path), "--device", "mock", "--list-engines"])
    assert code == 0
    captured = capsys.readouterr()
    # Must print each stage at least once.
    for stage in (
        "separation",
        "transcription",
        "alignment",
        "chord_recognition",
        "beat_tracking",
        "syllabification",
    ):
        assert stage in captured.out


@pytest.mark.integration
def test_cli_device_mock_uses_only_mocks(silent_wav: Path, tmp_path: Path) -> None:
    from titan_chordpro.cli import main
    from titan_chordpro.factory import last_selection

    out_path = tmp_path / "out.chordpro"
    code = main([str(silent_wav), "--output", str(out_path), "--device", "mock"])
    assert code == 0

    selections = last_selection()
    assert all(sel["real"] is False for sel in selections.values()), selections

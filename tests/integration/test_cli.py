"""CLI integration tests — Phase B extensions + Phase C T71."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

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


@pytest.mark.integration
class TestRichProgress:
    def test_library_does_not_import_rich(self) -> None:
        """`import titan_chordpro` must not transitively import rich."""
        import sys

        # The contract is that importing the *library* does not pull rich.
        # Drop rich if a prior test imported the CLI (which lazy-loads rich).
        for mod in list(sys.modules):
            if mod == "rich" or mod.startswith("rich."):
                del sys.modules[mod]
        # Re-import package root only (not cli).
        import importlib

        import titan_chordpro

        importlib.reload(titan_chordpro)
        assert "rich" not in sys.modules, (
            "titan_chordpro library import surface should not pull rich; rich is CLI-only"
        )


@pytest.mark.integration
class TestValidateFlag:
    def test_help_documents_validate(self, capsys: pytest.CaptureFixture[str]) -> None:
        from titan_chordpro.cli import main

        with pytest.raises(SystemExit) as exc:
            main(["--help"])
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "--validate" in out
        assert "--sample-size" in out

    def test_validate_flag_invokes_validation_runner(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """`titan-chordpro --validate <csv> --sample-size 1` runs the harness."""
        from benchmarks.validation_runner import ValidationReport
        from titan_chordpro.cli import main

        csv_path = tmp_path / "songs.csv"
        csv_path.write_text(
            'title,external_link,chordpro\nTest,https://youtu.be/aaaaaaaaaaa,"[C]Hello"\n',
            encoding="utf-8",
        )

        called: dict[str, bool] = {"yes": False}

        def fake_run(*args: object, **kwargs: object) -> ValidationReport:
            called["yes"] = True
            return ValidationReport(metrics=[], failures=[], skipped_from_corpus=0)

        # Patch where the CLI binds the names (lazy imports inside _run_validate).
        with (
            patch("benchmarks.validation_runner.run_validation", side_effect=fake_run),
            patch(
                "benchmarks.divergence_ranker.write_report",
                return_value=tmp_path / "top-divergences.md",
            ),
        ):
            code = main(["--validate", str(csv_path), "--sample-size", "1"])

        assert code == 0
        assert called["yes"] is True

    def test_validate_missing_csv_returns_error(self, tmp_path: Path) -> None:
        from titan_chordpro.cli import main

        missing = tmp_path / "nope.csv"
        code = main(["--validate", str(missing), "--sample-size", "1"])
        assert code == 2

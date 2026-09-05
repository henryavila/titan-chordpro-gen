"""Unit tests for the sibling-UI preview bridge."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from titan_chordpro.preview import (
    PreviewError,
    collect_chart_files,
    default_preview_paths,
    materialize_preview_dir,
    resolve_ui_root,
    start_preview,
)


@pytest.mark.unit
def test_library_import_does_not_load_preview() -> None:
    for mod in list(sys.modules):
        if mod == "titan_chordpro.preview" or mod.startswith("titan_chordpro.preview."):
            del sys.modules[mod]
    import importlib

    import titan_chordpro

    importlib.reload(titan_chordpro)
    assert "titan_chordpro.preview" not in sys.modules


@pytest.mark.unit
def test_collect_chart_files_from_dir(tmp_path: Path) -> None:
    (tmp_path / "a.chordpro").write_text("{title: A}\n[C]oi\n")
    (tmp_path / "b.txt").write_text("{title: B}\n[G]x///\n")
    (tmp_path / "notes.md").write_text("ignore me\n")
    (tmp_path / "hidden").mkdir()
    files = collect_chart_files([tmp_path])
    names = {p.name for p in files}
    assert names == {"a.chordpro", "b.txt"}


@pytest.mark.unit
def test_collect_chart_files_single_file(tmp_path: Path) -> None:
    cho = tmp_path / "song.cho"
    cho.write_text("{title: Song}\n")
    assert collect_chart_files([cho]) == [cho.resolve()]


@pytest.mark.unit
def test_collect_chart_files_rejects_missing(tmp_path: Path) -> None:
    with pytest.raises(PreviewError, match="path not found"):
        collect_chart_files([tmp_path / "nope.chordpro"])


@pytest.mark.unit
def test_collect_chart_files_rejects_unknown_suffix(tmp_path: Path) -> None:
    wav = tmp_path / "x.wav"
    wav.write_bytes(b"RIFF")
    with pytest.raises(PreviewError, match="not a ChordPro file"):
        collect_chart_files([wav])


@pytest.mark.unit
def test_materialize_preview_dir_same_parent(tmp_path: Path) -> None:
    a = tmp_path / "a.cho"
    b = tmp_path / "b.cho"
    a.write_text("{title: A}\n")
    b.write_text("{title: B}\n")
    assert materialize_preview_dir([a, b]) == tmp_path.resolve()


@pytest.mark.unit
def test_materialize_preview_dir_copies_across_parents(tmp_path: Path) -> None:
    d1 = tmp_path / "one"
    d2 = tmp_path / "two"
    d1.mkdir()
    d2.mkdir()
    f1 = d1 / "a.cho"
    f2 = d2 / "b.cho"
    f1.write_text("{title: A}\n")
    f2.write_text("{title: B}\n")
    dest = materialize_preview_dir([f1, f2])
    assert dest != d1.resolve()
    assert (dest / "a.cho").read_text() == "{title: A}\n"
    assert (dest / "b.cho").read_text() == "{title: B}\n"


@pytest.mark.unit
def test_materialize_preview_dir_empty_raises() -> None:
    with pytest.raises(PreviewError, match="no ChordPro"):
        materialize_preview_dir([])


@pytest.mark.unit
def test_resolve_ui_root_env_wins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ui = tmp_path / "custom-ui"
    ui.mkdir()
    (ui / "package.json").write_text(json.dumps({"name": "titan-chordpro-ui"}))
    monkeypatch.delenv("TITAN_CHORDPRO_UI", raising=False)
    got = resolve_ui_root(env={"TITAN_CHORDPRO_UI": str(ui)}, repo_root=tmp_path / "gen")
    assert got == ui.resolve()


@pytest.mark.unit
def test_resolve_ui_root_sibling(tmp_path: Path) -> None:
    gen = tmp_path / "titan-chordpro-gen"
    ui = tmp_path / "titan-chordpro-ui"
    gen.mkdir()
    ui.mkdir()
    (ui / "package.json").write_text(json.dumps({"name": "titan-chordpro-ui"}))
    got = resolve_ui_root(env={}, repo_root=gen)
    assert got == ui.resolve()


@pytest.mark.unit
def test_resolve_ui_root_missing(tmp_path: Path) -> None:
    with pytest.raises(PreviewError, match="titan-chordpro-ui not found"):
        resolve_ui_root(env={}, repo_root=tmp_path / "titan-chordpro-gen")


@pytest.mark.unit
def test_default_preview_paths_picks_latest_cifras(tmp_path: Path) -> None:
    old = tmp_path / "benchmarks" / "reports" / "2026-05-19" / "cifras"
    new = tmp_path / "benchmarks" / "reports" / "2026-08-04" / "cifras"
    old.mkdir(parents=True)
    new.mkdir(parents=True)
    (old / "old.txt").write_text("{title: old}\n")
    (new / "Ao-olhar-pra-cruz.txt").write_text("{title: Ao olhar pra cruz}\n")
    paths = default_preview_paths(tmp_path)
    assert paths == [new]


@pytest.mark.unit
def test_start_preview_sets_env_and_opens_browser(tmp_path: Path) -> None:
    ui = tmp_path / "titan-chordpro-ui"
    ui.mkdir()
    (ui / "package.json").write_text(json.dumps({"name": "titan-chordpro-ui"}))
    (ui / "node_modules" / "vite").mkdir(parents=True)
    chart = tmp_path / "song.chordpro"
    chart.write_text("{title: Song}\n[C]hey\n")

    launched: dict[str, Any] = {}

    class FakeProc:
        def __init__(self) -> None:
            self.returncode = None

        def poll(self) -> int | None:
            return None

        def terminate(self) -> None:
            launched["terminated"] = True

        def wait(self, timeout: float | None = None) -> int:
            return 0

    def fake_popen(cmd: list[str], **kwargs: Any) -> FakeProc:
        launched["cmd"] = cmd
        launched["cwd"] = kwargs.get("cwd")
        launched["env"] = kwargs.get("env")
        return FakeProc()

    opened: list[str] = []

    session = start_preview(
        [chart],
        open_browser=True,
        wait=False,
        port=5199,
        ui_root=ui,
        popen=fake_popen,
        browser_open=lambda url: opened.append(url),
        wait_ready=lambda url, timeout=30.0: None,
    )
    assert session.port == 5199
    assert "pnpm" in session.cmd[0] or session.cmd[0] == "pnpm"
    assert launched["env"]["TITAN_PREVIEW_DIR"] == str(chart.parent.resolve())
    assert opened == [f"http://127.0.0.1:5199/?song={chart.stem}"]
    assert launched["cwd"] == ui.resolve()

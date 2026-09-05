"""Launch the sibling titan-chordpro-ui demo against generated ChordPro files.

The UI stays in its own repo. This module only resolves that checkout, points
``TITAN_PREVIEW_DIR`` at the charts, and starts ``pnpm dev``.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import webbrowser
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from titan_chordpro.core.exceptions import TitanConfigError

CHART_SUFFIXES = {".cho", ".chordpro", ".chopro", ".onsong", ".txt", ".pro", ".crd"}
_DEFAULT_PORT = 5173


class PreviewError(TitanConfigError):
    """Sibling UI preview failed (missing checkout, no charts, demo down)."""


@dataclass
class PreviewSession:
    url: str
    preview_dir: Path
    ui_root: Path
    process: Any
    port: int
    cmd: list[str]


def collect_chart_files(paths: Sequence[Path]) -> list[Path]:
    """Expand files and directories into a de-duplicated chart list."""
    out: list[Path] = []
    seen: set[Path] = set()
    for raw in paths:
        path = raw.expanduser().resolve()
        if path.is_dir():
            for child in sorted(path.iterdir()):
                if child.is_file() and child.suffix.lower() in CHART_SUFFIXES:
                    if child not in seen:
                        seen.add(child)
                        out.append(child)
            continue
        if not path.is_file():
            raise PreviewError(f"path not found: {path}")
        if path.suffix.lower() not in CHART_SUFFIXES:
            raise PreviewError(f"not a ChordPro file: {path}")
        if path not in seen:
            seen.add(path)
            out.append(path)
    return out


def materialize_preview_dir(files: Sequence[Path]) -> Path:
    """Return a single directory that contains every chart (copy if needed)."""
    if not files:
        raise PreviewError("no ChordPro files to preview")
    resolved = [f.resolve() for f in files]
    parents = {f.parent for f in resolved}
    if len(parents) == 1:
        return next(iter(parents))
    dest = Path(tempfile.mkdtemp(prefix="titan-preview-"))
    for src in resolved:
        target = dest / src.name
        if target.exists():
            target = dest / f"{src.parent.name}-{src.name}"
        shutil.copy2(src, target)
    return dest


def default_preview_paths(repo_root: Path | None = None) -> list[Path]:
    """Latest ``benchmarks/reports/<date>/cifras`` that still has charts."""
    root = repo_root or Path.cwd()
    reports = root / "benchmarks" / "reports"
    if not reports.is_dir():
        return []
    dated = sorted(
        (p for p in reports.iterdir() if p.is_dir()),
        key=lambda p: p.name,
        reverse=True,
    )
    for day in dated:
        cifras = day / "cifras"
        if cifras.is_dir() and collect_chart_files([cifras]):
            return [cifras]
    return []


def resolve_ui_root(
    *,
    env: Mapping[str, str] | None = None,
    repo_root: Path | None = None,
) -> Path:
    """Prefer ``TITAN_CHORDPRO_UI``, else ``../titan-chordpro-ui`` next to gen."""
    environ = env if env is not None else os.environ
    override = environ.get("TITAN_CHORDPRO_UI")
    if override:
        path = Path(override).expanduser().resolve()
        _assert_ui_root(path)
        return path
    root = repo_root if repo_root is not None else Path(__file__).resolve().parents[1]
    sibling = (root.parent / "titan-chordpro-ui").resolve()
    if sibling.is_dir():
        _assert_ui_root(sibling)
        return sibling
    raise PreviewError(
        "titan-chordpro-ui not found. Set TITAN_CHORDPRO_UI to the sibling repo path "
        "(expected ../titan-chordpro-ui)."
    )


def start_preview(
    paths: Sequence[Path] | None = None,
    *,
    open_browser: bool = True,
    wait: bool = False,
    port: int | None = None,
    ui_root: Path | None = None,
    popen: Callable[..., Any] = subprocess.Popen,
    browser_open: Callable[[str], Any] = webbrowser.open,
    wait_ready: Callable[..., None] | None = None,
    repo_root: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> PreviewSession:
    """Start the Vue demo pointed at ``paths`` (or the latest harness cifras)."""
    chart_paths = list(paths) if paths else default_preview_paths(repo_root)
    files = collect_chart_files(chart_paths)
    preview_dir = materialize_preview_dir(files)
    if ui_root is not None:
        root = ui_root.resolve()
    else:
        root = resolve_ui_root(env=env, repo_root=repo_root)
    _assert_demo_installed(root)
    chosen_port = port if port is not None else _pick_port(_DEFAULT_PORT)
    cmd = [
        "pnpm",
        "dev",
        "--host",
        "127.0.0.1",
        "--port",
        str(chosen_port),
        "--strictPort",
    ]
    child_env = dict(os.environ if env is None else env)
    child_env["TITAN_PREVIEW_DIR"] = str(preview_dir)
    proc = popen(cmd, cwd=root, env=child_env)
    url = f"http://127.0.0.1:{chosen_port}/?song={files[0].stem}"
    try:
        if wait_ready is not None:
            wait_ready(url)
        else:
            _wait_http(url)
    except PreviewError:
        code = proc.poll() if hasattr(proc, "poll") else None
        if code is not None:
            raise PreviewError(
                f"UI demo exited early (code {code}). Is pnpm installed in {root}?"
            ) from None
        raise
    if open_browser:
        browser_open(url)
    if wait and proc is not None:
        try:
            proc.wait()
        except KeyboardInterrupt:
            _stop(proc)
    return PreviewSession(
        url=url,
        preview_dir=preview_dir,
        ui_root=root,
        process=proc,
        port=chosen_port,
        cmd=cmd,
    )


def _assert_ui_root(path: Path) -> None:
    pkg = path / "package.json"
    if not pkg.is_file():
        raise PreviewError(f"Not a titan-chordpro-ui checkout: {path} (missing package.json)")


def _assert_demo_installed(ui_root: Path) -> None:
    if not (ui_root / "node_modules" / "vite").exists():
        raise PreviewError(f"UI demo is not installed. Run pnpm install in {ui_root}")


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _pick_port(preferred: int) -> int:
    if not _port_in_use(preferred):
        return preferred
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_http(url: str, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    last: Exception | None = None
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=0.5)
            return
        except (OSError, urllib.error.URLError) as exc:
            last = exc
            time.sleep(0.1)
    raise PreviewError(f"UI demo did not start at {url}") from last


def _stop(proc: Any) -> None:
    terminate = getattr(proc, "terminate", None)
    if terminate is not None:
        terminate()
        wait = getattr(proc, "wait", None)
        if wait is not None:
            try:
                wait(timeout=5)
            except TypeError:
                wait()
            except Exception:  # noqa: BLE001
                kill = getattr(proc, "kill", None)
                if kill is not None:
                    kill()

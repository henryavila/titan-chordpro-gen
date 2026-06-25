"""Import isolation tests for the public hardware infra contract."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
BLOCKED_MODULES = (
    "titan_chordpro.orchestrator",
    "titan_chordpro.factory",
    "titan_chordpro.fusion",
    "titan_chordpro.core.schemas",
    "torch",
    "pydantic",
)


def _run_subprocess(source: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(source)],
        check=False,
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )


@pytest.mark.unit
def test_core_hardware_import_does_not_load_chordpro_domain_modules() -> None:
    result = _run_subprocess(
        f"""
        import json
        import sys

        import titan_chordpro.core.hardware

        blocked = {BLOCKED_MODULES!r}
        leaked = [name for name in blocked if name in sys.modules]
        print(json.dumps({{"leaked": leaked}}))
        """
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["leaked"] == []


@pytest.mark.unit
def test_package_root_public_api_remains_importable() -> None:
    result = _run_subprocess(
        """
        import json

        from titan_chordpro.version import __version__ as expected_version
        from titan_chordpro import ChordProDocument, __version__, transcribe

        print(json.dumps({
            "document_name": ChordProDocument.__name__,
            "version": __version__,
            "expected_version": expected_version,
            "transcribe_callable": callable(transcribe),
        }))
        """
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {
        "document_name": "ChordProDocument",
        "version": "0.1.0b2",
        "expected_version": "0.1.0b2",
        "transcribe_callable": True,
    }


@pytest.mark.unit
def test_package_root_unknown_attribute_raises_without_eager_domain_imports() -> None:
    result = _run_subprocess(
        f"""
        import json
        import sys

        import titan_chordpro

        try:
            getattr(titan_chordpro, "not_a_public_export")
        except AttributeError as exc:
            error = str(exc)
        else:
            raise AssertionError("unknown attribute did not raise AttributeError")

        blocked = {BLOCKED_MODULES!r}
        leaked = [name for name in blocked if name in sys.modules]
        print(json.dumps({{"error": error, "leaked": leaked}}))
        """
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert "not_a_public_export" in payload["error"]
    assert payload["leaked"] == []

"""Tests for the documented public infra contract consumed by curta."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_HARDWARE_API = (
    "titan_chordpro.core.hardware.detect_backend",
    "titan_chordpro.core.hardware.hardware_to_torch_device",
    "titan_chordpro.core.hardware.release_gpu_memory",
)


@pytest.mark.unit
def test_project_version_is_aligned_for_curta_contract() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())

    from titan_chordpro.version import __version__

    assert pyproject["project"]["version"] == "0.1.0b2"
    assert __version__ == "0.1.0b2"


@pytest.mark.unit
def test_readme_documents_only_the_public_hardware_infra_contract() -> None:
    readme = (REPO_ROOT / "README.md").read_text()
    section = readme.split("## Public infra contract for `curta`", maxsplit=1)[1].split(
        "\n## ", maxsplit=1
    )[0]

    assert "Version: `0.1.0b2`" in section
    for symbol in PUBLIC_HARDWARE_API:
        assert f"`{symbol}`" in section
    assert section.count("`titan_chordpro.core.hardware.") == len(PUBLIC_HARDWARE_API)
    assert "`titan_chordpro.core.cache`" in section
    assert "ChordPro-domain modules are outside the `curta` contract" in section

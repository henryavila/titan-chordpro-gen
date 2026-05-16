# tests/unit/test_smoke.py
"""Smoke test: package can be imported and version is correct."""

import pytest


@pytest.mark.unit
def test_package_import_and_version() -> None:
    import titan_chordpro

    assert titan_chordpro.__version__ == "0.1.0a0"

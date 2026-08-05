"""Unit tests for scripts/compare_chordpro_to_gt.py helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "compare_chordpro_to_gt.py"


def _load_compare_mod():
    import sys

    name = "compare_chordpro_to_gt"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    # Register before exec so @dataclass can resolve cls.__module__.
    sys.modules[name] = mod
    # Script inserts cwd for benchmarks.*; tests run from repo root.
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def compare_mod():
    return _load_compare_mod()


@pytest.mark.unit
class TestNormalizeMajminSoft:
    """soft=True collapses extensions; soft=False keeps quality tail honestly."""

    def test_soft_true_collapses_am7_to_amin(self, compare_mod) -> None:
        assert compare_mod.normalize_majmin("Am7", soft=True) == "A:min"
        assert compare_mod.normalize_majmin("Am", soft=True) == "A:min"
        assert compare_mod.normalize_majmin("Am7", soft=True) == compare_mod.normalize_majmin(
            "Am", soft=True
        )

    def test_soft_false_keeps_am7_distinct_from_am(self, compare_mod) -> None:
        am7 = compare_mod.normalize_majmin("Am7", soft=False)
        am = compare_mod.normalize_majmin("Am", soft=False)
        assert am7 != am, f"soft=False must not collapse Am7 and Am: {am7!r} vs {am!r}"
        assert am7.startswith("A:"), am7
        assert am.startswith("A:"), am
        # Quality tail retained (digits / extension present on Am7 only).
        assert "7" in am7
        assert "7" not in am

    def test_soft_true_collapses_maj7_and_7_to_maj(self, compare_mod) -> None:
        assert compare_mod.normalize_majmin("Cmaj7", soft=True) == "C:maj"
        assert compare_mod.normalize_majmin("C7", soft=True) == "C:maj"
        assert compare_mod.normalize_majmin("C", soft=True) == "C:maj"

    def test_soft_false_keeps_c7_distinct_from_c(self, compare_mod) -> None:
        c7 = compare_mod.normalize_majmin("C7", soft=False)
        c = compare_mod.normalize_majmin("C", soft=False)
        assert c7 != c
        assert "7" in c7

    def test_slash_stripped_both_modes(self, compare_mod) -> None:
        assert compare_mod.normalize_majmin("Am7/G", soft=True) == "A:min"
        soft_f = compare_mod.normalize_majmin("Am7/G", soft=False)
        assert soft_f.startswith("A:")
        assert "7" in soft_f
        assert "/" not in soft_f

    def test_n_and_empty(self, compare_mod) -> None:
        assert compare_mod.normalize_majmin("N", soft=True) == "N"
        assert compare_mod.normalize_majmin("N", soft=False) == "N"
        assert compare_mod.normalize_majmin("", soft=False) == "N"

"""Ablation monkeypatch must refresh def-time defaults (Codex P2)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "redetect_chords_from_cache.py"


def _load_redetect_mod():
    name = "redetect_chords_from_cache"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def redetect_mod():
    return _load_redetect_mod()


@pytest.mark.unit
def test_apply_ablation_refreshes_captured_defaults(redetect_mod) -> None:
    """Advertised ablation keys that bind at def-time must take effect.

    RESEG_PRIMARY_ONLY / RESEG_ALLOW_SECONDARY / MIN_CHORD_DURATION_S /
    CHROMA_SCORE_MARGIN / RESEG_MAX_PASSES are frozen into function defaults
    at import; monkeypatching module globals alone is not enough.
    """
    import titan_chordpro.engines.chord.chordino as ch

    apply_ablation = redetect_mod.apply_ablation
    restore_ablation = redetect_mod.restore_ablation

    orig_merge = ch.merge_short_chords.__defaults__
    orig_pool = dict(ch._reseg_candidate_pool.__kwdefaults__ or {})
    orig_reseg = dict(ch.resegment_long_holds.__kwdefaults__ or {})

    params = {
        "MIN_CHORD_DURATION_S": 0.99,
        "RESEG_PRIMARY_ONLY": False,
        "RESEG_ALLOW_SECONDARY": True,
        "CHROMA_SCORE_MARGIN": 0.123,
        "RESEG_MAX_PASSES": 2,
        # Runtime-read keys — still set so the advertised list is exercised.
        "MIN_HOLD_BEATS": 2.0,
        "LONG_HOLD_FORCE_RELABEL_S": 8.0,
    }
    previous = apply_ablation(params)
    try:
        assert ch.merge_short_chords.__defaults__ == (0.99,)
        pool_kw = ch._reseg_candidate_pool.__kwdefaults__
        assert pool_kw is not None
        assert pool_kw["primary_only"] is False
        assert pool_kw["allow_secondary"] is True
        reseg_kw = ch.resegment_long_holds.__kwdefaults__
        assert reseg_kw is not None
        assert reseg_kw["score_margin"] == 0.123
        assert reseg_kw["max_passes"] == 2
        assert ch.MIN_HOLD_BEATS == 2.0
        assert ch.LONG_HOLD_FORCE_RELABEL_S == 8.0
    finally:
        restore_ablation(previous)

    assert ch.merge_short_chords.__defaults__ == orig_merge
    assert ch._reseg_candidate_pool.__kwdefaults__ == orig_pool
    restored = ch.resegment_long_holds.__kwdefaults__ or {}
    assert restored["score_margin"] == orig_reseg["score_margin"]
    assert restored["max_passes"] == orig_reseg["max_passes"]

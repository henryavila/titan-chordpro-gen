#!/usr/bin/env python3
"""Re-run ChordinoEngine.detect on cached audio (eval only).

Supports:
  - default product path: cache/<id>/harmonic_mix.wav + bass from stems.json
  - explicit --harmonic-mix / --bass-stem
  - temporary module-constant ablation via --param KEY=VALUE (monkeypatch)

Never hardcodes song chord labels into product detect(). Song IDs are CLI inputs.

Examples:
  .venv-py312/bin/python scripts/redetect_chords_from_cache.py \\
      --youtube-id 9yZt5ekdceI --cache-id c54e57cd59ac8018 \\
      --out /tmp/out.chords.json

  .venv-py312/bin/python scripts/redetect_chords_from_cache.py \\
      --youtube-id 9yZt5ekdceI --harmonic-mix /tmp/other.wav \\
      --bass-stem /path/to/bass.wav --out /tmp/out.chords.json \\
      --param MIN_HOLD_BEATS=2.0 --param CHROMA_SCORE_MARGIN=0.005
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

CACHE_ROOT = Path.home() / ".cache" / "titan-chordpro" / "cache"

# Module constants that may be ablated offline (product knobs).
ABLATION_KEYS = (
    "MIN_HOLD_BEATS",
    "MIN_ALT_BEATS",
    "RESEG_MAX_PASSES",
    "LONG_HOLD_FORCE_RELABEL_S",
    "CHROMA_SCORE_MARGIN",
    "CHROMA_SCORE_MARGIN_DOMINANT",
    "CHROMA_SCORE_MARGIN_SECONDARY",
    "CHROMA_DOMINANT_SCORE_PRIOR",
    "RESEG_PRIMARY_ONLY",
    "RESEG_ALLOW_SECONDARY",
    "MIN_CHORD_DURATION_S",
    "BASS_NOTE_MIN_CONFIDENCE",
)


def _parse_value(raw: str):
    low = raw.lower()
    if low in {"true", "false"}:
        return low == "true"
    try:
        if "." in raw or "e" in low:
            return float(raw)
        return int(raw)
    except ValueError:
        return raw


def _sync_ablation_defaults(ch: object) -> None:
    """Refresh def-time defaults that captured module constants at import.

    Python binds default argument values once at ``def`` time. Monkeypatching
    the module globals alone does not change:

    * ``merge_short_chords(min_duration=MIN_CHORD_DURATION_S)``
    * ``_reseg_candidate_pool(primary_only=RESEG_PRIMARY_ONLY,
      allow_secondary=RESEG_ALLOW_SECONDARY)``
    * ``resegment_long_holds(score_margin=CHROMA_SCORE_MARGIN,
      max_passes=RESEG_MAX_PASSES)``

    Runtime reads (``MIN_HOLD_BEATS``, ``LONG_HOLD_FORCE_RELABEL_S``,
    ``CHROMA_SCORE_MARGIN_*``, ``BASS_NOTE_MIN_CONFIDENCE``, etc.) already
    pick up ``setattr`` without this helper.
    """
    merge_fn = ch.merge_short_chords  # type: ignore[attr-defined]
    if merge_fn.__defaults__ is not None:
        # signature: (events, min_duration=MIN_CHORD_DURATION_S)
        merge_fn.__defaults__ = (ch.MIN_CHORD_DURATION_S,)  # type: ignore[attr-defined]

    pool_fn = ch._reseg_candidate_pool  # type: ignore[attr-defined]
    if pool_fn.__kwdefaults__ is not None:
        kw = dict(pool_fn.__kwdefaults__)
        kw["primary_only"] = ch.RESEG_PRIMARY_ONLY  # type: ignore[attr-defined]
        kw["allow_secondary"] = ch.RESEG_ALLOW_SECONDARY  # type: ignore[attr-defined]
        pool_fn.__kwdefaults__ = kw

    reseg_fn = ch.resegment_long_holds  # type: ignore[attr-defined]
    if reseg_fn.__kwdefaults__ is not None:
        kw = dict(reseg_fn.__kwdefaults__)
        kw["score_margin"] = ch.CHROMA_SCORE_MARGIN  # type: ignore[attr-defined]
        kw["max_passes"] = ch.RESEG_MAX_PASSES  # type: ignore[attr-defined]
        reseg_fn.__kwdefaults__ = kw


def apply_ablation(params: dict[str, object]) -> dict[str, object]:
    """Monkeypatch titan_chordpro.engines.chord.chordino module constants.

    Also rewrites function defaults that frozen the constants at import time
    so every key in ``ABLATION_KEYS`` actually takes effect on the detect path.
    """
    import titan_chordpro.engines.chord.chordino as ch

    previous: dict[str, object] = {}
    for key, val in params.items():
        if not hasattr(ch, key):
            raise SystemExit(f"unknown ablation key {key!r}; choose from {ABLATION_KEYS}")
        previous[key] = getattr(ch, key)
        setattr(ch, key, val)

    _sync_ablation_defaults(ch)
    return previous


def restore_ablation(previous: dict[str, object]) -> None:
    import titan_chordpro.engines.chord.chordino as ch

    for key, val in previous.items():
        setattr(ch, key, val)
    _sync_ablation_defaults(ch)


def load_stems(cache_id: str) -> dict:
    stems_path = CACHE_ROOT / cache_id / "stems.json"
    if not stems_path.is_file():
        raise SystemExit(f"missing {stems_path}")
    return json.loads(stems_path.read_text(encoding="utf-8"))


def events_to_jsonable(events) -> list[dict]:
    out: list[dict] = []
    for e in events:
        out.append(
            {
                "symbol": e.symbol,
                "timestamp": {"start": e.timestamp.start, "end": e.timestamp.end},
                "bass_note": e.bass_note,
                "confidence": e.confidence,
                "source_engine": e.source_engine,
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--youtube-id", default="", help="optional label for logs")
    p.add_argument(
        "--cache-id", default=None, help="cache dir under ~/.cache/titan-chordpro/cache/"
    )
    p.add_argument("--harmonic-mix", type=Path, default=None)
    p.add_argument("--bass-stem", type=Path, default=None)
    p.add_argument("--no-bass", action="store_true", help="skip bass stem even if available")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument(
        "--param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help=f"ablate module constant (repeatable). Keys: {', '.join(ABLATION_KEYS)}",
    )
    args = p.parse_args(argv)

    harmonic: Path | None = args.harmonic_mix
    bass: Path | None = None if args.no_bass else args.bass_stem

    if args.cache_id:
        cache_dir = CACHE_ROOT / args.cache_id
        if harmonic is None:
            harmonic = cache_dir / "harmonic_mix.wav"
        if bass is None and not args.no_bass:
            stems = load_stems(args.cache_id)
            bass_path = stems.get("bass")
            if bass_path:
                bass = Path(bass_path)

    if harmonic is None or not harmonic.is_file():
        raise SystemExit(f"harmonic_mix not found: {harmonic}")
    if bass is not None and not bass.is_file():
        print(f"warning: bass stem missing ({bass}); detecting without bass", file=sys.stderr)
        bass = None

    params: dict[str, object] = {}
    for item in args.param:
        if "=" not in item:
            raise SystemExit(f"--param expects KEY=VALUE, got {item!r}")
        k, v = item.split("=", 1)
        params[k.strip()] = _parse_value(v.strip())

    previous = apply_ablation(params) if params else {}
    try:
        from titan_chordpro.engines.chord.chordino import ChordinoEngine

        engine = ChordinoEngine()
        t0 = time.perf_counter()
        events = engine.detect(harmonic, bass_stem=bass)
        elapsed = time.perf_counter() - t0
    finally:
        if previous:
            restore_ablation(previous)

    payload = events_to_jsonable(events)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "youtube_id": args.youtube_id,
                "harmonic_mix": str(harmonic),
                "bass_stem": str(bass) if bass else None,
                "n_events": len(payload),
                "detect_s": round(elapsed, 2),
                "params": params,
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

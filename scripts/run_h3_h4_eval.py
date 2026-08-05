#!/usr/bin/env python3
"""Offline H3 (stem mix) + H4 (reseg param ablation) eval for chord explore.

Writes:
  /tmp/titan-chord-explore/hyp-H3/{variant}/{yt}.chords.json
  /tmp/titan-chord-explore/hyp-H3/metrics.json
  /tmp/titan-chord-explore/hyp-H4/{combo}/{yt}.chords.json
  /tmp/titan-chord-explore/hyp-H4/metrics.json

Uses current ChordinoEngine HEAD (H1b multipass + H2 bass gates).
Does not change product defaults.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path.cwd()))

from scripts.compare_chordpro_to_gt import (  # noqa: E402
    compare_sequences,
    extract_from_chords_json,
    load_gt,
)
from scripts.redetect_chords_from_cache import (  # noqa: E402
    apply_ablation,
    events_to_jsonable,
    restore_ablation,
)

ROOT = Path("/tmp/titan-chord-explore")
CACHE = Path.home() / ".cache" / "titan-chordpro" / "cache"
CORPUS = Path("chordpros.csv/songs.csv")
PY = Path(".venv-py312/bin/python")

SONGS = [
    {
        "youtube_id": "9yZt5ekdceI",
        "cache_id": "c54e57cd59ac8018",
        "title": "Ao olhar pra cruz",
    },
    {
        "youtube_id": "LvoYT0loqLQ",
        "cache_id": "cad6e201af7353c6",
        "title": "Teu santo nome",
    },
    {
        "youtube_id": "LL5Pak4zcuA",
        "cache_id": "cae47354d4d9133b",
        "title": "Jesus Tu És a Minha Vida",
    },
]

# H4: ≤6 combos including product baseline
H4_COMBOS = [
    {
        "id": "baseline",
        "label": "product defaults MIN_HOLD=3 MARGIN=0.01 FORCE=12",
        "params": {
            "MIN_HOLD_BEATS": 3.0,
            "CHROMA_SCORE_MARGIN": 0.01,
            "LONG_HOLD_FORCE_RELABEL_S": 12.0,
        },
    },
    {
        "id": "hold2",
        "label": "MIN_HOLD_BEATS=2 (more reseg)",
        "params": {
            "MIN_HOLD_BEATS": 2.0,
            "CHROMA_SCORE_MARGIN": 0.01,
            "LONG_HOLD_FORCE_RELABEL_S": 12.0,
        },
    },
    {
        "id": "hold4",
        "label": "MIN_HOLD_BEATS=4 (less reseg)",
        "params": {
            "MIN_HOLD_BEATS": 4.0,
            "CHROMA_SCORE_MARGIN": 0.01,
            "LONG_HOLD_FORCE_RELABEL_S": 12.0,
        },
    },
    {
        "id": "margin005",
        "label": "CHROMA_SCORE_MARGIN=0.005 (easier alt)",
        "params": {
            "MIN_HOLD_BEATS": 3.0,
            "CHROMA_SCORE_MARGIN": 0.005,
            "LONG_HOLD_FORCE_RELABEL_S": 12.0,
        },
    },
    {
        "id": "force8",
        "label": "LONG_HOLD_FORCE_RELABEL_S=8 (earlier force)",
        "params": {
            "MIN_HOLD_BEATS": 3.0,
            "CHROMA_SCORE_MARGIN": 0.01,
            "LONG_HOLD_FORCE_RELABEL_S": 8.0,
        },
    },
    {
        "id": "aggressive",
        "label": "hold2+margin005+force8",
        "params": {
            "MIN_HOLD_BEATS": 2.0,
            "CHROMA_SCORE_MARGIN": 0.005,
            "LONG_HOLD_FORCE_RELABEL_S": 8.0,
        },
    },
]


def _mono_load(path: Path, target_sr: int | None = None) -> tuple[np.ndarray, int]:
    y, sr = sf.read(str(path), always_2d=False)
    if y.ndim > 1:
        y = np.mean(y, axis=1)
    y = np.asarray(y, dtype=np.float32)
    if target_sr is not None and sr != target_sr:
        # simple resample via linear interp (stems should already be 44.1k)
        n = int(round(len(y) * target_sr / sr))
        x_old = np.linspace(0.0, 1.0, num=len(y), endpoint=False)
        x_new = np.linspace(0.0, 1.0, num=n, endpoint=False)
        y = np.interp(x_new, x_old, y).astype(np.float32)
        sr = target_sr
    return y, sr


def _mix_and_write(paths: list[Path], out: Path, gains: list[float] | None = None) -> Path:
    if out.is_file():
        return out
    assert paths
    gains = gains or [1.0] * len(paths)
    ys = []
    sr0 = None
    for p, g in zip(paths, gains, strict=True):
        y, sr = _mono_load(p)
        if sr0 is None:
            sr0 = sr
        elif sr != sr0:
            y, sr = _mono_load(p, target_sr=sr0)
        ys.append(y.astype(np.float64) * float(g))
    n = min(len(y) for y in ys)
    mix = np.zeros(n, dtype=np.float64)
    for y in ys:
        mix += y[:n]
    peak = np.max(np.abs(mix)) if n else 0.0
    if peak > 1.0:
        mix = mix / peak * 0.99
    out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out), mix.astype(np.float32), sr0, subtype="PCM_16")
    return out


def stem_paths(cache_id: str) -> dict[str, Path]:
    stems = json.loads((CACHE / cache_id / "stems.json").read_text(encoding="utf-8"))
    out = {}
    for k in ("other", "bass", "drums", "vocals"):
        p = Path(stems[k])
        if not p.is_file():
            raise FileNotFoundError(f"stem missing: {k} -> {p}")
        out[k] = p
    out["harmonic_mix"] = CACHE / cache_id / "harmonic_mix.wav"
    return out


def score_chords_json(youtube_id: str, chords_json: Path) -> dict:
    title, gt = load_gt(youtube_id, CORPUS)
    est, spans = extract_from_chords_json(chords_json)
    result = compare_sequences(gt, est, youtube_id=youtube_id, title=title, soft=True, spans=spans)
    d = {
        "youtube_id": result.youtube_id,
        "title": result.title,
        "n_gt": result.n_gt,
        "n_est": result.n_est,
        "match": result.match,
        "sub": result.sub,
        "delete": result.delete,
        "insert": result.insert,
        "match_rate": result.match_rate,
        "lcs": result.lcs,
        "lcs_rate": result.lcs_rate,
        "edit_distance": result.edit_distance,
        "normalized_edit": result.normalized_edit,
        "max_hold_s": result.max_hold_s,
        "hold_penalty": result.hold_penalty,
        "soft": result.soft,
    }
    # slash / bass stats
    data = json.loads(chords_json.read_text(encoding="utf-8"))
    n_bass = sum(1 for e in data if e.get("bass_note"))
    n_slash = sum(1 for e in data if e.get("symbol") and "/" in e["symbol"])
    d["n_bass_notes"] = n_bass
    d["n_native_slash"] = n_slash
    d["n_events"] = len(data)
    holds = sorted(
        (
            {
                "dur": round(float(e["timestamp"]["end"]) - float(e["timestamp"]["start"]), 2),
                "symbol": e.get("symbol"),
            }
            for e in data
        ),
        key=lambda x: -x["dur"],
    )[:5]
    d["top_holds"] = holds
    return d


def detect_to(harmonic: Path, bass: Path | None, out: Path, params: dict | None = None) -> float:
    from titan_chordpro.engines.chord.chordino import ChordinoEngine

    previous = apply_ablation(params) if params else {}
    try:
        engine = ChordinoEngine()
        t0 = time.perf_counter()
        events = engine.detect(harmonic, bass_stem=bass)
        elapsed = time.perf_counter() - t0
    finally:
        if previous:
            restore_ablation(previous)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(events_to_jsonable(events), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return elapsed


def run_h3() -> dict:
    out_root = ROOT / "hyp-H3"
    mix_root = ROOT / "hyp-H3" / "_mixes"

    # Per-song prepare mix paths
    song_variants: dict[str, dict[str, Path]] = {}
    for song in SONGS:
        stems = stem_paths(song["cache_id"])
        cid = song["cache_id"]
        yt = song["youtube_id"]
        mixes = {
            "other+bass": stems["harmonic_mix"],  # product control
            "other-only": _mix_and_write([stems["other"]], mix_root / f"{cid}_other-only.wav"),
            "other+bass+drums": _mix_and_write(
                [stems["other"], stems["bass"], stems["drums"]],
                mix_root / f"{cid}_other+bass+drums.wav",
            ),
            # same as other+bass+drums for demucs 4-stem (no separate "no-vocal" beyond this)
            "no-vocal": _mix_and_write(
                [stems["other"], stems["bass"], stems["drums"]],
                mix_root / f"{cid}_no-vocal.wav",
            ),
        }
        song_variants[yt] = {"bass": stems["bass"], **mixes}

    variant_names = ["other+bass", "other-only", "other+bass+drums", "no-vocal"]
    # other+bass+drums == no-vocal on 4-stem demucs; keep both keys for clarity,
    # detect once and symlink metrics later to save time.
    detect_variants = ["other+bass", "other-only", "other+bass+drums"]

    results_by_variant: dict[str, list[dict]] = {v: [] for v in variant_names}

    for song in SONGS:
        yt = song["youtube_id"]
        bass = song_variants[yt]["bass"]
        for variant in detect_variants:
            harmonic = song_variants[yt][variant]
            chords_out = out_root / variant / f"{yt}.chords.json"
            print(f"[H3] {variant} {yt} ...", flush=True)
            elapsed = detect_to(harmonic, bass, chords_out, params=None)
            m = score_chords_json(yt, chords_out)
            m["detect_s"] = round(elapsed, 2)
            m["variant"] = variant
            (out_root / variant / f"{yt}.metrics.json").write_text(
                json.dumps(m, indent=2, ensure_ascii=False) + "\n"
            )
            results_by_variant[variant].append(m)
            print(
                f"  match_rate={m['match_rate']:.4f} max_hold={m['max_hold_s']:.2f}s "
                f"n={m['n_events']} t={elapsed:.1f}s",
                flush=True,
            )

        # no-vocal: reuse other+bass+drums outputs (identical mix on 4-stem)
        src_v = "other+bass+drums"
        dst_v = "no-vocal"
        src_chords = out_root / src_v / f"{yt}.chords.json"
        dst_chords = out_root / dst_v / f"{yt}.chords.json"
        dst_chords.parent.mkdir(parents=True, exist_ok=True)
        if not dst_chords.exists() or dst_chords.stat().st_mtime < src_chords.stat().st_mtime:
            dst_chords.write_text(src_chords.read_text(encoding="utf-8"), encoding="utf-8")
        m = score_chords_json(yt, dst_chords)
        m["detect_s"] = next(
            x["detect_s"] for x in results_by_variant[src_v] if x["youtube_id"] == yt
        )
        m["variant"] = dst_v
        m["note"] = "identical to other+bass+drums on htdemucs 4-stem (no separate other residual)"
        (out_root / dst_v / f"{yt}.metrics.json").write_text(
            json.dumps(m, indent=2, ensure_ascii=False) + "\n"
        )
        results_by_variant[dst_v].append(m)

    ranking = []
    for v in variant_names:
        songs = results_by_variant[v]
        mean_mr = sum(s["match_rate"] for s in songs) / len(songs)
        mean_lcs = sum(s["lcs_rate"] for s in songs) / len(songs)
        ranking.append(
            {
                "variant": v,
                "mean_match_rate": mean_mr,
                "mean_lcs_rate": mean_lcs,
                "per_song": {s["youtube_id"]: s["match_rate"] for s in songs},
                "songs": songs,
            }
        )
    ranking.sort(key=lambda r: -r["mean_match_rate"])

    control = next(r for r in ranking if r["variant"] == "other+bass")
    promote_candidates = []
    for r in ranking:
        if r["variant"] == "other+bass":
            continue
        delta_mean = (r["mean_match_rate"] - control["mean_match_rate"]) * 100
        drops = []
        ok_no_drop = True
        for yt in control["per_song"]:
            d_pp = (r["per_song"][yt] - control["per_song"][yt]) * 100
            if d_pp < -10:
                ok_no_drop = False
            drops.append({"youtube_id": yt, "delta_pp": d_pp})
        promote = delta_mean >= 2.0 and ok_no_drop
        promote_candidates.append(
            {
                "variant": r["variant"],
                "delta_mean_pp": delta_mean,
                "no_song_drop_gt_10pp": ok_no_drop,
                "per_song_delta_pp": drops,
                "promote": promote,
            }
        )

    any_promote = any(c["promote"] for c in promote_candidates)
    payload = {
        "hypothesis": "H3",
        "label": "dual-path stems: other+bass vs other-only vs other+bass+drums/no-vocal",
        "baseline_commit_hint": "HEAD with H1b multipass + H2 bass gates",
        "control": "other+bass (harmonic_mix.wav)",
        "ranking": ranking,
        "promote_rule": "mean match ≥ control +2pp AND no song drops >10pp",
        "promote_eval": promote_candidates,
        "recommendation": (
            "PROMOTE mix change" if any_promote else "NO-PROMOTE: keep other+bass product default"
        ),
        "note_no_vocal": "On htdemucs 4-stem, no-vocal == other+bass+drums (scored as copy).",
    }
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "metrics.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return payload


def run_h4() -> dict:
    out_root = ROOT / "hyp-H4"
    results_by_combo: dict[str, list[dict]] = {}

    for combo in H4_COMBOS:
        cid = combo["id"]
        results_by_combo[cid] = []
        for song in SONGS:
            yt = song["youtube_id"]
            harmonic = CACHE / song["cache_id"] / "harmonic_mix.wav"
            stems = stem_paths(song["cache_id"])
            bass = stems["bass"]
            chords_out = out_root / cid / f"{yt}.chords.json"
            print(f"[H4] {cid} {yt} params={combo['params']} ...", flush=True)
            elapsed = detect_to(harmonic, bass, chords_out, params=combo["params"])
            m = score_chords_json(yt, chords_out)
            m["detect_s"] = round(elapsed, 2)
            m["combo"] = cid
            m["params"] = combo["params"]
            (out_root / cid / f"{yt}.metrics.json").write_text(
                json.dumps(m, indent=2, ensure_ascii=False) + "\n"
            )
            results_by_combo[cid].append(m)
            print(
                f"  match_rate={m['match_rate']:.4f} max_hold={m['max_hold_s']:.2f}s "
                f"n={m['n_events']} t={elapsed:.1f}s",
                flush=True,
            )

    ranking = []
    for combo in H4_COMBOS:
        cid = combo["id"]
        songs = results_by_combo[cid]
        mean_mr = sum(s["match_rate"] for s in songs) / len(songs)
        mean_lcs = sum(s["lcs_rate"] for s in songs) / len(songs)
        mean_hold = sum((s["max_hold_s"] or 0) for s in songs) / len(songs)
        ranking.append(
            {
                "combo": cid,
                "label": combo["label"],
                "params": combo["params"],
                "mean_match_rate": mean_mr,
                "mean_lcs_rate": mean_lcs,
                "mean_max_hold_s": mean_hold,
                "per_song": {s["youtube_id"]: s["match_rate"] for s in songs},
                "per_song_max_hold": {s["youtube_id"]: s["max_hold_s"] for s in songs},
                "songs": songs,
            }
        )
    ranking.sort(key=lambda r: (-r["mean_match_rate"], r["mean_max_hold_s"]))

    baseline = next(r for r in ranking if r["combo"] == "baseline")
    # load H2 / H1b external baselines if present
    external = {}
    for hyp in ("hyp-H2", "hyp-H1b", "hyp-H0"):
        p = ROOT / hyp / "metrics.json"
        if p.is_file():
            data = json.loads(p.read_text(encoding="utf-8"))
            means = data.get("means") or {}
            external[hyp] = {
                "mean_match_rate": means.get("match_rate_majmin")
                or means.get("match_rate")
                or (
                    sum(s["match_rate"] for s in data.get("songs", [])) / len(data["songs"])
                    if data.get("songs")
                    else None
                ),
                "per_song": {s["youtube_id"]: s["match_rate"] for s in data.get("songs", [])},
            }

    promote_eval = []
    for r in ranking:
        if r["combo"] == "baseline":
            continue
        delta_mean = (r["mean_match_rate"] - baseline["mean_match_rate"]) * 100
        ok_no_drop = True
        drops = []
        for yt in baseline["per_song"]:
            d_pp = (r["per_song"][yt] - baseline["per_song"][yt]) * 100
            if d_pp < -10:
                ok_no_drop = False
            drops.append({"youtube_id": yt, "delta_pp": d_pp})
        promote = delta_mean >= 2.0 and ok_no_drop
        promote_eval.append(
            {
                "combo": r["combo"],
                "delta_mean_pp_vs_baseline": delta_mean,
                "no_song_drop_gt_10pp": ok_no_drop,
                "per_song_delta_pp": drops,
                "promote": promote,
            }
        )

    any_promote = any(c["promote"] for c in promote_eval)
    best = ranking[0]
    payload = {
        "hypothesis": "H4",
        "label": "Chordino reseg param ablation via monkeypatch (≤6 combos)",
        "baseline": baseline,
        "ranking": ranking,
        "external_baselines": external,
        "promote_rule": "mean match ≥ baseline +2pp AND no song drops >10pp",
        "promote_eval": promote_eval,
        "best_combo": best["combo"],
        "recommendation": (
            f"PROMOTE params {best['params']}"
            if any_promote and best["combo"] != "baseline"
            else "NO-PROMOTE: keep product reseg constants"
        ),
    }
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "metrics.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return payload


def main() -> int:
    which = sys.argv[1:] if len(sys.argv) > 1 else ["h3", "h4"]
    if "h3" in which:
        print("=== H3 stem dual-path ===", flush=True)
        h3 = run_h3()
        print(
            json.dumps(
                {
                    "recommendation": h3["recommendation"],
                    "ranking": [
                        {
                            "variant": r["variant"],
                            "mean_match_rate": r["mean_match_rate"],
                            "per_song": r["per_song"],
                        }
                        for r in h3["ranking"]
                    ],
                },
                indent=2,
            ),
            flush=True,
        )
    if "h4" in which:
        print("=== H4 reseg param ablation ===", flush=True)
        h4 = run_h4()
        print(
            json.dumps(
                {
                    "recommendation": h4["recommendation"],
                    "best_combo": h4["best_combo"],
                    "ranking": [
                        {
                            "combo": r["combo"],
                            "mean_match_rate": r["mean_match_rate"],
                            "mean_max_hold_s": r["mean_max_hold_s"],
                            "per_song": r["per_song"],
                        }
                        for r in h4["ranking"]
                    ],
                },
                indent=2,
            ),
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

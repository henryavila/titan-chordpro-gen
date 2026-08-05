#!/usr/bin/env python3
"""Compare Titan chord sequences (or events) against human ChordPro GT.

Eval-only script for the chord-explore lane. Never hardcodes song IDs into
the product engine — IDs here are CLI inputs / corpus lookups.

Metrics (majmin-normalized by default):
  - match / sub / del / ins via Needleman–Wunsch (unit costs)
  - match_rate = match / n_gt
  - lcs_rate = LCS / n_gt
  - max_hold_s from timed events when available
  - soft match (optional): Am7≈Am, Dm7≈Dm collapse before majmin

Usage:
  .venv-py312/bin/python scripts/compare_chordpro_to_gt.py \\
      --est /tmp/titan-chord-explore/hyp-H0/9yZt5ekdceI.chordpro \\
      --youtube-id 9yZt5ekdceI

  .venv-py312/bin/python scripts/compare_chordpro_to_gt.py \\
      --chords-json ~/.cache/titan-chordpro/cache/<id>/chords.json \\
      --youtube-id 9yZt5ekdceI --json-out metrics.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from benchmarks.chordpro_parser import extract_chord_sequence  # noqa: E402
from benchmarks.corpus import load_corpus  # noqa: E402

_BRACKET_RE = re.compile(r"\[([^\[\]]+)\]")
_ROOT_RE = re.compile(r"^([A-G][#b]?)(.*)$")
_FLAT_TO_SHARP = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#"}


def normalize_majmin(symbol: str, *, soft: bool = True) -> str:
    """Collapse a Titan/human chord symbol to root+maj|min (or N)."""
    s = symbol.strip()
    if not s or s.upper() in {"N", "NC", "X"}:
        return "N"
    # Strip slash bass for majmin identity.
    if "/" in s:
        s = s.split("/", 1)[0].strip()
    m = _ROOT_RE.match(s)
    if not m:
        return s
    root, rest = m.group(1), m.group(2)
    root = _FLAT_TO_SHARP.get(root, root)
    rest_l = rest.lower()
    is_min = False
    if rest_l.startswith("min") or rest_l.startswith("m") and not rest_l.startswith("maj"):
        # m, min, m7, m9, min7 … but not maj / maj7
        if not rest_l.startswith("maj"):
            is_min = True
    # soft: treat 7/maj7/sus as major root quality already handled
    qual = "min" if is_min else "maj"
    return f"{root}:{qual}"


def extract_from_chordpro_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return extract_chord_sequence(text)


def extract_from_chords_json(path: Path) -> tuple[list[str], list[tuple[float, float]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"expected list in {path}")
    symbols: list[str] = []
    spans: list[tuple[float, float]] = []
    for item in data:
        sym = item.get("symbol")
        if not sym:
            continue
        # Prefer effective slash spelling for display; majmin ignores slash.
        bass = item.get("bass_note")
        if bass and "/" not in sym:
            display = f"{sym}/{bass}"
        else:
            display = sym
        symbols.append(display)
        ts = item.get("timestamp") or {}
        spans.append((float(ts.get("start", 0.0)), float(ts.get("end", 0.0))))
    return symbols, spans


def lcs_length(a: list[str], b: list[str]) -> int:
    n, m = len(a), len(b)
    if n == 0 or m == 0:
        return 0
    # O(min(n,m)) memory
    if m > n:
        a, b = b, a
        n, m = m, n
    prev = [0] * (m + 1)
    for i in range(1, n + 1):
        cur = [0] * (m + 1)
        ai = a[i - 1]
        for j in range(1, m + 1):
            if ai == b[j - 1]:
                cur[j] = prev[j - 1] + 1
            else:
                cur[j] = max(prev[j], cur[j - 1])
        prev = cur
    return prev[m]


def edit_alignment(gt: list[str], est: list[str]) -> tuple[int, int, int, int]:
    """Needleman–Wunsch with unit match/sub/indel costs.

    Returns (match, sub, delete, insert) where delete = missing in est,
    insert = extra in est.
    """
    n, m = len(gt), len(est)
    # dp cost
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    bt: list[list[str]] = [[""] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0] = i
        bt[i][0] = "D"
    for j in range(1, m + 1):
        dp[0][j] = j
        bt[0][j] = "I"
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if gt[i - 1] == est[j - 1]:
                best = dp[i - 1][j - 1]
                op = "M"
            else:
                best = dp[i - 1][j - 1] + 1
                op = "S"
            del_c = dp[i - 1][j] + 1
            if del_c < best:
                best = del_c
                op = "D"
            ins_c = dp[i][j - 1] + 1
            if ins_c < best:
                best = ins_c
                op = "I"
            dp[i][j] = best
            bt[i][j] = op
    match = sub = delete = insert = 0
    i, j = n, m
    while i > 0 or j > 0:
        op = bt[i][j] if i >= 0 and j >= 0 else ("D" if i > 0 else "I")
        if op == "M":
            match += 1
            i -= 1
            j -= 1
        elif op == "S":
            sub += 1
            i -= 1
            j -= 1
        elif op == "D":
            delete += 1
            i -= 1
        else:
            insert += 1
            j -= 1
    return match, sub, delete, insert


@dataclass
class CompareResult:
    youtube_id: str
    title: str
    n_gt: int
    n_est: int
    match: int
    sub: int
    delete: int
    insert: int
    match_rate: float
    lcs: int
    lcs_rate: float
    edit_distance: int
    normalized_edit: float
    max_hold_s: float | None
    hold_penalty: float
    soft: bool


def hold_penalty(max_hold_s: float | None, soft_cap: float = 12.0) -> float:
    if max_hold_s is None:
        return 1.0
    if max_hold_s <= soft_cap:
        return 1.0
    # decay: at 24s → 0.5, at 36s → ~0.33
    return soft_cap / max_hold_s


def compare_sequences(
    gt_raw: list[str],
    est_raw: list[str],
    *,
    youtube_id: str = "",
    title: str = "",
    soft: bool = True,
    spans: list[tuple[float, float]] | None = None,
) -> CompareResult:
    gt = [normalize_majmin(s, soft=soft) for s in gt_raw]
    est = [normalize_majmin(s, soft=soft) for s in est_raw]
    match, sub, delete, insert = edit_alignment(gt, est)
    n_gt = len(gt)
    n_est = len(est)
    lcs = lcs_length(gt, est)
    edit = sub + delete + insert
    denom = max(n_gt, n_est, 1)
    max_hold: float | None = None
    if spans:
        holds = [max(0.0, e - s) for s, e in spans]
        max_hold = max(holds) if holds else 0.0
    return CompareResult(
        youtube_id=youtube_id,
        title=title,
        n_gt=n_gt,
        n_est=n_est,
        match=match,
        sub=sub,
        delete=delete,
        insert=insert,
        match_rate=(match / n_gt) if n_gt else 0.0,
        lcs=lcs,
        lcs_rate=(lcs / n_gt) if n_gt else 0.0,
        edit_distance=edit,
        normalized_edit=edit / denom,
        max_hold_s=max_hold,
        hold_penalty=hold_penalty(max_hold),
        soft=soft,
    )


def load_gt(youtube_id: str, corpus: Path) -> tuple[str, list[str]]:
    songs, _ = load_corpus(corpus)
    song = next((s for s in songs if s.youtube_id == youtube_id), None)
    if song is None:
        raise SystemExit(f"youtube_id {youtube_id!r} not in corpus {corpus}")
    return song.title, extract_chord_sequence(song.chordpro)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--youtube-id", required=True)
    p.add_argument(
        "--corpus",
        type=Path,
        default=Path("chordpros.csv/songs.csv"),
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--est", type=Path, help="Predicted .chordpro file")
    src.add_argument("--chords-json", type=Path, help="Cached chords.json events")
    p.add_argument("--json-out", type=Path, default=None)
    p.add_argument("--no-soft", action="store_true")
    args = p.parse_args(argv)

    title, gt = load_gt(args.youtube_id, args.corpus)
    spans: list[tuple[float, float]] | None = None
    if args.est is not None:
        est = extract_from_chordpro_file(args.est)
    else:
        est, spans = extract_from_chords_json(args.chords_json)

    result = compare_sequences(
        gt,
        est,
        youtube_id=args.youtube_id,
        title=title,
        soft=not args.no_soft,
        spans=spans,
    )
    payload = asdict(result)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

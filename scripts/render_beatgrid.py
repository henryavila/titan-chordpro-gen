"""Render beat-grid diagnostic — replace chords with `|N` markers per beat.

Walks every cached `document.json`, then for each lyric line inserts
`|N` markers *before the word whose alignment timestamp the beat lands
on*. `N` is the 1-indexed position within the measure (1 = downbeat).
Beats falling in instrumental gaps (between lyric lines) are emitted on
their own standalone line so the operator can see whether BeatThis +
the meter detector are tracking the bars correctly, independent of
chord placement quality.

Run from repo root:
    .venv-py312/bin/python scripts/render_beatgrid.py
"""

from __future__ import annotations

import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

_SLUG_RE = re.compile(r"[^a-zA-Z0-9\-_]+")


def slugify(title: str) -> str:
    return _SLUG_RE.sub("-", title.strip()).strip("-") or "untitled"


def load_title_map(corpus_path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    with corpus_path.open() as f:
        for row in csv.DictReader(f):
            link = (row.get("external_link") or "").strip()
            title = (row.get("title") or "").strip()
            if not link or not title:
                continue
            if "v=" in link:
                yt = link.split("v=", 1)[1].split("&")[0]
            else:
                yt = link.rsplit("/", 1)[-1].split("?")[0]
            out[yt] = title
    return out


def beat_positions(beats: list[float], downbeats: list[int]) -> list[tuple[float, int]]:
    """For each beat, compute its 1-indexed position within its measure.

    Walks the beats in order. Whenever we hit a beat whose index is in
    `downbeats`, position resets to 1. Otherwise position increments.
    Tolerant of variable meter — if a measure has 3 or 5 beats between
    downbeats, the count reflects that.
    """
    if not beats:
        return []
    db = set(downbeats or [])
    out: list[tuple[float, int]] = []
    pos = 0
    for i, t in enumerate(beats):
        if i in db or i == 0:
            pos = 1
        else:
            pos += 1
        out.append((float(t), pos))
    return out


def _span_distance(t: float, w_start: float, w_end: float) -> float:
    """Distance from `t` to the closed interval [w_start, w_end]. 0 if inside."""
    if t < w_start:
        return w_start - t
    if t > w_end:
        return t - w_end
    return 0.0


# Held-vowel cap: words whose forced-alignment span exceeds
# LONG_WORD_THRESHOLD_S are treated as sustained notes — only the first
# beat inside the span becomes an inline marker (the note's attack);
# subsequent beats inside become orphans and drain inline / on a gap
# line. Short words still get up to 2 inline beats (e.g. `Andei`
# → `|1 An|2dei`).
LONG_WORD_THRESHOLD_S = 3.0
INSIDE_CAP_LONG = 1
INSIDE_CAP_SHORT = 2


def render_doc(doc: dict, human_title: str) -> str:
    """Render with nearest-word snap + inline split inside the word.

    For each beat: find the word_alignment whose [start, end] span is
    closest (distance-to-interval, not just to start). If that distance
    is <= tolerance (1 beat-gap), the marker attaches to that word in
    one of three slots:

      - `before` (beat earlier than word's onset) → `|1 An...`
      - `inside` (beat falls inside [start, end])  → `An|2dei`
            (rendered at the char-position proportional to where the
             beat lands inside the word's time span — approximates
             syllable-level split without a real syllabifier)
      - `after` (beat past word's end)              → `cego, |4`

    Beats whose nearest-word distance exceeds tolerance become
    "orphans" and emit on their own standalone line at the
    chronological gap between lyric lines.
    """
    bg = doc.get("beat_grid") or {}
    beats = bg.get("beats") or []
    downbeats = bg.get("downbeat_indices") or []
    meter = bg.get("meter") or "?"
    bpm = bg.get("bpm")

    pairs = beat_positions(beats, downbeats)

    avg_gap = (beats[-1] - beats[0]) / (len(beats) - 1) if len(beats) >= 2 else 1.0
    tolerance = avg_gap  # one full beat width either side

    # Collect every word_alignment with start/end and back-pointer.
    tokens: list[tuple[float, float, int, int, int, str]] = []
    for si, sec in enumerate(doc.get("sections", [])):
        for li, ln in enumerate(sec.get("lines", [])):
            if ln.get("line_type") != "lyric":
                continue
            for ti, w in enumerate(ln.get("word_alignments") or []):
                tokens.append(
                    (
                        float(w["timestamp"]["start"]),
                        float(w["timestamp"]["end"]),
                        si,
                        li,
                        ti,
                        str(w.get("text", "")),
                    )
                )

    # slot for each attached word
    attached: dict[
        tuple[int, int, int],
        dict[str, list],  # {"text": str, "before": [m], "inside": [(pos,m)], "after": [m]}
    ] = {}
    orphans: list[tuple[float, str]] = []

    inside_count: dict[tuple[int, int, int], int] = {}

    for t, pos in pairs:
        marker = f"|{pos}"
        if not tokens:
            orphans.append((t, marker))
            continue
        nearest = min(tokens, key=lambda tok: _span_distance(t, tok[0], tok[1]))
        d = _span_distance(t, nearest[0], nearest[1])
        if d > tolerance:
            orphans.append((t, marker))
            continue

        w_start, w_end, si, li, ti, w_text = nearest
        key = (si, li, ti)
        slot = attached.setdefault(key, {"text": w_text, "before": [], "inside": [], "after": []})
        if t < w_start:
            slot["before"].append(marker)
        elif t > w_end:
            # Beats past the word's right edge are routed to orphans
            # (instead of the word's "after" slot) so the inline drain
            # interleaves them in true chronological order with any
            # overflow-cap'd inside beats from the same word. With a
            # dedicated "after" slot they would render immediately
            # after the word's text, ahead of an earlier-in-time
            # overflow orphan.
            orphans.append((t, marker))
            continue
        else:
            span = w_end - w_start
            cap = INSIDE_CAP_LONG if span > LONG_WORD_THRESHOLD_S else INSIDE_CAP_SHORT
            if inside_count.get(key, 0) >= cap:
                orphans.append((t, marker))
                continue
            if span > 0 and w_text:
                proportion = (t - w_start) / span
                char_pos = int(round(proportion * len(w_text)))
                char_pos = max(0, min(len(w_text), char_pos))
            else:
                char_pos = 0
            slot["inside"].append((char_pos, marker))
            inside_count[key] = inside_count.get(key, 0) + 1

    def render_word(slot: dict) -> str:
        parts: list[str] = []
        for m in slot["before"]:
            parts.append(m + " ")
        text = slot["text"]
        if slot["inside"]:
            inside = sorted(slot["inside"], key=lambda x: x[0])
            cursor = 0
            buf: list[str] = []
            for cp, m in inside:
                if cp > cursor:
                    buf.append(text[cursor:cp])
                buf.append(m)
                cursor = cp
            if cursor < len(text):
                buf.append(text[cursor:])
            parts.append("".join(buf))
        else:
            parts.append(text)
        for m in slot["after"]:
            parts.append(" " + m)
        return "".join(parts)

    lines: list[str] = []
    lines.append(f"{{title: {human_title}}}")
    lines.append(
        f"{{meta: beats={len(beats)} downbeats={len(downbeats)} "
        f"meter={meter} bpm={bpm} tolerance={tolerance:.2f}s "
        f"orphans={len(orphans)}}}"
    )
    lines.append("")

    orph_iter = iter(orphans)
    next_orph = next(orph_iter, None)

    def drain_orphans_until(t_limit: float | None) -> None:
        nonlocal next_orph
        gap: list[str] = []
        while next_orph is not None and (t_limit is None or next_orph[0] < t_limit):
            gap.append(next_orph[1])
            next_orph = next(orph_iter, None)
        if gap:
            lines.append(" ".join(gap))

    for si, sec in enumerate(doc.get("sections", [])):
        stype = sec.get("type", "section")
        lines.append(f"{{start_of_{stype}}}")
        for li, ln in enumerate(sec.get("lines", [])):
            if ln.get("line_type") != "lyric":
                continue
            words = ln.get("word_alignments") or []
            if not words:
                lines.append(ln.get("text", ""))
                continue

            line_start = float(words[0]["timestamp"]["start"])
            drain_orphans_until(line_start)

            rendered_words: list[str] = []
            for ti, w in enumerate(words):
                key = (si, li, ti)
                if key in attached:
                    rendered_words.append(render_word(attached[key]))
                else:
                    rendered_words.append(str(w.get("text", "")))
                # Inline drain in chronological order: orphans before the
                # next word in this line emit between the two words.
                # For the final word in the line, drain orphans up to
                # one full measure (4 × beat-gap) past the word's end —
                # keeps short instrumental fills (e.g. `descanso. |2 |3
                # |4`) on the same line as the lyric they trail from,
                # without pulling multi-measure interludes inline.
                if ti + 1 < len(words):
                    inline_limit = float(words[ti + 1]["timestamp"]["start"])
                else:
                    inline_limit = float(w["timestamp"]["end"]) + 4.0 * tolerance
                while next_orph is not None and next_orph[0] < inline_limit:
                    rendered_words.append(next_orph[1])
                    next_orph = next(orph_iter, None)
            lines.append(" ".join(rendered_words))

        lines.append(f"{{end_of_{stype}}}")
        lines.append("")

    if next_orph is not None:
        lines.append("{c: trailing beats (after last section)}")
        drain_orphans_until(None)

    return "\n".join(lines) + "\n"


def main() -> int:
    cache_root = Path.home() / ".cache" / "titan-chordpro" / "cache"
    out_dir = Path("benchmarks/reports") / str(date.today()) / "beatgrid"
    out_dir.mkdir(parents=True, exist_ok=True)
    titles = load_title_map(Path("chordpros.csv/songs.csv"))

    # Purge previous run so the output set always matches the current cache.
    for stale in out_dir.glob("*.txt"):
        stale.unlink()

    rendered: list[tuple[str, Path]] = []
    skipped: list[Path] = []

    for cache_dir in sorted(cache_root.iterdir()):
        doc_path = cache_dir / "document.json"
        if not doc_path.exists():
            skipped.append(cache_dir)
            continue
        try:
            doc = json.loads(doc_path.read_text())
        except Exception as exc:  # noqa: BLE001
            print(f"  X {cache_dir.name}: json load failed - {exc}")
            skipped.append(cache_dir)
            continue

        youtube_id = ((doc.get("metadata") or {}).get("title") or "").strip()
        human_title = titles.get(youtube_id, youtube_id or cache_dir.name)
        out_path = out_dir / f"{slugify(human_title)}.txt"
        out_path.write_text(render_doc(doc, human_title))
        rendered.append((human_title, out_path))

    print(f"\n-> Rendered {len(rendered)} beat-grid diagnostic files to {out_dir}\n")
    for title, path in rendered:
        print(f"  - {title:35s} {path.stat().st_size:>6d} B  {path}")
    if skipped:
        print(f"\nSkipped {len(skipped)} cache dirs without document.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())

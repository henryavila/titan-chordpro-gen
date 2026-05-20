"""Render every cached document.json to .chordpro with the song title.

Walks ~/.cache/titan-chordpro/cache/*/document.json, loads each, looks up
the human title from chordpros.csv/songs.csv by youtube_id, then writes
<output_dir>/<slugified_title>.chordpro using the InlineSlashProfile.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from titan_chordpro.core.schemas import ChordProDocument  # noqa: E402
from titan_chordpro.writer.profiles.inline_slash import InlineSlashProfile  # noqa: E402

_SLUG_RE = re.compile(r"[^a-zA-Z0-9\-_]+")


def slugify(title: str) -> str:
    s = _SLUG_RE.sub("-", title.strip()).strip("-")
    return s or "untitled"


def load_title_map(corpus_path: Path) -> dict[str, str]:
    """Map youtube_id → human title from songs.csv."""
    out: dict[str, str] = {}
    with corpus_path.open() as f:
        for row in csv.DictReader(f):
            link = row.get("external_link", "")
            title = row.get("title", "").strip()
            if not link or not title:
                continue
            # Extract youtube id from URL (handles both youtu.be/ID and ...watch?v=ID).
            yt = link.rsplit("/", 1)[-1].split("?")[0].split("&")[0]
            if "v=" in link:
                # youtube.com/watch?v=ID form
                qs = link.split("v=", 1)[1]
                yt = qs.split("&")[0]
            out[yt] = title
    return out


def main() -> int:
    cache_root = Path.home() / ".cache" / "titan-chordpro" / "cache"
    out_dir = Path("benchmarks/reports") / str(date.today()) / "cifras"
    out_dir.mkdir(parents=True, exist_ok=True)
    titles = load_title_map(Path("chordpros.csv/songs.csv"))

    profile = InlineSlashProfile()
    rendered: list[tuple[str, Path]] = []
    skipped: list[Path] = []

    # First, purge any previously-written cifra files (both .chordpro and
    # .txt) — we want a clean, human-titled output set each run.
    for ext in ("*.chordpro", "*.txt"):
        for stale in out_dir.glob(ext):
            stale.unlink()

    for cache_dir in sorted(cache_root.iterdir()):
        doc_path = cache_dir / "document.json"
        if not doc_path.exists():
            skipped.append(cache_dir)
            continue
        try:
            doc = ChordProDocument.model_validate(json.loads(doc_path.read_text()))
        except Exception as exc:  # noqa: BLE001
            print(f"  X {cache_dir.name}: model_validate failed - {exc}")
            skipped.append(cache_dir)
            continue
        # The orchestrator stores audio_id (sha256 prefix) in metadata.title;
        # the human title lives in songs.csv, keyed by youtube_id.
        youtube_id = (doc.metadata.title or "").strip()
        human_title = titles.get(youtube_id, youtube_id or cache_dir.name)
        # User asked for .txt extension so the files render as plain text
        # in browsers / mail clients instead of triggering a download prompt.
        # ChordPro is plain text — extension is cosmetic only.
        out_path = out_dir / f"{slugify(human_title)}.txt"
        # Rewrite metadata.title with the human title before rendering so the
        # {t: ...} directive in the output matches the filename.
        doc.metadata.title = human_title
        out_path.write_text(profile.render(doc))
        rendered.append((human_title, out_path))

    print(f"\n-> Rendered {len(rendered)} .chordpro files to {out_dir}\n")
    for title, path in rendered:
        size = path.stat().st_size
        print(f"  - {title:35s} {size:>6d} B  {path}")
    if skipped:
        print(f"\nSkipped {len(skipped)} cache dirs without document.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""songs.csv loader for the iasdermelinda corpus.

Replaces the Phase A stub `export_corpus.py`. The corpus arrives as a
CSV (not a SQL dump) — Henry exported 155 rows from the iasdermelinda
catalog with three columns: title, external_link, chordpro. 151 rows
have a YouTube URL; 4 are skipped (logged via `skipped` return value).
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

_YT_ID_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"youtu\.be/([A-Za-z0-9_-]{11})"),
    re.compile(r"[?&]v=([A-Za-z0-9_-]{11})"),
    re.compile(r"youtube\.com/embed/([A-Za-z0-9_-]{11})"),
)

_REQUIRED_COLUMNS: frozenset[str] = frozenset({"title", "external_link", "chordpro"})


@dataclass(frozen=True)
class Song:
    """A single corpus row with a parsed YouTube ID."""

    title: str
    external_link: str
    chordpro: str
    youtube_id: str


def parse_youtube_id(url: str) -> str | None:
    """Extract the 11-char YouTube video ID from a URL, or return None.

    Handles the four URL shapes present in songs.csv:
      - https://youtu.be/<id>
      - https://www.youtube.com/watch?v=<id>
      - https://youtube.com/watch?v=<id>&t=...
      - https://www.youtube.com/embed/<id>

    Returns None for empty / non-YouTube URLs (Vimeo, plain text, etc.).
    """
    if not url:
        return None
    for pattern in _YT_ID_PATTERNS:
        m = pattern.search(url)
        if m:
            return m.group(1)
    return None


def load_corpus(csv_path: Path) -> tuple[list[Song], int]:
    """Load songs.csv → (songs, skipped_count).

    A row is skipped when:
      - external_link is empty, OR
      - external_link is not a recognizable YouTube URL.

    The skipped count is reported back so the validation report can
    log "loaded 151 / 155 (4 skipped: empty or non-YouTube external_link)".

    Raises FileNotFoundError if the CSV is missing.
    Raises ValueError if required columns (title, external_link, chordpro) are missing.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"corpus CSV not found: {csv_path}")

    songs: list[Song] = []
    skipped = 0

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("corpus CSV has no header row")
        present = set(reader.fieldnames)
        missing = _REQUIRED_COLUMNS - present
        if missing:
            raise ValueError(f"corpus CSV missing required column(s): {sorted(missing)}")

        for row in reader:
            url = (row.get("external_link") or "").strip()
            yt_id = parse_youtube_id(url)
            if yt_id is None:
                skipped += 1
                continue
            songs.append(
                Song(
                    title=row["title"].strip(),
                    external_link=url,
                    chordpro=row["chordpro"],
                    youtube_id=yt_id,
                )
            )

    return songs, skipped

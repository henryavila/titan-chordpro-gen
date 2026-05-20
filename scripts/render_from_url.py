"""Render a ChordPro file from a single YouTube URL.

One-shot wrapper around `benchmarks.audio_downloader.download_audio`
+ `titan_chordpro.orchestrator.transcribe` + the writer profile. Reuses
the per-stage disk cache under `~/.cache/titan-chordpro/`, so re-running
on the same URL is idempotent and near-instant.

Usage from repo root:
    .venv-py312/bin/python scripts/render_from_url.py <url_or_id>
    .venv-py312/bin/python scripts/render_from_url.py <url_or_id> \\
        --title "Ao olhar pra cruz" \\
        --output ao-olhar.chordpro \\
        --beatgrid

URL forms accepted:
    https://www.youtube.com/watch?v=ABC123XYZ_K
    https://youtu.be/ABC123XYZ_K
    ABC123XYZ_K   (raw 11-char id)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from benchmarks.audio_downloader import download_audio  # noqa: E402
from scripts.render_beatgrid import render_doc as render_beatgrid_doc  # noqa: E402
from scripts.render_chordpros import slugify  # noqa: E402
from titan_chordpro.orchestrator import transcribe  # noqa: E402

_MIN_YT_ID_LEN = 11


def extract_youtube_id(s: str) -> str:
    """Pull the 11-char video id out of a URL (or pass through a raw id)."""
    s = s.strip()
    if "v=" in s:
        s = s.split("v=", 1)[1]
    elif "/" in s:
        s = s.rsplit("/", 1)[-1]
    s = s.split("?")[0].split("&")[0]
    if len(s) < _MIN_YT_ID_LEN:
        raise ValueError(f"Could not extract a YouTube id (>= {_MIN_YT_ID_LEN} chars) from input")
    return s


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Download audio for a YouTube URL and render a .chordpro file."
    )
    p.add_argument("url", help="YouTube URL or 11-char video id")
    p.add_argument(
        "--title",
        default=None,
        help="Human title to embed in the {title:} directive. Default: youtube id.",
    )
    p.add_argument(
        "--language",
        default="pt",
        help="Transcription language code (default: pt).",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Where to write the .chordpro file. Default: ./<slug>.chordpro",
    )
    p.add_argument(
        "--profile",
        default="inline_slash",
        help="Writer profile (default: inline_slash). See `titan-chordpro --list-profiles`.",
    )
    p.add_argument(
        "--beatgrid",
        action="store_true",
        help="Also write `<slug>.beatgrid.txt` next to the chordpro for visual beat validation.",
    )
    args = p.parse_args(argv)

    youtube_id = extract_youtube_id(args.url)
    title = args.title or youtube_id
    slug = slugify(title)

    print(f"[1/3] Downloading audio for {youtube_id} ...")
    audio_path = download_audio(youtube_id)
    print(f"      -> {audio_path}")

    print("[2/3] Running pipeline (cache=True; first run ~5 min, re-run < 1 s) ...")
    doc = transcribe(audio_path, language=args.language, cache=True)
    doc.metadata.title = title

    out_path = args.output or Path(f"{slug}.chordpro").resolve()
    doc.write(out_path, profile=args.profile)
    print(f"[3/3] Wrote {out_path}")

    if args.beatgrid:
        beatgrid_path = out_path.with_suffix(".beatgrid.txt")
        beatgrid_path.write_text(render_beatgrid_doc(doc.model_dump(mode="json"), title))
        print(f"      Wrote {beatgrid_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

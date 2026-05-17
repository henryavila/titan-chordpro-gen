"""CLI entrypoint for titan-chordpro."""

from __future__ import annotations

import argparse
from pathlib import Path

from titan_chordpro.orchestrator import transcribe
from titan_chordpro.writer.profiles import PROFILES


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="titan-chordpro")
    parser.add_argument("audio", type=Path, nargs="?")
    parser.add_argument("--profile", default="inline_slash")
    parser.add_argument("--language", default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--keep-stems", action="store_true")
    parser.add_argument("--cache", action="store_true")
    parser.add_argument("--list-profiles", action="store_true")
    args = parser.parse_args(argv)

    if args.list_profiles:
        for name, profile in PROFILES.items():
            print(f"  {name:14s} {profile.description}")
        return 0

    if args.audio is None:
        parser.print_help()
        return 1

    doc = transcribe(
        args.audio,
        language=args.language,
        output_profile=args.profile,
        keep_stems=args.keep_stems,
        cache=args.cache,
    )
    out = args.output or args.audio.with_suffix(".chordpro")
    doc.write(out, profile=args.profile)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

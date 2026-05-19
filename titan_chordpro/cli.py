"""CLI entrypoint for titan-chordpro."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from titan_chordpro.factory import last_selection
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
    # Phase B additions:
    parser.add_argument(
        "--device",
        choices=("auto", "mps", "cuda", "cpu", "mock"),
        default="auto",
        help=(
            "Backend preference. 'auto' (default) probes hardware. 'mock' "
            "forces every engine to its mock implementation."
        ),
    )
    parser.add_argument(
        "--list-engines",
        action="store_true",
        help="After running the pipeline, print which engine ran each stage.",
    )
    parser.add_argument(
        "--whisper-model",
        default=None,
        choices=("tiny", "base", "small", "medium", "large-v2", "large-v3"),
        help=(
            "whisper.cpp model size. Default 'medium' (override via "
            "TITAN_WHISPER_MODEL env var). 'base' is faster but mistranscribes "
            "PT-BR vocals; 'large-v3' is slower but most accurate."
        ),
    )
    args = parser.parse_args(argv)

    if args.list_profiles:
        for name, profile in PROFILES.items():
            print(f"  {name:14s} {profile.description}")
        return 0

    if args.audio is None:
        parser.print_help()
        return 1

    force_mock = args.device == "mock"
    backend: str | None = args.device if args.device not in ("auto", "mock") else None

    engine_kwargs: dict[str, Any] = {}
    if args.whisper_model is not None:
        engine_kwargs["transcription_model_id"] = args.whisper_model

    doc = transcribe(
        args.audio,
        language=args.language,
        output_profile=args.profile,
        keep_stems=args.keep_stems,
        cache=args.cache,
        force_mock=force_mock,
        backend=backend,
        **engine_kwargs,
    )
    out = args.output or args.audio.with_suffix(".chordpro")
    doc.write(out, profile=args.profile)

    if args.list_engines:
        print("--- engine selections ---")
        for stage, info in last_selection().items():
            real_tag = "real" if info["real"] else "mock"
            print(f"  {stage:20s} {info['engine']:20s} [{real_tag}] ({info['reason']})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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
    # Phase C T71: validation harness + rich progress.
    parser.add_argument(
        "--validate",
        type=Path,
        default=None,
        metavar="CSV",
        help=(
            "Run the validation harness against the corpus CSV at this path "
            "(e.g. chordpros.csv/songs.csv). Mutually exclusive with audio."
        ),
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=151,
        help="Number of corpus rows to validate (use with --validate). Default 151.",
    )
    args = parser.parse_args(argv)

    if args.list_profiles:
        for name, profile in PROFILES.items():
            print(f"  {name:14s} {profile.description}")
        return 0

    if args.validate is not None:
        if args.audio is not None:
            parser.error("--validate is mutually exclusive with the audio positional argument")
        return _run_validate(args.validate, args.sample_size)

    if args.audio is None:
        parser.print_help()
        return 1

    force_mock = args.device == "mock"
    backend: str | None = args.device if args.device not in ("auto", "mock") else None

    engine_kwargs: dict[str, Any] = {}
    if args.whisper_model is not None:
        engine_kwargs["transcription_model_id"] = args.whisper_model

    doc = _transcribe_with_progress(
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


def _transcribe_with_progress(audio: Path, **kwargs: Any) -> Any:
    """Wrap single-song ``transcribe`` in a rich Progress spinner.

    Per-stage callbacks are a v0.2 polish; for Phase C T71 we show one
    indeterminate task for the full multi-stage run. ``rich`` is imported
    lazily so the library surface stays clean when CLI is unused.
    """
    try:
        from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
    except ImportError:
        return transcribe(audio, **kwargs)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        transient=True,
    ) as progress:
        progress.add_task(description=f"Transcribing {audio.name}", total=None)
        return transcribe(audio, **kwargs)


def _run_validate(csv_path: Path, sample_size: int) -> int:
    """Invoke the benchmarks validation harness with a rich Progress bar.

    Lazy-imports ``rich`` and ``benchmarks.*`` so a plain
    ``import titan_chordpro`` never pulls them in.
    """
    from rich.console import Console
    from rich.progress import BarColumn, Progress, TextColumn, TimeRemainingColumn

    from benchmarks.corpus import load_corpus
    from benchmarks.divergence_ranker import write_report
    from benchmarks.validation_runner import run_validation

    if not csv_path.exists():
        print(f"error: corpus CSV not found: {csv_path}", flush=True)
        return 2

    console = Console()
    songs, skipped = load_corpus(csv_path)
    sample = songs[: max(0, sample_size)]
    console.log(
        f"Loaded {len(songs)} songs ({skipped} skipped). Running validation on {len(sample)}."
    )

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task("Validating", total=len(sample))

        def on_song(song: Any, idx: int, total: int) -> None:
            title = getattr(song, "title", str(song))
            progress.update(
                task_id,
                description=f"Validating {str(title)[:30]}",
                completed=idx,
            )

        report = run_validation(
            sample,
            transcribe_fn=transcribe,
            skipped_from_corpus=skipped,
            progress=on_song,
        )
        progress.update(task_id, completed=len(sample))

    out_path = write_report(report, output_dir=Path("benchmarks/reports"), top_n=20)
    console.log(f"Mean WCSR-majmin: {report.mean_wcsr:.3f}")
    console.log(f"Report: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

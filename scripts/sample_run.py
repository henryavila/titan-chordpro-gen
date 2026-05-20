"""End-to-end pipeline run on 3 selected songs with all Phase C T70-iter2 fixes.

Selection is by youtube_id (not corpus row index) so the user controls
which songs run. Validates real chordino, whisper medium, sectioner
behavior on real Portuguese vocals, plus Beat F cross-detector diagnostic.
"""

from __future__ import annotations

import logging
import sys
import time
from datetime import date
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
sys.path.insert(0, str(Path.cwd()))

from benchmarks.corpus import load_corpus  # noqa: E402
from benchmarks.divergence_ranker import write_report  # noqa: E402
from benchmarks.validation_runner import run_validation  # noqa: E402
from titan_chordpro.orchestrator import transcribe  # noqa: E402

# Selected songs — pinned by youtube_id so order + identity are explicit.
_SELECTED_YT_IDS: tuple[str, ...] = (
    "9yZt5ekdceI",  # Ao olhar pra cruz
    "LvoYT0loqLQ",  # Teu santo nome
    "LL5Pak4zcuA",  # Jesus Tu És a Minha Vida (alt version — tUQH1xOlsbs is unavailable)
)


def main() -> int:
    corpus_path = Path("chordpros.csv/songs.csv")
    all_songs, skipped = load_corpus(corpus_path)
    by_id = {s.youtube_id: s for s in all_songs}
    missing = [yt for yt in _SELECTED_YT_IDS if yt not in by_id]
    if missing:
        print(f"FATAL: youtube_id(s) not in corpus: {missing}")
        return 2
    sample = [by_id[yt] for yt in _SELECTED_YT_IDS]
    print(f"\n→ Running {len(sample)} songs — REAL chordino + whisper medium\n")
    for i, s in enumerate(sample, 1):
        print(f"  {i}. {s.title}  ({s.youtube_id})")
    print()

    t0 = time.time()
    report = run_validation(
        sample,
        transcribe_fn=transcribe,
        skipped_from_corpus=skipped,
    )
    elapsed = time.time() - t0

    out_path = write_report(
        report, output_dir=Path("benchmarks/reports"), top_n=20, today=date.today()
    )
    print(f"\n→ Report: {out_path}")
    print(f"  Attempted   : {report.total_attempted}")
    print(f"  Metrics     : {len(report.metrics)}")
    print(f"  Failures    : {len(report.failures)}")
    print(f"  Mean WCSR   : {report.mean_wcsr:.3f}")
    print(f"  Elapsed     : {elapsed:.1f}s ({elapsed / 60:.1f} min)")
    print()
    for m in report.metrics:
        print(
            f"  • {m.song_title:35s}  WCSR={m.wcsr_majmin:.3f}  "
            f"beat_F_xlibrosa={m.beat_f_cross_librosa:.3f}  "
            f"beat_AMLt_xlibrosa={m.beat_amlt_cross_librosa:.3f}  "
            f"({m.num_chords_est} chords est)"
        )
    for f in report.failures:
        print(f"  ✗ {f.song_title}: {f.error}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

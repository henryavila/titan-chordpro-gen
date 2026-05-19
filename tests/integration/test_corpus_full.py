"""Full corpus run (Tier 2.5) — opt-in via env + marker.

Run with:
    BENCHMARKS_SAMPLE_SIZE=151 pytest -m corpus_full -v

This test is the actual measurement of Phase C. CI invokes it on a cron
(nightly.yml). It is gated behind a marker so `pytest -q` (the dev loop)
does not trigger it.
"""

from __future__ import annotations

import logging
import os
from datetime import date
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.corpus_full,
    pytest.mark.skipif(
        os.environ.get("BENCHMARKS_SAMPLE_SIZE") is None,
        reason="BENCHMARKS_SAMPLE_SIZE env var not set — opt-in only",
    ),
]

_log = logging.getLogger(__name__)


def test_full_corpus_validation() -> None:
    pytest.importorskip("yt_dlp")
    pytest.importorskip("mir_eval")
    pytest.importorskip("librosa")

    from benchmarks.corpus import load_corpus
    from benchmarks.divergence_ranker import write_report
    from benchmarks.validation_runner import run_validation
    from titan_chordpro.orchestrator import transcribe

    sample_size = int(os.environ["BENCHMARKS_SAMPLE_SIZE"])
    corpus_path = Path("chordpros.csv/songs.csv")
    if not corpus_path.exists():
        pytest.skip(f"corpus file missing: {corpus_path}")

    songs, skipped = load_corpus(corpus_path)
    sample = songs[:sample_size]
    _log.info("running validation over %d songs (skipped %d empty URLs)", len(sample), skipped)

    report = run_validation(
        sample,
        transcribe_fn=transcribe,
        skipped_from_corpus=skipped,
    )

    output_dir = Path("benchmarks/reports")
    out_path = write_report(report, output_dir=output_dir, top_n=20, today=date.today())
    _log.info("report written: %s", out_path)

    # Phase C target: mean WCSR-majmin >= 0.70 (spec §1683).
    # INFORMATIONAL on first nightly — Henry reviews manually at T70.
    if report.mean_wcsr < 0.70:
        _log.warning("mean WCSR %.3f below 0.70 target — see %s", report.mean_wcsr, out_path)

    assert report.total_attempted > 0

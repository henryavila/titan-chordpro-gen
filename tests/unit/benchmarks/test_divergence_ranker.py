"""Tests for benchmarks.divergence_ranker."""

from __future__ import annotations

from pathlib import Path

import pytest


def _metric(title: str, score: float):
    from benchmarks.validation_runner import SongMetric

    return SongMetric(
        song_title=title,
        youtube_id="x" * 11,
        wcsr_majmin=score,
        num_chords_ref=10,
        num_chords_est=10,
    )


class TestSeverityClassify:
    @pytest.mark.parametrize(
        "score,expected",
        [
            (0.30, "CRITICAL"),
            (0.49, "CRITICAL"),
            (0.50, "HIGH"),
            (0.69, "HIGH"),
            (0.70, "MEDIUM"),
            (0.84, "MEDIUM"),
            (0.85, "LOW"),
            (0.94, "LOW"),
            (0.95, "NEGLIGIBLE"),
            (1.0, "NEGLIGIBLE"),
        ],
    )
    def test_classify(self, score: float, expected: str) -> None:
        from benchmarks.divergence_ranker import classify

        assert classify(score).name == expected


class TestRankDivergences:
    def test_ranks_by_severity_then_score(self) -> None:
        from benchmarks.divergence_ranker import rank_divergences
        from benchmarks.validation_runner import ValidationReport

        report = ValidationReport(
            metrics=[
                _metric("A", 0.92),  # LOW
                _metric("B", 0.40),  # CRITICAL
                _metric("C", 0.65),  # HIGH
                _metric("D", 0.30),  # CRITICAL (worse than B)
            ],
        )
        ranked = rank_divergences(report, top_n=4)
        names = [d.song_title for d in ranked]
        assert names == ["D", "B", "C", "A"]

    def test_top_n_caps_result(self) -> None:
        from benchmarks.divergence_ranker import rank_divergences
        from benchmarks.validation_runner import ValidationReport

        report = ValidationReport(
            metrics=[_metric(f"S{i}", 0.30 + 0.05 * i) for i in range(20)],
        )
        assert len(rank_divergences(report, top_n=5)) == 5


class TestWriteReport:
    def test_writes_markdown(self, tmp_path: Path) -> None:
        from benchmarks.divergence_ranker import write_report
        from benchmarks.validation_runner import ValidationReport

        report = ValidationReport(metrics=[_metric("Hino", 0.42)])
        path = write_report(report, output_dir=tmp_path, top_n=10)
        assert path.exists()
        assert path.suffix == ".md"
        content = path.read_text()
        assert "Hino" in content
        assert "CRITICAL" in content

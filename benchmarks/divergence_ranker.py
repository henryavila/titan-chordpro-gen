"""Severity-based ranking of validation divergences + markdown report.

Spec §1579. Severity boundaries:
  CRITICAL    WCSR < 50%
  HIGH        50% <= WCSR < 70%
  MEDIUM      70% <= WCSR < 85%
  LOW         85% <= WCSR < 95%  — often the chart is wrong, not Titan
  NEGLIGIBLE  WCSR >= 95%
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from pathlib import Path

from benchmarks.validation_runner import ValidationReport


class Severity(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    NEGLIGIBLE = 5


def classify(wcsr: float) -> Severity:
    if wcsr < 0.50:
        return Severity.CRITICAL
    if wcsr < 0.70:
        return Severity.HIGH
    if wcsr < 0.85:
        return Severity.MEDIUM
    if wcsr < 0.95:
        return Severity.LOW
    return Severity.NEGLIGIBLE


@dataclass(frozen=True)
class Divergence:
    song_title: str
    youtube_id: str
    wcsr: float
    severity: Severity
    num_chords_ref: int
    num_chords_est: int


def rank_divergences(report: ValidationReport, top_n: int = 20) -> list[Divergence]:
    """Rank validation results worst-first."""
    divs = [
        Divergence(
            song_title=m.song_title,
            youtube_id=m.youtube_id,
            wcsr=m.wcsr_majmin,
            severity=classify(m.wcsr_majmin),
            num_chords_ref=m.num_chords_ref,
            num_chords_est=m.num_chords_est,
        )
        for m in report.metrics
    ]
    # Worst severity first (CRITICAL value=1 < HIGH=2 < ...), then worst score.
    divs.sort(key=lambda d: (d.severity.value, d.wcsr))
    return divs[:top_n]


def write_report(
    report: ValidationReport,
    output_dir: Path,
    top_n: int = 20,
    today: date | None = None,
) -> Path:
    """Write `<output_dir>/<YYYY-MM-DD>/top-divergences.md` and return its path."""
    day = today or date.today()
    out_root = output_dir / day.isoformat()
    out_root.mkdir(parents=True, exist_ok=True)
    out_path = out_root / "top-divergences.md"

    ranked = rank_divergences(report, top_n=top_n)
    lines: list[str] = [
        f"# Top {top_n} divergences — {day.isoformat()}",
        "",
        f"- Total attempted: **{report.total_attempted}**",
        f"- Successful metrics: **{len(report.metrics)}**",
        f"- Failures: **{len(report.failures)}**",
        f"- Skipped from corpus (empty URL / non-YouTube): **{report.skipped_from_corpus}**",
        f"- Mean WCSR-majmin: **{report.mean_wcsr:.3f}**",
        "",
        "| Rank | Severity | WCSR | Title | YouTube | Chords ref / est |",
        "|-----:|----------|-----:|-------|---------|------------------|",
    ]
    for i, d in enumerate(ranked, start=1):
        lines.append(
            f"| {i} | **{d.severity.name}** | {d.wcsr:.3f} | {d.song_title} | "
            f"`{d.youtube_id}` | {d.num_chords_ref} / {d.num_chords_est} |"
        )

    if report.failures:
        lines.extend(["", "## Failures (no metric computed)", ""])
        for f in report.failures:
            lines.append(f"- **{f.song_title}** (`{f.youtube_id}`) — {f.error}")

    out_path.write_text("\n".join(lines) + "\n")
    return out_path

"""Validation runner — full corpus pipeline + scoring.

Spec §1558. Loads the corpus, downloads audio, runs transcribe(cache=True),
scores each song via mir_eval, returns a ValidationReport. Failures are
captured as FailedMetric (not raised) so a single bad song doesn't kill
the whole nightly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from benchmarks.audio_downloader import default_cache_root, download_audio
from benchmarks.chordpro_parser import extract_chord_sequence, to_intervals_labels
from benchmarks.corpus import Song
from benchmarks.metrics import (
    chord_events_to_intervals,
    compute_beat_consistency_vs_librosa,
    compute_wcsr_majmin,
    to_mir_eval_chord,
)

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SongMetric:
    song_title: str
    youtube_id: str
    wcsr_majmin: float
    num_chords_ref: int
    num_chords_est: int
    # Beat consistency vs librosa (cross-detector diagnostic — NOT a gate).
    # See compute_beat_consistency_vs_librosa for rationale. Phase D will
    # replace with a true ground-truth beat F-measure on a labeled subset.
    beat_f_cross_librosa: float = 0.0
    beat_amlt_cross_librosa: float = 0.0


@dataclass(frozen=True)
class FailedMetric:
    song_title: str
    youtube_id: str
    error: str


@dataclass(frozen=True)
class ValidationReport:
    metrics: list[SongMetric] = field(default_factory=list)
    failures: list[FailedMetric] = field(default_factory=list)
    skipped_from_corpus: int = 0

    @property
    def mean_wcsr(self) -> float:
        if not self.metrics:
            return 0.0
        return sum(m.wcsr_majmin for m in self.metrics) / len(self.metrics)

    @property
    def total_attempted(self) -> int:
        return len(self.metrics) + len(self.failures)


def run_validation(
    songs: list[Song],
    *,
    transcribe_fn: Any,
    audio_cache_root: Path | None = None,
    titan_cache_root: Path | None = None,
    skipped_from_corpus: int = 0,
    progress: Any = None,
) -> ValidationReport:
    """Run validation over a list of Songs.

    Returns: ValidationReport with per-song metrics and failures.
    """
    audio_root = audio_cache_root if audio_cache_root is not None else default_cache_root()
    titan_root = (
        titan_cache_root
        if titan_cache_root is not None
        else (Path.home() / ".cache" / "titan-chordpro" / "cache")
    )

    metrics: list[SongMetric] = []
    failures: list[FailedMetric] = []

    for idx, song in enumerate(songs):
        if progress is not None:
            try:
                progress(song, idx, len(songs))
            except Exception:  # noqa: BLE001
                pass
        try:
            audio = download_audio(song.youtube_id, root=audio_root)
            doc = transcribe_fn(audio, language="pt", cache=True, cache_root=titan_root)

            # F-003 (Codex review): collect Titan chord events from the REAL
            # schema fields. LyricLine stores chords as chord_markers[].chord;
            # InstrumentalLine stores them in .chords.
            titan_chords: list[Any] = []
            for section in doc.sections:
                for line in section.lines:
                    if getattr(line, "line_type", None) == "lyric":
                        for marker in line.chord_markers:
                            titan_chords.append(marker.chord)
                    elif getattr(line, "line_type", None) == "instrumental":
                        for chord in line.chords:
                            titan_chords.append(chord)
            est_intervals, est_labels = chord_events_to_intervals(titan_chords)

            ref_seq = extract_chord_sequence(song.chordpro)
            if not ref_seq:
                raise ValueError("ground truth has no chords")
            ref_seq_mir = [to_mir_eval_chord(s) for s in ref_seq]

            # F-004 (Codex review): probe duration from the DOWNLOADED AUDIO
            # (not Titan's last interval).
            #
            # Phase C T70 iteration: switched from soundfile.info to
            # librosa.get_duration. soundfile bundles libsndfile which does
            # NOT support AAC/m4a (yt-dlp's default container). librosa
            # falls back to audioread+ffmpeg for codecs libsndfile rejects.
            import librosa

            duration = float(librosa.get_duration(path=str(audio)))
            if duration <= 0.0:
                raise ValueError(f"audio duration invalid for {audio}")
            if not est_intervals:
                raise ValueError("Titan produced no chord intervals")
            ref_intervals, ref_labels = to_intervals_labels(ref_seq_mir, duration)

            score = compute_wcsr_majmin(ref_intervals, ref_labels, est_intervals, est_labels)

            # Beat consistency diagnostic — derived from titan beat_grid on
            # the document (orchestrator always populates it). Skipped if
            # absent. NOT a gate — see metrics.compute_beat_consistency_vs_librosa.
            titan_beat_times: list[float] = []
            bg = getattr(doc, "beat_grid", None)
            if bg is not None:
                titan_beat_times = list(getattr(bg, "beats", []) or [])
            try:
                beat_consistency = compute_beat_consistency_vs_librosa(audio, titan_beat_times)
            except Exception as exc:  # noqa: BLE001
                _log.warning("beat consistency failed for %s: %s", song.youtube_id, exc)
                beat_consistency = {"f_measure": 0.0, "amlt": 0.0}

            metrics.append(
                SongMetric(
                    song_title=song.title,
                    youtube_id=song.youtube_id,
                    wcsr_majmin=score,
                    num_chords_ref=len(ref_seq),
                    num_chords_est=len(titan_chords),
                    beat_f_cross_librosa=beat_consistency["f_measure"],
                    beat_amlt_cross_librosa=beat_consistency["amlt"],
                )
            )
        except Exception as exc:  # noqa: BLE001
            _log.warning("validation failed for %s (%s): %s", song.title, song.youtube_id, exc)
            failures.append(
                FailedMetric(song_title=song.title, youtube_id=song.youtube_id, error=str(exc))
            )

    return ValidationReport(
        metrics=metrics,
        failures=failures,
        skipped_from_corpus=skipped_from_corpus,
    )

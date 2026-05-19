# titan_chordpro/engines/beat/beatthis.py
"""BeatThis (CPJKU 2024) — BeatTrackingEngine implementation.

Paper: https://github.com/CPJKU/beat_this
License: MIT
Backends: CUDA + MPS (Apple Silicon) + CPU fallback

The wrapper imports `beat_this.inference.File2Beats` lazily so that just
`import titan_chordpro.engines.beat.beatthis` never touches torch.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from titan_chordpro.core.exceptions import BeatTrackingError, EngineUnavailableError
from titan_chordpro.core.hardware import Backend, detect_backend
from titan_chordpro.core.schemas import BeatGrid, EngineInfo

_BEAT_THIS_VERSION_FALLBACK = "0.1.0"
_log = logging.getLogger(__name__)


def _load_audio2beats(backend: Backend) -> Any:
    """Import beat_this lazily; raise EngineUnavailableError if missing.

    Phase C T70 iter: use Audio2Beats (in-memory ndarray API) instead of
    File2Beats (which delegates to torchaudio.load → torchcodec → ffmpeg 4
    ABI; fails on Homebrew ffmpeg 8). The wrapper loads audio via librosa
    and passes the ndarray + sample rate to Audio2Beats.__call__.
    """
    try:
        from beat_this.inference import Audio2Beats
    except ImportError as exc:
        raise EngineUnavailableError(
            "beat_this is not installed; install with `pip install -e .[mac]` "
            "or `pip install beat-this`",
            engine="beat_this",
            cause=exc,
        ) from exc

    device = "cpu" if backend == "cpu" else backend
    return Audio2Beats(device=device)


class BeatThisEngine:
    """Conforms to BeatTrackingEngine Protocol (core.protocols).

    Args:
        backend: optional backend override; defaults to autodetect.
    """

    def __init__(self, backend: str | None = None) -> None:
        self._backend: Backend = detect_backend(prefer=backend)
        self._audio2beats = _load_audio2beats(self._backend)

    @property
    def info(self) -> EngineInfo:
        try:
            from beat_this import __version__ as version
        except ImportError:
            version = _BEAT_THIS_VERSION_FALLBACK
        return EngineInfo(
            name="beat_this",
            version=str(version),
            backend=self._backend,
        )

    @property
    def supports_variable_tempo(self) -> bool:
        return True

    @property
    def supports_meter_detection(self) -> bool:
        # BeatThis predicts beats + downbeats but does not infer time signature.
        return False

    def track(self, audio: Path) -> BeatGrid:
        """Run BeatThis on the audio file and return a BeatGrid.

        Phase C T70 iter: load via librosa (handles m4a/opus via ffmpeg
        fallback) and feed ndarray to Audio2Beats — bypasses torchaudio
        2.11+ torchcodec ffmpeg ABI mismatch.

        Raises BeatTrackingError when the model returns no beats.
        """
        try:
            import librosa

            # BeatThis expects 22050 Hz mono per beat_this.utils.load_audio.
            signal, sr = librosa.load(str(audio), sr=22050, mono=True)
            beats, downbeats = self._audio2beats(signal, sr)
        except Exception as exc:  # noqa: BLE001 — wrap third-party error
            raise BeatTrackingError(
                f"beat_this inference failed on {audio.name}",
                engine="beat_this",
                cause=exc,
            ) from exc

        beats_list = [float(b) for b in beats]
        downbeats_list = [float(d) for d in downbeats]

        if not beats_list:
            raise BeatTrackingError(
                f"beat_this returned empty beats list for {audio.name}",
                engine="beat_this",
            )

        # Map downbeats (seconds) to indices into the beats list. Use the
        # nearest-neighbor index for each downbeat — tolerates float drift.
        downbeat_indices = sorted({_nearest_index(beats_list, d) for d in downbeats_list})

        # Estimate global BPM as 60 / median inter-beat interval.
        intervals = [b2 - b1 for b1, b2 in zip(beats_list, beats_list[1:], strict=False)]
        if intervals:
            intervals.sort()
            median = intervals[len(intervals) // 2]
            bpm = 60.0 / median if median > 0 else 0.0
        else:
            bpm = 0.0

        if bpm <= 0:
            raise BeatTrackingError(
                f"beat_this produced non-positive bpm ({bpm}) for {audio.name}",
                engine="beat_this",
            )

        return BeatGrid(
            beats=beats_list,
            downbeat_indices=downbeat_indices,
            bpm=bpm,
            bpm_variable=False,  # set true only when variance > threshold (v0.2)
            meter=(4, 4),  # BeatThis does not predict; default 4/4
            source_engine="beat_this",
        )


def _nearest_index(sorted_values: list[float], target: float) -> int:
    """Return the index of the value in `sorted_values` nearest to `target`."""
    if not sorted_values:
        raise ValueError("sorted_values is empty")
    best_idx = 0
    best_dist = abs(sorted_values[0] - target)
    for i, v in enumerate(sorted_values[1:], start=1):
        d = abs(v - target)
        if d < best_dist:
            best_dist = d
            best_idx = i
    return best_idx

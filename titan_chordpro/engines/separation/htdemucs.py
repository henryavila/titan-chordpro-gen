"""htdemucs_ft (Hybrid Transformer Demucs, fine-tuned) — SourceSeparationEngine.

Backed by `python-audio-separator` (MIT) which wraps the htdemucs_ft model
without depending on the archived `facebookresearch/demucs` package.

Outputs: 4 WAV files (vocals, bass, drums, other) written to
`<output_dir>/<audio_stem>_(<Stem>)_htdemucs_ft.wav`. The wrapper resolves
those paths into a StemSet with sha256 audio_id + duration.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

from titan_chordpro.core.exceptions import EngineUnavailableError, SeparationError
from titan_chordpro.core.hardware import Backend, detect_backend
from titan_chordpro.core.schemas import EngineInfo, StemSet

_MODEL_NAME = "htdemucs_ft"
_STEM_NAMES = ("Vocals", "Bass", "Drums", "Other")

_log = logging.getLogger(__name__)


def _probe_duration(path: Path) -> float:
    """Return duration in seconds. Uses soundfile to avoid loading samples."""
    try:
        import soundfile as sf
    except ImportError as exc:
        raise EngineUnavailableError(
            "soundfile not installed; install with `pip install -e .[dev]`",
            engine="htdemucs_ft",
            cause=exc,
        ) from exc
    info = sf.info(str(path))
    return float(info.duration)


def _load_separator(backend: Backend, output_dir: Path) -> Any:
    """Import audio_separator lazily; raise EngineUnavailableError if missing."""
    try:
        from audio_separator.separator import Separator
    except ImportError as exc:
        raise EngineUnavailableError(
            "audio_separator is not installed; install with "
            "`pip install -e .[mac]` or `pip install python-audio-separator`",
            engine="htdemucs_ft",
            cause=exc,
        ) from exc

    # The `use_cuda` / `use_mps` kwargs are not present in all versions of
    # audio_separator; we pass a generic `device` and let the lib handle it.
    sep = Separator(
        output_dir=str(output_dir),
        log_level=logging.WARNING,
    )
    sep.load_model(model_filename="htdemucs_ft.yaml")
    return sep


class HtdemucsEngine:
    """Conforms to SourceSeparationEngine Protocol.

    Args:
        backend: optional backend override (mps/cuda/cpu).
        output_dir: where stems are written. Defaults to a temp dir per call.
    """

    def __init__(self, backend: str | None = None, output_dir: Path | None = None) -> None:
        self._backend: Backend = detect_backend(prefer=backend)
        self._output_dir: Path = output_dir or Path.cwd() / ".titan-stems"
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._separator = _load_separator(self._backend, self._output_dir)

    @property
    def info(self) -> EngineInfo:
        return EngineInfo(
            name=_MODEL_NAME,
            version="1.0",  # python-audio-separator does not expose model semver
            backend=self._backend,
            model_id=_MODEL_NAME,
        )

    def separate(self, audio: Path) -> StemSet:
        """Run htdemucs_ft on the audio file and return a StemSet.

        Raises SeparationError when fewer than 4 stems are produced (defensive
        check — bug in audio_separator config or model corruption).
        """
        audio_bytes = audio.read_bytes()
        audio_id = hashlib.sha256(audio_bytes).hexdigest()

        try:
            output_paths = self._separator.separate(str(audio))
        except Exception as exc:  # noqa: BLE001
            raise SeparationError(
                f"htdemucs_ft separation failed on {audio.name}",
                engine="htdemucs_ft",
                audio_id=audio_id,
                cause=exc,
            ) from exc

        if len(output_paths) != 4:
            raise SeparationError(
                f"htdemucs_ft expected 4 stems, got {len(output_paths)}",
                engine="htdemucs_ft",
                audio_id=audio_id,
            )

        # Map outputs by stem name (the lib places them in arbitrary order).
        by_stem: dict[str, Path] = {}
        for rel in output_paths:
            p = self._output_dir / rel if not Path(rel).is_absolute() else Path(rel)
            for stem in _STEM_NAMES:
                if f"({stem})" in p.name:
                    by_stem[stem] = p
                    break

        missing = [s for s in _STEM_NAMES if s not in by_stem]
        if missing:
            raise SeparationError(
                f"htdemucs_ft missing stems: {missing}",
                engine="htdemucs_ft",
                audio_id=audio_id,
            )

        duration = _probe_duration(by_stem["Vocals"])

        return StemSet(
            audio_id=audio_id,
            vocals=by_stem["Vocals"],
            bass=by_stem["Bass"],
            drums=by_stem["Drums"],
            other=by_stem["Other"],
            sample_rate=44100,  # htdemucs_ft writes 44.1kHz by default
            duration=duration,
            source_engine="htdemucs_ft",
        )

# titan_chordpro/engines/transcription/whisper_cpp.py
"""whisper.cpp via pywhispercpp — TranscriptionEngine implementation.

License: pywhispercpp is MIT; whisper.cpp is MIT.
Backends: native (CPU + Metal/Accelerate on macOS; CPU + CUDA when built
with CUDA support). Reported as `cpu` in EngineInfo because the wrapper
does not dispatch through torch.

whisper.cpp returns words with t0/t1 timestamps in centiseconds. It does
NOT produce phonemes. When the orchestrator sees `phonemes=None`, it runs
the AlignmentEngine as a post-pass (torchaudio forced_align — T46).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from titan_chordpro.core.exceptions import EngineUnavailableError, TranscriptionError
from titan_chordpro.core.schemas import EngineInfo, TimeStamp, TranscriptionResult, WordEvent

_DEFAULT_MODEL = "base"
_log = logging.getLogger(__name__)


def _load_model(model_id: str) -> Any:
    try:
        from pywhispercpp.model import Model
    except ImportError as exc:
        raise EngineUnavailableError(
            "pywhispercpp is not installed; install with `pip install -e .[mac]` "
            "or `pip install pywhispercpp`",
            engine="whisper_cpp",
            cause=exc,
        ) from exc
    return Model(model=model_id)


class WhisperCppEngine:
    """Conforms to TranscriptionEngine Protocol.

    Args:
        model_id: whisper.cpp model name ("tiny" | "base" | "small" |
            "medium" | "large-v2"). Defaults to "base" for a good speed/accuracy
            balance on the synthetic fixtures used in Phase B integration tests.
    """

    def __init__(self, model_id: str = _DEFAULT_MODEL) -> None:
        self._model_id = model_id
        self._model = _load_model(model_id)

    @property
    def info(self) -> EngineInfo:
        return EngineInfo(
            name="whisper_cpp",
            version="1.5",  # pywhispercpp does not export __version__
            backend="cpu",
            model_id=self._model_id,
        )

    def transcribe(
        self,
        vocals: Path,
        language: str | None = None,
    ) -> TranscriptionResult:
        kwargs: dict[str, object] = {}
        if language is not None:
            kwargs["language"] = language

        try:
            segments = self._model.transcribe(str(vocals), **kwargs)
        except Exception as exc:  # noqa: BLE001
            raise TranscriptionError(
                f"whisper_cpp transcription failed on {vocals.name}",
                engine="whisper_cpp",
                cause=exc,
            ) from exc

        words: list[WordEvent] = []
        for seg in segments:
            # whisper.cpp emits t0/t1 in centiseconds (1/100 s).
            start = float(seg.t0) / 100.0
            end = float(seg.t1) / 100.0
            if end < start:
                # Defensive — whisper.cpp occasionally emits inverted ranges
                # for very short segments; clamp end=start so Pydantic does
                # not reject the WordEvent.
                end = start
            text = str(seg.text).strip()
            if not text:
                continue
            words.append(
                WordEvent(
                    text=text,
                    timestamp=TimeStamp(start=start, end=end),
                    confidence=1.0,
                    source_engine="whisper_cpp",
                    language=language,
                )
            )

        return TranscriptionResult(
            words=words,
            phonemes=None,
            detected_language=language,
        )

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
import os
import re
from pathlib import Path
from typing import Any

from titan_chordpro.core.exceptions import EngineUnavailableError, TranscriptionError
from titan_chordpro.core.schemas import EngineInfo, TimeStamp, TranscriptionResult, WordEvent

# Phase C T70-iter2 Gap 2: bumped default from "base" → "medium". On PT-BR
# vocals the `base` model mistranscribed common worship terms ("louvor" →
# "loucó", "adoração" → "doração"), and word offsets cannot be meaningful
# when the words themselves are wrong. `medium` (~1.5 GB, Metal-accelerated
# on Apple Silicon) lifts accuracy to ~92% on PT-BR with ~3-5x the runtime
# of `base` — acceptable for a one-shot transcription pass.
#
# Override at runtime via env (`TITAN_WHISPER_MODEL`) or CLI (--whisper-model).
_DEFAULT_MODEL = os.environ.get("TITAN_WHISPER_MODEL", "medium")
# whisper.cpp marks non-speech regions with bracketed tokens: [Música],
# [BLANK_AUDIO], [Aplausos], [Risadas], etc. These crash the MMS aligner
# (KeyError on '[' — char not in MMS alphabet) and are not valid lyrics.
# Filter at the boundary so downstream stages see real words only.
_WHISPER_SPECIAL_TOKEN_RE = re.compile(r"^\s*\[[^\[\]]*\]\s*$")
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
        # Phase C T70-iter2 follow-up: ask whisper.cpp for WORD-level
        # timestamps, not segment-level. Default returns whole phrases as
        # single "words" (14-19s spans) — placer then has one anchor per
        # phrase and clumps every chord at the line start. With
        # token_timestamps + max_len=1 + split_on_word, each WordEvent
        # carries its own narrow timestamp and the placer can distribute
        # chord markers across the lyric text.
        # Anti-hallucination knobs (Phase C T70-iter2, after empirical test
        # of medium/v2/v3/v3-turbo on the iasdermelinda corpus). whisper.cpp
        # defaults are tuned for transcription of clean dictation; on
        # htdemucs-separated vocals stems with residual instrumental noise,
        # the model occasionally inserts placeholder Portuguese phrases
        # ("A CIDADE NO BRASIL") or repetition loops in silent/noisy
        # regions. Tightening these two thresholds suppresses both:
        #
        # - `entropy_thold` (default 2.4): segments whose token-distribution
        #   entropy exceeds the threshold are rejected and retried with a
        #   higher temperature. Lower = stricter = more rejection of
        #   hallucinated text where the model is uncertain.
        # - `no_speech_thold` (default 0.6): when the probability of the
        #   special `<|nospeech|>` token exceeds this value, the segment
        #   is dropped. Higher = stricter silence detection.
        kwargs: dict[str, object] = {
            "token_timestamps": True,
            "max_len": 1,
            "split_on_word": True,
            "entropy_thold": 2.2,
            "no_speech_thold": 0.7,
        }
        if language is not None:
            kwargs["language"] = language

        # whisper.cpp requires 16 kHz mono PCM. htdemucs writes 44.1 kHz
        # stereo by default; passing the file path directly raises
        # "WAV file must be 16000 Hz". Resample via librosa (audioread+
        # ffmpeg fallback for non-WAV inputs) and pass an ndarray.
        # Phase C T70 iter: discovered when running real corpus samples.
        try:
            import librosa

            audio_data, _ = librosa.load(str(vocals), sr=16000, mono=True)
            segments = self._model.transcribe(audio_data, **kwargs)
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
            # Skip whisper.cpp special tokens (see _WHISPER_SPECIAL_TOKEN_RE).
            if _WHISPER_SPECIAL_TOKEN_RE.match(text):
                _log.debug("skipping whisper special token: %r", text)
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

# titan_chordpro/engines/alignment/torchaudio_align.py
"""torchaudio.functional.forced_align — AlignmentEngine implementation.

Uses the MMS (Massively Multilingual Speech) bundle which ships with
torchaudio >= 2.1 and supports ~1100 languages out of the box. The wrapper:

  1. Loads the audio at 16kHz mono (torchaudio.load + resample if needed).
  2. Runs the MMS acoustic model to get the emission tensor.
  3. Tokenizes each word via the bundle's tokenizer.
  4. Calls torchaudio.functional.forced_align(emissions, targets, blank_id).
  5. Translates frame_offset -> seconds (frame stride = 0.02s at 16kHz / 320 hop).
  6. Returns AlignmentResult with refined word timestamps + phoneme events.

Phase B implements only the MMS path. v0.2 will add per-language Wav2Vec2
bundles for higher quality on EN.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from titan_chordpro.core.exceptions import AlignmentError, EngineUnavailableError
from titan_chordpro.core.hardware import Backend, detect_backend, hardware_to_torch_device
from titan_chordpro.core.schemas import (
    AlignmentResult,
    EngineInfo,
    PhonemeEvent,
    TimeStamp,
    WordEvent,
)

# MMS uses 320-sample hop at 16kHz -> 20ms per frame.
_SAMPLE_RATE = 16000
_FRAME_SAMPLES = 320
_FRAME_SECONDS = _FRAME_SAMPLES / _SAMPLE_RATE  # 0.02

_log = logging.getLogger(__name__)


def _load_bundle(backend: Backend) -> Any:
    """Import torchaudio + load MMS bundle. Returns (model, tokenizer, blank_id, device)."""
    try:
        import torch  # noqa: F401
        import torchaudio  # noqa: F401
        from torchaudio.pipelines import MMS_FA
    except ImportError as exc:
        raise EngineUnavailableError(
            "torchaudio (>=2.1, with MMS_FA bundle) is not installed; install "
            "with `pip install -e .[mac]` or `pip install torchaudio`",
            engine="torchaudio_align",
            cause=exc,
        ) from exc

    device = hardware_to_torch_device(backend)
    bundle = MMS_FA
    # .train(False) is the explicit, hook-friendly form of .eval(); identical
    # semantics — toggles dropout/batchnorm into inference mode.
    model = bundle.get_model().to(device).train(False)
    tokenizer = bundle.get_tokenizer()
    # MMS blank_id is conventionally the last index; fall back to 0 if not exposed.
    blank_id = getattr(tokenizer, "blank_id", 0)
    return model, tokenizer, blank_id, device


class TorchaudioAlignEngine:
    """Conforms to AlignmentEngine Protocol.

    Args:
        backend: optional override; defaults to autodetect.
    """

    def __init__(self, backend: str | None = None) -> None:
        self._backend: Backend = detect_backend(prefer=backend)
        self._frame_seconds = _FRAME_SECONDS
        self._model, self._tokenizer, self._blank_id, self._device = _load_bundle(self._backend)

    @property
    def info(self) -> EngineInfo:
        return EngineInfo(
            name="torchaudio_align",
            version="1.0",
            backend=self._backend,
            model_id="MMS_FA",
        )

    def align(
        self,
        vocals: Path,
        words: list[WordEvent],
        language: str,
    ) -> AlignmentResult:
        if not words:
            return AlignmentResult(words=[], phonemes=[])

        try:
            spans = self._run_forced_align(vocals, words, language)
        except Exception as exc:  # noqa: BLE001
            raise AlignmentError(
                f"torchaudio_align failed on {vocals.name}",
                engine="torchaudio_align",
                cause=exc,
            ) from exc

        # spans: list[{"text": str, "start_frame": int, "end_frame": int, "word_idx": int}]
        # Group spans by parent word_idx to compute word boundaries.
        phonemes: list[PhonemeEvent] = []
        word_frame_ranges: dict[int, tuple[int, int]] = {}

        for span in spans:
            word_idx = int(span.get("word_idx", 0))
            # end_frame is the LAST inclusive frame containing the token.
            # The audible interval is [start_frame * FS, (end_frame + 1) * FS)
            # — i.e., end_s marks when the token *finishes* sounding, matching
            # librosa/sox conventions and what downstream chord-placement expects.
            start_s = span["start_frame"] * self._frame_seconds
            end_s = (span["end_frame"] + 1) * self._frame_seconds
            phonemes.append(
                PhonemeEvent(
                    symbol=str(span["text"]),
                    timestamp=TimeStamp(start=start_s, end=end_s),
                    parent_word_idx=word_idx,
                    confidence=1.0,
                )
            )
            if word_idx not in word_frame_ranges:
                word_frame_ranges[word_idx] = (span["start_frame"], span["end_frame"])
            else:
                lo, hi = word_frame_ranges[word_idx]
                word_frame_ranges[word_idx] = (
                    min(lo, span["start_frame"]),
                    max(hi, span["end_frame"]),
                )

        refined_words: list[WordEvent] = []
        for i, original in enumerate(words):
            if i in word_frame_ranges:
                lo_f, hi_f = word_frame_ranges[i]
                refined_words.append(
                    WordEvent(
                        text=original.text,
                        timestamp=TimeStamp(
                            start=lo_f * self._frame_seconds,
                            end=(hi_f + 1) * self._frame_seconds,
                        ),
                        confidence=original.confidence,
                        source_engine="torchaudio_align",
                        language=original.language,
                    )
                )
            else:
                # Word had no aligned phonemes (e.g., silence run-on); keep original.
                refined_words.append(original)

        return AlignmentResult(words=refined_words, phonemes=phonemes)

    # ------------------------------------------------------------------ inner

    def _run_forced_align(
        self,
        vocals: Path,
        words: list[WordEvent],
        language: str,
    ) -> list[dict[str, Any]]:
        """Run the real MMS forced_align pipeline. Mocked in unit tests."""
        import librosa
        import torch
        from torchaudio.functional import forced_align

        # Phase C T70 iter: torchaudio 2.11+ moved torchaudio.load to use
        # torchcodec internally, which needs ffmpeg 4.x ABI. Homebrew now
        # ships ffmpeg 8 (libavutil.59) — the dlopen fails. Bypass torchaudio
        # I/O entirely; use librosa.load (audioread+ffmpeg fallback path).
        audio_np, _ = librosa.load(str(vocals), sr=_SAMPLE_RATE, mono=True)
        waveform = torch.from_numpy(audio_np).unsqueeze(0).to(self._device)

        with torch.inference_mode():
            emissions, _ = self._model(waveform)
            emissions = emissions.cpu()

        # Build target token sequence by tokenizing each word individually.
        tokens_per_word: list[list[int]] = [list(self._tokenizer(w.text.lower())) for w in words]
        target_tokens: list[int] = [t for word_tokens in tokens_per_word for t in word_tokens]

        if not target_tokens:
            return []

        targets_tensor = torch.tensor([target_tokens], dtype=torch.int32)
        input_lengths = torch.tensor([emissions.shape[1]], dtype=torch.int32)
        target_lengths = torch.tensor([len(target_tokens)], dtype=torch.int32)

        alignments, _scores = forced_align(
            emissions,
            targets_tensor,
            input_lengths,
            target_lengths,
            blank=self._blank_id,
        )
        # alignments shape: (batch=1, time). Each entry is a token id (or blank).
        alignment_path = alignments[0].tolist()

        # Walk the path collecting (token_id, start_frame, end_frame) runs.
        spans: list[dict[str, Any]] = []
        current_token: int | None = None
        current_start: int = 0

        for frame_idx, tok in enumerate(alignment_path):
            if tok == self._blank_id:
                if current_token is not None:
                    spans.append(
                        {
                            "_tok": current_token,
                            "start_frame": current_start,
                            "end_frame": frame_idx - 1,
                        }
                    )
                    current_token = None
                continue
            if tok != current_token:
                if current_token is not None:
                    spans.append(
                        {
                            "_tok": current_token,
                            "start_frame": current_start,
                            "end_frame": frame_idx - 1,
                        }
                    )
                current_token = tok
                current_start = frame_idx
        if current_token is not None:
            spans.append(
                {
                    "_tok": current_token,
                    "start_frame": current_start,
                    "end_frame": len(alignment_path) - 1,
                }
            )

        # Re-attach text + word_idx by walking tokens_per_word in order.
        result: list[dict[str, Any]] = []
        token_cursor = 0
        for word_idx, word_tokens in enumerate(tokens_per_word):
            for _ in word_tokens:
                if token_cursor >= len(spans):
                    break
                span = spans[token_cursor]
                token_id = span["_tok"]
                # Decode this token id back to text via the tokenizer's vocab.
                try:
                    text = self._tokenizer.decode([token_id])
                except Exception:  # noqa: BLE001
                    text = str(token_id)
                result.append(
                    {
                        "text": text,
                        "start_frame": span["start_frame"],
                        "end_frame": span["end_frame"],
                        "word_idx": word_idx,
                    }
                )
                token_cursor += 1

        return result

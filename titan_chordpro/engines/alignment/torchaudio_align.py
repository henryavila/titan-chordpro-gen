# titan_chordpro/engines/alignment/torchaudio_align.py
"""torchaudio.functional.forced_align — AlignmentEngine implementation.

Uses the MMS (Massively Multilingual Speech) bundle which ships with
torchaudio >= 2.1 and supports ~1100 languages out of the box.

Phase C T70 iter — chunked emissions + global Viterbi:
  1. Loads audio at 16kHz mono via librosa (ffmpeg fallback for non-WAV).
  2. Splits waveform into 30s windows with 2s context on each side; runs
     the MMS encoder per chunk (peak memory ~1 GiB vs 7-11 GiB single-shot).
  3. Crops context-region emission frames from each chunk's output.
  4. Concatenates emissions into a single global tensor (T_total, vocab).
  5. Runs ONE torchaudio.functional.forced_align over the stitched
     emissions — Viterbi decision is global, so alignment quality inside
     chunk interiors is mathematically equivalent to single-shot.
  6. Translates frame_offset -> seconds (frame stride = 0.02s at 16kHz / 320 hop).
  7. Returns AlignmentResult with refined word timestamps + phoneme events.

References:
- HuggingFace blog "Making ASR work on large files with Wav2Vec2"
  (canonical chunk + stride + drop-sides derivation for CTC).
- MahmoudAshraf97/ctc-forced-aligner — production library, MIT.
- IRCAM/MDPI Appl. Sci. 13/3/1854 — quantifies CTC alignment error
  (50ms speech / 120ms singing voice) on DALI.
"""

from __future__ import annotations

import logging
import math
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

# MMS uses 320-sample hop at 16kHz -> 20ms per frame -> 50 fps.
_SAMPLE_RATE = 16000
_FRAME_SAMPLES = 320
_FRAME_SECONDS = _FRAME_SAMPLES / _SAMPLE_RATE  # 0.02

# Chunked emissions parameters (Phase C T70 iter). 30 s window matches the
# ctc-forced-aligner default; 2 s context is ~100 frames at 50 fps, vastly
# larger than wav2vec2's ~25 ms receptive field — absorbs all edge effects.
_CHUNK_WINDOW_SEC = 30.0
_CHUNK_CONTEXT_SEC = 2.0

_log = logging.getLogger(__name__)


def _sanitize_for_mms(text: str) -> str:
    """Strip characters MMS_FA's tokenizer doesn't accept (whitespace,
    punctuation, brackets, digits). Preserves Unicode letters including
    PT-BR accents (á, é, ã, õ, ç, ...) since the multilingual MMS
    tokenizer covers them.

    Phase C T70 iter: whisper.cpp returns multi-word segments with spaces
    and occasional punctuation; tokenizing those directly raises KeyError
    on ' ' or ',' or '.'. Sanitizing at the alignment-wrapper boundary
    keeps the upstream transcription engine's API unchanged.
    """
    return "".join(c for c in text if c.isalpha())


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

    def _generate_emissions(
        self,
        waveform_1d: Any,
        window_sec: float = _CHUNK_WINDOW_SEC,
        context_sec: float = _CHUNK_CONTEXT_SEC,
        batch_size: int = 1,
    ) -> Any:
        """Chunked encoder forward with global emissions stitching.

        Splits a 1-D mono waveform into windows of `window_sec` with
        `context_sec` of overlap on each side. Runs the MMS encoder on
        each chunk independently, crops the context-region emission
        frames, and concatenates the inner frames into a single global
        emissions tensor with shape (1, T_total, vocab).

        Algorithm follows HuggingFace's canonical chunk+stride+drop-sides
        recipe for CTC + MMS. The downstream `forced_align` then runs a
        SINGLE global Viterbi on the stitched emissions — alignment
        decisions are mathematically equivalent to single-shot for chunk
        interiors. Edge artifacts are bounded by wav2vec2's ~25 ms
        receptive field, vastly smaller than the 2 s context.

        Args:
            waveform_1d: 1-D float32 tensor of mono audio at 16 kHz.
            window_sec: inner-window duration per chunk (default 30 s).
            context_sec: context overlap on each side (default 2 s).
            batch_size: chunks to process per forward (1 = lowest memory).

        Returns:
            Tensor of shape (1, T_total, vocab) — batched global emissions
            ready to pass to torchaudio.functional.forced_align.
        """
        import torch

        n = int(waveform_1d.size(0))
        window_samples = int(window_sec * _SAMPLE_RATE)
        context_samples = int(context_sec * _SAMPLE_RATE)
        context_frames = int(round(context_sec / _FRAME_SECONDS))  # 100 frames @ 50fps

        # Short audio (<= window): single-shot is cheap and avoids the
        # extra padding bookkeeping. Same path the original implementation
        # took, but now isolated.
        if n <= window_samples:
            with torch.inference_mode():
                em, _ = self._model(waveform_1d.unsqueeze(0).to(self._device))
            return em.cpu()

        # Pad so audio length is a multiple of window_samples. Add context
        # on both sides so each chunk sees [context | window | context].
        extension = math.ceil(n / window_samples) * window_samples - n
        padded = torch.nn.functional.pad(
            waveform_1d, (context_samples, context_samples + extension)
        )
        chunk_len = window_samples + 2 * context_samples
        # unfold(dim, size, step) → (num_chunks, chunk_len). step=window
        # ensures inner regions tile exactly with no inner overlap; only
        # the context regions overlap between consecutive chunks.
        chunks = padded.unfold(0, chunk_len, window_samples)

        emissions_list = []
        with torch.inference_mode():
            for i in range(0, int(chunks.size(0)), batch_size):
                batch = chunks[i : i + batch_size].to(self._device)
                em_batch, _ = self._model(batch)
                emissions_list.append(em_batch.cpu())
        emissions = torch.cat(emissions_list, dim=0)
        # emissions shape: (num_chunks, frames_per_chunk, vocab)

        # Crop the context-region frames from each chunk. context_frames
        # at start AND end; the remaining inner frames tile to form a
        # contiguous global emissions sequence.
        if context_frames > 0:
            emissions = emissions[:, context_frames:-context_frames, :]

        # Flatten chunks into a single global sequence.
        emissions = emissions.flatten(0, 1)  # (num_chunks * frames_inner, vocab)

        # Trim the right-side extension we padded earlier (in frames).
        extension_frames = int(round((extension / _SAMPLE_RATE) / _FRAME_SECONDS))
        if extension_frames > 0:
            emissions = emissions[:-extension_frames]

        # Add the batch dim back so forced_align sees (1, T, vocab).
        return emissions.unsqueeze(0)

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
        waveform_1d = torch.from_numpy(audio_np)

        # Phase C T70 iter: chunked emissions + global Viterbi. Single-shot
        # forward on 4-5 min audio exhausts 11+ GiB of MPS activations.
        emissions = self._generate_emissions(waveform_1d)

        # Build target token sequence by tokenizing each word individually.
        # Phase C T70 iter: whisper.cpp returns multi-word segments ("Tudo
        # que há de bom em mim") and the MMS tokenizer has no entry for
        # space/punctuation → KeyError. Sanitize each segment by stripping
        # characters outside the tokenizer's alphabet before tokenizing.
        # The aligner still receives one entry per WordEvent (preserving
        # the word_idx contract), but multi-word segments collapse to
        # their letter-only form for tokenization purposes — alignment
        # boundaries land on segment endpoints, not internal word breaks.
        tokens_per_word: list[list[int]] = []
        for w in words:
            sanitized = _sanitize_for_mms(w.text.lower())
            if not sanitized:
                tokens_per_word.append([])
                continue
            try:
                tokens_per_word.append(list(self._tokenizer(sanitized)))
            except KeyError as exc:
                # Belt-and-suspenders: skip a word whose surviving chars
                # somehow still hit a vocab miss, rather than crash the run.
                _log.warning(
                    "tokenizer rejected %r (sanitized to %r); skipping (cause=%s)",
                    w.text,
                    sanitized,
                    exc,
                )
                tokens_per_word.append([])
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

"""orchestrator.py — transcribe() master pipeline.

Wires all 6 engine Protocols via factory.py. Never imports torch/whisper/etc.
All ML is behind Protocols; Phase A uses mock engines.

Phase C: cache=True wiring (T66). When the caller opts into the cache,
each stage reads from <cache_root>/<audio_id>/<stage>.json if present,
otherwise runs the engine and writes the result back. Cache writes are
atomic (see core/cache.py). Cache-miss falls back to the live engine —
corruption is silently treated as miss.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from titan_chordpro import factory
from titan_chordpro.core.cache import Stage, dump_stage, load_stage
from titan_chordpro.core.hardware import release_gpu_memory
from titan_chordpro.core.schemas import (
    AlignmentResult,
    BeatGrid,
    ChordEvent,
    ChordProDocument,
    EngineInfo,
    EngineRegistry,
    InstrumentalLine,
    LyricLine,
    Metadata,
    Provenance,
    Section,
    StageConfidence,
    StemSet,
    SyllableEvent,
    TimeStamp,
    TranscriptionResult,
    WordEvent,
    aggregate_stage_confidence,
)
from titan_chordpro.fusion import (
    melisma as melisma_module,
)
from titan_chordpro.fusion import (
    placer,
    sectioner,
    stress,
)
from titan_chordpro.fusion.melisma import Melisma


def transcribe(
    audio: Path,
    language: str | None = None,
    output_profile: str = "inline_slash",
    keep_stems: bool = False,
    cache: bool = False,
    cache_root: Path | None = None,
    **engine_overrides: Any,
) -> ChordProDocument:
    """Run the full transcription pipeline on an audio file.

    Args:
        audio: source audio path.
        language: optional language hint (`pt`, `en`); autodetected when None.
        output_profile: profile name reserved for future use.
        keep_stems: when True, stems are written next to the audio file.
        cache: when True, each stage reads/writes JSON under
            `<cache_root>/<audio_id>/<stage>.json`. Defaults False.
        cache_root: directory for cache files; defaults to `.titan-cache`
            relative to cwd.
        **engine_overrides: passed through to factory.select_* — supports
            `force_mock=True`, `backend="mps"|"cuda"|"cpu"`, etc.
    """
    started_at = datetime.now(UTC)
    audio_id = _sha256_id(audio)

    # F-002 fast path (Codex review 2026-05-19): when a fully cached document
    # exists, return it with ZERO engine selection. Idempotent reruns are
    # engine-free as long as the cache is intact.
    if cache:
        cached_doc = load_stage(audio_id, "document", root=cache_root)
        if cached_doc is not None:
            return ChordProDocument.model_validate(cached_doc)

    # Lazy engine selection — each select_* runs at most once, only when
    # its stage misses cache. Engines are remembered for the Provenance
    # block at the end. `engine_infos` keeps EngineInfo even after the
    # heavy engine object is released (Phase C T70 iter — memory relief).
    engines: dict[str, Any] = {}
    engine_infos: dict[str, EngineInfo] = {}

    def _engine(name: str, **extra: Any) -> Any:
        # Key includes extra kwargs (e.g. language) so syllabification
        # picks the right wrapper when language is autodetected.
        key = name if not extra else f"{name}:{extra.get('language', '')}"
        if key not in engines:
            select = getattr(factory, f"select_{name}")
            engines[key] = select(**engine_overrides, **extra)
            # Stash info NOW so provenance can still read it even after
            # _release_engine drops the heavy model object.
            engine_infos[name] = engines[key].info
        return engines[key]

    def _release_engine(name: str) -> None:
        """Phase C T70 iter: drop the heavy engine refs after its stage is
        done and ask the GPU backend to flush its allocator cache. Info is
        preserved in engine_infos so Provenance still has access.

        Safe to call multiple times. Safe on engines that were cache-hit
        (and so never instantiated) — nothing to release.
        """
        for key in list(engines.keys()):
            if key == name or key.startswith(name + ":"):
                del engines[key]
        release_gpu_memory()

    stems = _run_or_cache(
        cache=cache,
        cache_root=cache_root,
        audio_id=audio_id,
        stage="stems",
        schema=StemSet,
        compute=lambda: _engine("separation").separate(audio),
    )
    # htdemucs ~700 MB — release before whisper.cpp Metal context spawns.
    _release_engine("separation")

    trans_result = _run_or_cache(
        cache=cache,
        cache_root=cache_root,
        audio_id=audio_id,
        stage="transcription",
        schema=TranscriptionResult,
        compute=lambda: _engine("transcription").transcribe(stems.vocals, language=language),
    )
    # whisper.cpp Metal context ~150 MB — release before MMS_FA loads.
    _release_engine("transcription")

    # Phase C T70-iter2 Gap 3 (defensive): when transcription yields zero
    # words on a vocals stem that has audible content, surface a clear
    # diagnostic. The downstream sectioner correctly classifies a wordless
    # transcription as a single Instrumental section — but if the cause is
    # an undersized whisper model rather than a truly instrumental song,
    # the operator needs to know. Empty-word renders look like sectioner
    # bugs but are almost always transcription failures (e.g. whisper "base"
    # on PT-BR worship vocals tags everything as [Música] and our filter
    # drops the lot). Try --whisper-model medium or larger.
    if not trans_result.words:
        try:
            import librosa as _librosa
            import numpy as _np

            _y, _sr = _librosa.load(str(stems.vocals), sr=22050, mono=True)
            _rms = float(_np.sqrt(_np.mean(_y * _y))) if _y.size else 0.0
        except Exception:  # noqa: BLE001
            _rms = 0.0
        if _rms > 0.01:
            import logging as _logging

            _logging.getLogger(__name__).warning(
                "transcription yielded 0 words but vocals stem RMS=%.4f is audible — "
                "the song will render as a single Instrumental section. "
                "Likely cause: undersized whisper model. Retry with "
                "--whisper-model medium (or larger) and TITAN_WHISPER_MODEL env. "
                "Audio: %s",
                _rms,
                audio,
            )

    if trans_result.phonemes is None:
        align_result = _run_or_cache(
            cache=cache,
            cache_root=cache_root,
            audio_id=audio_id,
            stage="alignment",
            schema=AlignmentResult,
            compute=lambda: _engine("alignment").align(
                stems.vocals, trans_result.words, language=language or "pt"
            ),
        )
        words: list[WordEvent] = align_result.words
        phonemes = align_result.phonemes
        # MMS_FA ~1.2 GB + activations — release before chord/beat models.
        _release_engine("alignment")
    else:
        words = trans_result.words
        phonemes = trans_result.phonemes

    detected_lang = trans_result.detected_language or language or "en"

    syllables = _run_or_cache_list(
        cache=cache,
        cache_root=cache_root,
        audio_id=audio_id,
        stage="syllables",
        item_schema=SyllableEvent,
        compute=lambda: _engine("syllabification", language=detected_lang).syllabify(
            words, phonemes
        ),
    )
    # gruut/g2p_en are lightweight; no release needed.

    stress_detector = _stress_detector_for(detected_lang)
    _apply_stress(words, syllables, stress_detector)

    chords = _run_or_cache_list(
        cache=cache,
        cache_root=cache_root,
        audio_id=audio_id,
        stage="chords",
        item_schema=ChordEvent,
        compute=lambda: _engine("chord_recognition").detect(audio, bass_stem=stems.bass),
    )
    # chord_extractor is a thin Python wrapper; no release.

    beats = _run_or_cache(
        cache=cache,
        cache_root=cache_root,
        audio_id=audio_id,
        stage="beats",
        schema=BeatGrid,
        compute=lambda: _engine("beat_tracking").track(audio),
    )
    # BeatThis ~500 MB — release; provenance reads from engine_infos.
    _release_engine("beat_tracking")

    melismas = melisma_module.detect_melismas(syllables, chords, beats)

    sections_raw = sectioner.infer_sections(words, chords, beats, stems.duration)
    sections = _place_all_chords(
        sections_raw, words, syllables, chords, beats, melismas, detected_lang
    )

    completed_at = datetime.now(UTC)

    # Provenance reads from `engine_infos` (Phase C T70 iter — populated
    # by _engine() when each engine was first selected; persists even
    # after _release_engine drops the heavy model). Any info still
    # missing means that stage was a cache-hit, so we force-select once
    # to grab .info (debug-only path; normal first-runs already populated).
    for required in (
        "separation",
        "transcription",
        "alignment",
        "chord_recognition",
        "beat_tracking",
    ):
        if required not in engine_infos:
            engine_infos[required] = _engine(required).info
    if "syllabification" not in engine_infos:
        engine_infos["syllabification"] = _engine("syllabification", language=detected_lang).info

    confidence_aggregates: list[StageConfidence] = [
        aggregate_stage_confidence("transcription", trans_result.words),
        aggregate_stage_confidence("alignment", words),
        aggregate_stage_confidence("chord_recognition", chords),
        aggregate_stage_confidence("syllabification", syllables),
    ]

    provenance = Provenance(
        titan_version=_titan_version(),
        audio_id=audio_id,
        engines=EngineRegistry(
            separation=engine_infos["separation"],
            transcription=engine_infos["transcription"],
            alignment=engine_infos["alignment"],
            chord_recognition=engine_infos["chord_recognition"],
            beat_tracking=engine_infos["beat_tracking"],
            syllabification=engine_infos["syllabification"],
        ),
        started_at=started_at,
        completed_at=completed_at,
        confidence=confidence_aggregates,
    )

    document = ChordProDocument(
        metadata=Metadata(title=audio.stem),
        sections=sections,
        provenance=provenance,
        beat_grid=beats,
    )

    if cache:
        dump_stage(audio_id, "document", document.model_dump(mode="json"), root=cache_root)
        dump_stage(audio_id, "provenance", provenance.model_dump(mode="json"), root=cache_root)

    return document


def _run_or_cache(
    *,
    cache: bool,
    cache_root: Path | None,
    audio_id: str,
    stage: Stage,
    schema: Any,
    compute: Any,
) -> Any:
    """Cache-aware single-result stage runner."""
    if cache:
        cached = load_stage(audio_id, stage, root=cache_root)
        if cached is not None:
            return schema.model_validate(cached)
    result = compute()
    if cache:
        dump_stage(audio_id, stage, result.model_dump(mode="json"), root=cache_root)
    return result


def _run_or_cache_list(
    *,
    cache: bool,
    cache_root: Path | None,
    audio_id: str,
    stage: Stage,
    item_schema: Any,
    compute: Any,
) -> list[Any]:
    """Cache-aware list-result stage runner (chords, syllables — list[Pydantic])."""
    if cache:
        cached = load_stage(audio_id, stage, root=cache_root)
        if cached is not None:
            return [item_schema.model_validate(d) for d in cached]
    result: list[Any] = compute()
    if cache:
        dump_stage(
            audio_id,
            stage,
            [item.model_dump(mode="json") for item in result],
            root=cache_root,
        )
    return result


def _sha256_id(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    except OSError:
        return hashlib.sha256(str(path).encode()).hexdigest()[:16]


def _titan_version() -> str:
    try:
        from titan_chordpro.version import __version__

        return __version__
    except ImportError:
        return "0.1.0a0"


def _stress_detector_for(language: str) -> stress.StressDetector:
    if language.startswith("pt"):
        return stress.PortugueseStressDetector()
    return stress.EnglishStressDetector()


def _apply_stress(
    words: list[WordEvent],
    syllables: list[SyllableEvent],
    detector: stress.StressDetector,
) -> None:
    word_syllables: dict[int, list[SyllableEvent]] = {}
    for syl in syllables:
        word_syllables.setdefault(syl.parent_word_idx, []).append(syl)
    for idx, word in enumerate(words):
        word_syls = word_syllables.get(idx, [])
        if not word_syls:
            continue
        stressed = detector.detect_stressed_syllable(word, word_syls)
        word_syls[stressed].is_stressed = True


def _place_all_chords(
    sections: list[Section],
    words: list[WordEvent],
    syllables: list[SyllableEvent],
    chords: list[ChordEvent],
    beats: BeatGrid,
    melismas: list[Melisma],
    language: str,
) -> list[Section]:
    word_index = {id(w): i for i, w in enumerate(words)}
    syl_by_global_word: dict[int, list[SyllableEvent]] = {}
    for syl in syllables:
        syl_by_global_word.setdefault(syl.parent_word_idx, []).append(syl)

    result: list[Section] = []
    for section in sections:
        new_lines: list[LyricLine | InstrumentalLine] = []
        for line in section.lines:
            if not isinstance(line, LyricLine):
                new_lines.append(line)
                continue
            line_words = line.word_alignments
            global_indices = [word_index.get(id(w), -1) for w in line_words]
            line_syls = [
                s for gi in global_indices if gi >= 0 for s in syl_by_global_word.get(gi, [])
            ]
            if line_words:
                line_span = TimeStamp(
                    start=line_words[0].timestamp.start,
                    end=line_words[-1].timestamp.end,
                )
            else:
                line_span = section.timestamp
            line_chords = [c for c in chords if _chord_in_span(c, line_span)]
            placed, _orphans = placer.place_chords_in_line(
                line_text=line.text,
                words=line_words,
                syllables=line_syls,
                chords_in_line=line_chords,
                beat_grid=beats,
                melismas=melismas,
                language=language,
            )
            new_lines.append(placed)
        result.append(section.model_copy(update={"lines": new_lines}))
    return result


def _chord_in_span(chord: ChordEvent, timestamp: TimeStamp) -> bool:
    return chord.timestamp.start < timestamp.end and chord.timestamp.end > timestamp.start

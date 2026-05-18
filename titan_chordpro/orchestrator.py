"""orchestrator.py — transcribe() master pipeline.

Wires all 6 engine Protocols via factory.py. Never imports torch/whisper/etc.
All ML is behind Protocols; Phase A uses mock engines.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from titan_chordpro import factory
from titan_chordpro.core.schemas import (
    BeatGrid,
    ChordEvent,
    ChordProDocument,
    EngineRegistry,
    InstrumentalLine,
    LyricLine,
    Metadata,
    Provenance,
    Section,
    SyllableEvent,
    TimeStamp,
    WordEvent,
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
    force_mock: bool = False,
    backend: str | None = None,
) -> ChordProDocument:
    """Run the full transcription pipeline on an audio file.

    Returns a ChordProDocument ready for rendering via doc.to_string() / doc.write().

    Args:
        force_mock: If True, all engines will use mock implementations.
        backend: Backend hint for torch engines (e.g. "mps", "cuda", "cpu").
    """
    started_at = datetime.now(UTC)
    audio_id = _sha256_id(audio)

    factory_kwargs: dict[str, object] = {"force_mock": force_mock, "backend": backend}

    sep_engine = factory.select_separation(**factory_kwargs)  # type: ignore[arg-type]
    trans_engine = factory.select_transcription(**factory_kwargs)  # type: ignore[arg-type]
    align_engine = factory.select_alignment(**factory_kwargs)  # type: ignore[arg-type]
    chord_engine = factory.select_chord_recognition(**factory_kwargs)  # type: ignore[arg-type]
    beat_engine = factory.select_beat_tracking(**factory_kwargs)  # type: ignore[arg-type]

    stems = sep_engine.separate(audio)

    trans_result = trans_engine.transcribe(stems.vocals, language=language)

    if trans_result.phonemes is None:
        align_result = align_engine.align(
            stems.vocals, trans_result.words, language=language or "pt"
        )
        words: list[WordEvent] = align_result.words
        phonemes = align_result.phonemes
    else:
        words = trans_result.words
        phonemes = trans_result.phonemes

    detected_lang = trans_result.detected_language or language or "en"
    syll_engine = factory.select_syllabification(language=detected_lang)
    syllables: list[SyllableEvent] = syll_engine.syllabify(words, phonemes)

    stress_detector = _stress_detector_for(detected_lang)
    _apply_stress(words, syllables, stress_detector)

    chords = chord_engine.detect(stems.bass)
    beats = beat_engine.track(audio)

    melismas = melisma_module.detect_melismas(syllables, chords, beats)

    sections_raw = sectioner.infer_sections(words, chords, beats, stems.duration)
    sections = _place_all_chords(
        sections_raw, words, syllables, chords, beats, melismas, detected_lang
    )

    completed_at = datetime.now(UTC)

    provenance = Provenance(
        titan_version=_titan_version(),
        audio_id=audio_id,
        engines=EngineRegistry(
            separation=sep_engine.info,
            transcription=trans_engine.info,
            alignment=align_engine.info,
            chord_recognition=chord_engine.info,
            beat_tracking=beat_engine.info,
            syllabification=syll_engine.info,
        ),
        started_at=started_at,
        completed_at=completed_at,
        confidence=[],
    )

    return ChordProDocument(
        metadata=Metadata(title=audio.stem),
        sections=sections,
        provenance=provenance,
    )


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
            line_chords = [c for c in chords if _chord_in_span(c, section.timestamp)]
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

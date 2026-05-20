# titan_chordpro/fusion/sectioner.py
"""V0.1 heuristic section inference from word gaps in lyrics.

Algorithm:
    1. Derive gap threshold from beat_grid: 4 beats × beat_period seconds.
       (Threshold scales with tempo — 4s @ 60bpm, 1.33s @ 180bpm.)
    2. Group sequential words into "lyric blocks" separated by gaps > threshold.
    3. Classify chronologically:
       - 0 to first lyric block (if gap > threshold) → Intro
       - Between two lyric blocks (if gap > threshold) → Instrumental break
       - Last lyric block end to duration (if gap > threshold) → Outro
       - Lyric blocks themselves → alternate Verse/Chorus starting with Verse 1
    4. Within each lyric block, split into LyricLines on smaller gaps (2 beats).
    5. Partition chord events by timestamp into the section they fall into.

Limitations (documented in spec Section 3.6):
    - Verse vs Chorus is positional alternation, not content-based detection.
    - Bridge / Pre-chorus not detected — folded into the alternation cycle.
    - Single-line audio with no lyrics → one Instrumental section.

V0.2 plan: integrate mir-aidj/all-in-one for joint structure analysis.

Spec reference: docs/superpowers/specs/2026-05-09-titan-v0.1-design.md → Section 3.6
"""

from __future__ import annotations

import statistics

from titan_chordpro.core.schemas import (
    BeatGrid,
    ChordEvent,
    InstrumentalLine,
    Line,
    LyricLine,
    Section,
    TimeStamp,
    WordEvent,
)

INSTRUMENTAL_GAP_BEATS = 4  # legacy beat-based fallback (rarely active now)
LYRIC_LINE_GAP_BEATS = 2  # legacy beat-based fallback (rarely active now)

# Phase C T70-iter2 follow-up: word-level whisper timestamps (one
# WordEvent per word, not per phrase) exposed real breath pauses that
# segment-level whisper had hidden inside long "word" spans. The legacy
# beat-based thresholds tuned for segment-level whisper now over-fire on
# fast-tempo songs because 4 × beat_period falls below typical breath
# pauses (~2s). Switch to adaptive thresholds derived from the song's
# own inter-word gap distribution, floored at an absolute minimum.
#
# `INSTRUMENTAL_GAP_MULT * median(inter_word_gap)` captures the song's
# rhythm — a song with tight phrasing gets a tighter threshold; one with
# long sustained phrases gets a relaxed one. The floor prevents tiny
# breath pauses from registering as breaks when the median is unusually
# small (busy chorus, etc).
INSTRUMENTAL_GAP_MULT = 8.0
LYRIC_LINE_GAP_MULT = 2.5
MIN_INSTRUMENTAL_GAP_SEC = 4.0
MIN_LYRIC_LINE_GAP_SEC = 1.0


def _compute_adaptive_thresholds(
    words: list[WordEvent],
    beat_grid: BeatGrid,
) -> tuple[float, float]:
    """Return (instrumental_gap_sec, lyric_line_gap_sec) adapted to the song.

    With < 2 words, falls back to the legacy beat-based formula. Otherwise
    derives from the median of positive inter-word gaps, floored at the
    MIN_*_SEC constants.
    """
    beat_period = _beat_period(beat_grid)
    if len(words) < 2:
        return (
            max(INSTRUMENTAL_GAP_BEATS * beat_period, MIN_INSTRUMENTAL_GAP_SEC),
            max(LYRIC_LINE_GAP_BEATS * beat_period, MIN_LYRIC_LINE_GAP_SEC),
        )
    gaps = [words[i + 1].timestamp.start - words[i].timestamp.end for i in range(len(words) - 1)]
    gaps = [g for g in gaps if g > 0.0]
    if not gaps:
        return MIN_INSTRUMENTAL_GAP_SEC, MIN_LYRIC_LINE_GAP_SEC
    median_gap = statistics.median(gaps)
    instrumental = max(INSTRUMENTAL_GAP_MULT * median_gap, MIN_INSTRUMENTAL_GAP_SEC)
    line = max(LYRIC_LINE_GAP_MULT * median_gap, MIN_LYRIC_LINE_GAP_SEC)
    return instrumental, line


def infer_sections(
    words: list[WordEvent],
    chords: list[ChordEvent],
    beat_grid: BeatGrid,
    duration: float,
) -> list[Section]:
    """Infer Section objects from words + chords + beat_grid.

    Returns sections in chronological order covering [0, duration].
    """
    if duration <= 0:
        return []

    gap_threshold, line_gap_threshold = _compute_adaptive_thresholds(words, beat_grid)

    # Case 1: no lyrics → entire audio is one instrumental section.
    if not words:
        return [
            _make_instrumental_section(
                chords=chords,
                timestamp=TimeStamp(start=0.0, end=duration),
                beat_grid=beat_grid,
                label="Instrumental",
                section_type="instrumental",
            )
        ]

    # Group words into lyric blocks (internal gaps < threshold).
    lyric_blocks = _group_words_into_blocks(words, gap_threshold)

    sections: list[Section] = []
    verse_count = 0
    chorus_count = 0
    cursor = 0.0

    # Intro: leading silence/instrumental before first lyric block.
    first_block_start = lyric_blocks[0][0].timestamp.start
    if first_block_start - cursor > gap_threshold:
        intro_chords = [c for c in chords if c.timestamp.start < first_block_start]
        sections.append(
            _make_instrumental_section(
                chords=intro_chords,
                timestamp=TimeStamp(start=0.0, end=first_block_start),
                beat_grid=beat_grid,
                label="Intro",
                section_type="intro",
            )
        )
        cursor = first_block_start

    for i, block in enumerate(lyric_blocks):
        block_start = block[0].timestamp.start
        block_end = block[-1].timestamp.end

        # Instrumental break between previous block and this one.
        if cursor < block_start and block_start - cursor > gap_threshold:
            gap_chords = [c for c in chords if cursor <= c.timestamp.start < block_start]
            instr_idx = sum(1 for s in sections if s.type == "instrumental")
            instr_label = f"Instrumental {instr_idx + 1}" if instr_idx else "Instrumental"
            sections.append(
                _make_instrumental_section(
                    chords=gap_chords,
                    timestamp=TimeStamp(start=cursor, end=block_start),
                    beat_grid=beat_grid,
                    label=instr_label,
                    section_type="instrumental",
                )
            )

        # Alternation: even-indexed blocks = Verse, odd-indexed = Chorus.
        if i % 2 == 0:
            verse_count += 1
            label = f"Verse {verse_count}"
            section_type = "verse"
        else:
            chorus_count += 1
            label = "Chorus" if chorus_count == 1 else f"Chorus {chorus_count}"
            section_type = "chorus"

        block_chords = [c for c in chords if block_start <= c.timestamp.start <= block_end]
        sections.append(
            _make_lyric_section(
                words=block,
                chords=block_chords,
                beat_grid=beat_grid,
                label=label,
                section_type=section_type,
                timestamp=TimeStamp(start=block_start, end=block_end),
                line_gap=line_gap_threshold,
            )
        )
        cursor = block_end

    # Outro: trailing instrumental after last lyric block.
    if duration - cursor > gap_threshold:
        outro_chords = [c for c in chords if c.timestamp.start >= cursor]
        sections.append(
            _make_instrumental_section(
                chords=outro_chords,
                timestamp=TimeStamp(start=cursor, end=duration),
                beat_grid=beat_grid,
                label="Outro",
                section_type="outro",
            )
        )

    return sections


# ───────────────────── Helpers ─────────────────────


def _beat_period(beat_grid: BeatGrid) -> float:
    """Median beat-to-beat interval in seconds (robust to outliers / BPM drift)."""
    if len(beat_grid.beats) < 2:
        return 60.0 / beat_grid.bpm
    intervals = sorted(
        beat_grid.beats[i + 1] - beat_grid.beats[i] for i in range(len(beat_grid.beats) - 1)
    )
    return intervals[len(intervals) // 2]


def _group_words_into_blocks(
    words: list[WordEvent],
    gap_threshold: float,
) -> list[list[WordEvent]]:
    """Group sequential words; break on gap > threshold."""
    if not words:
        return []
    blocks: list[list[WordEvent]] = [[words[0]]]
    for w in words[1:]:
        prev = blocks[-1][-1]
        if w.timestamp.start - prev.timestamp.end > gap_threshold:
            blocks.append([w])
        else:
            blocks[-1].append(w)
    return blocks


def _group_words_into_lines(
    words: list[WordEvent],
    line_gap: float,
) -> list[list[WordEvent]]:
    """Split a block into LyricLines on smaller gaps (intra-block phrasing)."""
    if not words:
        return []
    lines: list[list[WordEvent]] = [[words[0]]]
    for w in words[1:]:
        prev = lines[-1][-1]
        if w.timestamp.start - prev.timestamp.end > line_gap:
            lines.append([w])
        else:
            lines[-1].append(w)
    return lines


def _measures_in_span(
    timestamp: TimeStamp,
    beat_grid: BeatGrid,
) -> int:
    """Approximate measures in a time span. Floor to 1 to satisfy schema `gt=0`."""
    beats_in_span = sum(1 for b in beat_grid.beats if timestamp.start <= b <= timestamp.end)
    beats_per_measure = beat_grid.meter[0]
    return max(1, beats_in_span // beats_per_measure)


def _make_instrumental_section(
    chords: list[ChordEvent],
    timestamp: TimeStamp,
    beat_grid: BeatGrid,
    label: str,
    section_type: str,
) -> Section:
    line = InstrumentalLine(
        chords=chords,
        measures=_measures_in_span(timestamp, beat_grid),
        label=label if section_type != "instrumental" else None,
    )
    return Section(
        type=section_type,  # type: ignore[arg-type]
        label=label,
        lines=[line],
        timestamp=timestamp,
    )


def _make_lyric_section(
    words: list[WordEvent],
    chords: list[ChordEvent],
    beat_grid: BeatGrid,
    label: str,
    section_type: str,
    timestamp: TimeStamp,
    line_gap: float | None = None,
) -> Section:
    """Build a lyric Section with one LyricLine per phrasal group.

    The placer (T20) is responsible for filling LyricLine.chord_markers later.
    Here we just wire the LyricLines with their word_alignments.

    `line_gap` is the threshold (in seconds) for splitting a block into
    multiple LyricLines. When None, falls back to the legacy beat-based
    formula (LYRIC_LINE_GAP_BEATS × beat_period) — kept for back-compat
    with callers that don't pass the adaptive value (e.g. unit tests).
    """
    if line_gap is None:
        line_gap = LYRIC_LINE_GAP_BEATS * _beat_period(beat_grid)
    line_word_groups = _group_words_into_lines(words, line_gap)

    lines: list[Line] = []
    for line_words in line_word_groups:
        line_text = " ".join(w.text for w in line_words)
        lines.append(
            LyricLine(
                text=line_text,
                chord_markers=[],
                word_alignments=line_words,
                syllable_alignments=[],
            )
        )
    return Section(
        type=section_type,  # type: ignore[arg-type]
        label=label,
        lines=lines,
        timestamp=timestamp,
    )

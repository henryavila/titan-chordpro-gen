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

INSTRUMENTAL_GAP_BEATS = 4  # gap > this many beats → instrumental break
LYRIC_LINE_GAP_BEATS = 2  # gap > this many beats within a block → new LyricLine


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

    beat_period = _beat_period(beat_grid)
    gap_threshold = INSTRUMENTAL_GAP_BEATS * beat_period

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
) -> Section:
    """Build a lyric Section with one LyricLine per phrasal group.

    The placer (T20) is responsible for filling LyricLine.chord_markers later.
    Here we just wire the LyricLines with their word_alignments.
    """
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

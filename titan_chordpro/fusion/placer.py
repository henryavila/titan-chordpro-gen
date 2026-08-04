# titan_chordpro/fusion/placer.py
"""Chord placement using a 5-strategy hierarchical fallback algorithm.

This is the central IP of the library — it decides exactly which orthographic
character position in a rendered LyricLine receives each chord marker.

Strategies (first match wins, in order):
    1. melisma_start    — chord falls inside a detected melisma span, unless a
                          nearer syllable exists within the any-syllable window
                          (RC5: multi-syllable restore prefers time proximity)
    2. stressed_syllable — chord near tonic syllable (span-aware, beat-scaled)
    3. any_syllable     — chord near any syllable (span-aware, beat-scaled)
    4. before_word      — chord near closest word span (beat-scaled window)
    5. orphan           — no syllable/word in any window; returned as leftover
                          for the sectioner to insert as a sibling InstrumentalLine

Tolerance rationale (research/09-chord-on-syllable.md + RC5):
    - Floors: ±150ms stressed / ±300ms any-syllable / ±500ms before-word.
    - Beat scaling: windows widen to fractions of the local beat period so slow
      worship tempos (~70 BPM) do not orphan mid-bar holds that fall inside a
      word span or just past a word boundary.
    - Distance is to the event *span* (0 if t is inside [start, end]), not only
      to the start timestamp — mid-lyric holds were systematically orphaned when
      only start-distance was used.

Spec reference: docs/superpowers/specs/2026-05-09-titan-v0.1-design.md → Section 3.7
"""

from __future__ import annotations

from statistics import median

from titan_chordpro.core.schemas import (
    BeatGrid,
    ChordEvent,
    ChordMarker,
    LyricLine,
    SyllableEvent,
    WordEvent,
)
from titan_chordpro.fusion.melisma import Melisma
from titan_chordpro.fusion.onset_fusion import fuse_onsets_v01

# Floor tolerance windows (seconds) — see module docstring for rationale.
STRESSED_TOL_S = 0.150
ANY_SYLLABLE_TOL_S = 0.300
BEFORE_WORD_TOL_S = 0.500

# Beat-period multipliers for RC5 adaptive windows (applied as max(floor, k * beat)).
_STRESSED_BEAT_FRAC = 0.33
_ANY_SYLLABLE_BEAT_FRAC = 0.60
_BEFORE_WORD_BEAT_FRAC = 1.00

# Clamp estimated beat period to a musically plausible range.
_MIN_BEAT_PERIOD_S = 0.25  # 240 BPM
_MAX_BEAT_PERIOD_S = 1.50  # 40 BPM
_DEFAULT_BEAT_PERIOD_S = 0.50  # 120 BPM fallback


def place_chords_in_line(
    line_text: str,
    words: list[WordEvent],
    syllables: list[SyllableEvent],
    chords_in_line: list[ChordEvent],
    beat_grid: BeatGrid,
    melismas: list[Melisma],
    language: str,
) -> tuple[LyricLine, list[ChordEvent]]:
    """Place chords using hierarchical fallback. Returns (LyricLine, orphan chords).

    The LyricLine.chord_markers are sorted by char_position to keep ChordPro
    output stable across runs (Pydantic equality + snapshot tests).
    """
    word_char_positions = _build_word_char_positions(line_text, words)
    stressed_tol, any_syl_tol, before_word_tol = _placement_tolerances(beat_grid)

    markers: list[ChordMarker] = []
    orphans: list[ChordEvent] = []

    for chord in chords_in_line:
        t_anchor = fuse_onsets_v01(chord, beat_grid)

        # Strategy 1: melisma overlap — but defer when a closer syllable exists
        # within the any-syllable window (prefer time proximity over melisma pin).
        melisma = _find_melisma_at(melismas, t_anchor)
        if melisma is not None and 0 <= melisma.syllable_idx < len(syllables):
            m1_syl: SyllableEvent = syllables[melisma.syllable_idx]
            nearer = _find_any_syllable_within(syllables, t_anchor, any_syl_tol)
            if nearer is not None and nearer is not m1_syl:
                m1_dist = _event_temporal_distance(
                    m1_syl.timestamp.start, m1_syl.timestamp.end, t_anchor
                )
                near_dist = _event_temporal_distance(
                    nearer.timestamp.start, nearer.timestamp.end, t_anchor
                )
                if near_dist < m1_dist:
                    # Fall through to strategies 2–4 with the nearer syllable.
                    pass
                else:
                    char_pos = _char_pos_of_syllable(
                        line_text,
                        m1_syl,
                        syllables,
                        words,
                        word_char_positions,
                    )
                    markers.append(
                        ChordMarker(
                            chord=chord,
                            char_position=char_pos,
                            placement_strategy="melisma_start",
                        )
                    )
                    continue
            else:
                char_pos = _char_pos_of_syllable(
                    line_text,
                    m1_syl,
                    syllables,
                    words,
                    word_char_positions,
                )
                markers.append(
                    ChordMarker(
                        chord=chord,
                        char_position=char_pos,
                        placement_strategy="melisma_start",
                    )
                )
                continue

        # Strategy 2: stressed syllable within beat-scaled window
        cand_syl: SyllableEvent | None = _find_stressed_syllable_within(
            syllables, t_anchor, stressed_tol
        )
        if cand_syl is not None:
            char_pos = _char_pos_of_syllable(
                line_text,
                cand_syl,
                syllables,
                words,
                word_char_positions,
            )
            markers.append(
                ChordMarker(
                    chord=chord,
                    char_position=char_pos,
                    placement_strategy="stressed_syllable",
                )
            )
            continue

        # Strategy 3: any syllable within beat-scaled window
        cand_syl = _find_any_syllable_within(syllables, t_anchor, any_syl_tol)
        if cand_syl is not None:
            char_pos = _char_pos_of_syllable(
                line_text,
                cand_syl,
                syllables,
                words,
                word_char_positions,
            )
            markers.append(
                ChordMarker(
                    chord=chord,
                    char_position=char_pos,
                    placement_strategy="any_syllable",
                )
            )
            continue

        # Strategy 4: nearest word by span distance within beat-scaled window
        cand_word_idx = _closest_word(words, t_anchor)
        if cand_word_idx is not None:
            cand_word = words[cand_word_idx]
            dist = _event_temporal_distance(
                cand_word.timestamp.start, cand_word.timestamp.end, t_anchor
            )
            if dist <= before_word_tol:
                char_pos = _char_pos_of_word_start(cand_word_idx, word_char_positions)
                markers.append(
                    ChordMarker(
                        chord=chord,
                        char_position=char_pos,
                        placement_strategy="before_word",
                    )
                )
                continue

        # Strategy 5: orphan — defer to sectioner
        orphans.append(chord)

    # Phase C T70: destack markers that landed on the same char_position.
    # Worship charts put one chord per syllable/onset; stacked [F][G]meus is
    # the dominant human-visible failure mode when several chord changes fall
    # between two words. Keep chronological order; advance later chords to the
    # next free orthographic slot; if the line is exhausted, demote to orphan.
    markers, stack_orphans = _destack_markers(markers, line_text)
    orphans.extend(stack_orphans)

    # Stable ordering for serialization / snapshot tests
    markers.sort(key=lambda m: (m.char_position, m.chord.timestamp.start))

    line = LyricLine(
        text=line_text,
        chord_markers=markers,
        word_alignments=words,
        syllable_alignments=syllables,
        confidence=_aggregate_confidence(words, chords_in_line),
    )
    return line, orphans


# ───────────────────── Helpers ─────────────────────


def _event_temporal_distance(start: float, end: float, t_anchor: float) -> float:
    """Distance from t_anchor to [start, end]; 0 when inside the closed span."""
    if start <= t_anchor <= end:
        return 0.0
    if t_anchor < start:
        return start - t_anchor
    return t_anchor - end


def _beat_period_s(beat_grid: BeatGrid) -> float:
    """Estimate beat period (seconds) from BPM or median inter-beat interval."""
    if beat_grid.bpm and beat_grid.bpm > 0:
        period = 60.0 / float(beat_grid.bpm)
        return max(_MIN_BEAT_PERIOD_S, min(_MAX_BEAT_PERIOD_S, period))

    beats = beat_grid.beats
    if len(beats) >= 2:
        diffs = [
            beats[i + 1] - beats[i]
            for i in range(len(beats) - 1)
            if _MIN_BEAT_PERIOD_S <= (beats[i + 1] - beats[i]) <= _MAX_BEAT_PERIOD_S
        ]
        if diffs:
            return float(median(diffs))
    return _DEFAULT_BEAT_PERIOD_S


def _placement_tolerances(beat_grid: BeatGrid) -> tuple[float, float, float]:
    """Return (stressed, any_syllable, before_word) tolerances in seconds.

    Floors preserve the original research windows; beat fractions widen them at
    slow tempos so mid-bar lyric holds are not systematically orphaned.
    """
    beat = _beat_period_s(beat_grid)
    stressed = max(STRESSED_TOL_S, _STRESSED_BEAT_FRAC * beat)
    any_syl = max(ANY_SYLLABLE_TOL_S, _ANY_SYLLABLE_BEAT_FRAC * beat)
    before_word = max(BEFORE_WORD_TOL_S, _BEFORE_WORD_BEAT_FRAC * beat)
    return stressed, any_syl, before_word


def _find_melisma_at(
    melismas: list[Melisma],
    t_anchor: float,
) -> Melisma | None:
    """Return the first melisma whose span contains t_anchor (inclusive)."""
    for m in melismas:
        if m.span.start <= t_anchor <= m.span.end:
            return m
    return None


def _find_stressed_syllable_within(
    syllables: list[SyllableEvent],
    t_anchor: float,
    tol: float,
) -> SyllableEvent | None:
    """Closest stressed syllable within ±tol of t_anchor; None if no match."""
    candidates = [s for s in syllables if s.is_stressed]
    return _closest_syllable_within(candidates, t_anchor, tol)


def _find_any_syllable_within(
    syllables: list[SyllableEvent],
    t_anchor: float,
    tol: float,
) -> SyllableEvent | None:
    """Closest syllable (regardless of stress) within ±tol of t_anchor."""
    return _closest_syllable_within(syllables, t_anchor, tol)


def _closest_syllable_within(
    syllables: list[SyllableEvent],
    t_anchor: float,
    tol: float,
) -> SyllableEvent | None:
    """Closest syllable by span distance (0 if t is inside the syllable)."""
    best: SyllableEvent | None = None
    best_dist = float("inf")
    for s in syllables:
        dist = _event_temporal_distance(s.timestamp.start, s.timestamp.end, t_anchor)
        if dist <= tol and dist < best_dist:
            best = s
            best_dist = dist
    return best


def _closest_word(
    words: list[WordEvent],
    t_anchor: float,
) -> int | None:
    """Index of closest word by span distance to t_anchor; None if list empty."""
    if not words:
        return None
    best_idx = 0
    best_dist = _event_temporal_distance(words[0].timestamp.start, words[0].timestamp.end, t_anchor)
    for i, w in enumerate(words[1:], start=1):
        dist = _event_temporal_distance(w.timestamp.start, w.timestamp.end, t_anchor)
        if dist < best_dist:
            best_idx = i
            best_dist = dist
    return best_idx


def _build_word_char_positions(
    line_text: str,
    words: list[WordEvent],
) -> dict[int, int]:
    """Map word_idx → char position in line_text.

    Strategy: scan line_text left-to-right (case-insensitive), matching each
    word's surface form sequentially. Handles repeated words correctly via
    advancing cursor. If a word can't be found, falls back to current cursor
    position (degraded but deterministic).
    """
    positions: dict[int, int] = {}
    cursor = 0
    lower_line = line_text.lower()
    for w_idx, word in enumerate(words):
        target = word.text.lower()
        found = lower_line.find(target, cursor)
        if found < 0:
            positions[w_idx] = cursor
        else:
            positions[w_idx] = found
            cursor = found + len(target)
    return positions


def _char_pos_of_word_start(
    word_idx: int,
    word_char_positions: dict[int, int],
) -> int:
    return word_char_positions.get(word_idx, 0)


def _char_pos_of_syllable(
    line_text: str,
    syllable: SyllableEvent,
    all_syllables: list[SyllableEvent],
    words: list[WordEvent],
    word_char_positions: dict[int, int],
) -> int:
    """Char position of syllable start in line_text.

    Strategy: find the syllable's index among its siblings (same parent_word_idx),
    then linearly distribute the parent word's orthographic length across the
    sibling count. This is approximate but deterministic — proper phonetic-to-
    orthographic alignment is a v0.2 enhancement.
    """
    parent_idx = syllable.parent_word_idx
    if parent_idx < 0 or parent_idx >= len(words):
        return word_char_positions.get(0, 0)
    parent_word = words[parent_idx]
    parent_pos = word_char_positions.get(parent_idx, 0)

    siblings = [s for s in all_syllables if s.parent_word_idx == parent_idx]
    if not siblings:
        return parent_pos

    try:
        syl_local_idx = siblings.index(syllable)
    except ValueError:
        return parent_pos

    n_siblings = len(siblings)
    word_len = len(parent_word.text)
    char_offset = (syl_local_idx * word_len) // n_siblings
    return parent_pos + char_offset


def _aggregate_confidence(
    words: list[WordEvent],
    chords: list[ChordEvent],
) -> float:
    """Mean confidence across all word + chord events in the line."""
    items: list[float] = [w.confidence for w in words]
    items.extend(c.confidence for c in chords)
    if not items:
        return 1.0
    return sum(items) / len(items)


def _destack_markers(
    markers: list[ChordMarker],
    line_text: str,
) -> tuple[list[ChordMarker], list[ChordEvent]]:
    """Ensure at most one chord marker per char_position.

    Markers are processed in chord-onset order. When a marker's preferred
    position is already occupied, it walks forward one character at a time
    (capped at ``len(line_text)``) looking for a free slot. If none remains,
    the chord becomes an orphan InstrumentalLine sibling (sectioner path).
    """
    if not markers:
        return [], []

    ordered = sorted(markers, key=lambda m: (m.chord.timestamp.start, m.char_position))
    occupied: set[int] = set()
    kept: list[ChordMarker] = []
    orphans: list[ChordEvent] = []
    max_pos = max(len(line_text), 0)

    for m in ordered:
        pos = m.char_position
        if pos not in occupied:
            occupied.add(pos)
            kept.append(m)
            continue
        # Walk forward for a free orthographic slot.
        placed = False
        for candidate in range(pos + 1, max_pos + 1):
            if candidate not in occupied:
                occupied.add(candidate)
                kept.append(m.model_copy(update={"char_position": candidate}))
                placed = True
                break
        if not placed:
            orphans.append(m.chord)
    return kept, orphans

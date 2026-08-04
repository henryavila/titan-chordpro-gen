# titan_chordpro/fusion/placer.py
"""Chord placement using a 5-strategy hierarchical fallback algorithm.

This is the central IP of the library — it decides exactly which orthographic
character position in a rendered LyricLine receives each chord marker.

Strategies (first match wins, in order):
    1. melisma_start    — chord falls inside a detected melisma span
    2. stressed_syllable — chord on tonic syllable within ±150ms of fused onset
    3. any_syllable     — chord on closest syllable within ±300ms
    4. before_word      — chord positioned before closest word (within ±500ms)
    5. orphan           — no syllable/word in any window; returned as leftover
                          for the sectioner to insert as a sibling InstrumentalLine

Tolerance rationale (research/09-chord-on-syllable.md):
    - ±150ms: typical sustained syllable duration; covers Whisper word-offset
      median error (~30ms) plus phonetic boundary uncertainty.
    - ±300ms: 1 beat at 200bpm; covers any reasonably-placed syllable.
    - ±500ms: half a measure at 120bpm; reflects "before this word" intuition.

Spec reference: docs/superpowers/specs/2026-05-09-titan-v0.1-design.md → Section 3.7
"""

from __future__ import annotations

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

# Tolerance windows (seconds) — see module docstring for rationale.
STRESSED_TOL_S = 0.150
ANY_SYLLABLE_TOL_S = 0.300
BEFORE_WORD_TOL_S = 0.500


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

    markers: list[ChordMarker] = []
    orphans: list[ChordEvent] = []

    for chord in chords_in_line:
        t_anchor = fuse_onsets_v01(chord, beat_grid)

        # Strategy 1: melisma overlap (semantic priority — chord IS the melisma anchor)
        melisma = _find_melisma_at(melismas, t_anchor)
        if melisma is not None and 0 <= melisma.syllable_idx < len(syllables):
            m1_syl: SyllableEvent = syllables[melisma.syllable_idx]
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

        # Strategy 2: stressed syllable within ±150ms (best case — chord on tonic)
        cand_syl: SyllableEvent | None = _find_stressed_syllable_within(
            syllables, t_anchor, STRESSED_TOL_S
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

        # Strategy 3: any syllable within ±300ms (good case — chord on a syllable)
        cand_syl = _find_any_syllable_within(syllables, t_anchor, ANY_SYLLABLE_TOL_S)
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

        # Strategy 4: before the closest word within ±500ms
        cand_word_idx = _closest_word(words, t_anchor)
        if cand_word_idx is not None:
            cand_word = words[cand_word_idx]
            if abs(cand_word.timestamp.start - t_anchor) < BEFORE_WORD_TOL_S:
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

    # Stable ordering for serialization / snapshot tests
    markers.sort(key=lambda m: m.char_position)

    line = LyricLine(
        text=line_text,
        chord_markers=markers,
        word_alignments=words,
        syllable_alignments=syllables,
        confidence=_aggregate_confidence(words, chords_in_line),
    )
    return line, orphans


# ───────────────────── Helpers ─────────────────────


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
    best: SyllableEvent | None = None
    best_dist = float("inf")
    for s in syllables:
        dist = abs(s.timestamp.start - t_anchor)
        if dist <= tol and dist < best_dist:
            best = s
            best_dist = dist
    return best


def _closest_word(
    words: list[WordEvent],
    t_anchor: float,
) -> int | None:
    """Index of closest word (by start time) to t_anchor; None if list empty."""
    if not words:
        return None
    best_idx = 0
    best_dist = abs(words[0].timestamp.start - t_anchor)
    for i, w in enumerate(words[1:], start=1):
        dist = abs(w.timestamp.start - t_anchor)
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

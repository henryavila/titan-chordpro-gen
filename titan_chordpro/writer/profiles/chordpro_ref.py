"""Strict canonical ChordPro profile with {start_of_grid}/{end_of_grid} blocks.

Differs from inline_slash ONLY in InstrumentalLine rendering: this profile
emits a grid block (per ChordPro reference spec 6.x) instead of `[C]x///`
inline rhythm tokens. LyricLine rendering is identical (reuses inline_slash
helpers via composition).

Grid layout rules (4/4 default, configurable from Metadata.time_signature):
- full_measure: each measure is `| Chord . . . |` (chord on beat 1, rest dots).
- half_measure: each measure is `| C1 . C2 . |` (two chords per measure).
- beat: each measure has N cells (N = beats in meter), one chord per beat.

Targets: chordpro.org strict CLI, Linkesoft Songbook, LivePrompter PDF.

Spec reference: docs/superpowers/specs/2026-05-09-titan-v0.1-design.md → Section 4
"""

from __future__ import annotations

from titan_chordpro.core.schemas import (
    ChordEvent,
    ChordProDocument,
    InstrumentalLine,
    Line,
    LyricLine,
    Section,
)
from titan_chordpro.writer.profiles.inline_slash import InlineSlashProfile
from titan_chordpro.writer.serializer import _pair_chords_per_measure, render_header

DEFAULT_METER: tuple[int, int] = (4, 4)


class ChordProReferenceProfile:
    """Strict ChordPro reference with grid blocks for instrumentals."""

    name: str = "chordpro_ref"
    description: str = (
        "Strict canonical ChordPro with {start_of_grid}/{end_of_grid} blocks. "
        "Targets chordpro CLI, Linkesoft Songbook, LivePrompter."
    )

    def __init__(self) -> None:
        self._inline = InlineSlashProfile()

    def render(self, doc: ChordProDocument) -> str:
        header = render_header(doc.metadata, doc.provenance)
        meter = doc.metadata.time_signature or DEFAULT_METER
        sections = "\n".join(self._render_section(s, meter) for s in doc.sections)
        return header + sections

    def render_line(self, line: Line) -> str:
        if isinstance(line, LyricLine):
            return self._inline.render_line(line)
        return self.render_instrumental_grid(line, meter=DEFAULT_METER)

    def render_instrumental_grid(self, line: InstrumentalLine, meter: tuple[int, int]) -> str:
        beats_per_measure = meter[0]
        if line.pattern_hint == "full_measure":
            cells_per_measure = self._cells_full_measure(beats_per_measure)
            measures = [
                self._measure_cells(_grid_symbol(c), cells_per_measure) for c in line.chords
            ]
        elif line.pattern_hint == "half_measure":
            pairs = _pair_chords_per_measure(line.chords)
            measures = [
                self._measure_half(_grid_symbol(a), _grid_symbol(b), beats_per_measure)
                for a, b in pairs
            ]
        else:  # pattern_hint == "beat"
            measures = []
            for i in range(0, len(line.chords), beats_per_measure):
                cells = [_grid_symbol(c) for c in line.chords[i : i + beats_per_measure]]
                measures.append(" ".join(cells))

        return "| " + " | ".join(measures) + " |"

    @staticmethod
    def _cells_full_measure(beats: int) -> list[str]:
        return ["."] * beats

    @staticmethod
    def _measure_cells(chord_symbol: str, cell_template: list[str]) -> str:
        cells = [chord_symbol] + cell_template[1:]
        return " ".join(cells)

    @staticmethod
    def _measure_half(symbol_a: str, symbol_b: str, beats: int) -> str:
        half = beats // 2
        cells = [symbol_a] + ["."] * (half - 1) + [symbol_b] + ["."] * (half - 1)
        if beats % 2:
            cells.append(".")
        return " ".join(cells)

    def _render_section(self, section: Section, meter: tuple[int, int]) -> str:
        if all(isinstance(line, LyricLine) for line in section.lines):
            return self._inline._render_section(section)  # noqa: SLF001

        grid_rows = [
            self.render_instrumental_grid(line, meter)
            for line in section.lines
            if isinstance(line, InstrumentalLine)
        ]
        body = "\n".join(grid_rows)
        return f"{{start_of_grid: {section.label}}}\n{body}\n{{end_of_grid}}\n"


def _grid_symbol(chord: ChordEvent) -> str:
    """Bare chord symbol for grid cells (no brackets, slash collapses)."""
    if "/" in chord.symbol:
        return chord.symbol
    if chord.bass_note:
        return f"{chord.symbol}/{chord.bass_note}"
    return chord.symbol

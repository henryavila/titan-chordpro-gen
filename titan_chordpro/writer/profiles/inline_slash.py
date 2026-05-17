"""DEFAULT output profile — `[chord]` inline + `[C]x///` rhythmic notation.

Targets: OnSong, ProPresenter, SongbookPro, iasdermelinda.com.br, and any
ChordPro renderer that accepts inline brackets. Maximizes practical
compatibility at the cost of strict-spec correctness.

Spec reference: docs/superpowers/specs/2026-05-09-titan-v0.1-design.md → Section 4
"""

from __future__ import annotations

from titan_chordpro.core.schemas import (
    ChordProDocument,
    InstrumentalLine,
    Line,
    LyricLine,
    Section,
)
from titan_chordpro.writer.serializer import (
    _format_chord,
    _pair_chords_per_measure,
    render_header,
    render_section_wrapper,
)


class InlineSlashProfile:
    """ChordPro output with inline `[chord]` markers and `[C]x///` rhythm."""

    name: str = "inline_slash"
    description: str = (
        "DEFAULT — inline [chord] markers + [C]x/// rhythm notation. "
        "Compatible with OnSong, ProPresenter, SongbookPro."
    )

    def render(self, doc: ChordProDocument) -> str:
        header = render_header(doc.metadata, doc.provenance)
        sections = "\n".join(self._render_section(s) for s in doc.sections)
        return header + sections

    def render_line(self, line: Line) -> str:
        if isinstance(line, LyricLine):
            return self._render_lyric_line(line)
        return self._render_instrumental_line(line)

    def _render_section(self, section: Section) -> str:
        body = "\n".join(self.render_line(line) for line in section.lines)
        return render_section_wrapper(section, body)

    def _render_lyric_line(self, line: LyricLine) -> str:
        if not line.chord_markers:
            return line.text
        markers = sorted(line.chord_markers, key=lambda m: m.char_position)
        parts: list[str] = []
        cursor = 0
        for marker in markers:
            parts.append(line.text[cursor : marker.char_position])
            parts.append(_format_chord(marker.chord))
            cursor = marker.char_position
        parts.append(line.text[cursor:])
        return "".join(parts)

    def _render_instrumental_line(self, line: InstrumentalLine) -> str:
        if line.pattern_hint == "full_measure":
            return "   ".join(f"[{c.symbol}]x///" for c in line.chords)
        if line.pattern_hint == "half_measure":
            paired = _pair_chords_per_measure(line.chords)
            return "   ".join(f"[{a.symbol}]x/[{b.symbol}]/" for a, b in paired)
        # pattern_hint == "beat"
        return " ".join(f"[{c.symbol}]/" for c in line.chords)

"""Shared writer helpers consumed by all 5 output profiles.

Three responsibilities:
1. `_format_chord(chord)` — single source of truth for the `[Symbol]` /
   `[Symbol/Bass]` decision (handles both slash-in-symbol and independent
   `bass_note` cases).
2. `render_header(meta, prov)` — produces the `{title}`, `{artist}`, `{key}`,
   `{tempo}`, `{time}`, `{capo}`, `{meta: titan_*}`, and metadata.extensions
   directives in spec order (Section 4 → Header rendering).
3. `SECTION_DIRECTIVES` + `render_section_wrapper(section, body)` — maps the
   7 Section.type values to either a start/end directive pair (verse/chorus/
   bridge) or a `{c: <label>}` prepend (intro/outro/instrumental/pre-chorus).

`_pair_chords_per_measure` is used only by InstrumentalLine renderers when
`pattern_hint == "half_measure"`; living here keeps the writer DRY across
profiles.
"""

from __future__ import annotations

from titan_chordpro.core.schemas import (
    ChordEvent,
    Metadata,
    Provenance,
    Section,
)

SECTION_DIRECTIVES: dict[str, tuple[str, str] | None] = {
    "verse": ("{start_of_verse}", "{end_of_verse}"),
    "chorus": ("{start_of_chorus}", "{end_of_chorus}"),
    "bridge": ("{start_of_bridge}", "{end_of_bridge}"),
    "pre-chorus": None,
    "instrumental": None,
    "intro": None,
    "outro": None,
}


def _format_chord(chord: ChordEvent) -> str:
    if "/" in chord.symbol:
        return f"[{chord.symbol}]"
    if chord.bass_note:
        return f"[{chord.symbol}/{chord.bass_note}]"
    return f"[{chord.symbol}]"


def _pair_chords_per_measure(
    chords: list[ChordEvent],
) -> list[tuple[ChordEvent, ChordEvent]]:
    if not chords:
        return []
    pairs: list[tuple[ChordEvent, ChordEvent]] = []
    i = 0
    while i < len(chords) - 1:
        pairs.append((chords[i], chords[i + 1]))
        i += 2
    if i == len(chords) - 1:
        pairs.append((chords[i], chords[i]))
    return pairs


def _format_time_signature(time_sig: tuple[int, int]) -> str:
    num, den = time_sig
    return f"{num}/{den}"


def render_header(meta: Metadata, prov: Provenance) -> str:
    lines: list[str] = [f"{{title: {meta.title}}}"]
    if meta.artist:
        lines.append(f"{{artist: {meta.artist}}}")
    if meta.key:
        lines.append(f"{{key: {meta.key}}}")
    if meta.tempo is not None:
        lines.append(f"{{tempo: {meta.tempo}}}")
    if meta.time_signature is not None:
        lines.append(f"{{time: {_format_time_signature(meta.time_signature)}}}")
    if meta.capo > 0:
        lines.append(f"{{capo: {meta.capo}}}")

    lines.append(f"{{meta: titan_version {prov.titan_version}}}")
    for stage_conf in prov.confidence:
        lines.append(f"{{meta: titan_confidence_{stage_conf.stage} {stage_conf.mean:.2f}}}")
    for k, v in meta.extensions.items():
        lines.append(f"{{meta: {k} {v}}}")

    return "\n".join(lines) + "\n\n"


def render_section_wrapper(section: Section, body: str) -> str:
    directive_pair = SECTION_DIRECTIVES.get(section.type)
    if directive_pair is not None:
        start, end = directive_pair
        return f"{start}\n{body}\n{end}\n"
    return f"{{c: {section.label}}}\n{body}\n"

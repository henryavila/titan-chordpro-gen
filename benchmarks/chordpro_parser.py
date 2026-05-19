"""Minimal ChordPro ground-truth parser.

The iasdermelinda corpus stores ChordPro as plain `[chord]lyrics` text
with `{directive}` lines. There are NO native timestamps. The parser:

  1. Extracts the chord sequence in order of appearance.
  2. Assigns equal-length intervals across the audio duration.

This is intentionally crude — Phase C uses WCSR-majmin to measure which
chords are present in the right *relative* order, not exact alignment.
"""

from __future__ import annotations

import re

_CHORD_RE = re.compile(r"\[([^\[\]]+)\]")
_DIRECTIVE_RE = re.compile(r"^\s*\{[^}]+\}\s*$")


def extract_chord_sequence(chordpro: str) -> list[str]:
    """Return chord symbols in order of appearance in lyric lines.

    Directives like `{t: ...}` and `{key: ...}` are skipped.
    """
    if not chordpro:
        return []
    result: list[str] = []
    for line in chordpro.splitlines():
        if _DIRECTIVE_RE.match(line):
            continue
        for m in _CHORD_RE.finditer(line):
            result.append(m.group(1).strip())
    return result


def to_intervals_labels(
    sequence: list[str],
    duration: float,
) -> tuple[list[tuple[float, float]], list[str]]:
    """Assign equal-length intervals to a chord sequence."""
    if not sequence:
        return [], []
    n = len(sequence)
    step = duration / n
    intervals = [(i * step, (i + 1) * step) for i in range(n)]
    return intervals, list(sequence)

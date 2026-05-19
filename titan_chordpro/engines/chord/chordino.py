# titan_chordpro/engines/chord/chordino.py
"""Chordino via chord-extractor — ChordRecognitionEngine implementation.

Chordino is a VAMP plugin (GPL-2.0). It must be installed via
`scripts/install_vamp.sh` (T49). chord-extractor (MIT-licensed Python
wrapper) calls Chordino as a subprocess; runtime separation means the
GPL contagion does not extend to titan-chordpro-lib (which stays MIT).

Output format:
  - chord_extractor returns objects with `.chord` (e.g. "C:maj", "G:min7",
    "N" for no-chord) and `.timestamp` (start time in seconds).
  - Chord intervals are derived by pairing each onset with the next one;
    the last chord runs to the end of the audio (Chordino does not emit
    an explicit "end" marker — we use a sentinel from soundfile).

F-004 (Phase C): when a bass stem is provided, per-interval bass-note
chroma is computed via `bass_chroma.extract_bass_note`. The detected
note is emitted as `ChordEvent.bass_note` ONLY when it differs from the
chord root (no spurious "F/F" slash chords) AND chroma confidence ≥ 0.5
(asymmetric — root position is the safer default).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Literal

from titan_chordpro.core.exceptions import ChordRecognitionError, EngineUnavailableError
from titan_chordpro.core.schemas import ChordEvent, EngineInfo, TimeStamp
from titan_chordpro.engines.chord.bass_chroma import extract_bass_note

_MAJ_QUAL = ":maj"
_MIN_QUAL = ":min"
_CHORD_ROOT_RE = re.compile(r"^[A-G][#b]?")
_log = logging.getLogger(__name__)


def _load_extractor() -> Any:
    try:
        from chord_extractor.extractors import Chordino
    except ImportError as exc:
        raise EngineUnavailableError(
            "chord_extractor (with Chordino VAMP plugin) is not installed; "
            "run scripts/install_vamp.sh and see docs/setup-vamp.md",
            engine="chordino",
            cause=exc,
        ) from exc
    return Chordino()


def _normalize_chord_symbol(raw: str) -> str | None:
    """Convert chord_extractor output to ChordEvent.symbol format."""
    if not raw or raw == "N":
        return None
    if _MAJ_QUAL in raw:
        root, _, suffix = raw.partition(_MAJ_QUAL)
        return root if not suffix else f"{root}maj{suffix}"
    if _MIN_QUAL in raw:
        root, _, suffix = raw.partition(_MIN_QUAL)
        return f"{root}m{suffix}" if suffix else f"{root}m"
    return raw.replace(":", "")


def _chord_root(symbol: str) -> str:
    """Extract the root letter (sharp form) from a chord symbol.

    Phase C operates on sharp form internally; rendering layer handles
    enharmonic preferences. Flat-to-sharp mapping ensures bass_chroma
    (sharp-only) compares correctly to chord symbols that may carry flats.
    """
    m = _CHORD_ROOT_RE.match(symbol)
    if not m:
        return symbol
    root = m.group(0)
    flat_to_sharp = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#"}
    return flat_to_sharp.get(root, root)


def _probe_duration(path: Path) -> float:
    import soundfile as sf

    return float(sf.info(str(path)).duration)


class ChordinoEngine:
    """Conforms to ChordRecognitionEngine Protocol."""

    def __init__(self) -> None:
        self._extractor = _load_extractor()

    @property
    def info(self) -> EngineInfo:
        return EngineInfo(
            name="chordino",
            version="1.0",
            backend="cpu",
            model_id="chordino",
        )

    @property
    def vocabulary(self) -> Literal["majmin", "sevenths", "tetrads", "extended_170"]:
        return "majmin"

    @property
    def supports_inversions(self) -> bool:
        # Phase C T64 / Codex F-004: bass-stem chroma analysis now active
        # when a bass_stem is provided to detect(). Slash chords F/A, G/B,
        # C/E in the PT-BR corpus emit as inversions when bass-stem chroma
        # confidence ≥ 0.5 and the detected note differs from the chord
        # root. See engines/chord/bass_chroma.py for the chroma extractor.
        return True

    def detect(
        self,
        harmonic_mix: Path,
        bass_stem: Path | None = None,
    ) -> list[ChordEvent]:
        try:
            raw_chords = self._extractor.extract(str(harmonic_mix))
        except Exception as exc:  # noqa: BLE001
            raise ChordRecognitionError(
                f"chordino extraction failed on {harmonic_mix.name}",
                engine="chordino",
                cause=exc,
            ) from exc

        all_events: list[tuple[str | None, float]] = []
        for c in raw_chords:
            symbol = _normalize_chord_symbol(str(c.chord))
            all_events.append((symbol, float(c.timestamp)))

        if not any(sym is not None for sym, _ in all_events):
            return []

        try:
            duration = _probe_duration(harmonic_mix)
        except Exception:  # noqa: BLE001
            duration = all_events[-1][1] + 1.0

        events: list[ChordEvent] = []
        for i, (symbol, start) in enumerate(all_events):
            if symbol is None:
                continue
            end = all_events[i + 1][1] if i + 1 < len(all_events) else duration
            if end < start:
                end = start

            # F-004: derive bass_note from the bass stem if one was provided.
            bass_note: str | None = None
            if bass_stem is not None:
                try:
                    letter, _ = extract_bass_note(bass_stem, start=start, end=end)
                except FileNotFoundError:
                    _log.warning("bass_stem path %s vanished mid-detection; skipping", bass_stem)
                    letter = None
                except Exception as exc:  # noqa: BLE001
                    _log.warning("bass_chroma failed on interval %.3f-%.3f: %s", start, end, exc)
                    letter = None
                if letter is not None and letter != _chord_root(symbol):
                    bass_note = letter

            events.append(
                ChordEvent(
                    symbol=symbol,
                    timestamp=TimeStamp(start=start, end=end),
                    bass_note=bass_note,
                    confidence=1.0,
                    source_engine="chordino",
                )
            )

        return [e for e in events if e.timestamp.end > e.timestamp.start]

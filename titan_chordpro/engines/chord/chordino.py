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
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Literal

from titan_chordpro.core.exceptions import ChordRecognitionError, EngineUnavailableError
from titan_chordpro.core.schemas import ChordEvent, EngineInfo, TimeStamp

_MAJ_QUAL = ":maj"
_MIN_QUAL = ":min"
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
    """Convert chord_extractor output to ChordEvent.symbol format.

    Examples:
        "C:maj"   -> "C"
        "G:min"   -> "Gm"
        "G:min7"  -> "Gm7"
        "C:7"     -> "C7"
        "N"       -> None (no-chord)
        ""        -> None
    """
    if not raw or raw == "N":
        return None
    if _MAJ_QUAL in raw:
        # "C:maj" -> "C", "C:maj7" -> "Cmaj7"
        root, _, suffix = raw.partition(_MAJ_QUAL)
        return root if not suffix else f"{root}maj{suffix}"
    if _MIN_QUAL in raw:
        root, _, suffix = raw.partition(_MIN_QUAL)
        return f"{root}m{suffix}" if suffix else f"{root}m"
    # No quality marker — pass through (e.g. "C:7" stays "C:7" -> sanitize colon).
    return raw.replace(":", "")


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
            version="1.0",  # VAMP plugin version not exposed via wrapper
            backend="cpu",  # VAMP runs natively on CPU
            model_id="chordino",
        )

    @property
    def vocabulary(self) -> Literal["majmin", "sevenths", "tetrads", "extended_170"]:
        return "majmin"

    @property
    def supports_inversions(self) -> bool:
        # Spec §406 mandates v0.1 Chordino "vocab=majmin + bass note → derive
        # inversions". This v0.1.0-b1 release ships without bass-stem chroma
        # analysis — slash chords F/A, G/B, C/E in the PT-BR corpus collapse
        # to root position. Codex cross-model review F-004 (2026-05-18-2116)
        # flags this as a known v0.1 gap; implementation moves to Phase C
        # alongside the validation harness (bass chroma analysis requires
        # librosa/numpy + per-interval pitch detection, not a single edit).
        return False

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

        # Keep ALL events (including N) so end times can be derived against
        # the next boundary — whether that boundary is another chord or a
        # no-chord region. Dropping "N" before this step would smear the
        # previous chord across the silence (caught by Codex review F-003).
        all_events: list[tuple[str | None, float]] = []
        for c in raw_chords:
            symbol = _normalize_chord_symbol(str(c.chord))
            all_events.append((symbol, float(c.timestamp)))

        # Skip if no real chord exists at all.
        if not any(sym is not None for sym, _ in all_events):
            return []

        # Derive end times: each event runs until the next; last runs to file end.
        try:
            duration = _probe_duration(harmonic_mix)
        except Exception:  # noqa: BLE001
            # Fallback: extend last event by 1s (defensive; loses precision).
            duration = all_events[-1][1] + 1.0

        events: list[ChordEvent] = []
        for i, (symbol, start) in enumerate(all_events):
            if symbol is None:
                continue  # N markers are boundaries only, not emitted as ChordEvents
            end = all_events[i + 1][1] if i + 1 < len(all_events) else duration
            if end < start:
                end = start
            # Phase B: bass_note left None even when bass_stem is provided;
            # bass detection pass arrives in Phase C alongside corpus validation.
            events.append(
                ChordEvent(
                    symbol=symbol,
                    timestamp=TimeStamp(start=start, end=end),
                    bass_note=None,
                    confidence=1.0,
                    source_engine="chordino",
                )
            )

        # Defensive: discard zero-duration events caused by duplicate onsets.
        return [e for e in events if e.timestamp.end > e.timestamp.start]

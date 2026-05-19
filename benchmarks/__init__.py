"""Validation harness package.

Public modules:
- corpus: load songs.csv into Song dataclasses
- audio_downloader: yt-dlp wrapper with disk cache
- chordpro_parser: parse ChordPro ground truth into ChordProDocument
- metrics: mir_eval adapters (chord alphabet, time intervals)
- validation_runner: full corpus run → ValidationReport
- divergence_ranker: severity ranking + report writer

The package is opt-in (requires `pip install .[validation]`). It is NOT
imported by `titan_chordpro` itself — keeping the validation harness off
the library import surface is enforced by tests/integration/test_validation_smoke.py.
"""

from __future__ import annotations

__all__ = ["__version__"]
__version__ = "0.1.0c0.dev0"

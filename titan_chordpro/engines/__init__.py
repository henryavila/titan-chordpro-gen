# titan_chordpro/engines/__init__.py
"""Concrete engine implementations for Phase B+.

Each submodule (beat, separation, transcription, alignment, chord, lang)
provides a wrapper class that conforms to the matching Protocol in
`titan_chordpro.core.protocols`. Wrappers import their backing libraries
lazily so importing this package never triggers torch/audio-separator/etc.
"""

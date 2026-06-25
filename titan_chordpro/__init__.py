from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

from titan_chordpro.version import __version__

__all__ = ["ChordProDocument", "transcribe", "__version__"]

if TYPE_CHECKING:
    from titan_chordpro.core.schemas import ChordProDocument
    from titan_chordpro.orchestrator import transcribe


_LAZY_EXPORTS = {
    "ChordProDocument": ("titan_chordpro.core.schemas", "ChordProDocument"),
    "transcribe": ("titan_chordpro.orchestrator", "transcribe"),
}


def __getattr__(name: str) -> object:
    try:
        module_name, attr_name = _LAZY_EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None

    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))

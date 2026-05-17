from typing import Protocol, runtime_checkable

from titan_chordpro.core.schemas import ChordProDocument


@runtime_checkable
class OutputProfile(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def description(self) -> str: ...
    def render(self, doc: ChordProDocument) -> str: ...

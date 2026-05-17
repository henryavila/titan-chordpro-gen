"""Stub for SQL → JSON export. Fully implemented in Phase C."""

import json
from pathlib import Path


def export_corpus(output: Path) -> None:
    output.write_text(json.dumps([], indent=2))
    print(f"(stub) wrote empty corpus to {output}")

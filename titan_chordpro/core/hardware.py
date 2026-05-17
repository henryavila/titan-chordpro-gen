# titan_chordpro/core/hardware.py
"""Hardware backend detection.

Single source of truth for which PyTorch backend the engines should target.
Engines never call `torch.backends.mps.is_available()` themselves — they
ask this module. The probe runs once per process and the result is cached.

Public API:
    detect_backend(prefer=None) -> Backend
    hardware_to_torch_device(backend) -> torch.device
"""

from __future__ import annotations

import logging
from typing import Any, Literal

Backend = Literal["mps", "cuda", "cpu"]

_VALID_BACKENDS: frozenset[str] = frozenset({"mps", "cuda", "cpu"})
_cached_backend: Backend | None = None

_log = logging.getLogger(__name__)


def detect_backend(prefer: str | None = None) -> Backend:
    """Return the best PyTorch backend available on this host.

    Args:
        prefer: One of "mps", "cuda", "cpu" to force a specific backend.
            If the preferred backend is not actually available, the call
            falls back to autodetect (does NOT raise). Unknown strings are
            silently ignored (also fall back to autodetect).

    Returns:
        "mps" on Apple Silicon with MPS available,
        "cuda" on a host with a CUDA-capable GPU,
        "cpu" otherwise (including when torch itself is missing).

    The result is cached per process. Use the private `_cached_backend = None`
    reset for tests that need to re-probe.
    """
    global _cached_backend

    if prefer == "cpu":
        # "cpu" is always honored — useful for CI, debugging, deterministic tests.
        return "cpu"

    if _cached_backend is not None and prefer is None:
        return _cached_backend

    try:
        import torch  # noqa: F401  — presence check
    except ImportError:
        _log.debug("torch not importable; defaulting to cpu backend")
        _cached_backend = "cpu"
        return "cpu"

    import torch

    auto: Backend = "cpu"
    # MPS check is gated behind hasattr because torch < 1.12 lacks the namespace.
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        auto = "mps"
    elif torch.cuda.is_available():
        auto = "cuda"

    if prefer in _VALID_BACKENDS:
        # Honor preference only if the backend is actually available.
        if prefer == "mps" and auto == "mps":
            _cached_backend = "mps"
            return "mps"
        if prefer == "cuda" and torch.cuda.is_available():
            _cached_backend = "cuda"
            return "cuda"
        # Preferred backend unavailable — fall through to autodetect.
        _log.info("preferred backend %r unavailable; using %r", prefer, auto)

    _cached_backend = auto
    return auto


def hardware_to_torch_device(backend: Backend) -> Any:
    """Translate a backend literal into the torch.device an engine should use.

    Raises ValueError for unsupported backends. Imports torch lazily so this
    function is only callable when torch is actually installed (the [mac] or
    [cuda] extras must be present).
    """
    if backend not in _VALID_BACKENDS:
        raise ValueError(f"unsupported backend: {backend!r}")
    import torch

    return torch.device(backend)

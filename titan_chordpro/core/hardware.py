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

from titan_chordpro.core.exceptions import TitanConfigError

Backend = Literal["mps", "cuda", "cpu"]

_VALID_BACKENDS: frozenset[str] = frozenset({"mps", "cuda", "cpu"})
_cached_backend: Backend | None = None

_log = logging.getLogger(__name__)


def detect_backend(prefer: str | None = None) -> Backend:
    """Return the best PyTorch backend available on this host.

    Args:
        prefer: One of "mps", "cuda", "cpu" to force a specific backend.
            "cpu" is always honored. "mps"/"cuda" raise TitanConfigError
            when the requested backend is not available on this host —
            silent fallback is a footgun for users debugging dual-path
            behavior. Unknown strings raise ValueError.
            None means autodetect (cached per process).

    Returns:
        "mps" on Apple Silicon with MPS available,
        "cuda" on a host with a CUDA-capable GPU,
        "cpu" otherwise (including when torch itself is missing).
    """
    global _cached_backend

    if prefer == "cpu":
        return "cpu"

    if prefer is not None and prefer not in _VALID_BACKENDS:
        raise ValueError(
            f"unsupported backend preference {prefer!r}; expected one of {sorted(_VALID_BACKENDS)}"
        )

    if _cached_backend is not None and prefer is None:
        return _cached_backend

    try:
        import torch  # noqa: F401  — presence check
    except ImportError:
        if prefer in ("mps", "cuda"):
            raise TitanConfigError(
                f"requested backend {prefer!r} is not available: torch is not installed"
            ) from None
        _log.debug("torch not importable; defaulting to cpu backend")
        _cached_backend = "cpu"
        return "cpu"

    import torch

    auto: Backend = "cpu"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        auto = "mps"
    elif torch.cuda.is_available():
        auto = "cuda"

    if prefer == "mps":
        if auto == "mps":
            _cached_backend = "mps"
            return "mps"
        raise TitanConfigError(
            f"requested backend 'mps' is not available on this host (autodetect: {auto!r})"
        )
    if prefer == "cuda":
        if torch.cuda.is_available():
            _cached_backend = "cuda"
            return "cuda"
        raise TitanConfigError(
            f"requested backend 'cuda' is not available on this host (autodetect: {auto!r})"
        )

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


def release_gpu_memory() -> None:
    """Best-effort release of GPU-side allocations (MPS / CUDA).

    Phase C T70 iter — helps the orchestrator hand back memory between
    pipeline stages so the next heavy model has headroom. No-op when
    torch is not installed (e.g., mock-only test runs in py3.14 venv).

    Calls torch.cuda.empty_cache() on CUDA hosts and torch.mps.empty_cache()
    on Apple Silicon. Both are safe to call even when the cache is empty.
    """
    try:
        import torch
    except ImportError:
        return

    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            torch.mps.empty_cache()
    except Exception as exc:  # noqa: BLE001
        # Defensive: empty_cache is documented as best-effort and has been
        # known to raise on rare driver versions; we never want a memory
        # hint to crash the pipeline.
        _log.debug("release_gpu_memory: ignoring %s: %s", type(exc).__name__, exc)

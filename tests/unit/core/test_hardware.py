# tests/unit/core/test_hardware.py
"""Tests for backend hardware probe."""

from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.mark.unit
class TestDetectBackend:
    def test_returns_one_of_three_literals(self) -> None:
        from titan_chordpro.core.hardware import detect_backend

        backend = detect_backend()
        assert backend in ("mps", "cuda", "cpu")

    def test_prefer_cpu_always_honored(self) -> None:
        from titan_chordpro.core.hardware import detect_backend

        assert detect_backend(prefer="cpu") == "cpu"

    def test_prefer_unknown_raises_value_error(self) -> None:
        """Codex F-008: unknown backend strings raise ValueError (was silent fallback)."""
        from titan_chordpro.core.hardware import detect_backend

        with pytest.raises(ValueError, match="unsupported backend preference"):
            detect_backend(prefer="tpu")  # type: ignore[arg-type]

    def test_prefer_unavailable_explicit_backend_raises(self) -> None:
        """Codex F-008: explicit mps/cuda preference must fail-fast when unavailable."""
        from titan_chordpro.core import hardware
        from titan_chordpro.core.exceptions import TitanConfigError

        with patch.dict("sys.modules", {"torch": None}):
            hardware._cached_backend = None
            with pytest.raises(TitanConfigError):
                hardware.detect_backend(prefer="cuda")
        hardware._cached_backend = None

    def test_torch_missing_returns_cpu(self) -> None:
        from titan_chordpro.core import hardware

        # Simulate torch import failing.
        with patch.dict("sys.modules", {"torch": None}):
            hardware._cached_backend = None  # bust cache
            assert hardware.detect_backend() == "cpu"
        hardware._cached_backend = None  # restore for next test

    def test_caching_returns_same_value(self) -> None:
        from titan_chordpro.core.hardware import detect_backend

        a = detect_backend()
        b = detect_backend()
        assert a is b or a == b


@pytest.mark.unit
class TestHardwareToTorchDevice:
    def test_cpu_string(self) -> None:
        pytest.importorskip("torch")
        from titan_chordpro.core.hardware import hardware_to_torch_device

        device = hardware_to_torch_device("cpu")
        assert str(device) == "cpu"

    def test_unsupported_backend_raises(self) -> None:
        pytest.importorskip("torch")
        from titan_chordpro.core.hardware import hardware_to_torch_device

        with pytest.raises(ValueError, match="unsupported backend"):
            hardware_to_torch_device("foo")  # type: ignore[arg-type]

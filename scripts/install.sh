#!/usr/bin/env bash
# scripts/install.sh
# End-to-end installer for Titan ChordPro Gen on macOS Apple Silicon.
#
# Sets up everything needed for `scripts/render_from_url.py` to work from
# a fresh clone:
#   1. Homebrew prerequisites (python@3.12, ffmpeg, git — vamp-plugin-sdk
#      and boost are pulled in by install_vamp.sh)
#   2. Python 3.12 virtualenv at `.venv-py312/`
#   3. Project + ML deps via `pip install -e .[mac,validation,dev]`
#   4. Chordino Vamp plugin built from source (delegates to install_vamp.sh)
#
# Idempotent — safe to re-run on an existing checkout. Lazy ML model
# downloads (whisper medium ~1.5 GB, htdemucs, BeatThis, torchaudio MMS)
# happen on first pipeline run, not here.
#
# Linux / CUDA / Windows are not supported by this script. For those,
# install manually: `pip install -e .[cuda,validation,dev]` plus run
# scripts/install_vamp.sh (Linux path) and ensure ffmpeg is in PATH.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

OS="$(uname -s)"
ARCH="$(uname -m)"
VENV=".venv-py312"

if [ "$OS" != "Darwin" ]; then
    echo "ERROR: this installer targets macOS only (detected: $OS)."
    echo "For Linux/CUDA install manually — see README.md."
    exit 1
fi

if [ "$ARCH" != "arm64" ]; then
    echo "WARN: detected $ARCH on macOS. Intel macs are untested."
    echo "      Continuing, but if PyTorch MPS fails, fall back to CPU."
fi

if ! command -v brew >/dev/null 2>&1; then
    echo "ERROR: Homebrew is required. Install from https://brew.sh"
    exit 1
fi

echo "==> [1/4] Homebrew prerequisites"
# `brew install` is idempotent — already-installed formulas just print a
# notice. Bundling them in one call so a single brew lock is held.
brew install python@3.12 ffmpeg git

PYTHON312="$(brew --prefix python@3.12)/bin/python3.12"
if [ ! -x "$PYTHON312" ]; then
    echo "ERROR: python3.12 not found at $PYTHON312 after brew install."
    exit 1
fi

echo "==> [2/4] Python virtualenv at $VENV (python 3.12)"
if [ ! -d "$VENV" ]; then
    "$PYTHON312" -m venv "$VENV"
else
    echo "    reusing existing $VENV"
fi

# Activate so the rest of the script and the install_vamp.sh verify step
# both use the venv's interpreter (otherwise `python3` would resolve to
# the system one, which lacks vampyhost).
# shellcheck disable=SC1091
source "$VENV/bin/activate"

echo "==> [3/4] Installing project + ML extras (.[mac,validation,dev])"
pip install --upgrade pip wheel
pip install -e ".[mac,validation,dev]"

echo "==> [4/4] Building & installing the Chordino Vamp plugin"
"$REPO_ROOT/scripts/install_vamp.sh"

echo
echo "==> Install complete."
echo
echo "Try it out (cached audio, sub-second on re-runs):"
echo "    $VENV/bin/python scripts/render_from_url.py <youtube_url>"
echo
echo "On the first URL, expect ~5 min cold (htdemucs + whisper medium"
echo "model download + chord/beat/align). Models cache locally and the"
echo "per-stage cache under ~/.cache/titan-chordpro/ makes re-runs fast."

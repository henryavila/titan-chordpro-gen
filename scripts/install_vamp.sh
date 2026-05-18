#!/usr/bin/env bash
# scripts/install_vamp.sh
# Install the VAMP plugin SDK + Chordino plugin on macOS or Linux.
# See docs/setup-vamp.md for context.

set -euo pipefail

OS="$(uname -s)"
CHORDINO_VERSION="${CHORDINO_VERSION:-1.2}"

install_macos() {
    echo "==> Installing VAMP plugin SDK (Homebrew)"
    if ! command -v brew >/dev/null 2>&1; then
        echo "ERROR: Homebrew is required. See https://brew.sh"
        exit 1
    fi
    brew install vamp-plugin-sdk sonic-annotator

    # Chordino plugin
    plugin_dir="$HOME/Library/Audio/Plug-Ins/Vamp"
    mkdir -p "$plugin_dir"
    archive_url="https://code.soundsoftware.ac.uk/attachments/download/2540/chordino-vamp-plugin-mac.tar.gz"
    archive="/tmp/chordino-vamp.tar.gz"

    echo "==> Downloading Chordino plugin"
    curl -fL -o "$archive" "$archive_url"
    tar -xzf "$archive" -C "$plugin_dir"
    rm "$archive"
}

install_linux() {
    echo "==> Installing VAMP plugin SDK (apt-get)"
    if ! command -v apt-get >/dev/null 2>&1; then
        echo "ERROR: apt-get not found. Manual install required — see docs/setup-vamp.md"
        exit 1
    fi
    sudo apt-get update
    sudo apt-get install -y vamp-plugin-sdk sonic-annotator

    plugin_dir="$HOME/vamp"
    mkdir -p "$plugin_dir"
    archive_url="https://code.soundsoftware.ac.uk/attachments/download/2539/chordino-vamp-plugin-linux64.tar.gz"
    archive="/tmp/chordino-vamp.tar.gz"

    echo "==> Downloading Chordino plugin"
    curl -fL -o "$archive" "$archive_url"
    tar -xzf "$archive" -C "$plugin_dir"
    rm "$archive"
}

verify() {
    echo "==> Verifying installation"
    if ! command -v sonic-annotator >/dev/null 2>&1; then
        echo "ERROR: sonic-annotator not on PATH"
        exit 1
    fi
    if ! sonic-annotator -l 2>/dev/null | grep -q "nnls-chroma:chordino"; then
        echo "WARN: chordino plugin not detected by sonic-annotator -l"
        echo "      check VAMP_PATH; expected one of: $HOME/vamp, $HOME/Library/Audio/Plug-Ins/Vamp"
    else
        echo "OK: chordino plugin detected"
    fi
}

case "$OS" in
    Darwin) install_macos ;;
    Linux) install_linux ;;
    *) echo "Unsupported OS: $OS"; exit 1 ;;
esac

verify
echo "==> Done. Re-run pytest tests/integration/test_chordino_smoke.py to verify."

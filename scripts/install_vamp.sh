#!/usr/bin/env bash
# scripts/install_vamp.sh
# Install the VAMP plugin SDK + Chordino (nnls-chroma) VAMP plugin.
#
# Background: the upstream binary mirror at code.soundsoftware.ac.uk no longer
# serves the macOS tarball reliably, and Homebrew dropped `sonic-annotator`
# from core. We don't need sonic-annotator — chord_extractor calls the plugin
# via the `vamp` Python package (vampyhost direct binding). We DO need:
#   1. The VAMP SDK headers + libvamp-sdk.a (Homebrew on macOS, apt on Linux)
#   2. The nnls-chroma plugin shared library (.dylib / .so) for the running
#      architecture, in a VAMP plugin search dir
#   3. The plugin's .cat and .n3 RDF descriptors next to the library
#
# Strategy: build nnls-chroma from source (c4dm/nnls-chroma on GitHub) for the
# current arch. This is the only path that works on Apple Silicon as of 2026.
#
# See docs/setup-vamp.md.

set -euo pipefail

OS="$(uname -s)"
ARCH="$(uname -m)"
BUILD_DIR="${BUILD_DIR:-/tmp/titan-build/nnls-chroma}"
NNLS_REPO="${NNLS_REPO:-https://github.com/c4dm/nnls-chroma.git}"

clone_or_update_source() {
    mkdir -p "$(dirname "$BUILD_DIR")"
    if [ -d "$BUILD_DIR/.git" ]; then
        echo "==> Updating existing source at $BUILD_DIR"
        git -C "$BUILD_DIR" pull --ff-only
    else
        echo "==> Cloning nnls-chroma source to $BUILD_DIR"
        rm -rf "$BUILD_DIR"
        git clone --depth=1 "$NNLS_REPO" "$BUILD_DIR"
    fi
}

install_macos() {
    if ! command -v brew >/dev/null 2>&1; then
        echo "ERROR: Homebrew is required on macOS. See https://brew.sh"
        exit 1
    fi
    echo "==> Installing build deps via Homebrew (vamp-plugin-sdk + boost)"
    brew install vamp-plugin-sdk boost

    VAMP_PREFIX="$(brew --prefix vamp-plugin-sdk)"
    BOOST_PREFIX="$(brew --prefix boost)"
    plugin_dir="$HOME/Library/Audio/Plug-Ins/Vamp"

    clone_or_update_source
    echo "==> Building nnls-chroma for $ARCH"
    (
        cd "$BUILD_DIR"
        make -f Makefile.osx clean >/dev/null 2>&1 || true
        make -f Makefile.osx \
            VAMP_SDK_DIR="$VAMP_PREFIX/include" \
            BOOST_ROOT="$BOOST_PREFIX/include" \
            ARCHFLAGS="-mmacosx-version-min=11.0 -arch $ARCH" \
            LDFLAGS="-mmacosx-version-min=11.0 -arch $ARCH -dynamiclib -install_name nnls-chroma.dylib $VAMP_PREFIX/lib/libvamp-sdk.a -exported_symbols_list vamp-plugin.list -framework Accelerate"
    )

    echo "==> Installing plugin to $plugin_dir"
    mkdir -p "$plugin_dir"
    cp "$BUILD_DIR/nnls-chroma.dylib" "$plugin_dir/"
    cp "$BUILD_DIR/nnls-chroma.cat" "$plugin_dir/"
    cp "$BUILD_DIR/nnls-chroma.n3" "$plugin_dir/"
}

install_linux() {
    if ! command -v apt-get >/dev/null 2>&1; then
        echo "ERROR: apt-get not found. Manual install required — see docs/setup-vamp.md"
        exit 1
    fi
    echo "==> Installing build deps (vamp-plugin-sdk + libboost-dev)"
    sudo apt-get update
    sudo apt-get install -y vamp-plugin-sdk libboost-dev build-essential git gfortran

    plugin_dir="$HOME/vamp"

    clone_or_update_source
    echo "==> Building nnls-chroma for $ARCH"
    (
        cd "$BUILD_DIR"
        make -f Makefile.linux clean >/dev/null 2>&1 || true
        make -f Makefile.linux
    )

    echo "==> Installing plugin to $plugin_dir"
    mkdir -p "$plugin_dir"
    cp "$BUILD_DIR"/nnls-chroma.so "$plugin_dir/"
    cp "$BUILD_DIR"/nnls-chroma.cat "$plugin_dir/"
    cp "$BUILD_DIR"/nnls-chroma.n3 "$plugin_dir/"
}

verify() {
    echo "==> Verifying installation via vampyhost"
    if ! python3 -c "import vampyhost" >/dev/null 2>&1; then
        echo "WARN: 'vampyhost' Python module not importable in current interpreter."
        echo "      Install chord-extractor in the project venv: 'pip install -e .[mac]'"
        echo "      Then re-run: python -c \"import vampyhost; print(vampyhost.list_plugins())\""
        return
    fi
    python3 - <<'PY'
import sys
import vampyhost
plugins = vampyhost.list_plugins()
if "nnls-chroma:chordino" in plugins:
    print(f"OK: chordino plugin discovered ({len(plugins)} plugins total)")
else:
    print(f"FAIL: chordino plugin not in vampyhost.list_plugins() -> {plugins}")
    print(f"      search paths: {vampyhost.get_plugin_path()}")
    sys.exit(1)
PY
}

case "$OS" in
    Darwin) install_macos ;;
    Linux) install_linux ;;
    *) echo "Unsupported OS: $OS"; exit 1 ;;
esac

verify
echo "==> Done. Re-run pytest tests/integration/test_chordino_smoke.py to verify integration."

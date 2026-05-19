# Setting up the Chordino VAMP plugin

The `titan_chordpro` Chordino engine wraps the [nnls-chroma / Chordino](https://github.com/c4dm/nnls-chroma)
VAMP plugin (GPL-2.0). The plugin is a native dynamic library loaded at
runtime by the `vamp` Python package (which ships a `vampyhost` ctypes
binding). Because of the GPL license, we do NOT bundle Chordino in the
titan-chordpro wheel; users build and install it locally.

> **Why build from source?** The original macOS binary tarball hosted at
> `code.soundsoftware.ac.uk` is no longer reliably reachable, and the
> `chord_extractor` PyPI package only bundles a Linux x86_64 `.so` (not
> Apple Silicon). Building from source is the only path that works on
> macOS arm64 today, and the build itself is small (~30s, no heavy deps).

Quick install
-------------

```
./scripts/install_vamp.sh
```

This handles both macOS (Homebrew: `vamp-plugin-sdk` + `boost`; plugin to
`~/Library/Audio/Plug-Ins/Vamp`) and Linux (apt: `vamp-plugin-sdk` +
`libboost-dev`; plugin to `~/vamp`). Verifies via `vampyhost.list_plugins()`.

Manual install (macOS, Apple Silicon)
-------------------------------------

1. `brew install vamp-plugin-sdk boost`
2. `git clone --depth=1 https://github.com/c4dm/nnls-chroma.git /tmp/nnls-chroma`
3. Build the plugin for arm64:

   ```bash
   cd /tmp/nnls-chroma
   VAMP_PREFIX="$(brew --prefix vamp-plugin-sdk)"
   BOOST_PREFIX="$(brew --prefix boost)"
   make -f Makefile.osx \
       VAMP_SDK_DIR="$VAMP_PREFIX/include" \
       BOOST_ROOT="$BOOST_PREFIX/include" \
       ARCHFLAGS="-mmacosx-version-min=11.0 -arch arm64" \
       LDFLAGS="-mmacosx-version-min=11.0 -arch arm64 -dynamiclib \
                -install_name nnls-chroma.dylib \
                $VAMP_PREFIX/lib/libvamp-sdk.a \
                -exported_symbols_list vamp-plugin.list \
                -framework Accelerate"
   ```
4. Install plugin + descriptors:

   ```bash
   mkdir -p ~/Library/Audio/Plug-Ins/Vamp
   cp nnls-chroma.dylib nnls-chroma.cat nnls-chroma.n3 ~/Library/Audio/Plug-Ins/Vamp/
   ```
5. Verify (in the project venv with `chord-extractor` installed):

   ```bash
   python -c "import vampyhost; print(vampyhost.list_plugins())"
   # → ['nnls-chroma:chordino', 'nnls-chroma:nnls-chroma', 'nnls-chroma:tuning']
   ```

Manual install (Linux)
----------------------

1. `sudo apt-get install vamp-plugin-sdk libboost-dev build-essential git gfortran`
2. `git clone --depth=1 https://github.com/c4dm/nnls-chroma.git && cd nnls-chroma`
3. `make -f Makefile.linux`
4. `mkdir -p ~/vamp && cp nnls-chroma.so nnls-chroma.cat nnls-chroma.n3 ~/vamp/`
5. Verify as above.

Troubleshooting
---------------

- `vampyhost.list_plugins()` returns `[]` — plugin not in a known dir. macOS
  searches `~/Library/Audio/Plug-Ins/Vamp` and `/Library/Audio/Plug-Ins/Vamp`;
  Linux uses `$HOME/vamp` + `/usr/local/lib/vamp` + `/usr/lib/vamp`. Override
  with `VAMP_PATH=/abs/path/to/dir`.
- `boost/tokenizer.hpp file not found` during build — boost not linked. Run
  `brew link boost --overwrite` and retry.
- `ld: warning: object file ... built for newer macOS version` — harmless;
  the `libvamp-sdk.a` archive was built against the current SDK while we
  link for `-mmacosx-version-min=11.0`. Runtime is fine.
- `chord_extractor` package import warning about `VAMP_PATH` not being set —
  that warning fires unconditionally on macOS. As long as the verify step
  prints `OK`, the plugin is being found via the standard macOS dir.
- Integration test `test_chordino_smoke.py` is `SKIPPED` — see the test
  module: it skips when `chord_extractor` is not importable OR when
  `vampyhost.list_plugins()` contains no `nnls-chroma:chordino` entry.

CI
--

The plugin must be present in CI to exercise the smoke test. On ubuntu-latest
the workflow runs `./scripts/install_vamp.sh` before the test job; on macOS
runners the same script handles Homebrew + source build. When the plugin is
unavailable, `test_chordino_smoke.py` skips automatically (it does NOT fail
the build).

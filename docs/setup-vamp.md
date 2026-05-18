# Setting up the VAMP plugin SDK + Chordino plugin

The `titan_chordpro` Chordino engine wraps the [Chordino](https://www.isophonics.net/nnls-chroma)
VAMP plugin (GPL-2.0). VAMP plugins live outside the Python ecosystem — they
are dynamic libraries loaded by the `sonic-annotator` host process at runtime.
Because of the GPL license, we do NOT bundle Chordino in the titan-chordpro
wheel; users install it locally.

Quick install
-------------

```
./scripts/install_vamp.sh
```

This handles both macOS (Homebrew + plugin download to
`~/Library/Audio/Plug-Ins/Vamp`) and Linux (apt-get + plugin to `~/vamp`).

Manual install (macOS)
----------------------

1. `brew install vamp-plugin-sdk sonic-annotator`
2. Download the [Chordino plugin (mac)](https://code.soundsoftware.ac.uk/projects/nnls-chroma/files).
3. Extract `.dylib` + `.cat` + `.n3` files to `~/Library/Audio/Plug-Ins/Vamp/`.
4. Verify: `sonic-annotator -l | grep chordino`.

Manual install (Linux)
----------------------

1. `sudo apt-get install vamp-plugin-sdk sonic-annotator`
2. Download the [Chordino plugin (linux64)](https://code.soundsoftware.ac.uk/projects/nnls-chroma/files).
3. Extract `.so` + `.cat` + `.n3` files to `~/vamp/`.
4. Verify: `sonic-annotator -l | grep chordino`.

Troubleshooting
---------------

- `sonic-annotator: command not found` — plugin SDK not installed.
- `sonic-annotator -l` lists no Chordino plugin — wrong directory. Set
  `VAMP_PATH=<dir-containing-.so-or-.dylib> sonic-annotator -l`.
- Integration test `test_chordino_smoke.py` is `SKIPPED` — `chord_extractor`
  Python package not installed. Install via `pip install -e .[mac]` and re-run.
- `RuntimeError: VAMP plugin not found` from `chord_extractor` — confirm
  the plugin directory is in `VAMP_PATH` (export it in your shell rc).

CI
--

GitHub Actions installs the plugin on ubuntu-latest via apt-get in
`.github/workflows/ci.yml` (T58). macOS-14 jobs install via Homebrew. When
the plugin is unavailable, `test_chordino_smoke.py` skips automatically.

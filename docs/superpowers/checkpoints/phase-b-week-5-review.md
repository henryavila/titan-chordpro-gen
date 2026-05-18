# Phase B — Week 5 Architectural Review (Source separation + cache)

You are an Opus subagent doing architectural review of Phase B Week 5 (T41-T43: htdemucs_ft wrapper + cache helper). Sonnet has finished Week 5. Source separation is the heaviest stage by output size (4 WAV files per run); a bug in path resolution silently corrupts every downstream test.

## What was supposed to be built

1. `docs/superpowers/plans/2026-05-17-titan-v0.1-phase-b.md` — Week 5 section (T41-T43 + Checkpoint 5).
2. `docs/superpowers/specs/2026-05-09-titan-v0.1-design.md` — Section 2.1 (SourceSeparationEngine) + "JSON serialization" subsection.

## What actually got built

```bash
ls -la titan_chordpro/engines/separation/ titan_chordpro/core/cache.py
git log --oneline -- titan_chordpro/engines/separation/ titan_chordpro/core/cache.py
pytest tests/unit/engines/separation/ tests/unit/core/test_cache.py -v
pytest tests/integration/test_htdemucs_smoke.py -v
```

Read in full:
- `titan_chordpro/engines/separation/htdemucs.py`
- `titan_chordpro/core/cache.py`

## Focus areas

### 1. StemSet audio_id (T41)
- Is `audio_id` sha256 of the SOURCE audio bytes (not the output stems)? Stems vary per separation run; source bytes are stable.
- Is the sha256 hex-encoded (not base64, not raw bytes)?

### 2. Stem path resolution (T41)
- Is the mapping `{Vocals, Bass, Drums, Other} -> Path` robust to `python-audio-separator` putting stems in arbitrary order?
- What happens if a stem filename contains the parent directory's name that also matches `(Vocals)` (e.g., `Vocals_Demo_(Vocals)_htdemucs_ft.wav`)? Does the substring match resolve correctly?
- Does the wrapper raise `SeparationError` with `audio_id=` populated when fewer than 4 stems are produced?

### 3. Duration probe (T41)
- Is `_probe_duration` called on the VOCALS stem (not the source)? Source may not be at htdemucs's 44.1kHz output rate.
- Does the probe use `soundfile.info()` (header-only, fast) or `soundfile.read()` (loads samples, slow)?
- Is the EngineUnavailableError raised cleanly if soundfile is missing (it's in `[dev]` so this is mostly defensive)?

### 4. Cache helper (T43)
- Does `cache_dir()` create the directory eagerly (so the caller can write immediately) or lazily?
- Does `stage_file()` NOT create the file (callers may want to check existence first)?
- Are the 6 stage names in spec ("stems", "transcription", "alignment", "chords", "beats", "syllables") all covered by `_VALID_STAGES`?
- Does the cache root default to `.titan-cache` in CWD per spec, NOT in the user home dir?

### 5. Path layout matches spec
- Compare against spec Section 2 "JSON serialization (cache opt-in)" — same nesting (`<root>/<audio_id>/<stage>.json`)?
- Does the layout allow a future Phase C `audio_downloader.py` to put downloaded audio alongside cache (e.g., `<root>/<audio_id>/source.mp3`)? If not, flag the constraint.

### 6. No side effects on import
- `import titan_chordpro.core.cache` should NOT create `.titan-cache/` anywhere.
- `import titan_chordpro.engines.separation.htdemucs` should NOT trigger model download.

## What NOT to review

- htdemucs_ft model accuracy on real music — Phase C.
- Cache invalidation strategy — Phase C concern (when sources change).
- Bass note detection for slash chord synthesis — explicitly deferred to Phase C in T48 RI.

## Output format

```
# Phase B Week 5 Architectural Review

## Status
[Sound / Drift detected / Path-resolution bug found]

## Findings
1. [File:line] — Issue — Severity (Critical/Significant/Minor)

## Continue to Week 6?
[Yes / Yes with caveats / NO — fix first]

## Notes for Henry
```

Max 500 words. Extra scrutiny on audio_id derivation and stem path resolution — those bugs are invisible in the schema but corrupt every downstream stage.

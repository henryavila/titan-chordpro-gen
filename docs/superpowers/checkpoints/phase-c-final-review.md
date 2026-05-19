# Phase C — Final Review (before v0.1.0-c0 tag)

You are an Opus subagent doing the FINAL review of Phase C before Henry tags `v0.1.0-c0`. Phase C is the first phase where Titan output is measured against real ground truth — the bar for "shipped" is higher than Phase A's "compiles + tests pass" or Phase B's "engines load on M-series."

## What Phase C promised

From `docs/superpowers/plans/2026-05-19-titan-v0.1-phase-c.md` (and locked-in scope decisions 2026-05-19):

1. Validation harness over **all 151 songs** in `chordpros.csv/songs.csv` (Tier 2.5, exceeds spec §1518 target of 30 stratified).
2. **F-004 — Chordino bass-note inversion** via librosa CQT chroma. Asymmetric gate: emit only when confidence ≥ 0.5 AND differs from chord root.
3. **Cache JSON serialization** — `transcribe(cache=True)` round-trips all 8 stages.
4. Nightly cron at 06:00 UTC.
5. CLI polish (rich progress, `--validate`).
6. README + CHANGELOG + v0.1.0c0 version bump.
7. Spec §1683 targets:
   - Tier 2 WCSR-majmin ≥ 70%
   - Beat F-measure ≥ 0.85 (informational; not a hard gate for first run)
   - Word alignment median offset < 100ms (same)
   - Top-10 divergences: ≤ 3 are "Titan errado"

## What to verify

```bash
git log --oneline v0.1.0-b1..HEAD
git diff --stat v0.1.0-b1..HEAD
pytest -q
cat titan_chordpro/version.py
ls -la benchmarks/
sed -n '1,30p' CHANGELOG.md
grep -n 'supports_inversions' titan_chordpro/engines/chord/chordino.py
```

Read in full:
- `docs/roadmap.md` Updates Log latest entry — does it claim ✅ on Phase C deliverables that the code actually delivers?
- `CHANGELOG.md` [0.1.0c0] section — does every entry map to a real commit?
- `benchmarks/reports/<latest>/top-divergences.md` (if present) — sample 3 entries; do the WCSR + severity columns look plausible?
- `titan_chordpro/version.py` — must read `"0.1.0c0"`.

## Focus areas

### 1. T70 verdict trail

- Is there a commit referencing "T70" with a top-10 classification (titan_errado / chart_errado / edge_case_aceitavel)?
- Did Henry GO at T70 or did a fix-task (T70.1, T70.2, ...) intervene? If yes, are those fix-tasks committed and their tests passing?
- Mean WCSR-majmin from the first run: is it ≥ 0.70? If not, is the deviation small enough that Henry signed off, or is a known-bug-list documented somewhere reachable from the roadmap?

### 2. F-004 — sample a real song

If `benchmarks/reports/<latest>/` exists, pick the song with the worst WCSR that the T70 verdict marked as `titan_errado`. Read its corresponding `chordpros.csv/songs.csv` row. Spot-check 3 chords:
- Did Titan emit them in the right order?
- For chords that should have a slash (F/A, G/B), did Titan emit `bass_note` or default to root?
- Does the rendered `inline_slash` profile show the slash chords correctly?

This is not a quantitative review — it's a sanity check that F-004 isn't 100% root-position fallback.

### 3. Cache integrity at runtime

Trigger a synthetic re-run check (no need to actually run real audio):

```bash
pytest tests/integration/test_cache_wiring.py -v
```

Verify:
- All 4 tests pass.
- The "second run skips engines" test actually patches `factory.select_separation` and asserts `assert_not_called`.
- Corrupted-cache test produces a real json parse failure and is recovered silently.

### 4. License hygiene

- `pyproject.toml` `[validation]` block: `yt-dlp` (Unlicense), `mir_eval` (MIT), `librosa` (ISC), `scipy` (BSD-3), `rich` (MIT). None are GPL or LGPL.
- Chordino remains accessed via subprocess (`chord_extractor` import is lazy inside `_load_extractor`). The Phase B GPL boundary is intact.
- `LICENSE` file in repo root: still MIT.

### 5. Test discipline — final

- `pytest -q` exits 0 with no failures, no errors.
- Test count is at least 426 (Week 8 expected 424; Week 9 added at least 2 CLI tests).
- `pytest --cov` (if Henry runs it manually) returns ≥ 80% (Phase B baseline 85%; Phase C should not regress).
- No `@pytest.mark.skip` or `@pytest.mark.xfail` added in Phase C without a roadmap entry explaining why.

### 6. Library import surface

```bash
python -c "import titan_chordpro; import sys; assert 'rich' not in sys.modules; assert 'yt_dlp' not in sys.modules; print('clean')"
```

Expected: `clean`. The validation harness must stay off the library import surface.

### 7. Roadmap + CHANGELOG accuracy

- Does the roadmap "Updates Log" entry for Phase C list a date that matches the commit author date of the T73 commit?
- Is the **carry-over to v0.2** section accurate (BTC-ISMIR19, mlx-whisper, demucs-mlx)? Spec §1737 lists these — confirm.
- Does CHANGELOG attribute F-004 closure to T64 (not just "phase C")?

### 8. Tag readiness

- `git status` is clean (no uncommitted changes).
- `git log -1 --format=%s` shows the T73 wrap-up commit.
- The tag command Henry will run is documented at the bottom of T73's instructions (`git tag -a v0.1.0-c0 -m "..."`).

## What NOT to review

- v0.2 / Phase D scope. Out of bounds.
- BTC-ISMIR19 implementation details. v0.2.
- Whether yt-dlp downloads work in Henry's specific network — that's a Henry-runs-it concern.
- README design / wording style — T72 territory; only review that the validation section exists and points at the right docs.

## Output format

```
# Phase C Final Review

## Verdict
[Sound — tag] / [Sound with caveats — tag with caveats noted] / [Drift detected — fix in T73a] / [STOP — escalate to Henry]

## Findings (worst first)
1. [File:line OR area] — Issue — Severity (Critical/Significant/Minor)

## T70 trail
[Confirm — first-run mean WCSR <N>, top-10 verdict trail in commit log]
[BROKEN — describe gap]

## F-004 reality check
[Confirm — sampled <N> slash-chord songs; F-004 emitting bass_note in real audio]
[INERT — F-004 ships but doesn't actually emit slash chords; root-position fallback dominates]

## Cache integrity
[Confirm — round-trip green on mocks; corrupted cache recovers silently]
[BROKEN — describe]

## License + import surface
[Confirm — MIT preserved; library does not pull rich/yt_dlp]

## Continue to tag?
[Yes / Yes with caveats / NO]

## Tag command to surface to Henry
git tag -a v0.1.0-c0 -m "Phase C — validation harness + F-004 + cache wiring"
git push origin v0.1.0-c0

## Notes for Henry
```

Max 1000 words. This is the only checkpoint that can BLOCK the tag — its verdict is load-bearing.

# Session resume — CHORD lane (2026-08-05)

**Branch:** `plan/titan-v01`  
**Worktree:** `/Users/henry/.grok/worktrees/code-titan-chordpro-lib/plan`  
**Status:** partial-promote ready for operator validation; **not pushed until this save**.

## Narrative

Chord explore lane ran autonomously on this branch (not a separate impl/chord-explore WT). H0 measured; H1/H1b multipass+force-relabel; H2 bass gates; H3 stems and H4 params eval-only (no-promote); Codex reviews each phase with P2/P3 fixes. BTC remains only on sibling `impl/chord-explore` (`btc.py` absent here).

## Decision log

1. Stay on `plan/titan-v01` (operator) — no new chord worktree for this session.
2. **partial-promote:** H1b + H2 + Codex fixes; keep Chordino + other+bass defaults.
3. H3 other-only worse; H4 best +0.4pp — no param/mix promote.
4. H6 BTC: no default (song3 −11pp); not ported to this branch.
5. Do not claim WCSR gate; 3-song sample only.
6. Do not edit `.atomic-skills/` from CHORD lane.

## Commits (since handoff docs `94d2c3a`)

| SHA | Summary |
|-----|---------|
| de8e218 | feat multipass reseg + force-relabel ≥12s |
| 05efb5d | feat H2 bass slash stability |
| 4264ddf | fix Codex P3 |
| 4714136 | chore eval harness |
| abdc5d5 | fix Codex P2 |
| 21c877c | docs research chord-lane |

## Single nextAction

Operator validates **partial-promote** in `2026-08-05-chord-lane-PROMOTE.md`, then either merge quality path or continue residuals (song3 / larger sample / optional BTC from impl/chord-explore).

## Verbatim paths

- Report: `.ai/memory/handoffs/2026-08-05-chord-lane-REPORT.md`
- Promote: `.ai/memory/handoffs/2026-08-05-chord-lane-PROMOTE.md`
- Metrics: `.ai/memory/handoffs/chord-explore-metrics/hyp-*-metrics.json`
- Product: `titan_chordpro/engines/chord/chordino.py`, `bass_chroma.py`
- Eval: `scripts/compare_chordpro_to_gt.py`, `redetect_chords_from_cache.py`, `run_h3_h4_eval.py`
- Research: `docs/research/chord-lane-2026-08-05.md`
- Ephemeral full chords still under `/tmp/titan-chord-explore/` (may vanish on reboot)

## Uncommitted at save

Expected: only local symlinks `.venv-py312`, `chordpros.csv` (do not commit).

## Do not

- `done` / `phase-done` / edit initiative YAML from this lane
- Switch factory default to BTC
- Hardcode song IDs into `detect()`

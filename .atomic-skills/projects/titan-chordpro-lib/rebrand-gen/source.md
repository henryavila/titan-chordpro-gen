# Rebrand to titan-chordpro-gen

Flip external identity (repo, PyPI name, live docs, CLI primary) from `titan-chordpro-lib` to `titan-chordpro-gen` while keeping the Python import package `titan_chordpro` stable (Option A). Coordinate the GitHub/folder rename window with `curta` pins and sibling path links. Design SoT: `design.md` (critic Approved, user Approved 2026-08-28).

## Principles

### P1 External identity, stable import
Change what people install and type (`titan-chordpro-gen`); do not rename `import titan_chordpro` in this plan.

### P2 Live surface only
Update README, roadmap H1, CLAUDE.md, install scripts, live product docstrings, CHANGELOG Unreleased. Leave `docs/research/**` and `docs/superpowers/**` untouched.

### P3 Staged cutover with a same-day consumer window
Merge metadata/docs PR in this repo first; then operator renames GitHub + local folder; same operational day update `curta` pins/paths and `chordpro-viewer` NAMING link.

### P4 Own initiative — not F2
Do not piggyback on the Phase C quality loop. Anchor `rebrand-gen` (or explicit ad-hoc) before code edits.

### P5 Operator owns irreversible renames
GitHub repository rename and local directory rename are operator steps; agent prepares strings and verifies after.

## Glossary

| Term | Definition |
|------|------------|
| **Option A** | Keep Python import package `titan_chordpro`; only distribution/repo/docs/CLI surface rename |
| **Primary CLI** | Console script `titan-chordpro-gen` → `titan_chordpro.cli:main` |
| **Alias CLI** | Console script `titan-chordpro` kept for compat (same entry) |
| **Live surface** | Installable/product-facing docs and strings (not historical research) |
| **Cutover window** | Same-day operator GitHub+folder rename + curta pin/path PR |

## F0 — Anchor and inventory

**Goal:** Initiative/branch anchored; MUST_CHANGE inventory confirmed against design; no code rename yet.

### Tasks

- **T-001** Declare / materialize initiative for `rebrand-gen` (or explicit ad-hoc) matching the working branch; park or leave F2 untouched.
- **T-002** Freeze MUST_CHANGE list from `research-digest.md` + design (pyproject, uv.lock, README, CLAUDE, roadmap H1, CHANGELOG Unreleased, install.sh, live core docstrings, chordino MIT blurb).
- **T-003** Note curta + chordpro-viewer external paths for the cutover window (no edit yet).

### Exit criteria

- Initiative or ad-hoc declared.
- Inventory checked against design Decisions 1–7.

## F1 — This-repo identity flip

**Goal:** This repository’s distribution name, CLI scripts, live docs, and CHANGELOG reflect `titan-chordpro-gen` with Option A imports; tests green.

### Tasks

- **T-010** `pyproject.toml`: `[project].name = "titan-chordpro-gen"`; description may say generator/audio-to-ChordPro; dual `[project.scripts]` (`titan-chordpro-gen` primary + `titan-chordpro` alias).
- **T-011** Regenerate `uv.lock` for the new distribution name.
- **T-012** CHANGELOG: add `[Unreleased]` chore entry — repo/PyPI rename; import path unchanged; CLI primary + alias.
- **T-013** Live docs: README title **Titan ChordPro Gen** + formerly line + link to `docs/REBRAND-HANDOFF.md`; roadmap H1; CLAUDE.md H1; `scripts/install.sh` banner/strings.
- **T-014** Live product strings in `titan_chordpro/core/{exceptions,schemas,protocols,logging}.py` and `engines/chord/chordino.py` MIT blurb → Gen / new dist name where product-titled.
- **T-015** Verify: `pytest` (unit) green; `python -c "import titan_chordpro"`; `titan-chordpro-gen --help` and `titan-chordpro --help` after editable install.
- **T-016** Commit `chore: rebrand repository to titan-chordpro-gen` (per handoff §7); open/merge PR for this repo only. **Do not** flip badge URLs to `-gen` until F2 operator rename lands (or flip in a follow-up commit same window).

### Exit criteria

- `pyproject` name is `titan-chordpro-gen`.
- Import `titan_chordpro` still works.
- Both CLI entrypoints respond to `--help`.
- Historical research/superpowers unchanged.

## F2 — Operator rename + consumer window

**Goal:** GitHub repo and local directory are `titan-chordpro-gen`; badges point at new slug; curta and chordpro-viewer paths/pins updated same day.

### Tasks

- **T-020** **Operator:** rename GitHub `titan-chordpro-lib` → `titan-chordpro-gen`; update local folder + `git remote -v`.
- **T-021** Flip README CI/Nightly badge URLs to `henryavila/titan-chordpro-gen`.
- **T-022** **curta:** update `pyproject.toml` git pins/distribution name; `bin/setup` default `../titan-chordpro-gen` + log strings; regen lock; keep `import titan_chordpro`.
- **T-023** **chordpro-viewer:** update `docs/NAMING.md` relative link to handoff; scrub transitional “hoje lib” in README/SPEC if still present.
- **T-024** **sda-v2 (docs only):** polish `07b-cifra-viewer.md` transitional wording if needed.
- **T-025** Fill handoff checklist boxes in PR body; confirm done criteria §4.7.

### Exit criteria

- Remote + directory named `titan-chordpro-gen`.
- curta installs via new path/pin; `import titan_chordpro` still OK.
- Sibling NAMING link resolves.
- Handoff §4.7 checklist complete.

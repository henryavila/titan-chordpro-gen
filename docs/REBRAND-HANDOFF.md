# Handoff — Rebrand `titan-chordpro-lib` → `titan-chordpro-gen`

> **Audience:** agent or human executing the rename.  
> **Locked:** 2026-08-28 (with sibling UI naming).  
> **Sibling SoT:** [`../chordpro-viewer/docs/NAMING.md`](../../chordpro-viewer/docs/NAMING.md) (seed of `titan-chordpro-ui`).

---

## 1. Decision (do not re-litigate)

| Piece | Target name | Role | Layout |
|---|---|---|---|
| **This repo** | **`titan-chordpro-gen`** | Audio → `.chordpro` / `.cho` (generator / factory) | **Own git repo** |
| **UI sibling** | **`titan-chordpro-ui`** | Viewer **+** editor (one layer) | **Own git repo** (seed: `chordpro-viewer`) |
| **Titan app/studio** | — | None | **Not now** |
| **Monorepo** | — | — | **Not now** |
| **SDA** | `sda-v2` | Consumes **ui only** | Separate |

**Why `-gen`:** once UI exists, `-lib` is ambiguous (UI is also a library). **gen** = ML/audio factory.

**Supersedes** roadmap labels `titan-chordpro-render` + “Theme CSS + editor” as a single **`titan-chordpro-ui`** package — not part of this repo’s rename job.

---

## 2. Scope of *this* handoff

### In scope

- Rename **git repo / directory / GitHub remote** to `titan-chordpro-gen`.
- Rename **PyPI / project name** in `pyproject.toml` to `titan-chordpro-gen`.
- Update **docs, badges, CI workflow names/URLs, CHANGELOG, README title**.
- Update **roadmap Phase 2** to point at `titan-chordpro-ui` + this name (already sketched).
- Document **import path** policy (§3).
- Grep & fix **in-repo** references to `titan-chordpro-lib` / “Titan ChordPro Lib” as product title.

### Out of scope (other agents / later)

- Implementing or moving **viewer/editor** into this tree.
- Renaming **`sda-v2`** paths or Nuxt code (SDA does not import this package for UI).
- Creating a Titan **app**.
- Merging into a monorepo.
- Changing ML pipeline behavior, schemas, or validation metrics.

---

## 3. Python import path policy (choose A unless blocked)

| Option | Distribution name | `import …` | When |
|---|---|---|---|
| **A (recommended for this rename)** | `titan-chordpro-gen` | keep **`titan_chordpro`** | Repo/PyPI rename only; **zero** break for `curta` / callers of `titan_chordpro.core.hardware` |
| **B (later major)** | `titan-chordpro-gen` | `titan_chordpro_gen` | Coordinated breaking release + migrate curta + docs |

**Default for the executing agent: Option A.**  
If you take B, bump major / document migration in CHANGELOG and update the **Public infra contract for `curta`** section in README.

CLI entrypoint today: `titan-chordpro` — **keep** the command name (product family). Optional alias `titan-chordpro-gen` may be added; do not remove `titan-chordpro` without a deprecation note.

---

## 4. Checklist (execute in order)

### 4.1 Preflight

- [ ] Confirm no open PR that hardcodes the old GitHub URL in external repos you own (`curta`, etc.) — list them in the PR description.
- [ ] `git status` clean (or only this handoff committed).
- [ ] Note current version (`0.1.0c0` / tag plan `v0.1.0-c0`) — rename does **not** require a version bump by itself; use a `chore:` changelog entry.

### 4.2 Project metadata

- [x] `pyproject.toml` → `[project].name = "titan-chordpro-gen"`.
- [x] Description may say “generator” / “audio-to-ChordPro”.
- [x] Scripts/entry points: primary `titan-chordpro-gen` + alias `titan-chordpro`.
- [ ] License/authors unchanged.

### 4.3 Docs & branding strings

- [x] README title: **Titan ChordPro Gen** (was “Lib”).
- [x] Badges: CI/Nightly URLs → `henryavila/titan-chordpro-gen`.
- [x] `docs/roadmap.md` — Phase 2 table uses `titan-chordpro-gen` / `titan-chordpro-ui`.
- [x] Link this file from README (“Rebrand”).
- [x] `CHANGELOG.md` — entry under Unreleased: repo & PyPI rename; import path unchanged (A).
- [x] Replace user-facing “ChordPro Lib” with “ChordPro Gen” where it means **this product**; leave historical commit messages alone.

### 4.4 CI / GitHub

- [x] Rename GitHub repository `titan-chordpro-lib` → `titan-chordpro-gen`.
- [x] Update workflow `paths` / badge URLs if any embed the old name. (workflows had none; badges flipped)
- [ ] Local folder rename: `code/titan-chordpro-lib` → `code/titan-chordpro-gen` (operator).
- [ ] Update sibling docs that point at `../titan-chordpro-lib` (`chordpro-viewer/docs/NAMING.md`, sda `07b`, etc.) in the **same** change window when possible.

### 4.5 External consumers (notify / PR)

| Consumer | Action |
|---|---|
| **`curta`** | If only imports `titan_chordpro.*` (option A): bump dependency name to `titan-chordpro-gen` when published; **no** import edits. |
| **`chordpro-viewer` / ui seed** | Update NAMING + README sibling path when folder renames. |
| **`sda-v2`** | Docs only (`07b`, any path to this repo). No runtime dep on gen for Nuxt UI. |
| **PyPI** | Publish under new name; yank or leave old name with README redirect note if ever published. |

### 4.6 Verify

- [x] `pytest` (unit) green after string renames.
- [x] editable install still exposes `import titan_chordpro` (option A).
- [x] CLI `titan-chordpro-gen --help` + alias `titan-chordpro --help` work.
- [x] README install instructions still accurate.

### 4.7 Done criteria

Rename is **DONE** when:

1. GitHub repo + local directory are `titan-chordpro-gen`.
2. `pyproject.toml` project name is `titan-chordpro-gen`.
3. README/badges/roadmap say Gen, not Lib (as product title).
4. Option A: existing `import titan_chordpro` still works; CHANGELOG states that.
5. This handoff checked boxes filled in the PR body.

---

## 5. Family map (after rename)

```
titan-chordpro-gen/     ← THIS repo (Python) — audio → ChordPro text
titan-chordpro-ui/      ← sibling (TS/Vue) — view + edit  [seed: chordpro-viewer]
sda-v2/                 ← consumes ui only
(apps/studio)           ← none yet
```

Interchange format between gen and ui: **ChordPro text** (`.chordpro` / `.cho`). No shared Python/TS runtime required.

---

## 5b. Follow-up (approved, not this PR)

Optional later split: thin **`titan-chordpro-lib`** (infra only — what `curta` consumes) extracted from this tree; **`titan-chordpro-gen`** keeps the audio→ChordPro pipeline and depends on that lib. **Not** part of this rename cutover.

## 6. Explicit non-goals

- Do **not** move UI code into this repository.
- Do **not** add a `packages/ui` monorepo layout in this pass.
- Do **not** rename write profiles (`inline_slash`, etc.) or ChordPro schema fields.
- Do **not** auto-tag `v0.1.0-c0` as part of rebrand (operator-owned tag remains separate).

---

## 7. Suggested commit / PR

```
chore: rebrand repository to titan-chordpro-gen

- PyPI/project name titan-chordpro-gen
- Keep Python import package titan_chordpro (compat)
- Docs/badges/roadmap updated; see docs/REBRAND-HANDOFF.md
```

---

## 8. Operator commands (reference)

```bash
# After GitHub rename + local move:
cd /Volumes/External/code/titan-chordpro-gen
# update remotes if needed
git remote -v

# editable install still:
.venv-py312/bin/pip install -e ".[mac]"
.venv-py312/bin/python -c "import titan_chordpro; print(titan_chordpro.__file__)"
```

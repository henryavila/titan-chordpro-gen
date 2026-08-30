---
lastUpdated: 2026-08-30T21:48:50Z
schemaVersion: '0.1'
activePlans: 1
activeInitiatives: 1
archivedCount: 2
---

# Project Status Index

Canonical entry point. Auto-updated by `atomic-skills:project`. Read first every session.

This repo follows a 3-level model under `projects/<project-id>/`:

- **Plan** — multi-phase project (`<plan-slug>/plan.md`)
- **Initiative** — one phase (`<plan-slug>/phases/f<N>-<slug>.md`)
- **Task** — atomic action inside a phase initiative (`tasks[]`)

## Active Plans

| Slug | Status | Current Phase | Branch | Started |
|------|--------|---------------|--------|---------|
| titan-v01 | active | F2 — Phase C Validation and quality | plan/titan-v01 | 2026-05-08 |

### titan-v01 — active phase initiatives

| Slug | Phase | Status | Next Action |
|------|-------|--------|-------------|
| titan-v01-f2-phase-c-validation-and-quality | F2 | active | Continue T-003 quality loop until mean WCSR-majmin >= 0.70, then done T-003 |

## Active Initiatives (standalone)

| _(empty)_ | | | | |

## Recently Archived (last 10)

| Slug | Status | Branch | Archived |
|------|--------|--------|----------|
| rebrand-gen | archived | plan/rebrand-gen | 2026-08-30T21:48:50Z |
| titan-core-decoupling | archived | plan/titan-core-decoupling | 2026-06-25T00:51:51Z |

## Ad-Hoc Sessions Log (last 5)

| Timestamp | Description |
|-----------|-------------|
| 2026-08-30 | merge PR #5; archive rebrand-gen; resume titan-v01 F2 |
| 2026-08-30 | validated rebrand deliverables; close phases; publish PR vs plan/titan-v01 |
| 2026-08-28 | pause titan-v01; materialize rebrand-gen on plan/rebrand-gen worktree |
| 2026-08-04 | adopt titan-v01 nested; legacy flat → legacy-flat-pre-adopt-2026-08-04 |

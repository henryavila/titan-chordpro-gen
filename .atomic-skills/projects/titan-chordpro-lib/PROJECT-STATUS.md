---
lastUpdated: 2026-08-29T02:48:40Z
schemaVersion: '0.1'
activePlans: 1
activeInitiatives: 1
archivedCount: 1
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
| rebrand-gen | active | F0 — Anchor and inventory | plan/rebrand-gen | 2026-08-28 |
| titan-v01 | paused | F2 — Phase C Validation and quality | plan/titan-v01 | 2026-05-08 |

### rebrand-gen — active phase initiatives

| Slug | Phase | Status | Next Action |
|------|-------|--------|-------------|
| rebrand-gen-f0-anchor-and-inventory | F0 | active | Start T-001: Ancorar iniciativa / ad-hoc |

### titan-v01 — paused phase initiatives

| Slug | Phase | Status | Next Action |
|------|-------|--------|-------------|
| titan-v01-f2-phase-c-validation-and-quality | F2 | paused | (paused for rebrand-gen) |

## Active Initiatives (standalone)

| _(empty)_ | | | | |

## Recently Archived (last 10)

| Slug | Status | Branch | Archived |
|------|--------|--------|----------|
| titan-core-decoupling | archived | plan/titan-core-decoupling | 2026-06-25T00:51:51Z |

## Ad-Hoc Sessions Log (last 5)

| Timestamp | Description |
|-----------|-------------|
| 2026-08-28 | pause titan-v01; materialize rebrand-gen on plan/rebrand-gen worktree |
| 2026-08-04 | adopt titan-v01 nested; legacy flat → legacy-flat-pre-adopt-2026-08-04 |

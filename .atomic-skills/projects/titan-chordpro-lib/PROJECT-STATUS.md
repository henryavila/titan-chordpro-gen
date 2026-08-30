---
lastUpdated: 2026-08-30T13:23:58Z
schemaVersion: '0.1'
activePlans: 1
activeInitiatives: 0
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
| rebrand-gen | active (phases done — ready to publish) | F2 done | plan/rebrand-gen | 2026-08-28 |
| titan-v01 | paused | F2 — Phase C Validation and quality | plan/titan-v01 | 2026-05-08 |

### rebrand-gen — phase initiatives

| Slug | Phase | Status | Next Action |
|------|-------|--------|-------------|
| rebrand-gen-f0-anchor-and-inventory | F0 | done | finalize / PR |
| rebrand-gen-f1-this-repo-identity-flip | F1 | done | — |
| rebrand-gen-f2-operator-rename-consumer-window | F2 | done | — |

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
| 2026-08-30 | validated rebrand deliverables; close phases post-hoc; publish PR vs plan/titan-v01 |
| 2026-08-28 | pause titan-v01; materialize rebrand-gen on plan/rebrand-gen worktree |
| 2026-08-04 | adopt titan-v01 nested; legacy flat → legacy-flat-pre-adopt-2026-08-04 |

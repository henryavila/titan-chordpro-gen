---
schemaVersion: "0.1"
slug: rebrand-gen
title: Rebrand to titan-chordpro-gen
version: "1.0"
status: active
started: 2026-08-29T02:46:42.203Z
lastUpdated: 2026-08-30T13:23:58Z
branch: plan/rebrand-gen
currentPhase: F2
parallelismAllowed: false
principles:
  - id: P1
    title: External identity, stable import
    body: Change what people install and type (`titan-chordpro-gen`); do not rename
      `import titan_chordpro` in this plan.
  - id: P2
    title: Live surface only
    body: Update README, roadmap H1, CLAUDE.md, install scripts, live product
      docstrings, CHANGELOG Unreleased. Leave `docs/research/**` and
      `docs/superpowers/**` untouched.
  - id: P3
    title: Staged cutover with a same-day consumer window
    body: Merge metadata/docs PR in this repo first; then operator renames GitHub +
      local folder; same operational day update `curta` pins/paths and
      `chordpro-viewer` NAMING link.
  - id: P4
    title: Own initiative — not F2
    body: Do not piggyback on the Phase C quality loop. Anchor `rebrand-gen` (or
      explicit ad-hoc) before code edits.
  - id: P5
    title: Operator owns irreversible renames
    body: GitHub repository rename and local directory rename are operator steps;
      agent prepares strings and verifies after.
glossary:
  - term: Option A
    definition: Keep Python import package `titan_chordpro`; only
      distribution/repo/docs/CLI surface rename
  - term: Primary CLI
    definition: Console script `titan-chordpro-gen` → `titan_chordpro.cli:main`
  - term: Alias CLI
    definition: Console script `titan-chordpro` kept for compat (same entry)
  - term: Live surface
    definition: Installable/product-facing docs and strings (not historical research)
  - term: Cutover window
    definition: Same-day operator GitHub+folder rename + curta pin/path PR
phases:
  - id: F0
    slug: rebrand-gen-f0-anchor-and-inventory
    title: Anchor and inventory
    goal: Initiative/branch anchored; MUST_CHANGE inventory confirmed against
      design; no code rename yet.
    dependsOn: []
    subPhaseCount: 3
    summary: Ancorar o plano e congelar o inventário MUST_CHANGE
    exitGate:
      summary: Initiative ancorada + inventário fechado
      criteria:
        - id: F0-G1
          description: Branch plan/rebrand-gen ativa e titan-v01 pausado
          status: met
          metAt: 2026-08-30T13:23:58Z
          evidence:
            verifierKind: manual
            verifiedAt: 2026-08-30T13:23:58Z
            verifiedCommit: 95934484581c191a081a2ca23109589b551ff339
            passed: true
            outputSummary: Validated 2026-08-30 against worktree + consumers
        - id: F0-G2
          description: Inventário MUST_CHANGE alinhado ao design/digest
          status: met
          metAt: 2026-08-30T13:23:58Z
          evidence:
            verifierKind: manual
            verifiedAt: 2026-08-30T13:23:58Z
            verifiedCommit: 95934484581c191a081a2ca23109589b551ff339
            passed: true
            outputSummary: Validated 2026-08-30 against worktree + consumers
    reviewGate:
      status: skipped
      reason: "post-hoc close after validated rebrand deliverables (non-automate finalize)"
      verifiedAt: 2026-08-30T13:23:58Z
    status: done
    businessIntent:
      value: Acabar a ambiguidade -lib vs UI alinhando repo, PyPI e CLI primary a
        titan-chordpro-gen sem quebrar callers.
      workflow: Inventário MUST_CHANGE → PR de metadata/docs/scripts neste repo →
        rename GitHub+pasta (operator) → pins/paths curta e link NAMING no mesmo
        dia.
      rules: Option A (import titan_chordpro); LEAVE research/superpowers; CLI primary
        titan-chordpro-gen + alias titan-chordpro; não misturar com F2 quality
        loop; slug atomic-skills do projeto não migra agora.
      outOfScope: UI/viewer/editor neste tree; monorepo; app Titan; mudanças
        ML/schemas/profiles; Option B import rename; auto-tag v0.1.0-c0.
      doneWhen: "Handoff §4.7: repo+dir gen, pyproject name gen, README/roadmap Gen,
        import titan_chordpro ok, CLIs --help, checklist preenchido."
  - id: F1
    slug: rebrand-gen-f1-this-repo-identity-flip
    title: This-repo identity flip
    goal: This repository's distribution name, CLI scripts, live docs, and CHANGELOG
      reflect `titan-chordpro-gen` with Option A imports; tests green.
    dependsOn:
      - F0
    subPhaseCount: 0
    summary: Renomear PyPI/docs/CLI neste repo com Option A
    exitGate:
      summary: pyproject gen + import/CLI verdes + PR deste repo
      criteria:
        - id: F1-G1
          description: pyproject name titan-chordpro-gen e dual scripts
          status: met
          metAt: 2026-08-30T13:23:58Z
          evidence:
            verifierKind: manual
            verifiedAt: 2026-08-30T13:23:58Z
            verifiedCommit: 95934484581c191a081a2ca23109589b551ff339
            passed: true
            outputSummary: Validated 2026-08-30 against worktree + consumers
        - id: F1-G2
          description: pytest + import titan_chordpro + ambos CLIs --help
          status: met
          metAt: 2026-08-30T13:23:58Z
          evidence:
            verifierKind: manual
            verifiedAt: 2026-08-30T13:23:58Z
            verifiedCommit: 95934484581c191a081a2ca23109589b551ff339
            passed: true
            outputSummary: Validated 2026-08-30 against worktree + consumers
    reviewGate:
      status: skipped
      reason: "post-hoc close after validated rebrand deliverables (non-automate finalize)"
      verifiedAt: 2026-08-30T13:23:58Z
    status: done
  - id: F2
    slug: rebrand-gen-f2-operator-rename-consumer-window
    title: Operator rename + consumer window
    goal: GitHub repo and local directory are `titan-chordpro-gen`; badges point at
      new slug; curta and chordpro-viewer paths/pins updated same day.
    dependsOn:
      - F1
    subPhaseCount: 0
    summary: Rename GitHub/pasta + pins curta/siblings no mesmo dia
    exitGate:
      summary: Remote/dir gen + curta/siblings atualizados + handoff §4.7
      criteria:
        - id: F2-G1
          description: GitHub e pasta local titan-chordpro-gen
          status: met
          metAt: 2026-08-30T13:23:58Z
          evidence:
            verifierKind: manual
            verifiedAt: 2026-08-30T13:23:58Z
            verifiedCommit: 95934484581c191a081a2ca23109589b551ff339
            passed: true
            outputSummary: Validated 2026-08-30 against worktree + consumers
        - id: F2-G2
          description: curta pins/path + NAMING link + badges
          status: met
          metAt: 2026-08-30T13:23:58Z
          evidence:
            verifierKind: manual
            verifiedAt: 2026-08-30T13:23:58Z
            verifiedCommit: 95934484581c191a081a2ca23109589b551ff339
            passed: true
            outputSummary: Validated 2026-08-30 against worktree + consumers
    reviewGate:
      status: skipped
      reason: "post-hoc close after validated rebrand deliverables (non-automate finalize)"
      verifiedAt: 2026-08-30T13:23:58Z
    status: done
references: []
---

# Rebrand to titan-chordpro-gen

## 1. Context

Flip external identity (repo, PyPI name, live docs, CLI primary) from `titan-chordpro-lib` to `titan-chordpro-gen` while keeping the Python import package `titan_chordpro` stable (Option A). Coordinate the GitHub/folder rename window with `curta` pins and sibling path links. Design SoT: `design.md` (critic Approved, user Approved 2026-08-28).

## 2. Inviolable principles

- **P1 External identity, stable import** — Change what people install and type (`titan-chordpro-gen`); do not rename `import titan_chordpro` in this plan.
- **P2 Live surface only** — Update README, roadmap H1, CLAUDE.md, install scripts, live product docstrings, CHANGELOG Unreleased. Leave `docs/research/**` and `docs/superpowers/**` untouched.
- **P3 Staged cutover with a same-day consumer window** — Merge metadata/docs PR in this repo first; then operator renames GitHub + local folder; same operational day update `curta` pins/paths and `chordpro-viewer` NAMING link.
- **P4 Own initiative — not F2** — Do not piggyback on the Phase C quality loop. Anchor `rebrand-gen` (or explicit ad-hoc) before code edits.
- **P5 Operator owns irreversible renames** — GitHub repository rename and local directory rename are operator steps; agent prepares strings and verifies after.

## 3. Phase tree

_(Canonical list in frontmatter `phases:`. aiDeck renders the tree visually when running.)_

## Reviews

- plan-end: SKIPPED — non-automate; operator accepted residual risk after deliverable validation (2026-08-30T13:23:58Z).
- phase reviewGates: skipped (post-hoc close) for F0/F1/F2.

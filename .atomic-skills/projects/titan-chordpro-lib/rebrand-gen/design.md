# Design — Rebrand to `titan-chordpro-gen`

## Interview

| Field | Ratified content |
|-------|------------------|
| **Problema** | Com `titan-chordpro-ui` no mapa, o sufixo `-lib` fica ambíguo; a identidade repo/PyPI/docs precisa alinhar a `-gen` sem quebrar callers. |
| **In-scope** | Metadata deste repo (PyPI/project name, scripts, docs live, CHANGELOG), paths/pins do `curta`, link relativo do `chordpro-viewer` na janela do rename. |
| **Out-of-scope** | UI/viewer/editor neste tree; monorepo; app Titan; mudanças de ML/schemas/write profiles; auto-tag `v0.1.0-c0`; Option B (rename do import) nesta rodada. |
| **Done-when (design)** | `design.md` com checklist ordenado, mapa agent vs operator, política histórico vs live, e verificação Option A + CLI. |
| **Stakes** | Rename GitHub + pasta local (one-way operacional); Option B import seria one-way de API (explicitamente fora). |
| **Fontes** | `docs/REBRAND-HANDOFF.md`, `chordpro-viewer/docs/NAMING.md`, `curta/bin/setup` + `curta/pyproject.toml`, `pyproject.toml` / README / CHANGELOG deste repo. |

Entrevista ecoada após auditoria; conflito Option A vs “reabrir B” + “alterar CLI” resolvido na ratificação pós-debate: **A nos imports; CLI primary novo**.

## Context

O handoff `docs/REBRAND-HANDOFF.md` (2026-08-28) trava a família: este repo = **generator** `titan-chordpro-gen`; sibling = `titan-chordpro-ui` (seed `chordpro-viewer`); SDA consome só UI. Roadmap e README já esboçam a decisão; `pyproject.toml` e remote ainda são `-lib`. O consumidor live mais acoplado é **`curta`** (pin git + path sibling + `import titan_chordpro`).

## Decisions

1. **Distribution / repo name:** `titan-chordpro-gen` (GitHub, pasta local, `[project].name`). verified_by: `docs/REBRAND-HANDOFF.md` §1; `chordpro-viewer/docs/NAMING.md`.
2. **Import path (Option A):** manter pacote Python `titan_chordpro` e hatch `packages = ["titan_chordpro"]`. verified_by: handoff §3 Option A; `curta` imports `titan_chordpro`.
3. **CLI:** entrypoint **primário** `titan-chordpro-gen`; manter `titan-chordpro` como alias no mesmo `[project.scripts]` apontando para `titan_chordpro.cli:main`. CHANGELOG registra o primary novo e o alias de compat (sem data de remoção nesta rodada — debt consciente, não Option B). verified_by: ratificação pós-debate 2026-08-28.
4. **Docs policy:** reescrever só **superfície viva** (README, roadmap H1, CLAUDE.md H1, install.sh, docstrings de produto em `titan_chordpro/core/*`, chordino MIT blurb, CHANGELOG Unreleased). **LEAVE** `docs/research/**`, `docs/superpowers/**`, corpos de releases passadas. README leva linha “formerly `titan-chordpro-lib`”.
5. **Cutover:** (a) PR agent neste repo (metadata + docs live + scripts); (b) janela operator: rename GitHub + pasta local + flip badges; (c) mesmo dia operacional: PR `curta` (pins + `bin/setup` path) + update link `chordpro-viewer/docs/NAMING.md`.
6. **Processo:** trabalho sob iniciativa/plan `rebrand-gen` (ou ad-hoc explícito) — **não** misturar com F2 quality loop. Slug `.atomic-skills/projects/titan-chordpro-lib/` **não** migra neste cutover.
7. **Versioning:** rename sozinho **não** exige bump; entrada `chore` em `[Unreleased]`. Tag `v0.1.0-c0` continua operator-owned e fora deste design.

## Chosen approach

**“External identity flip, internal API stable.”**

Abordagens pesadas:

| Approach | Resultado |
|----------|-----------|
| **A — Repo/PyPI/CLI surface + keep import** (escolhida) | Remove ambiguidade `-lib`; zero churn de import no curta; dual CLI por compat. |
| **B — Full Python rename `titan_chordpro_gen`** (rejeitada agora) | Identidade única; breaking major + migração curta; maior blast nesta rodada. |
| **Wait until F2 closes** (rejeitada) | Evita creep; prolonga ambiguidade já locked nos siblings. |
| **Atomic single mega-PR (lib+curta+GitHub)** (rejeitada) | Rollback incompleto; redirect mascara drift. |

Sequência operacional (owners):

| # | Ação | Owner |
|---|------|-------|
| 1 | Ancorar initiative `rebrand-gen` / declarar ad-hoc | operator + agent |
| 2 | `pyproject.toml` name + dual scripts; regen `uv.lock` | agent |
| 3 | CHANGELOG `[Unreleased]`; README/roadmap/CLAUDE/install.sh; live docstrings | agent |
| 4 | `pytest` + `import titan_chordpro` + `titan-chordpro-gen --help` (+ alias) | agent |
| 5 | Commit/PR neste repo | agent / operator merge |
| 6 | Rename GitHub repo + pasta local + `git remote` | **operator** |
| 7 | Flip badges README (se não no mesmo PR pós-rename) | agent/operator |
| 8 | curta: pyproject pins URL/name + `bin/setup` default path; regen lock | agent em `curta` / operator |
| 9 | chordpro-viewer NAMING relative path; sda `07b` tirar “hoje lib” se ainda transitório | agent siblings |
| 10 | Done criteria do handoff §4.7 | ambos |

## Blast radius

| One-way / caro | Containment |
|----------------|-------------|
| GitHub repo rename | Fazer na janela com curta pins; confirmar redirect git; não flipar badges antes |
| Pasta local `…/titan-chordpro-lib` → `…/titan-chordpro-gen` | Atualizar `CURTA_TITAN_DIR` default no mesmo dia; reabrir workspaces |
| PyPI name (se publish futuro) | First publish sob `-gen`; não republicar `-lib` sem redirect note |
| CLI dual entry | Contido a `pyproject` scripts; reversível; debt de alias documentada |
| Import rename (B) | **Fora** — não executar nesta rodada |

## Non-goals

- Mover UI/editor para este repositório.
- Layout monorepo `packages/ui`.
- Renomear write profiles / schemas ChordPro.
- Auto-tag `v0.1.0-c0`.
- Option B import rename.
- Mass-edit de `docs/research` / `docs/superpowers`.
- Migrar pasta `.atomic-skills/projects/titan-chordpro-lib/` neste cutover.

## Rejected alternatives

- **Option B agora** (Marina): rejeitado na ratificação — churn de import sem validar a hipótese de ambiguidade de produto; reservado a major futuro.
- **Adiar rebrand até F2 fechar** (Marina): rejeitado — siblings já documentam `-gen`; WIP parcial aumenta confusão.
- **Cutover 100% atômico lib+curta+GitHub num único movimento** : rejeitado (Aria) — falha de rollback / redirect masking.
- **Handoff literal CLI primary = `titan-chordpro` only**: rejeitado pós-entrevista — usuário pediu CLI no nome novo; alias cobre compat.
- **Rewrite histórico em massa**: rejeitado — ruído sem efeito em install.

## Open questions

1. Horizonte formal de remoção do alias `titan-chordpro` (próximo minor vs major) — **fora deste design**; registrar só a existência do alias.
2. Quem abre o PR do `curta` na janela D (mesmo agent com cwd externo vs operator) — decidir na materialização do plano.
3. Confirmção se `-lib` jamais foi publicado no PyPI — assume unpublished até evidência contrária (curta usa git pin).

## Self-review against code-quality gates

- G1 read-before-claim: applied — claims ancorados em `docs/REBRAND-HANDOFF.md`, `pyproject.toml` name/scripts, `curta/bin/setup` + `curta/pyproject.toml` pins, audit explore 2026-08-28, debate voices Priya/Aria/Devon/Marina.
- G2 soft-language: applied — decisões afirmativas (Option A, CLI primary, LEAVE, cutover stages); sem “might/should consider” como substituto de decisão.
- G6 reference-or-strike: applied — decisões 1–7 com verified_by ou ratificação explícita; open questions marcadas como não resolvidas.

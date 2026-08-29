# Research digest — rebrand-gen

## Scope (from Interview)

- **Problema:** com `titan-chordpro-ui` no mapa, o sufixo `-lib` é ambíguo; alinhar identidade repo/PyPI/docs para `-gen` sem quebrar callers.
- **In-scope:** metadata deste repo + docs live + paths/pins do `curta` + links do `chordpro-viewer` na janela do rename.
- **Julgamento pós-conflito:** Option A (`import titan_chordpro` permanece); CLI principal → `titan-chordpro-gen` (com `titan-chordpro` como alias).
- **Fontes:** `docs/REBRAND-HANDOFF.md`, `chordpro-viewer/docs/NAMING.md`, `curta/bin/setup` + `curta/pyproject.toml`, `pyproject.toml` / README / CHANGELOG deste repo.

## Findings

- **`docs/REBRAND-HANDOFF.md`**: decisão travada — repo = `titan-chordpro-gen`, UI sibling = `titan-chordpro-ui`, Option A default, CLI `titan-chordpro` “keep” com alias opcional; non-goals incluem sem UI/monorepo/app e sem auto-tag `v0.1.0-c0`.
- **`pyproject.toml`**: ainda `name = "titan-chordpro-lib"`; `[project.scripts]` = `titan-chordpro = "titan_chordpro.cli:main"`; hatch `packages = ["titan_chordpro"]` — Option A não toca o diretório de import.
- **`README.md` / `docs/roadmap.md` (WIP):** blurb de rebrand + tabela Phase 2 já citam `-gen` / `-ui`; H1 do roadmap ainda “Lib”; badges ainda `henryavila/titan-chordpro-lib`.
- **`.github/workflows/{ci,nightly}.yml`:** nenhum slug de repo hardcoded; flip de badge é só README, **depois** do rename no GitHub.
- **`CHANGELOG.md`:** existe; **sem** seção `[Unreleased]` — última é `[0.1.0c0] — 2026-08-04`.
- **Live product strings:** `scripts/install.sh` (“Titan ChordPro Lib”); docstrings em `titan_chordpro/core/{exceptions,schemas,protocols,logging}.py`; menção MIT em `engines/chord/chordino.py`.
- **LEAVE (histórico):** `docs/research/**`, `docs/superpowers/**`, corpos de releases passadas no CHANGELOG, PATHFINDER do curta.
- **`/Volumes/External/code/curta/bin/setup`:** default `CURTA_TITAN_DIR` → `../titan-chordpro-lib`; instala editable com log “titan-chordpro-lib”; verify importa `titan_chordpro` (Option A OK).
- **`/Volumes/External/code/curta/pyproject.toml`:** pin live `titan-chordpro-lib @ git+https://github.com/henryavila/titan-chordpro-lib.git@v0.1.0b2` (+ extra `[audio]`) — **quebra no dia do rename do GitHub** se não atualizado na mesma janela (redirect do GitHub pode mitigar clone URL; nome da dep ainda muda).
- **`chordpro-viewer/docs/NAMING.md`:** naming já locked para gen/ui; link relativo ainda `../titan-chordpro-lib/docs/REBRAND-HANDOFF.md`.
- **`sda-v2/design-handoff/prompts/07b-cifra-viewer.md`:** já fala gen; frase transitória “hoje `titan-chordpro-lib`”; sem dep runtime no gerador.
- **Estado git:** branch `plan/titan-v01`; remote ainda `titan-chordpro-lib`; iniciativa ativa F2 (quality loop) — rebrand precisa iniciativa própria / ad-hoc / park da F2.
- **PyPI:** sem evidência de publish sob `-lib` no repo; curta docs tratam sibling/git pin — first publish pode nascer como `-gen`.

## Open risks / seams

1. **Janela coordenada:** rename GitHub + pasta local + pins curta + badges + path NAMING — um só cutover.
2. **CLI vs handoff:** handoff manda *keep* `titan-chordpro`; entrevista pediu CLI no nome novo → resolver no design: primary=`titan-chordpro-gen`, alias/`titan-chordpro` retained + nota de depreciação suave (não Option B).
3. **`.atomic-skills/projects/titan-chordpro-lib/`:** slug de projeto vs pasta renomeada — migrate vs leave-as-history.
4. **Drift de versão no lock:** `uv.lock` pode mostrar `0.1.0rc0` vs código `0.1.0c0` (pré-existente; não misturar com rebrand).
5. **Initiative gate:** implementação bloqueada sem iniciativa ancorada na branch correta.

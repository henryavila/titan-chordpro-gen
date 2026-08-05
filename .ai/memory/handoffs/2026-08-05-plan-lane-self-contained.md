# Handoff SELF-CONTAINED — Lane PLAN (avanço do plano / release surface)

**Para:** sessão host / agent que **avança o plano** `titan-v01` **sem** reabrir a quality loop de acordes.  
**Data:** 2026-08-05  
**Repo:** `/Volumes/External/code/titan-chordpro-lib`  
**Branch de trabalho:** `plan/titan-v01`  
**HEAD de referência (pin):** `5e190a2` (atualizar com `git rev-parse --short HEAD` ao retomar)  
**Estado do produto:** **só dev — nunca lançado em produção.** Tags de release e WCSR “de marketing” não são sagrados; honestidade do lifecycle importa mais que fingir gate.

**Lane irmã (não é você):** chord explore — ver  
`.ai/memory/handoffs/2026-08-05-chord-lane-self-contained.md`  
Eles mexem em ACR/arquitetura de acordes em **outro worktree**. Você **não** compete com eles em `engines/chord/**`.

---

## 1. Missão desta sessão (PLAN)

1. Avançar o que o grafo do plano permite **enquanto o operador não faz GO de acorde**.  
2. Tratar a camada de acordes atual como **“boa o suficiente para desbloquear o resto”**, com residual documentado — **não** mentir WCSR ≥ 0.70.  
3. Preparar / executar **F3 prep** (docs, snapshots de writer com fixture, known-issues) conforme lifecycle Atomic Skills.  
4. **Nunca** editar a lane de experimentos de acorde; se precisar de wiring em `orchestrator.py`, minimize e documente; preferir não tocar.

**Fora de escopo PLAN**

- Trocar Chordino, BTC, reseg experimental, “melhorar WCSR do sample”.  
- `done` T-003 com verifier WCSR 0.70 verde se a métrica real não passou.  
- Tag `v0.1.0-c0` / `v0.1.0` sem decisão explícita do operador (e sem known-issues se residual existir).  
- Produção / PyPI.

---

## 2. Contexto do plano (SoT)

| Item | Valor |
|------|--------|
| Plan | `titan-v01` · `.atomic-skills/projects/titan-chordpro-lib/titan-v01/plan.md` |
| Fase ativa | **F2** Phase C Validation and quality |
| Initiative | `phases/f2-phase-c-validation-and-quality.md` |
| `executionMode` | `automate` (no plan frontmatter) |
| Branch | `plan/titan-v01` |

### Tasks F2

| ID | Título | Status |
|----|--------|--------|
| T-001 | Validation harness | **done** |
| T-002 | Structural placement | **done** |
| **T-003** | T70 quality loop (detection + placement) | **active** — gate WCSR formal não met |
| T-004 | CLI `--validate` + Progress | **done** |
| T-005 | README validation | **done** |
| T-006 | CHANGELOG + `0.1.0c0` + roadmap | **done** (package freeze cedo) |

### Exit gates F2 (todos pending)

| Gate | Significado |
|------|-------------|
| F2-G1 | Mean WCSR-majmin ≥ 0.70 (sample/Tier) — **hard no YAML; reality: stretch / re-spec needed** |
| F2-G2 | Henry GO on top-divergences |
| F2-G3 | Tag `v0.1.0-c0` exists |

### F3 Phase D

- Só sidecar: `phases/f3-phase-d-pre-release.source.json`  
- **Não materializada** · `dependsOn: F2` · goal: docs method/profiles/troubleshooting, demo, CHANGELOG `[0.1.0]`, known-issues, snapshot 5 profiles, tag `v0.1.0`  
- Lifecycle: sob automate, materialize exige package ratify — **não** inventar BI em silêncio.

### Tensão conhecida (não ignore)

Roadmap/CHANGELOG falam “Phase C closed / c0 ready”; initiative ainda tem **T-003 active** e gates abertos.  
**Trabalho PLAN honesto:** alinhar narrativa (roadmap/handoff) + avançar **prep F3 / known-issues**, **não** declarar WCSR met.

---

## 3. Estratégia híbrida (decisão de produto já discutida)

```
CONGELAR contrato ChordRecognitionEngine + ChordEvent
RE-SPEC: WCSR 0.70 no c0 = stretch (ou split T-003a done residual / T-003b parked v0.2)
AVANÇAR F3 prep / surface de release com fixtures
LANE CHORD (outro WT) experimenta ACR; promote só com métricas
GO do operador depois (lib não está em prod — barato reabrir só engine se preciso)
```

**Implicação para PLAN:** você implementa o “lado plano” do híbrido. A lane CHORD implementa experimentos. Merge **serial** em `plan/titan-v01`.

---

## 4. Allowlist / denylist de paths (PLAN)

### Pode editar

- `.atomic-skills/projects/titan-chordpro-lib/titan-v01/**` (state, re-spec text, handoff initiative)  
- `docs/**` (method, profiles, troubleshooting drafts, known-issues, roadmap honesty)  
- `README.md` só se necessário e sem reabrir T-005 scope desnecessariamente  
- `tests/**` para **snapshots de writer com Document fixture** (não `transcribe(audio)` real)  
- `scripts/**` de **review/compare** se ajudarem GO futuro (coordenar com chord lane se overlap)  
- `CHANGELOG.md` / version **só** com intenção de release clara do operador  

### Não editar (lane CHORD)

- `titan_chordpro/engines/chord/**`  
- Experimentos pesados em `orchestrator.py` de mix/detect  
- `titan_chordpro/fusion/**` “para melhorar cifra”  
- Cache `~/.cache/titan-chordpro/**` como “fix” de produto  

---

## 5. Backlog ordenado (faça nesta ordem)

### P0 — Honesty + desbloqueio mental

1. Atualizar `docs/roadmap.md` (e se preciso initiative `nextAction`) para:  
   - F2 quality **open** (T-003 / GO / WCSR stretch)  
   - package `0.1.0c0` no código ≠ gates de qualidade met  
2. Criar **`docs/known-issues.md`** com residuals já conhecidos (ver §6).  
3. Propor / aplicar **re-spec** do acceptance T-003 e F2-G1 (operador deve ratificar se automate):  
   - Exemplo: c0 = residual documentado + suite unitária; WCSR 0.70 → v0.2 / parked.  

### P1 — F3 prep (conteúdo; lifecycle conforme modo)

4. Drafts: `docs/method.md`, `docs/profiles.md`, `docs/troubleshooting.md`  
   - Conteúdo real: pipeline engines, other+bass para acordes, profiles, VAMP, cache.  
5. Snapshot tests dos **5 profiles** com Document **sintético/fixture** (não ACR).  
   Profiles: `inline_slash`, `chordpro_ref`, `onsong`, `propresenter`, `songbookpro` sob `titan_chordpro/writer/profiles/`.  
6. (Opcional) teste “chordpro CLI parse chordpro_ref” se binário disponível.  

### P2 — Lifecycle (só com operador / gates honestos)

7. Se re-spec ratificado: fechar T-003 de forma **GATE-R2-honesta** (verifier alinhado ao re-spec).  
8. F2-G2 continua **operador** (GO).  
9. Tag `v0.1.0-c0` só com known-issues + decisão explícita.  
10. Materialize F3 + tasks F3 + tag `v0.1.0` depois.  

### Não faça

- `phase-done` F2 com T-003 active e verifier antigo WCSR 0.70.  
- Merge cego da lane CHORD sem tabela de métricas.  
- PyPI / anúncio de produção.

---

## 6. Residuals de acorde (para known-issues — não para você “fixar”)

Baseline de qualidade (1 música estudada a fundo): **Ao olhar pra cruz** `9yZt5ekdceI`.

| Tema | Estado |
|------|--------|
| Pipeline acordes | htdemucs → **other+bass** → Chordino → reseg → bass recompute → placement |
| Progresso | LCS majmin brackets ~57% → ~92–93% (quality loop RC1–RC5 + v5) |
| Residual | Outro **F hold ~14.7s**; poucos FALTA/EXTRA/DIFF vs GT; inversões C/E vs C/G; ASR (`Me alver`…) |
| Separação | Vocals/drums **fora** do detect; full mix medido **pior** |
| GT humano | **Não é 100% verdade absoluta** — comparar com tolerância (lane CHORD detalha) |

Sample de 3 músicas (eval / GO futuro):

| youtube_id | Título | ~acordes no GT corpus |
|------------|--------|------------------------|
| `9yZt5ekdceI` | Ao olhar pra cruz | 105 |
| `LvoYT0loqLQ` | Teu santo nome | 84 |
| `LL5Pak4zcuA` | Jesus Tu És a Minha Vida | 97 |

Corpus: `chordpros.csv/songs.csv` (campo `chordpro` por linha).  
Render: `.venv-py312/bin/python scripts/render_from_url.py <id> --title "..." --language pt`  
Cache: `~/.cache/titan-chordpro/` (audio + cache stages).

---

## 7. Comandos úteis

```bash
cd /Volumes/External/code/titan-chordpro-lib
git checkout plan/titan-v01
git status && git log --oneline -5

# Estado do plano
# .atomic-skills/projects/titan-chordpro-lib/titan-v01/plan.md
# phases/f2-phase-c-validation-and-quality.md

# Worktree da lane CHORD (se existir) — NÃO commitar lá a partir desta sessão PLAN
git worktree list
```

**Automate:** se `executionMode: automate`, host PLAN não edita product chord; state + docs + fixtures ok; phase writer só se spawn para F3 **code** com brief selado.

---

## 8. Merge com a lane CHORD

1. CHORD rebase em `plan/titan-v01` com frequência.  
2. Promote CHORD → plan **só se**:  
   - allowlist de paths respeitada;  
   - testes unitários chord verdes;  
   - tabela before/after no sample (3 songs) com score ≥ baseline **ou** justificada;  
   - sem commits `.atomic-skills/` vindos do CHORD.  
3. Conflito em `orchestrator.py` / `pyproject.toml` → **PLAN arbitra**.  
4. Após merge CHORD: re-rodar unit tests; **não** apagar known-issues sem evidência.

---

## 9. Definition of done desta lane (sessão bem-sucedida)

- [ ] Roadmap/initiative honestos sobre F2 quality open  
- [ ] `docs/known-issues.md` existe e lista residual + “lib em dev only”  
- [ ] Re-spec T-003/G1 **proposto ou aplicado** (com ratify se automate)  
- [ ] Pelo menos um de: drafts F3 docs **ou** snapshots writer fixture verdes  
- [ ] Zero commits em `engines/chord/**`  
- [ ] Handoff initiative `## Session handoff` atualizado se mutou state  

---

## 10. Comunicação com o operador

- Português (BR) se for o host Grok neste projeto.  
- Não pedir GO de acorde como bloqueio de **todo** o trabalho — isso é F2-G2 quando ele puder.  
- Lembrar: **não está em produção**; errar c0 com known-issues é barato; mentir WCSR não.

---

## 11. Arquivos relacionados

| Arquivo | Uso |
|---------|-----|
| Este handoff | Lane PLAN |
| `.../2026-08-05-chord-lane-self-contained.md` | Lane CHORD |
| `.ai/memory/2026-08-04-titan-v01-session-handoff.md` | Histórico quality loop (pode estar desatualizado vs este) |
| `docs/roadmap.md` | Narrativa humana |
| `phases/f3-phase-d-pre-release.source.json` | Spec F3 |

**Fim do handoff PLAN — self-contained.**

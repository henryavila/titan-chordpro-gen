# Handoff SELF-CONTAINED — Lane CHORD (explorar acordes / arquiteturas)

**Para:** agent **code-only** (ou sessão dedicada) que **só** trabalha qualidade e arquitetura da **camada de reconhecimento de acordes**.  
**Data:** 2026-08-05  
**Repo root (referência):** `/Volumes/External/code/titan-chordpro-lib`  
**Branch recomendada:** `impl/chord-explore` (criar a partir de `plan/titan-v01`)  
**Worktree recomendada:** sibling **fora** do plan tree, ex.  
`/Volumes/External/code/titan-chord-explore`  
`git worktree add -b impl/chord-explore /Volumes/External/code/titan-chord-explore plan/titan-v01`  
**Produto:** biblioteca **apenas em dev — nunca lançada em produção.** Experimentar e descartar é barato.  
**Lane irmã:** PLAN avança F3/docs/lifecycle em `plan/titan-v01` — ver  
`.ai/memory/handoffs/2026-08-05-plan-lane-self-contained.md`  
Você **não** edita `.atomic-skills/`, não faz `done`/`phase-done`, não “fecha release”.

---

## 1. Missão

1. **Pesquisar** o estado da arte e hipóteses de ACR (audio chord recognition) aplicáveis a **Mac-first / local**, worship/pop PT-BR.  
2. **Implementar e testar** várias hipóteses / arquiteturas (não uma só), de forma **genérica** (proibido hardcode de título, youtube_id ou sequência de uma música no produto).  
3. **Comparar** cada candidato contra as **cifras-modelo do operador** (corpus) nas músicas do sample.  
4. **Escolher o melhor** por métricas + julgamento estruturado (não “parece ok”).  
5. Entregar: relatório + código no branch CHORD + **pedido de promote** se superar baseline.

### O que “melhor” significa aqui

- A cifra de referência do operador **não é 100% verdade absoluta** (arranjos, simplificações, erros humanos).  
- **Não** exija match perfeito de símbolos nem WCSR 1.0.  
- Prefira:  
  - **mesma progressão harmônica** na maior parte do tempo (raiz majmin / graus na tonalidade);  
  - **mudanças de acorde** nos lugares certos (não um F de 15s engolindo o outro);  
  - **menos faltas e extras grosseiros** que o baseline;  
  - legibilidade humana da cifra gerada.  
- WCSR-majmin do harness é **sinal útil**, não único juiz (GT denso ≠ igual-weight temporal).

---

## 2. Baseline do sistema atual (leia antes de reescrever o mundo)

### Pipeline de acordes (código atual)

```
áudio
  → HtdemucsEngine (vocals | bass | drums | other)     engines/separation/htdemucs.py
  → harmonic_mix = other + bass (mono)                 orchestrator._harmonic_mix_path
  → ChordinoEngine.detect(harmonic_mix, bass_stem=bass) engines/chord/chordino.py
       · VAMP Chordino
       · reseg de holds longos por chroma (funções primárias I/IV/V/vi/bVII)
       · postprocess (merge short, collapse majmin, key snap)
       · bass_note recompute pós-reseg                 engines/chord/bass_chroma.py
  → fusion placement / sectioner / writer              (NÃO é seu foco principal)
```

### Fatos de RCA já estabelecidos (não redescobrir às cegas)

| Fato | Implicação |
|------|------------|
| Detect roda em **other+bass**, **não** em vocals | Isolar voz **já** é o desenho; full mix medido **pior** em experimento anterior |
| `corr(harmonic_mix, other+bass) ≈ 1` | Mix está correto; bug principal **não** é “esqueceu de separar” |
| MMS_FA phoneme IDs quebravam sílabas | **Já corrigido** (RC1) — lane PLAN/histórico; não reverter |
| Placement melhorou (RC5) | Operador disse posicionamento ok; foque **símbolos / timeline de eventos** |
| Reseg subia LCS mas gerava Em (iii) falso; v5 limitou a funções primárias | Cuidado com FP de mediant |
| Residual forte | Hold **F ~14.7s** no outro; poucos FALTA/DIFF; inversões C/G vs C/E |

### Progresso histórico (1 música, Ao olhar pra cruz)

| Estágio | LCS majmin (ordem de grandeza) |
|---------|--------------------------------|
| Pré quality-loop | ~57% brackets |
| Pós RC1–RC5 + chord v5 | ~92–94% brackets / events |

**HEAD plan de onde ramificar (pin):** `5e190a2` ou mais novo `plan/titan-v01`.

---

## 3. Músicas-modelo (eval set do operador)

Definidas em `scripts/sample_run.py` (`_SELECTED_YT_IDS`).  
**Fonte de referência:** corpus `chordpros.csv/songs.csv` → objeto com `.youtube_id`, `.title`, `.chordpro` (texto ChordPro humano).

| # | youtube_id | Título | ~# brackets no GT |
|---|------------|--------|-------------------:|
| 1 | `9yZt5ekdceI` | Ao olhar pra cruz | 105 |
| 2 | `LvoYT0loqLQ` | Teu santo nome | 84 |
| 3 | `LL5Pak4zcuA` | Jesus Tu És a Minha Vida | 97 |

```python
from pathlib import Path
from benchmarks.corpus import load_corpus
songs, _ = load_corpus(Path("chordpros.csv/songs.csv"))
s = next(x for x in songs if x.youtube_id == "9yZt5ekdceI")
gt = s.chordpro  # referência humana (não 100% perfeita)
```

**Áudio cache:** `~/.cache/titan-chordpro/audio/<youtube_id>.m4a`  
**Stems (podem apontar paths antigos):** `.titan-stems/` ou paths em `stems.json` no stage cache  
**Stage cache:** `~/.cache/titan-chordpro/cache/<audio_id>/` (`chords.json`, `harmonic_mix.wav`, …)

**Render atual:**

```bash
cd /path/to/chord-explore-worktree
.venv-py312/bin/python scripts/render_from_url.py 9yZt5ekdceI \
  --title "Ao olhar pra cruz" --language pt \
  --output /tmp/titan-chord-explore/ao-olhar.chordpro
# scripts/render_from_url.py deve passar cache_root=~/.cache/titan-chordpro/cache
```

Comparação é **cara** (pipeline real + opcional re-detect). Estratégia:

1. Invalidar só stages necessários (`chords.json`, `document.json`) entre hipóteses de **detect**.  
2. Não re-rodar htdemucs/whisper se a hipótese é só ACR.  
3. Avaliar as **3 músicas** antes de declarar vencedor (não só uma).  
4. Guardar cada hipótese em diretório versionado:  
   `/tmp/titan-chord-explore/hyp-<name>/{id}.chordpro` + `metrics.json`.

---

## 4. Métricas de comparação (juiz automático)

Implemente ou reutilize um script (ex. `scripts/compare_chordpro_to_gt.py`) que, por música:

### 4.1 Sequência (obrigatório)

- Extraia símbolos `[...]` do GT e do Titan (ordem do documento **ou** ordem temporal se tiver eventos).  
- Normalize **raiz majmin** (C/Am/F/G…; slash opcional separado).  
- Alinhamento edit (match / substitute / delete=falta no Titan / insert=extra no Titan).  
- Reporte:  
  - `n_gt`, `n_est`  
  - `match`, `sub`, `del`, `ins`  
  - `match_rate = match / n_gt`  
  - LCS length / n_gt  

### 4.2 Timeline (se `chords.json` / eventos tiverem t)

- Duração máxima de hold por símbolo (flag se hold > N segundos, ex. 8–12s).  
- Contagem de “skip V” em loops tipo I–V–vi–IV se detectar tonalidade.

### 4.3 WCSR (opcional, harness existente)

- `benchmarks/` + `scripts/sample_run.py` se deps `[validation]` ok.  
- Não descarte hipótese só por WCSR se sequência harmônica melhorou muito (GT denso).

### 4.4 Score agregado sugerido (ranquear hipóteses)

```text
score = 0.50 * mean(match_rate_majmin)
      + 0.25 * mean(1 - normalized_edit_distance)
      + 0.15 * mean(hold_penalty)      # 1 se max_hold < 12s else decay
      + 0.10 * unit_tests_pass         # 0/1
```

Ajuste pesos se justificado no relatório; **fixe os pesos antes** de olhar os resultados finais (evita p-hacking).

### 4.5 Tolerância (referência ≠ perfeita)

- Não penalize só por `Am7` vs `Am` ou `Dm7` vs `Dm` **se** a raiz majmin bate (conte como match “soft” opcional).  
- Penalize forte: raiz errada em trechos estáveis, holds multi-compasso que apagam progressão, extras Em/iii sob pad.  
- Documente soft vs hard match nas tabelas.

---

## 5. Hipóteses / arquiteturas a explorar (fila — uma principal por vez)

Não implemente todas pela metade. Ordem sugerida (ROI):

| ID | Hipótese | Tipo | Notas |
|----|----------|------|-------|
| H0 | **Baseline pinada** (código atual em plan) | controle | Sempre re-medir primeiro |
| H1 | Reseg / split de **holds longos** (esp. fim de música) | pós-processo Chordino | Residual F 14.7s |
| H2 | Bass / slash (C/E vs C/G) mais estável | bass_chroma + attach order | |
| H3 | Vote / dual-path: other+bass vs other-only vs (opcional) no-vocal mix | arquitetura leve | Full mix já foi pior — revalidar se mudar features |
| H4 | Parâmetros Chordino / hop / merge thresholds | tuning | |
| H5 | Chroma-only ou template-Viterbi **sem** Chordino | ACR clássico | Pesquisa + protótipo |
| H6 | Modelo ML local (BTC / similar) se deps Mac viáveis | ACR ML | Pode ser pesado; BI 0.1 marca CUDA/BTC como oos de **release**, mas **dev explore ok** — não merge obrigatório |
| H7 | Multi-f0 / beat-sync change points | híbrido | |

Para cada Hn:

1. Branch ou commit `hyp-Hn-short-name`  
2. Testes unitários se mudar código de produto  
3. Rodar eval nas **3** músicas  
4. Escrever `hyp-Hn/metrics.json` + 10 linhas no relatório  
5. Comparar com H0  

**Promote para plan** só se: score agregado > H0 (margem mínima, ex. +2pp match_rate médio) **e** nenhuma regressão catastrófica numa das 3 músicas (ex. match_rate não cair >10pp em nenhuma).

---

## 6. Allowlist / denylist de paths

### Pode editar

- `titan_chordpro/engines/chord/**`  
- `titan_chordpro/engines/separation/**` só se a hipótese for separação (documente)  
- `titan_chordpro/orchestrator.py` **apenas** trechos de mix/detect wiring (diff mínimo)  
- `tests/unit/engines/chord/**`  
- `scripts/compare_*.py`, `scripts/render_from_url.py` (cache_root, flags de eval)  
- `benchmarks/**` só se necessário para métrica (não reescrever corpus)  
- Arquivos de relatório sob `/tmp/titan-chord-explore/` ou `docs/research/chord-explore-*.md` (se commitar research, ok)

### Não editar

- `.atomic-skills/**` (state do plano)  
- `docs/method.md` / F3 release docs (lane PLAN)  
- `titan_chordpro/cli.py`, README release polish  
- `titan_chordpro/fusion/**` **salvo** se inevitável — preferir NÃO; placement ok para o operador  
- Hardcode: `if title == "Ao olhar"` / listas de acordes de uma música em runtime  

### Hardcodes proibidos no **produto**

IDs de youtube e sequências GT **podem** aparecer em **scripts de eval** e testes — nunca no caminho de `detect()` de produção.

---

## 7. Pesquisa (faça de verdade)

Antes de H5/H6, leia e resuma (no relatório):

- Limitações de Chordino / NNLS / CRP em pads e loops I–V–vi–IV  
- Beat-synchronous chord recognition  
- Uso de stems (bass+other) na literatura  
- Opções Mac (CPU/MPS) sem assumir CUDA  

Cite 3–5 referências ou docs no relatório final da lane.

---

## 8. Processo de trabalho (obrigatório)

```text
1. Criar worktree + branch a partir de plan/titan-v01
2. Medir H0 (baseline) nas 3 músicas → metrics
3. Pesquisar + escolher próxima hipótese
4. TDD se mudar código de engine
5. Implementar hipótese (genérico)
6. Invalidar cache de chords/document; re-detect; render
7. Comparar vs GT modelo (tolerante); gravar metrics
8. Repetir 3–7
9. Escolher vencedor; escrever PROMOTE.md ou “no promote”
10. Nunca done/phase-done; nunca editar initiative YAML
```

### Microcommits

- Paths explícitos (`git add arquivo1 arquivo2`)  
- Mensagens: `feat(chord): ...` / `test(chord): ...` / `docs(research): ...`  

### Testes

```bash
.venv-py312/bin/python -m pytest tests/unit/engines/chord -q
# se tocou orchestrator de forma arriscada:
.venv-py312/bin/python -m pytest tests/unit/core tests/integration/test_cli.py -q
```

---

## 9. Entregáveis ao final da lane

1. **`/tmp/titan-chord-explore/REPORT.md`** (ou `docs/research/chord-lane-YYYY-MM-DD.md`) com:  
   - hipóteses testadas  
   - tabela 3 músicas × hipóteses (match_rate, del, ins, max_hold, WCSR se houver)  
   - vencedor e por quê  
   - o que **não** funcionou  
   - recomendações para PLAN (merge / known-issues / v0.2)  
2. Código no `impl/chord-explore` (ou commits claros).  
3. **`PROMOTE.md`** se pedir merge: lista de paths, métricas vs H0, riscos.  
4. Se nenhum beat H0: `PROMOTE.md` com `status: no-promote` e residuals para known-issues.

---

## 10. Coordenação com PLAN

| | PLAN | CHORD (você) |
|--|------|----------------|
| Branch | `plan/titan-v01` | `impl/chord-explore` |
| State AS | sim | **nunca** |
| F3 docs | sim | não |
| engines/chord | não | sim |
| Merge | dono do release | pede promote |

Rebase frequente:

```bash
cd /Volumes/External/code/titan-chord-explore
git fetch
git rebase plan/titan-v01   # ou merge; resolver sem trazer lixo
```

---

## 11. Comandos de bootstrap

```bash
cd /Volumes/External/code/titan-chordpro-lib
git fetch origin
git worktree add -b impl/chord-explore /Volumes/External/code/titan-chord-explore plan/titan-v01
cd /Volumes/External/code/titan-chord-explore
ln -sfn /Volumes/External/code/titan-chordpro-lib/.venv-py312 .venv-py312
ln -sfn /Volumes/External/code/titan-chordpro-lib/chordpros.csv chordpros.csv
mkdir -p /tmp/titan-chord-explore
# Medir baseline:
.venv-py312/bin/python scripts/render_from_url.py 9yZt5ekdceI --title "Ao olhar pra cruz" --language pt \
  --output /tmp/titan-chord-explore/hyp-H0/ao-olhar.chordpro
# ... idem outras 2 músicas; depois compare vs corpus GT
```

Python com ML: **`.venv-py312`**.  
Corpus e áudio já usados no dev do operador.

---

## 12. Definition of done (lane CHORD)

- [ ] H0 medido nas 3 músicas  
- [ ] ≥ 2 hipóteses além de H0 testadas **ou** 1 hipótese profunda com ablations  
- [ ] Relatório com tabela comparativa  
- [ ] Vencedor ou no-promote documentado  
- [ ] Testes unitários chord verdes no branch  
- [ ] Zero edits `.atomic-skills/`  
- [ ] Zero hardcodes de música no engine de produção  

---

## 13. Lembretes finais

- Referência humana **guia**, não oráculo.  
- Comparação é cara → minimize re-separation; maximize re-detect.  
- Operador validará com ouvido **depois**; seu trabalho é **reduzir o espaço de busca** com evidência.  
- Lib **não está em produção** — priorize aprendizado + melhor candidato mergeável, não perfeição.

**Fim do handoff CHORD — self-contained.**

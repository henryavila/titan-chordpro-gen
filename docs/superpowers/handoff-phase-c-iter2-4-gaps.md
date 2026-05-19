# Handoff — Phase C T70 iteração 2: 4 gaps descobertos antes de retomar T71

> **Para a próxima sessão Claude (qualquer modelo):** Leia este arquivo inteiro antes de qualquer coisa. Esta é uma pausa estratégica no meio do Phase C — T60-T69 estão entregues, T-pre executado, mas T70 (primeira rodada Tier 2.5) revelou **4 gaps** que precisam ser resolvidos antes de seguir T71-T73. Sua tarefa: atacar os 4 e me reportar antes de retomar a implementação do plano.

---

## Estado atual (verificado 2026-05-19)

- **Branch:** `main`
- **HEAD:** `ad62b4c fix(benchmarks/metrics): strip slash-bass for majmin scoring`
- **Tag mais recente:** `v0.1.0-b1`
- **Commits ahead de tag:** 24 (Phase C T60-T69 + 9 fixes T70-iter)
- **Test suite:** 447 passed / 16 skipped (`.venv` py3.14, mocks só)
- **ML stack:** instalado em `.venv-py312/` (Python 3.12.13 via uv)
- **ffmpeg:** 8.1.1 via brew (`/Volumes/External/homebrew/bin/ffmpeg`)
- **Working tree:** limpa exceto `.DS_Store` + pyc legados (ignorar)

### Pipeline atual (rodando)

`.venv-py312/bin/python /tmp/sample_run.py 3` roda 3 músicas end-to-end:
- yt-dlp ✓ (cache em `~/.cache/titan-chordpro/audio/`)
- htdemucs_ft ✓ (~3-7min por música)
- whisper.cpp (`base` model) ✓ (~3-5s)
- MMS forced_align (chunked emissions, ~2.5 GiB peak) ✓
- gruut PT ✓
- **chord_recognition = MOCK** (Chordino plugin offline)
- BeatThis (Audio2Beats API) ✓
- profile rendering ✓

Sistema **não trava mais** (memória liberada entre stages). 3/3 sucessos no último run. Cifras renderizadas em `benchmarks/reports/2026-05-19/cifras/*.chordpro`.

### O que está MEDINDO de verdade

WCSR=0.002. Isso **não diz nada** — mock chord (4 fixos C-G-Am-F no início) contra ground truth real (80-100 chords distribuídos) = score zero por design.

O que de fato funciona: download + separation + transcription + alignment + sectioning + syllabification + render + cache. **O que falta para o produto ser produto: cifras reais.**

---

## Os 4 gaps

### Gap 1 — Chordino plugin offline (BLOCKER do produto)

**Status:** plugin `code.soundsoftware.ac.uk/attachments/download/2540/chordino-vamp-plugin-mac.tar.gz` retorna timeout. `scripts/install_vamp.sh` falha silenciosamente. `brew install sonic-annotator` não existe mais no Homebrew. chord_extractor Python instala mas `extract()` crasha com `Failed to load plugin: nnls-chroma:chordino`.

**Impacto:** SEM chord_recognition real, validation harness é só estresse de infra. WCSR-majmin sempre será ~0. **Phase C não tem como validar a 1ª gate do spec §1683** (`WCSR ≥ 70%`).

**Investigar (ordem):**

1. **Mirror alternativo** do `chordino-vamp-plugin-mac.tar.gz`:
   - GitHub forks: `gh search repos chordino vamp`
   - archive.org wayback de `code.soundsoftware.ac.uk`
   - `web.archive.org/web/*/code.soundsoftware.ac.uk/attachments/download/2540/*`
   - apt/debian mirrors podem ter o `.so` Linux (não direto pra mac, mas pode dar pista)
2. **Build from source** — `https://github.com/c4dm/chordino` (last commit unclear): clone, build with VAMP SDK headers (`brew install vamp-plugin-sdk` ainda funciona — só sonic-annotator caiu). Build é autotools simples.
3. **`sonic-annotator` from source** — `https://github.com/cannam/sonic-annotator`. Não é estritamente necessário se chord_extractor usa libvamp diretamente (precisa testar).
4. **Trocar de detector** (escopo grande, último recurso):
   - `librosa.feature.chroma_cqt` + template matching → Sonificação pobre mas implementável em ~50 LOC
   - BTC-ISMIR19 (spec v0.2 §1739) — port pytorch, model neural, 1-2 semanas

**Critério de resolução:** rodar `pytest tests/integration/test_chordino_smoke.py -v` em `.venv-py312` e ver os 2 testes passando (não skipped por VAMP missing). Ou aceitar Plan B e abrir initiative pra trocar de chord detector.

**Arquivos relevantes:**
- `titan_chordpro/engines/chord/chordino.py` — wrapper
- `titan_chordpro/engines/chord/bass_chroma.py` — F-004 (já implementado, depende do chord_engine emitir chords reais)
- `scripts/install_vamp.sh` — install script que falha
- `docs/setup-vamp.md` — doc de install

---

### Gap 2 — Whisper modelo `base` é insuficiente

**Status:** `titan_chordpro/engines/transcription/whisper_cpp.py:23` tem `_DEFAULT_MODEL = "base"`. Phase B nunca questionou. Em PT-BR cantado real, `base` (~150 MB) acerta ~80%:
- "louvor" → "loucó"
- "adoração" → "doração"
- "Pois reconheço" → "Mas reconheço"

**Impacto:** spec §1683 não tem gate explícito de WER pra transcription, mas word offset < 100ms (também §1683) depende de palavras corretas pra ser sequer mensurável. E inspeção manual de cifra rendered fica horrível.

**Caminhos:**

1. **Trocar default pra `medium`** — 1 linha. Modelo `medium` é 1.5GB, ~92% accuracy. Download primeiro uso. Risco: lento em Mac sem GPU; mas com Metal backend (whisper.cpp já roda Metal aqui) é ~3-5x mais lento que `base`, aceitável.
2. **Expor model_id via CLI / env** — `--whisper-model medium` ou `TITAN_WHISPER_MODEL=medium`. Mais flexível.
3. **Per-language defaults** — PT-BR sai pra `medium`, EN fica `base` (whisper é mais forte em EN). Spec não diz isso explicitamente.

Recomendo **(1) + (2)** juntos: default `medium`, override via flag. Custa ~10 LOC + 1 teste.

**Critério de resolução:** re-rodar sample 1 song com `medium`; diff transcription.json (compare `text` field) com run anterior; visual inspect que letra ficou correta em >90%.

**Arquivos relevantes:**
- `titan_chordpro/engines/transcription/whisper_cpp.py` (linha 23, 49)
- `titan_chordpro/factory.py` — `select_transcription(model_id=...)` já aceita kwarg, pass-through funciona

---

### Gap 3 — Sectioner heurístico falha em músicas instrumental-heavy

**Status:** "Tua vontade" (intro 6/8 longo, vocais entram tarde) saiu com **única section "Instrumental"** — nenhuma letra renderizada. Sectioner em `titan_chordpro/fusion/sectioner.py` usa heurística simples (Phase A, spec §931-§953 chama de "v0.1: heurística simples"). Provavelmente: densidade de palavras por janela → se < threshold, classifica como instrumental.

**Impacto:** Phase C T70 manual gate (top-20 review) fica enganoso — músicas que falhem por sectioner aparecem como "Titan errado" quando o erro é só de classificação de boundary.

**Caminhos:**

1. **Inspecionar `sectioner.py`** — entender o threshold atual e qual janela está usando. Provavelmente é tunável via constante no topo do módulo.
2. **Frouxar threshold** — se a densidade média no áudio inteiro for X, só classifica instrumental quando janela < 0.3 * X. Adaptive.
3. **Forçar pelo menos 1 verse** quando houver palavras detectadas em qualquer trecho. Defensivo.
4. **Skip refactor** — sectioner é Phase A; v0.2 prevê All-In-One model (spec §1744). Aceitar como known-issue e documentar.

Recomendo **(2) + (3)** — ~20 LOC de patch, sem reescrever heurística.

**Critério de resolução:** re-rodar "Tua vontade" (já no cache); verificar que `document.json` tem pelo menos 1 LyricLine não-vazia.

**Arquivos relevantes:**
- `titan_chordpro/fusion/sectioner.py`
- `tests/unit/fusion/test_sectioner.py` (existem testes Phase A)

---

### Gap 4 — Plano omitiu 2 das 4 gates do spec §1683 (OBRIGATÓRIO)

**Status:** spec §1683 lista 4 gates para Phase C concluir:

```
1. WCSR-majmin ≥ 70%        ← plano T67 implementou (compute_wcsr_majmin)
2. Beat F-measure ≥ 0.85    ← OMITIDO no plano
3. word offset < 100ms      ← OMITIDO no plano
4. top-10 ≤ 3 "Titan errado" ← T70 manual gate (já implementado)
```

O plano `docs/superpowers/plans/2026-05-19-titan-v0.1-phase-c.md` T67 RI implementou **só `compute_wcsr_majmin`**. As outras 2 métricas (Beat F, word offset) **estão na spec mas não no plano**. **Codex review não pegou porque revisou plano vs si mesmo, não plano vs spec inteiro.**

**Impacto:** tecnicamente Phase C **não pode ser declarado completo** sem essas 2 métricas. T73 wrap-up + tag `v0.1.0-c0` seria spec-violating.

**Caminhos:**

1. **Implementar Beat F-measure no validation_runner.py:**
   - `mir_eval.beat.f_measure(reference_beats, estimated_beats, f_measure_threshold=0.07)`
   - Ref beats: do ground truth ChordPro **não tem timestamps de beat** — corpus iasdermelinda não inclui isso. Bloqueio real: precisa de outra fonte (BeatNet predictions de um modelo independente? Hand-annotated subset?).
   - Workaround: comparar Titan beats vs **um detector externo de referência** (madmom, BeatNet, librosa.beat). Não é ground-truth real mas é cross-validation.

2. **Implementar word offset metric:**
   - `mir_eval.transcription` não tem direto, mas existe método: pra cada palavra do ground truth, encontrar a palavra Titan mais próxima textualmente, calcular `abs(t_ref - t_titan)`. Reportar median.
   - Bloqueio: ChordPro do iasdermelinda **não tem word timestamps**. Mesmo problema do Beat F.

3. **Aceitar o gap e atualizar spec:**
   - Reconhecer que corpus iasdermelinda não tem timestamps suficientes pra essas 2 métricas
   - Editar spec §1683 pra remover ou flagear como "Phase D quando houver labeled corpus"
   - Manter só WCSR + top-10 como gates funcionais de Phase C

**Caminho que recomendo:** **(3)** + criar issue/initiative pra Phase D ou v0.2 implementar essas métricas com corpus labeled (ex.: DALI dataset). Documentar honestamente no roadmap.

**Critério de resolução:** decisão tomada + plano `docs/superpowers/plans/2026-05-19-titan-v0.1-phase-c.md` atualizado refletindo o que ficou IN e o que ficou OUT do scope final, com link pra a decisão.

**Arquivos relevantes:**
- `docs/superpowers/specs/2026-05-09-titan-v0.1-design.md` (§1683)
- `docs/superpowers/plans/2026-05-19-titan-v0.1-phase-c.md` (T67 RI)
- `benchmarks/validation_runner.py`
- `benchmarks/metrics.py`

---

## Ordem recomendada de ataque

1. **Gap 1 (Chordino)** primeiro — sem isso os outros gaps são polish em algo que não mede o produto.
2. **Gap 4 (spec gates)** segundo — decisão de escopo, não implementação. Destrava T73 wrap-up.
3. **Gap 2 (whisper medium)** depois — fix barato (~10 LOC + 1 teste).
4. **Gap 3 (sectioner)** por último — fix barato + tem fallback v0.2 (All-In-One).

Pode atacar em paralelo: Gap 1 (research) + Gap 4 (decisão) + Gap 2 (1 line change) em uma sessão.

---

## Referências rápidas

- **Plano Phase C:** `docs/superpowers/plans/2026-05-19-titan-v0.1-phase-c.md`
- **Spec v0.1:** `docs/superpowers/specs/2026-05-09-titan-v0.1-design.md`
- **Iniciativa ativa:** `.atomic-skills/initiatives/titan-phase-c.md` (status: active)
- **Review Codex:** `.atomic-skills/reviews/2026-05-19-1110-phase-c-plan-codex.md`
- **Memória CUDA vs MPS:** `~/.claude/projects/-Volumes-External-code-titan-chordpro-lib/memory/cuda_mps_alignment_comparison.md`
- **Cifras geradas (3 músicas):** `benchmarks/reports/2026-05-19/cifras/*.chordpro`
- **Report harness:** `benchmarks/reports/2026-05-19/top-divergences.md`

## Comandos úteis

```bash
# rodar sample 1 música (cache hit em 1+2 retorna instantâneo)
.venv-py312/bin/python /tmp/sample_run.py 1

# rodar com cache limpo
rm -rf ~/.cache/titan-chordpro/cache/ && .venv-py312/bin/python /tmp/sample_run.py 3

# rodar suite (não precisa de ML stack)
.venv/bin/pytest -q

# rodar suite com ML stack
.venv-py312/bin/pytest -q

# git status atual
git log --oneline v0.1.0-b1..HEAD

# render document.json → chordpro
.venv-py312/bin/python <<'PY'
import json
from pathlib import Path
from titan_chordpro.core.schemas import ChordProDocument
from titan_chordpro.writer.profiles.inline_slash import InlineSlashProfile
profile = InlineSlashProfile()
for d in sorted(Path.home().joinpath('.cache/titan-chordpro/cache').iterdir()):
    dp = d / 'document.json'
    if dp.exists():
        doc = ChordProDocument.model_validate(json.loads(dp.read_text()))
        print(f'=== {doc.metadata.title} ===')
        print(profile.render(doc))
PY
```

## Não-objetivos desta iteração

- NÃO retomar T71-T73 antes dos 4 gaps serem resolvidos / decididos
- NÃO implementar BTC-ISMIR19 v0.2 agora (escopo errado)
- NÃO mexer no Phase B engines exceto o whisper model_id default
- NÃO inflacionar plano com tasks novas; o plano já tem 15. Adicionar T67b / T70.1 se necessário.

## Quando voltar

Depois de resolver / decidir os 4 gaps, retomar implementação a partir de **T71** (CLI polish — rich progress + `--validate` flag). O plano daí em diante segue sem mudanças.

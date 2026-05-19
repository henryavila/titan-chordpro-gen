# Resolução — Phase C T70-iter2: os 4 gaps fechados

> Continuação de `docs/superpowers/handoff-phase-c-iter2-4-gaps.md`. Esta é a sessão que **resolveu** os 4 gaps. Próximo passo é retomar **T71** (CLI polish — rich progress + `--validate` flag) per o plano.

Data: 2026-05-19  ·  Branch: `main`  ·  Sessão: opus-4.7

---

## Resumo executivo

| Gap | Diagnóstico do handoff | Achado real após investigação | Resolução |
|-----|------------------------|------------------------------|-----------|
| 1 — Chordino plugin offline | URL de download morta; sonic-annotator caído do brew | `vampyhost` (arm64) já vinha no `chord_extractor`; faltava só o `.dylib` da arquitetura | Build from source — `c4dm/nnls-chroma` com `-arch arm64` via `Makefile.osx`. 94 chords reais em 3.2s na primeira validação |
| 2 — Whisper `base` insuficiente | Acerta ~80% PT-BR | Confirmado pior: em "Tua vontade" `base` retornou 17/17 segments como `[Música]` (filtrados → 0 palavras) | Default agora é `medium`; env `TITAN_WHISPER_MODEL` + flag `--whisper-model` para override |
| 3 — Sectioner falha em instrumental-heavy | "Algoritmo de densidade quebrado" (palpite do handoff) | **Misdiagnóstico**: sectioner estava correto. Falha real era whisper `base` produzindo 0 palavras (ver Gap 2) | Sem mudança no sectioner. Adicionado: log defensivo no orchestrator quando transcrição=0 mas RMS vocals>0.01, e regression test no sectioner |
| 4 — Plano omitiu 2 das 4 gates do spec | Gates Beat F + word offset não existem no plano T67 | Corpus iasdermelinda é text-only ChordPro — não dá pra gatear Beat F/word offset sem labeled corpus. Spec era inalcançável de fato | Spec §1683 e DoD atualizados: WCSR + top-20 ficam como gates; Beat F vira diagnóstico cross-detector (vs librosa); word offset é deferido pra Phase D. Plano ganhou tarefa T67b |

**Test suite:**
- `.venv` (py3.14, mocks): **469 passed**, 16 skipped (vs 447 baseline → +22 testes)
- `.venv-py312` (ML stack): **455 passed** unit. Integration: 34/35 passed; 1 falha pré-existente em `test_english_real_g2p_call` por NLTK data missing (não relacionada)

---

## Gap 1 — Chordino plugin: build from source

### Investigação

1. `chord_extractor` (pacote PyPI) usa `vamp` (python) → `vampyhost.cpython-312-darwin.so` **já é arm64**. O bug era apenas que o `.so` empacotado é Linux x86_64; em macOS arm64 não há plugin discoverável.
2. `vampyhost.get_plugin_path()` retorna `['~/Library/Audio/Plug-Ins/Vamp', '/Library/Audio/Plug-Ins/Vamp']` — basta colocar o plugin nativo lá.
3. `code.soundsoftware.ac.uk` (mirror oficial) está offline. `sonic-annotator` caiu do Homebrew core. Mas: **não precisamos de sonic-annotator** — `chord_extractor` usa `vampyhost` diretamente.
4. Source canônico: `https://github.com/c4dm/nnls-chroma` (GPL-2.0, 6 tags, último release 0.3). `Makefile.osx` aceita override de `ARCHFLAGS`.

### Build (executado nesta sessão)

```bash
brew install vamp-plugin-sdk boost
git clone --depth=1 https://github.com/c4dm/nnls-chroma.git /tmp/titan-build/nnls-chroma
cd /tmp/titan-build/nnls-chroma
make -f Makefile.osx \
    VAMP_SDK_DIR="$(brew --prefix vamp-plugin-sdk)/include" \
    BOOST_ROOT="$(brew --prefix boost)/include" \
    ARCHFLAGS="-mmacosx-version-min=11.0 -arch arm64" \
    LDFLAGS="-mmacosx-version-min=11.0 -arch arm64 -dynamiclib \
             -install_name nnls-chroma.dylib \
             $(brew --prefix vamp-plugin-sdk)/lib/libvamp-sdk.a \
             -exported_symbols_list vamp-plugin.list -framework Accelerate"
mkdir -p ~/Library/Audio/Plug-Ins/Vamp
cp nnls-chroma.{dylib,cat,n3} ~/Library/Audio/Plug-Ins/Vamp/
```

Tempo: ~30s. Output: `nnls-chroma.dylib` (289 KB, `Mach-O 64-bit dynamically linked shared library arm64`).

### Validação

```python
>>> import vampyhost; vampyhost.list_plugins()
['nnls-chroma:chordino', 'nnls-chroma:nnls-chroma', 'nnls-chroma:tuning']

>>> from chord_extractor.extractors import Chordino
>>> chords = Chordino().extract('/Users/henry/.cache/titan-chordpro/audio/5qDYNTIJPsI.m4a')
# 94 chord events in 3.2s on real M4A audio — including 'C#/G#' slash chord
```

Smoke tests (`tests/integration/test_chordino_smoke.py`) agora **passam** (antes: 3 SKIPPED por sonic-annotator missing).

### Arquivos modificados

- `scripts/install_vamp.sh` — reescrito do zero. Build-from-source, sem dependência do mirror morto, sem sonic-annotator
- `docs/setup-vamp.md` — instruções atualizadas para macOS arm64
- `tests/integration/test_chordino_smoke.py` — gate trocada de `shutil.which("sonic-annotator")` para `vampyhost.list_plugins()` (which é o que de fato matters)

---

## Gap 2 — Whisper default = `medium`

### Investigação

Rodando `base` vs `medium` no vocals stem real de "Tua vontade" (Z_LqMuDGsfs):

```
base   model: 17 segments in 1.0s — ALL 17 são '[Música]' (zero palavras reais)
medium model: 22 segments in 10.9s — primeiro segment é '[silêncio]' (intro 6/8 longo),
              resto: 'Norte ou sul, noite ou dia eu te seguirei', etc — letra correta
```

`base` é estruturalmente inviável para PT-BR cantado neste corpus. Não é cosmético — é catastrófico.

### Mudança

- `titan_chordpro/engines/transcription/whisper_cpp.py:24` — `_DEFAULT_MODEL = os.environ.get("TITAN_WHISPER_MODEL", "medium")` (era `"base"`)
- `titan_chordpro/factory.py` — `select_transcription(transcription_model_id=None)` aceita override via kwarg, propagado pelo orchestrator
- `titan_chordpro/cli.py` — flag `--whisper-model` com choices `tiny|base|small|medium|large-v2|large-v3`
- Testes: `test_whisper_cpp.py::TestWhisperCppDefaultModel` (env override + default)

### Custo

`medium` é ~10s para um vocals stem de 4 min em Apple M4 com Metal backend (vs ~1s para `base`). Aceitável dado que a alternativa era output inutilizável.

---

## Gap 3 — Sectioner: misdiagnóstico documentado

### O que o handoff disse

> "Sectioner em `titan_chordpro/fusion/sectioner.py` usa heurística simples. Provavelmente: densidade de palavras por janela → se < threshold, classifica como instrumental."

### O que a investigação encontrou

`sectioner.py` **não** usa densidade. Usa gap-based grouping: palavras com gap > `INSTRUMENTAL_GAP_BEATS * beat_period` são separadas em blocos diferentes. Quando há ≥ 1 palavra, **sempre** produz ≥ 1 lyric section. O algoritmo está correto.

A causa raiz do "Tua vontade tem só Instrumental" foi: `transcription.json` continha `words: []` (zero palavras). Sectioner cai no `if not words` (linha 60) → 1 instrumental para a duração inteira. Comportamento documentado e correto.

Por que `words: []`? Whisper `base` retornou 17 segments todos `[Música]`, e o filtro `_WHISPER_SPECIAL_TOKEN_RE` (whisper_cpp.py:29) corretamente descartou todos. Resultado: TranscriptionResult(words=[]).

**Conclusão**: Gap 3 é Gap 2 disfarçado. Com `medium` como default (Gap 2), o problema desaparece.

### Mudanças mesmo assim (defensivo)

1. `titan_chordpro/orchestrator.py` — quando `trans_result.words == []` mas `librosa.load(stems.vocals).rms > 0.01`, emite WARNING claro apontando para `--whisper-model medium`. Operador agora sabe diagnosticar em segundos.
2. `tests/unit/fusion/test_sectioner.py::test_any_words_present_produces_at_least_one_lyric_section` — pin de regressão para garantir que o sectioner sempre gera ≥ 1 lyric section quando há palavras. Comentário do teste explica o misdiagnóstico para futuros leitores.

Sectioner permanece intocado.

---

## Gap 4 — Gates do spec §1683: honestidade sobre corpus

### Investigação

Spec §1683 lista 4 gates: WCSR-majmin ≥ 70%, Beat F ≥ 0.85, word offset < 100ms, top-10 ≤ 3 errado.

Realidade do corpus iasdermelinda (`chordpros.csv/songs.csv`): cada linha tem `title, external_link, chordpro`. O `chordpro` é texto puro **sem timestamps de beat ou word**. Conclusão: **2 das 4 gates são inalcançáveis pelo corpus existente**.

Workarounds explorados:
- **Beat F via librosa.beat como referência?** Cross-detector consistency, não ground truth. Mostrado empiricamente: librosa detectou 152 BPM em "Entrega" (chordpro diz 77 BPM via `{tempo:}`). Nem librosa nem BeatThis dão verdade absoluta — comparar um contra o outro mede agreement, não correctness.
- **Word offset via WhisperX?** Circular — Titan já usa whisper. E adiciona dep pesada.

### Decisão (locked-in, refletida em spec + plano)

| Gate                          | Phase C status                              | Phase D plan |
|-------------------------------|---------------------------------------------|--------------|
| WCSR-majmin ≥ 70%             | **gate** (coarse interval mapping)          | tighten with labeled chord intervals |
| Top-10 ≤ 3 "Titan errado"     | **gate manual** (Henry T70)                 | unchanged |
| Beat F-measure ≥ 0.85         | **diagnóstico** (cross-detector vs librosa) | gate against labeled beats |
| Word offset < 100ms           | **deferido**                                | gate with labeled word boundaries |

### Implementação

- `benchmarks/metrics.py::compute_beat_consistency_vs_librosa(audio, titan_beats)` — usa `mir_eval.beat.f_measure` (sensível a octave error) + `mir_eval.beat.continuity` → AMLt (octave-invariant). Retorna `{f_measure, amlt}`.
- `benchmarks/validation_runner.py::SongMetric` ganha `beat_f_cross_librosa` e `beat_amlt_cross_librosa` (default 0.0). Diagnóstico só — não rejeita nightly se < 0.85.
- `docs/superpowers/specs/.../titan-v0.1-design.md` §1683 + DoD reescritos para refletir o que o corpus de fato suporta. Comentário explícito de que gates "≥ 0.85 / < 100ms" movem para Phase D.
- `docs/superpowers/plans/2026-05-19-titan-v0.1-phase-c.md` — nova tarefa **T67b** documentando a decisão.
- 3 testes novos: `TestComputeBeatConsistencyVsLibrosa` (synthetic click + edge cases).

---

## Estado da test suite e do próximo passo

- `.venv` (py3.14 mock-only): **469 passed**, 16 skipped
- `.venv-py312` (ML stack):    **455 passed** unit, **34 passed + 1 skipped** integration; 1 failure pré-existente em `test_english_real_g2p_call` (NLTK data missing — não-relacionada)

### O que retomar

`docs/superpowers/plans/2026-05-19-titan-v0.1-phase-c.md` agora aponta para **T71** (CLI polish — rich progress + `--validate` flag) como próxima tarefa. Plano interno (T60..T70) está done; T67b foi inserido entre T67 e Checkpoint 8 documentando a decisão de gates.

### Cache invalidation recomendada antes de T70 re-run

Cache atual em `~/.cache/titan-chordpro/cache/` foi gerada com whisper `base`. Para uma top-20 review honesta, invalidar:

```bash
rm -rf ~/.cache/titan-chordpro/cache/
# audio cache (~/.cache/titan-chordpro/audio/) pode ficar — yt-dlp downloads custosos
```

Próximo run usará whisper `medium` default. Tempo estimado para 151 songs end-to-end: ~6-8 horas em M4 (dominado por htdemucs + whisper medium).

# Handoff — Phase C T70-iter4: corrigir placement das cifras

> **Para a próxima sessão Claude:** leia este arquivo inteiro antes de qualquer coisa. Iter2/iter3 fecharam 4 gaps + word-level whisper + adaptive sectioner + anti-hallucination. Letra está em ~95% (validado por Henry). **Próximo problema: placement das cifras ainda muito errado.**

---

## Estado verificado (2026-05-20)

- **Branch:** `main`
- **HEAD:** `c4840b1 fix(phase-c): tighten whisper anti-hallucination thresholds`
- **Tag mais recente:** `v0.1.0-b1`
- **Test suite:** 451 passed / 7 skipped (`.venv` py3.14 mocks)
- **ML stack:** `.venv-py312/` (Python 3.12)
- **Cache:** `~/.cache/titan-chordpro/cache/` com 3 músicas processadas end-to-end:
  - `c54e57cd59ac8018` = Ao olhar pra cruz
  - `cad6e201af7353c6` = Teu santo nome
  - `cae47354d4d9133b` = Jesus Tu És a Minha Vida (alt LL5Pak4zcuA)

### Pipeline atual (todos os fixes aplicados)

- whisper.cpp `medium` (default) + `token_timestamps + max_len=1 + split_on_word` (word-level)
- `entropy_thold=2.2`, `no_speech_thold=0.7` (anti-hallucination)
- chordino real arm64 dylib (built from c4dm/nnls-chroma)
- MMS forced_align via torchaudio (chunked emissions)
- gruut PT syllabification
- sectioner adaptativo (`median_gap × 8`, floor 4.0s)
- Beat tracking BeatThis
- Document inclui `beat_grid` (Phase C T70-iter2 fix)

### .chordpro renderizados

`benchmarks/reports/2026-05-20/cifras/*.txt`:
- `Ao-olhar-pra-cruz.txt` — 1630 B
- `Teu-santo-nome.txt` — 1733 B
- `Jesus-Tu-s-a-Minha-Vida.txt` — 1238 B

---

## O problema

Henry validou letra em ~95% (whisper medium + anti-hallucination + word-level). Reportou: "as cifras estão melhor, mas ainda muito errado no placement".

Sample do problema atual (Ao olhar pra cruz, verse 1):

```
{start_of_verse}
Andei tão cego,
[G]sem rumo certo,
buscando a paz e [Em]descanso.
[Am]Eu procurei, por tantos meios, justificar meus [F]erros. Mas ao clamar,
[F][G]meus olhos abrir. E
[Am7]ao olhar pra [F]cruz, eu entendo o amor derramado a mim, [F]por [G]mim.
[F][C/G]Sacrifício de sangue por um pecador.
[Dm7]Não sou merecedor,
[C/G][Gm]tua graça me alcançou.
{end_of_verse}
```

Observações:
- `[F][G]meus olhos` — 2 chords stacked antes de "meus" (ambos chord changes acontecem entre "abrir" e "meus"?)
- `[F][G]por mim.` — similar stacking
- `[F][C/G]Sacrifício` — 2 chords no mesmo onset
- `[C/G][Gm]tua graça` — 2 chords stacked

Esperado (referência iasdermelinda):
```
[C]Andei tão [G]cego, sem rumo [Am]certo, [F]buscando a paz e des[C]canso.
[Am]Eu procurei por [F]tantos meios, [C]justificar meus [G]erros.
```

Cifras DEVERIAM estar distribuídas em cada beat/measure, não clumped em transições. Compare com ground truth.

---

## Hipóteses iniciais (não verificadas)

1. **Placer atribui chord markers só nos onsets**: se Chordino emite chord onset em t=X e a palavra mais próxima está em t=X-ε, todos os chords daquela transição agarram a mesma palavra → stacking.

2. **Chords em silêncio/instrumental entre frases vão para a próxima palavra**: gaps de 2-3s entre frases têm cifras (intro, fill), mas o placer sem syllable-anchor pode "empurrar" tudo pra próxima palavra.

3. **Falta heurística "chord per beat" para regiões instrumentais**: ground truth tem chord change a cada 2-4 beats; nosso placer atribui chord só quando chordino detecta mudança. Estes são fenômenos diferentes.

4. **`text_position` está sempre apontando para o início da palavra**: pode estar correto algoritmicamente mas visualmente fica clumped. Pode precisar de "spread" ou heuristic de displacement.

---

## Arquivos relevantes

- `titan_chordpro/fusion/placer.py` — onde rodadinha mora (chord-on-syllable algorithm)
- `titan_chordpro/core/schemas.py` — `ChordMarker.text_position`, `LyricLine.chord_markers`
- `titan_chordpro/writer/profiles/inline_slash.py` — renderiza `[chord]` no `text_position`
- `titan_chordpro/fusion/sectioner.py` — passa chords pra `_make_lyric_section` que chama placer
- `~/.cache/titan-chordpro/cache/<id>/document.json` — final output assembled

---

## Comandos úteis

```bash
# Inspecionar chord_markers de uma música cacheada
.venv-py312/bin/python -c "
import json
from pathlib import Path
doc = json.load(open(Path.home()/'.cache/titan-chordpro/cache/c54e57cd59ac8018/document.json'))
for s in doc['sections']:
    if s.get('type') != 'verse': continue
    for line in s['lines']:
        if line.get('line_type') != 'lyric': continue
        print(f'TEXT: {line[\"text\"]!r}')
        for m in line.get('chord_markers', []):
            print(f'  pos={m.get(\"text_position\")!r}  syll_idx={m.get(\"syllable_index\",\"?\")}  chord={m[\"chord\"][\"symbol\"]!r}  t={m[\"chord\"][\"timestamp\"][\"start\"]:.2f}s')
        break
    break
"

# Inspecionar chord events brutos (do chordino) para uma música
.venv-py312/bin/python -c "
import json
from pathlib import Path
ch = json.load(open(Path.home()/'.cache/titan-chordpro/cache/c54e57cd59ac8018/chords.json'))
for c in ch[:30]:
    print(f'{c[\"timestamp\"][\"start\"]:6.2f}-{c[\"timestamp\"][\"end\"]:6.2f}s  {c[\"symbol\"]!r}')
"

# Re-renderizar (não precisa re-rodar pipeline)
.venv-py312/bin/python /tmp/render_chordpros.py

# Re-rodar só assembly + render se mexer no placer
find ~/.cache/titan-chordpro/cache -name "document.json" -delete && \
.venv-py312/bin/python /tmp/sample_run.py
```

---

## Não-objetivos desta iteração

- NÃO mexer no whisper (já está bom o suficiente, foco é placement)
- NÃO mexer no sectioner (adaptive funcionou)
- NÃO trocar chordino (limitação majmin é conhecida, fora do scope v0.1)
- NÃO adicionar multi-arch ASR (pesquisa em iter3 mostrou ROI baixo em v0.1)
- NÃO inflacionar plano. Phase C ainda tem T71-T73 pendentes (CLI polish + README + tag).

---

## Quando voltar

Resolver placement → tagear `v0.1.0-c0` após Henry validar. Phase C wrap-up está esperando T71-T73.

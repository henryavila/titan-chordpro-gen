# Design — Seção 4: ChordPro Writer + Output Profiles

> Parte 4 de 6 do design do Titan ChordPro Lib v0.1.
> Esta seção define como o `ChordProDocument` (estrutura interna Pydantic) é serializado em texto `.chordpro` válido — incluindo múltiplos perfis de saída para compatibilidade com diferentes apps + o formato de fato usado pela comunidade do owner (iasdermelinda).
> Data: 2026-05-08

---

## Por que múltiplos perfis de saída

A pesquisa `05-chordpro-format.md` documentou um problema de fragmentação:

| Aspecto | Reference impl (chordpro.org) | OnSong | ProPresenter | SongbookPro | iasdermelinda (real-world) |
|---|---|---|---|---|---|
| `[chord]` inline | ✅ | ✅ | ✅ | ✅ | ✅ |
| `{sog}/{eog}` (chord grid block) | ✅ | ❌ | ❌ | ❌ | ❌ |
| `[C]x///` inline rhythm notation | (não-canonical) | ✅ | ✅ | ✅ | ✅ |
| Strum patterns `\|S` | ✅ (≥6.080) | ❌ | ❌ | ❌ | ❌ |
| `{sot}/{eot}` (tab block) | ✅ (PDF render) | ✅ | partial (text only) | ✅ | (não usado para ritmo) |

**Implicação:** se a Titan emitir só com `{sog}/{eog}` (canonical), a saída renderiza bem no chordpro reference impl mas **não nos apps de live-performance que dominam o mercado** (OnSong, ProPresenter, SongbookPro) **nem no fluxo real do owner** (iasdermelinda usa `[C]x///` inline).

Solução: **output profiles plugáveis**, com default que maximiza compatibilidade.

---

## Princípios de design dos profiles

1. **Mesma `ChordProDocument` → múltiplos textos `.chordpro`.** Documento interno é fonte única de verdade; profiles são serializadores diferentes.
2. **Profiles são puros** — apenas leem o documento e produzem string. Nunca mutam state.
3. **Profile padrão = mais permissivo.** `inline_slash` (formato real-world) é o default por gerar saída que funciona em mais apps. Reference profile fica como opt-in para usuários que querem strict canonical.
4. **Owner pode adicionar profile próprio** — Protocol simples permite plugin de terceiros.

---

## Output Profile Protocol

Em `writer/profiles/base.py`:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class OutputProfile(Protocol):
    """Serializes a ChordProDocument into .chordpro text for a specific target."""
    
    @property
    def name(self) -> str:
        """Profile identifier: 'chordpro_ref', 'inline_slash', 'onsong', etc."""
        ...
    
    @property
    def description(self) -> str:
        """Human-readable description of which apps this profile targets."""
        ...
    
    def render(self, doc: ChordProDocument) -> str:
        """Return the full .chordpro file content as a string."""
        ...
```

Registry em `writer/profiles/__init__.py`:

```python
PROFILES: dict[str, OutputProfile] = {
    'inline_slash': InlineSlashProfile(),         # default
    'chordpro_ref': ChordProReferenceProfile(),
    'onsong': OnSongProfile(),
    'propresenter': ProPresenterProfile(),
    'songbookpro': SongbookProProfile(),
}

def get_profile(name: str) -> OutputProfile:
    if name not in PROFILES:
        raise ValueError(f"Unknown output profile: {name!r}. Known: {list(PROFILES)}")
    return PROFILES[name]
```

---

## Profile 1 — `inline_slash` (DEFAULT)

**Target:** OnSong, ProPresenter, SongbookPro, iasdermelinda.com.br, qualquer app que renderiza ChordPro plano sem suporte a `{sog}/{eog}`. Cobre maior parte do mercado real.

**Características:**
- Chords inline `[chord]` em qualquer lugar
- Notação rítmica usando `[C]x///` (full measure) ou `[C]x/[G]/[F]/` (half/quarter measures)
- Tabs em `{sot}`/`{eot}` (suportado universalmente)
- Comments `{c:...}` para sinal real (Solo, Modulação, etc.)
- Sem grids `{sog}`/`{eog}`

**Exemplo de output:**

```chordpro
{title: Grande Deus}
{subtitle: Adoradores 2}
{key: E}
{tempo: 85}
{time: 4/4}
{meta: titan_version 0.1.0}
{meta: titan_confidence_chord 0.92}

{c:(Introdução)}
[E]x///   [E]x/[D]/[A]/     [E]x///   [E]x/[D]/[A]/

{start_of_verse}
Em [E]tua presença quero es[A/E]tar
[E]Completo quero me entre[A/E]gar
[E]x// Dar graças [E/G#]e can[A]tar [D/A]/
{end_of_verse}

{c:(SUBINDO)}
{start_of_chorus}
Pois tu, Se[B]nhor, és nosso criad[B]or
Nas tuas [C#m]mãos estão a terra e o [C#m]mar
{end_of_chorus}
```

**Regras de geração para LyricLines:**

```python
def render_lyric_line(line: LyricLine) -> str:
    """Insert [chord] markers at char_position."""
    result = []
    cursor = 0
    for marker in sorted(line.chord_markers, key=lambda m: m.char_position):
        result.append(line.text[cursor:marker.char_position])
        bracket = _format_chord(marker.chord)  # e.g. "[C]" or "[G/B]"
        result.append(bracket)
        cursor = marker.char_position
    result.append(line.text[cursor:])
    return ''.join(result)
```

**Regras de geração para InstrumentalLines:**

```python
def render_instrumental_line(line: InstrumentalLine) -> str:
    """Format instrumental measures using [chord]x/// notation.
    
    Pattern hint determines subdivision:
    - 'full_measure': [C]x///
    - 'half_measure': [C]x/ [G]x/ (or [C]x/[G]/ inline)
    - 'beat': [C]/[D]/[E]/[F]/ (one chord per beat)
    """
    if line.pattern_hint == 'full_measure':
        return '   '.join(f'[{c.symbol}]x///' for c in line.chords)
    elif line.pattern_hint == 'half_measure':
        # Pair chords per measure
        paired = _pair_chords_per_measure(line.chords)
        return '   '.join(f'[{a.symbol}]x/[{b.symbol}]/' for a, b in paired)
    elif line.pattern_hint == 'beat':
        return ' '.join(f'[{c.symbol}]/' for c in line.chords)
```

---

## Profile 2 — `chordpro_ref`

**Target:** Strict canonical ChordPro reference implementation, Linkesoft Songbook, LivePrompter. Para usuários que querem output que renderiza em PDF via `chordpro` CLI.

**Diferenças em relação a `inline_slash`:**
- Usa `{start_of_grid}` / `{end_of_grid}` blocks para passagens rítmicas (em vez de `[C]x///` inline)
- Suporta strum patterns `|S` se `Section.lines[i]` tiver pattern hint estruturado (v0.1 não emite, mas profile aceita extensions futuras)

**Exemplo de output:**

```chordpro
{title: Grande Deus}
{key: E}
{tempo: 85}
{time: 4/4}

{start_of_grid: Intro}
| E .   .   . | E . D . | A . . . |
{end_of_grid}

{start_of_verse}
Em [E]tua presença quero es[A/E]tar
{end_of_verse}
```

**Regra para mapping InstrumentalLine → grid:**

```python
def render_instrumental_as_grid(line: InstrumentalLine, time_sig: tuple[int, int]) -> str:
    """Convert chord sequence + pattern_hint to {sog}/{eog} grid block."""
    cells_per_measure = time_sig[0]  # 4 for 4/4, 6 for 6/8
    rows = _chunk_chords_to_grid(line.chords, cells_per_measure)
    body = '\n'.join('| ' + ' . '.join(c or '.' for c in row) + ' |' for row in rows)
    return f'{{start_of_grid}}\n{body}\n{{end_of_grid}}\n'
```

---

## Profile 3 — `onsong`

**Target:** OnSong app (iOS-popular para músicos worship/cover bands).

**Diferenças:**
- Não usa `{sog}/{eog}` (OnSong ignora silenciosamente)
- Usa `[chord]x///` inline (igual `inline_slash`)
- OnSong tem extensions próprias (`{x_*}`) que podemos usar quando útil:
  - `{x_capo: 2}` — equivalente a `{capo: 2}` mas reconhecido por OnSong
- Section directives `{soc}/{eoc}/{sov}/{eov}` todos suportados
- Tab blocks `{sot}/{eot}` suportados
- Conditional selectors `-Guitar`, `-Piano` (não emitimos por padrão; documentar como opção futura)

**Em essência:** `inline_slash` + extensions OnSong-friendly. ~80% mesmo código que `inline_slash`.

---

## Profile 4 — `propresenter`

**Target:** ProPresenter 7 (church live-performance dominante).

**Diferenças:**
- ProPresenter 7 trata maioria das directives como import-only (uma vez importado, app é dono)
- Algumas directives são silenciosamente ignoradas: `{tempo}`, `{time}`, `{capo}`, `{column_break}`, `{x_*}`
- Tab blocks renderizam como texto monoespaçado (sem semantic structure)
- **Importante:** ProPresenter prefere SEM `{sog}/{eog}` (não suporta), SEM strum patterns, COM section blocks e plain `[chord]` inline
- Uso de `{ccli}` é importante para integração com sistema de licenciamento ProPresenter

**Em essência:** subset de `inline_slash` + adicionar `{ccli: ...}` se metadata.extensions tiver, omitir directives ignored silenciosamente.

---

## Profile 5 — `songbookpro`

**Target:** SongbookPro (Android-popular, brasileiro).

**Diferenças:**
- Suporta extensions próprias `{x_sbp_tags: praise, contemporary}` para tagging
- Não suporta `{sog}/{eog}`
- Usa convention `{x_*}` para metadata adicional
- Tab blocks suportados como fixed-width text

**Em essência:** `inline_slash` + tag extensions quando metadata.extensions tiver chaves `sbp_*`.

---

## Header rendering (compartilhado entre profiles)

Cada profile começa com header padrão:

```python
def render_header(meta: Metadata, prov: Provenance) -> str:
    lines = [f'{{title: {meta.title}}}']
    if meta.artist:
        lines.append(f'{{artist: {meta.artist}}}')
    if meta.key:
        lines.append(f'{{key: {meta.key}}}')
    if meta.tempo:
        lines.append(f'{{tempo: {meta.tempo}}}')
    if meta.time_signature:
        num, den = meta.time_signature
        lines.append(f'{{time: {num}/{den}}}')
    if meta.capo > 0:
        lines.append(f'{{capo: {meta.capo}}}')
    
    # Provenance metadata as {meta: titan_*} entries (round-trip safe)
    lines.append(f'{{meta: titan_version {prov.titan_version}}}')
    for stage_conf in prov.confidence:
        lines.append(f'{{meta: titan_confidence_{stage_conf.stage} {stage_conf.mean:.2f}}}')
    
    # Custom extensions (if any)
    for k, v in meta.extensions.items():
        lines.append(f'{{meta: {k} {v}}}')
    
    return '\n'.join(lines) + '\n\n'
```

Profiles individuais podem sobrescrever esse método se precisarem (ex: `propresenter` adiciona `{ccli}`, `songbookpro` adiciona `{x_sbp_tags}`).

---

## Chord symbol formatting

Todos profiles emitem chord symbols da mesma forma:

```python
def _format_chord(chord: ChordEvent) -> str:
    """Returns '[C]', '[Cmaj7]', '[G/B]', etc."""
    # Validator on ChordEvent already ensures symbol/bass_note consistency.
    # If symbol contains '/', use it as-is. Otherwise, append /bass_note if present.
    if '/' in chord.symbol:
        return f'[{chord.symbol}]'
    if chord.bass_note:
        return f'[{chord.symbol}/{chord.bass_note}]'
    return f'[{chord.symbol}]'
```

Edge cases:
- Empty/null chord (silence/no-chord): emitido como `[N]` ou simplesmente omitido (default: omit; `[N]` opt-in via profile config)
- Chord muito longo (>10 chars, ex: `[Cmaj7sus4add9/E]`): renderizado como-is; é responsabilidade do usuário garantir que chord engine não produz lixo

---

## Section rendering

Sections (`Section`) viram blocos `{sov}/{eov}`, `{soc}/{eoc}`, `{sob}/{eob}` baseados em `Section.type`:

```python
SECTION_DIRECTIVES = {
    'verse':    ('{start_of_verse}',  '{end_of_verse}'),
    'chorus':   ('{start_of_chorus}', '{end_of_chorus}'),
    'bridge':   ('{start_of_bridge}', '{end_of_bridge}'),
    'pre-chorus': None,  # no canonical directive; render as comment instead
    'instrumental': None,  # render as comment + chord lines
    'intro':    None,
    'outro':    None,
}

def render_section(section: Section, profile: OutputProfile) -> str:
    if section.type in ('verse', 'chorus', 'bridge'):
        start, end = SECTION_DIRECTIVES[section.type]
        body = '\n'.join(profile.render_line(line) for line in section.lines)
        return f'{start}\n{body}\n{end}\n'
    else:
        # intro/outro/pre-chorus/instrumental: prepend {c: <label>}
        comment = f'{{c: {section.label}}}'
        body = '\n'.join(profile.render_line(line) for line in section.lines)
        return f'{comment}\n{body}\n'
```

---

## CLI integration

```bash
$ titan-chordpro song.mp3 --profile=inline_slash    # default
$ titan-chordpro song.mp3 --profile=onsong --output=song.chordpro
$ titan-chordpro song.mp3 --list-profiles
Available output profiles:
  inline_slash    Default. Compatible with OnSong, ProPresenter, SongbookPro,
                  and the iasdermelinda real-world format.
  chordpro_ref    Strict ChordPro reference. PDF rendering via chordpro CLI.
                  Uses {sog}/{eog} grids.
  onsong          OnSong-targeted with {x_*} extensions.
  propresenter    ProPresenter 7 import-friendly. Omits ignored directives.
  songbookpro     SongbookPro-targeted with tag extensions.
```

Library API:

```python
from titan_chordpro import transcribe

doc = transcribe("song.mp3")
text = doc.to_string(profile='inline_slash')   # default
text_pdf = doc.to_string(profile='chordpro_ref')
doc.write("song.chordpro", profile='inline_slash')
```

---

## Test strategy

Cada profile tem snapshot test:

```python
@pytest.mark.parametrize('profile_name', ['inline_slash', 'chordpro_ref', 'onsong', 'propresenter', 'songbookpro'])
def test_profile_snapshot(song_id: str, profile_name: str):
    truth = load_ground_truth(song_id)
    doc = build_doc_from_truth(truth)
    profile = get_profile(profile_name)
    rendered = profile.render(doc)
    expected = load_snapshot(song_id, profile_name)
    assert rendered == expected
```

Snapshots ficam em `tests/corpus/<song_id>/expected.<profile>.chordpro`. Para v0.1, snapshots focam em:
- `inline_slash`: comparação direta contra chordpro do site iasdermelinda (ground truth real)
- `chordpro_ref`: parseable pelo `chordpro` CLI sem warnings
- `onsong`: smoke test (parsing OK, sem garantias visuais)
- Outros: smoke tests

---

## Por que não há profile `semantic_html` em v0.1

Cogitamos um profile que emitiria HTML semântico (com `data-titan-*` attrs ricos: confidence, stressed, placement_strategy, melisma) para apps web consumirem e estilizarem.

**Decisão: não em v0.1, vai em sibling project separado** `titan-chordpro-render` (TypeScript/JS). Razões:

1. **Fit de linguagem:** HTML/DOM/CSS é domínio JS, não Python. Forçar Python a emitir HTML semântico viola o ecossistema natural de cada lado.
2. **Disciplina de escopo:** lib atual já é grande (5-engine pipeline + fusion + 5 output profiles + validation 147 songs). Adicionar HTML rendering blurs focus.
3. **Reusabilidade independente:** render semântico serve para QUALQUER fonte de ChordPro (não só Titan). Como projeto separado, contribui para a comunidade.
4. **Bridge gratuito:** `ChordProDocument.model_dump_json()` (Pydantic) já é a API perfeita. Renderer JS consome JSON; não precisa parsear `.chordpro` text.
5. **Phase 2 alignment:** o editor app (phase 2) provavelmente é web/TS — `npm install titan-chordpro-render` integra natural.

Detalhes em Seção 1 → "Ecossistema futuro". v0.1 da lib atual não é afetada.

## Pontos para review

- **Profile padrão:** `inline_slash` é a escolha certa? Compatibilidade real do mercado favorece, mas perdemos rigorousness do canonical em troca. Alternativas: `chordpro_ref` como default + `--profile=inline_slash` opt-in.
- **Profile order na escolha** — quando usuário passa `--profile=auto`, qual heurística? (não implementado v0.1, mas a decisão sobre default afeta isso)
- **`{c: titan_provenance_*}` vs `{meta: titan_*}`** — qual usar? Pesquisa apontou `{meta: ...}` como "preserved by every app that round-trips ChordPro". Concordo com `{meta:...}`?
- **Empty/null chord rendering** — `[N]` opt-in ou omit por default? Provavelmente omit (alinhado com `{c: no chord}` policy da Seção 3).
- **`pre-chorus` rendering** — sem canonical directive, vira `{c: Pre-Chorus}` + body. OK?
- **Conditional selectors** (`-Guitar`, `-Piano` no OnSong) — emitir por default em algum profile, ou só via override?
- **Strum patterns `|S` em chordpro_ref** — v0.1 não detecta, mas profile aceita. Documentar como extension point para v0.2+?

Quando terminar o review, me avise no chat.

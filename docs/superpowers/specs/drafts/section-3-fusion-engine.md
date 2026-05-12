# Design — Seção 3: Fusion Engine algorithm

> Parte 3 de 6 do design do Titan ChordPro Lib v0.1.
> Esta seção define o **IP central da lib**: o algoritmo que pega outputs dos 5 engines (separação, transcrição, alinhamento, chord recognition, beat tracking) e produz o `ChordProDocument` final com chord markers no lugar certo da letra.
> Pure Python, zero ML, totalmente testável com mocks.
> Baseado em `docs/research/09-chord-on-syllable.md` + `04-beat-tracking.md`.
> Data: 2026-05-08

---

## Por que fusion engine é o IP da lib

Os engines de ML são **commodity** em 2026 — Whisper, Demucs, BeatThis, Chordino são todos open-source. Qualquer um consegue rodá-los. **O que ninguém open-source faz bem é o que vem depois:**

1. **Quantizar chord events para o beat grid** dentro de tolerância perceptiva
2. **Subdividir palavras em sílabas** com timestamps derivados de fonemas
3. **Identificar a sílaba tônica** e ancorar chord markers nela
4. **Fundir múltiplas evidências** (chord onset + beat + bass + vocal) para reduzir falsos positivos
5. **Detectar melismas** e tratar adequadamente
6. **Inferir seções** (verse/chorus/instrumental) a partir de gaps na lyrics + repetição harmônica
7. **Gerar notação rítmica para instrumentais** (`[C] x///`, half-measures, 6/8 patterns)

Esse é o algoritmo que diferencia Titan de "outro pipeline com Whisper + Demucs".

Pure Python intencionalmente: **testável com fixtures determinísticos**, sem dependência de GPU. Bugs aqui são reproduzíveis e debugáveis.

---

## Inputs do fusion engine

O orquestrador chama os 5 engines + a syllabification engine, depois passa tudo para o fusion engine:

```python
def fuse(
    audio_id: str,
    duration: float,
    words: list[WordEvent],
    phonemes: list[PhonemeEvent] | None,  # may be None
    chords: list[ChordEvent],
    beats: BeatGrid,
    syllables: list[SyllableEvent],
    language: str,
    metadata_hint: Metadata | None = None,  # ID3 tags, etc.
) -> ChordProDocument:
    ...
```

A função é determinística: mesmos inputs → mesmo output. **Crítico para testes.**

---

## Sub-módulos do fusion engine

Sete arquivos em `titan_chordpro/fusion/`:

```
fusion/
├── syllabifier.py    # Maximum Onset Principle (phoneme → syllable boundaries)
├── stress.py         # Stress detection per language (EN: CMU; PT: orthographic)
├── beat_snap.py      # Quantization (mir_eval tolerances ±70ms / ±150ms)
├── onset_fusion.py   # Multi-evidence chord onset (v0.1: chord+beat; v0.2: +bass+vocal)
├── melisma.py        # Detection + chord placement strategy
├── sectioner.py      # Verse/chorus/instrumental boundary inference
└── placer.py         # place_chord_in_lyrics — main algorithm
```

Cada arquivo é testável isoladamente com fixtures.

---

### 3.1 `syllabifier.py` — Maximum Onset Principle

**Responsabilidade:** dado uma `WordEvent` e seus `PhonemeEvent`s, produzir `SyllableEvent`s com timestamps derivados das spans de fonemas.

```python
def syllabify_word(
    word: WordEvent,
    phonemes: list[PhonemeEvent],
    language: str,
) -> list[SyllableEvent]:
    """Decomposes a word into syllables using Maximum Onset Principle.
    
    1. Identify nuclei (vowels) — each becomes a syllable nucleus.
    2. Apply MOP: between two vowels, assign maximum legal consonant cluster
       to the FOLLOWING syllable's onset (subject to language phonotactics).
    3. Remaining consonants attach as coda of preceding syllable.
    
    Timestamp of each syllable: start of first phoneme to end of last phoneme.
    """
    ...
```

**Quando `phonemes` for None** (engine de transcription não suporta):

```python
def syllabify_word_orthographic(
    word: WordEvent,
    language: str,
) -> list[SyllableEvent]:
    """Fallback: syllabify orthographically, distribute timestamps linearly
    within the word duration."""
    ...
```

**Trade-off da fallback:** sílabas têm timestamps proporcionais (não acústicos). Para chord-on-syllable, isso degrada a precisão de placement de ~30ms para ~80-150ms (depende da duração da palavra). Aceitável para v0.1; melhora automática quando engine de transcription com phonemes for plugado.

**Português vs Inglês:**
- Inglês: usa CMU dict (via `g2p_en`) para ARPABET phonemes; aplica MOP com fonotática inglesa.
- Português: usa `gruut` para IPA phonemes; aplica MOP com fonotática do PT-BR (clusters mais restritos).

**Edge cases:**
- Palavras de 1 sílaba: retorna 1 SyllableEvent com text=palavra inteira.
- Palavras OOV (out-of-vocabulary): fallback para regras heurísticas (CV split em vowels).
- Hifens em compostos: cada subparte syllabifica independente (`well-known` → `well` + `known`).

---

### 3.2 `stress.py` — stress detection

**Responsabilidade:** marcar `SyllableEvent.is_stressed = True` na sílaba tônica de cada palavra.

```python
class StressDetector(Protocol):
    def detect_stressed_syllable(
        self,
        word: WordEvent,
        syllables: list[SyllableEvent],
    ) -> int:
        """Returns the index of the stressed syllable within the word."""
        ...
```

**Implementações:**

```python
class EnglishStressDetector:
    """Uses CMU dict via g2p_en. ARPABET stress markers (0/1/2) on each phoneme;
    syllable with marker '1' is primary stress."""
    def detect_stressed_syllable(self, word, syllables) -> int: ...

class PortugueseStressDetector:
    """Uses orthographic rules (~99% accuracy):
    - Word with written accent (´, `, ^, ~): stressed syllable is the marked one.
    - Unmarked, ends in r/l/z/x/i/u/im/um/om: oxítona (last syllable stressed).
    - Else: paroxítona (second-to-last syllable stressed).
    Falls back to gruut IPA stress markers for edge cases."""
    def detect_stressed_syllable(self, word, syllables) -> int: ...
```

**Acoustic prosody fallback (v0.1.5+, optional):** quando lexical stress for ambíguo (e.g., palavras com 2 acentos primários), usar acústica do vocal stem (F0 + RMS + duração) para escolher.

---

### 3.3 `beat_snap.py` — quantization to beat grid

**Responsabilidade:** ajustar timestamps de `ChordEvent` para o beat ou subdivisão mais próxima dentro de tolerância perceptiva.

```python
SNAP_TO_BEAT_TOLERANCE = 0.070   # ±70ms — mir_eval beat tolerance
SNAP_TO_8TH_TOLERANCE  = 0.150   # ±150ms — 8th-note tolerance

def snap_chord_to_grid(
    chord: ChordEvent,
    beat_grid: BeatGrid,
) -> tuple[ChordEvent, Literal['beat', '8th', 'unsnapped']]:
    """Snaps chord.timestamp.start to the nearest beat or 8th-note within tolerance.
    
    Returns the (possibly-modified) ChordEvent + which grid level it snapped to.
    
    Snap policy:
    1. If chord onset is within ±70ms of any beat → snap to that beat.
    2. Else if within ±150ms of an 8th-note position (between beats) → snap to 8th.
    3. Else: leave timestamp unchanged, mark as 'unsnapped' for downstream
       placement strategy decision.
    """
    ...
```

**Why both beat AND 8th tolerances:** chord changes frequently happen on the 8th-note offbeat in pop/rock (anticipation) or 16th in funk. Allowing 8th-note snap captures those without forcing them onto the beat (which would be musically wrong).

**Multi-beat chord events:** `ChordEvent` has a duration (`timestamp.end`). Snap is on `start`; `end` is recomputed as `next_chord.start - epsilon` or end of song.

---

### 3.4 `onset_fusion.py` — multi-evidence chord onset

**Responsabilidade (v0.1):** simples — usar `ChordEvent.timestamp.start` direto, snapped via `beat_snap`.

**Responsabilidade (v0.2+):** fundir múltiplas evidências:

```python
class OnsetEvidence(BaseModel):
    """A single onset signal with confidence."""
    timestamp: float
    confidence: float
    source: Literal['chord_recognizer', 'beat_grid', 'bass_attack', 'vocal_consonant', 'drum_hit']

def fuse_onsets(
    chord: ChordEvent,
    beats: BeatGrid,
    bass_onsets: list[float] | None = None,    # v0.2: librosa.onset on bass stem
    vocal_onsets: list[float] | None = None,   # v0.2: librosa.onset on vocal stem
    drum_onsets: list[float] | None = None,    # v0.2: librosa.onset on drums stem
) -> float:
    """Returns the fused onset timestamp.
    
    v0.1: returns chord.timestamp.start snapped to beat grid (chord+beat only).
    v0.2: weighted average of evidence within ±150ms window, weighted by confidence."""
    ...
```

**v0.1 algorithm:**

```python
def fuse_onsets_v01(chord: ChordEvent, beats: BeatGrid) -> float:
    snapped, level = snap_chord_to_grid(chord, beats)
    return snapped.timestamp.start
```

**v0.2 algorithm (sketch):**

```python
def fuse_onsets_v02(chord, beats, bass_onsets, vocal_onsets, drum_onsets) -> float:
    # 1. Collect evidence within ±150ms of chord.timestamp.start
    evidence = [OnsetEvidence(chord.timestamp.start, chord.confidence, 'chord_recognizer')]
    if bass_onsets:
        evidence.extend(_collect_within(bass_onsets, chord.timestamp.start, 0.15, 'bass_attack', 0.85))
    # ... similar for vocal, drum
    # 2. Add nearest beat as evidence
    nearest_beat = _nearest(beats.beats, chord.timestamp.start)
    evidence.append(OnsetEvidence(nearest_beat, 0.95, 'beat_grid'))
    # 3. Weighted average
    return sum(e.timestamp * e.confidence for e in evidence) / sum(e.confidence for e in evidence)
```

V0.1 ships só `fuse_onsets_v01`. V0.2 adiciona `fuse_onsets_v02` por trás de flag.

---

### 3.5 `melisma.py` — detection + handling

**Responsabilidade:** detectar quando uma sílaba é sustentada por múltiplos beats/notas e ajustar placement strategy.

```python
class Melisma(BaseModel):
    syllable_idx: int      # which syllable is sustained
    span: TimeStamp        # full sustained duration
    # note_count: int      # v0.2 — requires pitch tracking

def detect_melismas(
    syllables: list[SyllableEvent],
    chords: list[ChordEvent],
    beat_grid: BeatGrid,
    vocal_pitch_track: list[float] | None = None,  # f0 from vocal stem
) -> list[Melisma]:
    """Heuristic: a syllable is melismatic if ALL of:
    - duration > 600ms
    - spans more than one beat
    - (if pitch track available) pitch variance > 50 cents
    
    Returns Melisma objects covering the affected syllables."""
    ...
```

> **v0.1 simplification:** `Melisma.note_count` field is **deferred to v0.2** (requires pitch tracking on the vocal stem to estimate notes within the sustained vowel). v0.1 schema only carries `syllable_idx` + `span`.

**Placement strategy during melisma:**

- Chord changes durante a melisma caem **no início** da sílaba sustentada, não no meio dela
- Se múltiplas chord changes ocorrerem durante uma melisma, todas caem no início (visualmente: `[C][G][Am]hello-` em uma palavra)
- v0.2 considera re-segmentar a melisma e atribuir cada chord a uma sub-nota distinta

V0.1: melisma detection é simples (heurística sem pitch track) e a estratégia é "grupo no início".

---

### 3.6 `sectioner.py` — section boundary inference

**Responsabilidade:** dividir o pipeline output em `Section`s (verse, chorus, bridge, instrumental).

V0.1 abordagem **heurística simples**:

```python
def infer_sections(
    words: list[WordEvent],
    chords: list[ChordEvent],
    beat_grid: BeatGrid,
    duration: float,
) -> list[Section]:
    """V0.1 heuristics:
    - Find gaps in lyrics > 4 beats → instrumental boundary.
    - First lyric block → verse 1.
    - Subsequent lyric blocks: assume verse/chorus alternation.
    - Pre-lyric block: intro (instrumental).
    - Post-final-lyric block: outro (instrumental).
    
    No structural analysis (e.g., chord progression repetition matching).
    That's deferred to v0.2 with All-In-One model integration."""
    ...
```

**V0.1 limitations:**
- Não diferencia verse vs chorus de fato — apenas alterna labels
- Bridge não é detectado (vai virar verse N)
- Pre-chorus não detectado

**V0.2 plan:** integrar `mir-aidj/all-in-one` (já planejado para solo detection) que produz function labels (intro, verse, chorus, bridge, outro) joint com beat tracking. Rotacionar para algoritmo melhor sem refactor.

---

### 3.7 `placer.py` — main algorithm `place_chord_in_lyrics`

**Responsabilidade:** dado um `LyricLine` (texto + words/syllables alinhados) e a lista de chords que pertencem àquela linha, produzir os `ChordMarker`s posicionados.

```python
def place_chords_in_line(
    line_text: str,
    words: list[WordEvent],
    syllables: list[SyllableEvent],
    chords_in_line: list[ChordEvent],
    beat_grid: BeatGrid,
    melismas: list[Melisma],
    language: str,
) -> tuple[LyricLine, list[ChordEvent]]:
    """Main placement algorithm. Implements hierarchical fallback:
    1. melisma_start — chord falls inside a detected melisma → placed at
       its start.
    2. stressed_syllable — chord on stressed syllable within ±150ms of
       fused onset.
    3. any_syllable — chord on closest syllable (any) within ±300ms.
    4. before_word — chord BEFORE the closest word (line-position basis).
    5. orphaned — chord has no syllable within 500ms; returned as a
       leftover to be inserted as a sibling InstrumentalLine by the
       sectioner (NOT pinned to this LyricLine).
    
    Returns the LyricLine plus any orphaned chords that didn't fit the line.
    The orchestrator hands orphans to the sectioner for placement as
    micro-instrumental measures between/before/after lyric lines.
    """
    markers = []
    orphans = []  # chords that didn't fit any syllable/word
    for chord in chords_in_line:
        # Step 0: fuse onset evidence (v0.1: chord+beat snap)
        t_anchor = fuse_onsets(chord, beat_grid)
        
        # Step 1 (highest priority): chord falls inside a melisma?
        melisma = _find_melisma_at(melismas, t_anchor)
        if melisma is not None:
            cand = syllables[melisma.syllable_idx]
            markers.append(ChordMarker(
                chord=chord,
                char_position=_char_pos_of_syllable(line_text, cand),
                placement_strategy='melisma_start',
            ))
            continue
        
        # Step 2: stressed syllable within ±150ms?
        cand = _find_stressed_syllable_within(syllables, t_anchor, 0.15)
        if cand is not None:
            markers.append(ChordMarker(
                chord=chord,
                char_position=_char_pos_of_syllable(line_text, cand),
                placement_strategy='stressed_syllable',
            ))
            continue
        
        # Step 3: any syllable within ±300ms?
        cand = _find_any_syllable_within(syllables, t_anchor, 0.30)
        if cand is not None:
            markers.append(ChordMarker(
                chord=chord,
                char_position=_char_pos_of_syllable(line_text, cand),
                placement_strategy='any_syllable',
            ))
            continue
        
        # Step 4: place before closest word (within 500ms)
        cand_word = _closest_word(words, t_anchor)
        if cand_word is not None and abs(cand_word.timestamp.start - t_anchor) < 0.50:
            markers.append(ChordMarker(
                chord=chord,
                char_position=_char_pos_of_word_start(line_text, cand_word),
                placement_strategy='before_word',
            ))
            continue
        
        # Step 5: orphan — no syllable/word in window. Return as leftover
        # to be inserted as a sibling InstrumentalLine by the sectioner.
        # NOT pinned to this LyricLine.
        orphans.append(chord)
    
    line = LyricLine(
        text=line_text,
        chord_markers=markers,
        word_alignments=words,
        syllable_alignments=syllables,
        confidence=_aggregate_confidence(words, chords_in_line),
    )
    return line, orphans
```

**Note:** The `placement_strategy` enum has 5 values:

```python
placement_strategy: Literal[
    'melisma_start',       # chord falls inside a detected melisma
    'stressed_syllable',   # chord on tonic syllable (best case)
    'any_syllable',        # chord on nearest syllable (good case)
    'before_word',         # chord positioned before closest word
    'beat_boundary',       # reserved for InstrumentalLine usage
]
```

(`'beat_boundary'` is no longer used in `LyricLine` placement — orphans now flow to InstrumentalLines via the sectioner. The enum value remains valid for free-standing chords inside `InstrumentalLine.chords` representation, where their position is implicitly grid-based.)

**Why orphan flow instead of end-of-line:** in v0.1's earlier draft, orphans were placed at `char_position=len(line_text)` with `placement_strategy='beat_boundary'`. This produced visually awkward output — chord markers attached to the END of unrelated lyric lines. The refined design separates concerns: `LyricLine` has chords only when they actually align to its syllables; truly free-standing chords become micro-instrumental measures (handled by `sectioner.py`).

---

## Master pipeline

Como o orquestrador (`titan_chordpro/orchestrator.py`) chama tudo:

```python
def transcribe(
    audio: Path,
    language: str | None = None,
    output_profile: str = 'chordpro_ref',
    keep_stems: bool = False,
    cache: bool = False,
    **engine_overrides,
) -> ChordProDocument:
    # 1. Hash audio for provenance
    audio_id = sha256(audio)
    
    # 2. Engine selection (factory.py)
    sep_engine = factory.select_separation(**engine_overrides)
    trans_engine = factory.select_transcription(**engine_overrides)
    align_engine = factory.select_alignment(**engine_overrides)  # may be None
    chord_engine = factory.select_chord(**engine_overrides)
    beat_engine = factory.select_beat(**engine_overrides)
    
    # 3. ML stages (each may use cache)
    stems = sep_engine.separate(audio)
    trans_result = trans_engine.transcribe(stems.vocals, language=language)
    
    # 4. Alignment pass (only if transcription didn't produce phonemes)
    if trans_result.phonemes is None and align_engine is not None:
        align_result = align_engine.align(stems.vocals, trans_result.words, language)
        words, phonemes = align_result.words, align_result.phonemes
    else:
        words, phonemes = trans_result.words, trans_result.phonemes
    
    # 5. Detect/use language for syllabification
    detected_lang = trans_result.detected_language or language or 'en'
    syll_engine = factory.select_syllabification(detected_lang)
    syllables = syll_engine.syllabify(words, phonemes)
    
    # 6. Stress detection
    stress_detector = stress.detector_for(detected_lang)
    for word_idx, word_syllables in _group_by_word(syllables):
        stressed_idx = stress_detector.detect_stressed_syllable(words[word_idx], word_syllables)
        word_syllables[stressed_idx].is_stressed = True
    
    # 7. Harmonic + beat
    harmonic_mix = _mix_for_chord(stems)  # other + bass
    chords = chord_engine.detect(harmonic_mix, bass_stem=stems.bass)
    beats = beat_engine.track(audio)
    
    # 8. Fusion engine — IP central
    document = fusion.fuse(
        audio_id=audio_id,
        duration=stems.duration,
        words=words,
        phonemes=phonemes,
        chords=chords,
        beats=beats,
        syllables=syllables,
        language=detected_lang,
    )
    
    # 9. Provenance assembly
    document.provenance = _build_provenance(audio_id, sep_engine, trans_engine, ...)
    
    return document
```

Note: o orquestrador NUNCA importa `torch`, `whisper`, etc. — só importa as factories e os schemas. ML é encapsulado.

---

## Confidence aggregation

`fusion.fuse` calcula `Provenance.confidence: list[StageConfidence]` agregando:

```python
def aggregate_stage_confidence(events) -> StageConfidence:
    confidences = [e.confidence for e in events]
    return StageConfidence(
        stage=...,
        mean=mean(confidences),
        median=median(confidences),
        p10=percentile(confidences, 10),
    )
```

Stages agregados:
- separation: confidence reportada pelo SourceSeparationEngine (geralmente 1.0; alguns podem ter)
- transcription: agrega per-word confidences
- alignment: agrega per-word/per-phoneme
- chord_recognition: agrega per-chord
- beat_tracking: agrega F-measure ou model output confidence
- syllabification: 1.0 quando phonemes presentes; 0.7 quando orthographic fallback
- fusion: % de chords que caíram em `placement_strategy='stressed_syllable'` (highest), ponderado

`p10` flaga regiões problemáticas: "10% dos eventos têm confidence ≤ X" — útil para warnings em apps phase-2.

---

## Test strategy: golden fixtures

Pasta `tests/corpus/<song_id>/`:

```
tests/corpus/wonderwall/
├── audio.mp3                    # source (could be 30-second clip for CI)
├── ground_truth.json            # manually annotated:
│                                #   - words with timestamps
│                                #   - phonemes (optional)
│                                #   - syllables with stress
│                                #   - chords with timestamps and bass
│                                #   - beats and downbeats
│                                #   - sections
├── expected.chordpro            # expected output for chordpro_ref profile
├── expected.onsong.chordpro     # expected for onsong profile
└── notes.md                     # any subtleties (e.g., "verse 2 has melisma")
```

Test driver:

```python
@pytest.mark.parametrize('song_id', SONG_IDS)
def test_fusion_engine_golden(song_id: str):
    truth = load_ground_truth(song_id)
    
    # Use mock engines that return ground truth
    mocks = MockEngineSet.from_truth(truth)
    
    # Run fusion engine only (skip ML)
    doc = fusion.fuse(
        audio_id='test',
        duration=truth.duration,
        words=truth.words,
        phonemes=truth.phonemes,
        chords=truth.chords,
        beats=truth.beats,
        syllables=truth.syllables,
        language=truth.language,
    )
    
    # Compare rendered output to expected
    assert doc.to_string('chordpro_ref') == load_expected(song_id, 'chordpro_ref')
```

**Why this matters:** the fusion engine's output is **diffable**. Any change to the algorithm shows up as a diff in `expected.chordpro`. CI catches regressions immediately.

**V0.1 corpus PT-BR (6 músicas, definidas pelo dono do projeto):**

Todas vêm do site [iasdermelinda.com.br](https://iasdermelinda.com.br/musicas/listagem-banda), que armazena chord charts em **formato ChordPro nativo** (`{title}`, `{subtitle}`, `{key}`, `{tempo}`, `{time}`, `[chord]` brackets, `{c:...}` para dinâmicas). Significa que ground truth vem grátis — não precisa anotação manual.

| # | Música | Álbum | Edge case primário | URL |
|---|---|---|---|---|
| 1 | Deus é Refúgio | Adoradores 1 | **Slash chords:** F/A, G/B, C/E | [link](https://iasdermelinda.com.br/musicas/adoradores-1/deus-e-refugio/4xNKALq8) |
| 2 | Entrego minha vida | Adoradores 1 | (TBD — confirmar quando implementação começar) | [link](https://iasdermelinda.com.br/musicas/adoradores-1/entrego-minha-vida/R9Vv26VQ) |
| 3 | Grande Deus | Adoradores 2 | **Slash chords múltiplos** (A/E, E/G#, D/A); **time signature ambíguo** (chart 4/4, percepção 6/8 — testa BeatThis) | [link](https://iasdermelinda.com.br/musicas/adoradores-2/grande-deus/vYPEpeq3) |
| 4 | Fé e ação | Adoradores 3 | (TBD) | [link](https://iasdermelinda.com.br/musicas/adoradores-3/fe-e-acao/MkNzMgP7) |
| 5 | Nas mãos do Oleiro | Adoradores 3 | (TBD) | [link](https://iasdermelinda.com.br/musicas/adoradores-3/naos-maos-do-oleiro/v9N4Rbqx) |
| 6 | Não mais eu | Celebra São Paulo | (TBD) | [link](https://iasdermelinda.com.br/musicas/celebra-sao-paulo/nao-mais-eu/MLV5oDPB) |

**Política de ground truth PT-BR:**
- Site é referência inicial — algoritmo da Titan deve produzir output equivalente
- Quando algoritmo diverge do site, **owner valida pessoalmente** qual está correto (alguns charts do site não são perfeitos)
- Edge cases TBD são documentados quando começar a fase de teste (semana 1-3 do plano de implementação)

**V0.1 corpus EN:**

EN tem poucas músicas no escopo do owner — validação pessoal caso a caso, sem necessidade de ground truth externo. Estratégia:
- 1-3 EN de escolha do owner (decisão postergada para quando o EN syllabifier for plugado, semana 6 do plano)
- Owner valida output manualmente comparando com sua compreensão da música
- Não há requisito de ground truth automatizado para EN em v0.1

**CI strategy:**
- Snippets PT-BR (~30s) no repo para CI (audio + .chordpro de referência baixados do site)
- Full songs em ambiente local para nightly tests
- EN tests em v0.1 são unit tests sintéticos (mock data) + smoke tests manuais

**Validação estatística estendida (Tier 2+3, em v0.1):**

Owner do projeto também é owner do site `iasdermelinda.com.br` — pode exportar o catálogo completo (147+ músicas) direto do banco como JSON. Sem necessidade de scraping. Tres tiers:

| Tier | Quando | Quantas | Duração | Para quê |
|---|---|---|---|---|
| **1 — CI** | Cada commit | 6 (cadastradas acima) | ~3 min | Smoke test rápido |
| **2 — Nightly** | 1× ao dia (cron) | ~30 (sample do catálogo) | ~30-60 min | Métricas WCSR/F-measure; relatório de divergências |
| **3 — Pre-release** | Antes de cada release | 147+ (full catálogo) | ~5-7h | Validação completa; review manual top divergências |

**Estratégia de matching (decidida):** match against **canonical chordpro only** (cada música tem versão padrão). Versões alternativas (transposições, dificuldades) ignoradas para v0.1.

Detalhamento do harness (export script, audio downloader, validation runner, divergence ranker) → **Seção 5 (Error handling + Testing strategy)**.

---

## Edge cases & open decisions

1. **Empty lyrics (instrumental song):** all chords go into `InstrumentalLine`s. No `LyricLine`. Section structure: just `[intro, instrumental, outro]` with measure counts.

2. **No chord detected for a line:** `LyricLine.chord_markers = []`. Renderer outputs the line as plain text, **no annotation**. Ausência fala por si — `{c: ...}` comments são reservados para sinal real (ver abaixo).

3. **Very fast lyrics (rap):** syllables may overlap; multiple syllables per chord change. Algorithm picks the syllable with `is_stressed=True` first; if none, the closest. Should work but accuracy degrades.

4. **Out-of-tolerance chord (Step 4 fallback):** beat-boundary fallback puts the chord at end-of-line. Visually weird. **Decisão pendente:** flag this in provenance and add `{c: chord changed mid-rest}` comment? Or split the line?

5. **Sustain across line break:** chord starts mid-line, lasts beyond it. `ChordMarker` only fires once. Next line implicitly inherits — Standard ChordPro convention.

6. **Section boundary detection failure:** if no clear gap, everything ends up in "Verse 1". Not ideal but degraded gracefully.

7. **`{c: ...}` policy — reserved for high-signal markers only.** Comments must carry musical importance, not noise. v0.1 emits `{c: ...}` ONLY for things that are actually detected:

   | OK em v0.1 (algo detectável) | OK em v0.2+ | NÃO emitir |
   |---|---|---|
   | `{c: Solo}`, `{c: Bridge}` (instrumental sections) | `{c: f}`, `{c: p}` (dynamics via RMS) | `{c: no chord}` |
   | `{c: Modulação para G}` (key change detected) | `{c: cresc.}` (RMS gradient) | `{c: end of phrase}` |
   | `{c: Tempo muda para 6/8}` (meter change) | `{c: Hold}` (sustain detected) | `{c: pause}` |

   Default: comentário ausente. Linhas de letra sem chord markers são texto puro.

---

## Pontos para review

Os itens que estavam em aberto foram resolvidos no auto-review:

- ✅ `placement_strategy` enum — adicionado `'melisma_start'` (Step 1, prioridade máxima)
- ⏸ Acoustic prosody fallback em `stress.py` — postergado para v0.1.5+ (lexical detection já cobre 99% PT, ~85% EN; ROI baixo agora)
- ✅ `sectioner.py` v0.1 heurística simples — mantido com limitações documentadas; All-In-One model em v0.2
- ✅ Cache opt-in default-off — mantido (segurança contra surprise disk writes)
- ✅ Test corpus — 8 músicas propostas (4 EN + 4 PT-BR); pode ajustar
- ✅ `{c: ...}` policy — reservado para sinal real; sem `{c: no chord}` em LyricLines vazias
- ✅ `fuse_onsets_v01` em v0.1 — confirmado (multi-evidence é v0.2)
- ✅ Out-of-tolerance fallback — agora orphan flow para sibling InstrumentalLine via sectioner (não mais end-of-line)
- ✅ `Melisma.note_count` — removido de v0.1 (deferido para v0.2 com pitch tracking)

Itens RESOLVIDOS no fluxo de review:

- ✅ **Test corpus** — 6 PT-BR cadastradas (do site iasdermelinda.com.br, formato ChordPro nativo); EN postergado para semana 6 da implementação (poucas músicas, validação pessoal do owner)

Quando terminar o review, me avise no chat.

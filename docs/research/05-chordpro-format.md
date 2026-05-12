# ChordPro Format: Specification and Real-World Support (2026)

> Research conducted for Titan ChordPro Lib. Goal: ensure generated `.chordpro` files conform to the canonical spec AND are correctly rendered by major apps.
> Last updated: 2026-05-08

## Authoritative Sources

The canonical specification lives at **chordpro.org**, maintained by Johan Vromans and the ChordPro Team. The reference implementation is hosted on GitHub at `ChordPro/chordpro` (Artistic License 2.0).

| Source | URL | Notes |
|--------|-----|-------|
| Official spec | https://www.chordpro.org/chordpro/ | ChordPro 6 — current canonical |
| Reference impl | https://github.com/ChordPro/chordpro | Latest release **6.101.0** (2026-04-30) |
| Cheat sheet | https://www.chordpro.org/chordpro/chordpro-cheat_sheet/ | ChordPro 6.07 cheat sheet |
| Directives index | https://www.chordpro.org/chordpro/chordpro-directives/ | Full directive list |
| Grid env | https://www.chordpro.org/chordpro/directives-env_grid/ | `start_of_grid`/`sog` |
| Tab env | https://www.chordpro.org/chordpro/directives-env_tab/ | `start_of_tab`/`sot` |
| Time directive | https://www.chordpro.org/chordpro/directives-time/ | `time` directive — confirms mid-song changes |
| User forum | https://groups.io/g/ChordPro | Community Q&A |

### Historical baseline

ChordPro originated in **June 1991** (some sources say 1992) as the `chord` program by **Martin Leclerc and Mario Dorion**. The project went dormant until **2007** when Johan Vromans and Adam Monsen revived it as **Chordii** (format v4). In **2015** Vromans rewrote it as `ChordPro` with native PDF, Unicode, and the modern v6 format. The reference implementation hit **6.101.0** on 2026-04-30; 6.080 (2025-08-18) added strum patterns to grids; 6.090.1 (2026-01-03) was an emergency PDF fix; 6.100.0 (2026-04-21) reworked keys/transpositions.

The current spec is **ChordPro 6**.

## Core Syntax

A ChordPro file is plain text with three syntactic constructs:

1. **Inline chord brackets** — `[Cmaj7]` placed before the syllable they accompany.
2. **Directives** — single-line braced commands, e.g. `{title: My Song}`.
3. **Comments** — lines beginning with `#` are ignored by the processor.

ChordPro 6 also recognizes **annotations** with `[*Coda]` (asterisk prefix → text, not a chord) and supports a Pango-like markup for inline styling.

### Recommended file extensions
`.cho` (preferred), `.chordpro`, `.chopro`, `.crd`, `.pro`, `.chord`. OnSong additionally accepts `.cpm`.

### Inline chord brackets

Allowed inside `[...]`:

- Root notes: `C`, `F#`, `Bb`, `Db`, etc.
- Qualifiers: `m`, `maj`, `aug`, `dim`, `sus`, `add`
- Extensions: `7`, `maj7`, `9`, `11`, `13`, `sus4`, `sus2`, `add9`, `alt`
- Slash chords: `C/G`, `D/F#`
- Annotations (non-chord): `[*Rit.]`, `[*N.C.]`

ChordPro 6 has two parsing modes:
- **Strict** (default after 6.100.0 actually flips strict to false but warns when `{key}` is missing) — only built-in extensions accepted.
- **Relaxed** — accepts arbitrary extensions like `Cmaj7#11b13`.

For maximum compatibility, output should stay within the Strict-mode chord grammar.

### Directives — full table

| Group | Canonical | Short | Purpose |
|-------|-----------|-------|---------|
| Preamble | `new_song` | `ns` | Marks new song in multi-song file |
| Meta | `title` | `t` | Song title |
| Meta | `subtitle` | `st` | Subtitle |
| Meta | `artist` | — | Performing artist (repeatable) |
| Meta | `composer` | — | Composer |
| Meta | `lyricist` | — | Lyricist |
| Meta | `album` | — | Album |
| Meta | `year` | — | Release year |
| Meta | `copyright` | — | Copyright text |
| Meta | `key` | — | Musical key |
| Meta | `time` | — | Time signature |
| Meta | `tempo` | — | BPM |
| Meta | `duration` | — | Song length |
| Meta | `capo` | — | Capo position |
| Meta | `tag` | — | Custom tag (added 6.080) |
| Meta | `meta` | — | Generic `{meta: name value}` |
| Format | `comment` | `c` | Inline comment |
| Format | `comment_italic` | `ci` | Italic comment |
| Format | `comment_box` | `cb` | Boxed comment |
| Format | `highlight` | — | Highlighted text |
| Format | `image` | — | Embedded image (`src=…`) |
| Section | `start_of_chorus` / `end_of_chorus` | `soc` / `eoc` | Chorus block |
| Section | `chorus` | — | Repeat the previous chorus |
| Section | `start_of_verse` / `end_of_verse` | `sov` / `eov` | Verse block |
| Section | `start_of_bridge` / `end_of_bridge` | `sob` / `eob` | Bridge block |
| Env | `start_of_tab` / `end_of_tab` | `sot` / `eot` | Tablature (preformatted) |
| Env | `start_of_grid` / `end_of_grid` | `sog` / `eog` | Chord grid (Jazz Grilles) |
| Env | `start_of_abc` / `end_of_abc` | — | ABC notation block |
| Env | `start_of_ly` / `end_of_ly` | — | Lilypond block |
| Env | `start_of_svg` / `end_of_svg` | — | SVG block |
| Env | `start_of_textblock` / `end_of_textblock` | — | Plain text block |
| Chord def | `define` | — | `{define: Cmaj7 base-fret 0 frets 0 3 2 0 0 0}` |
| Transpose | `transpose` | — | Semitone offset |
| Output | `new_page` | `np` | Page break |
| Output | `new_physical_page` | `npp` | Physical page break |
| Output | `column_break` | `colb` / `cb` | Column break |
| Output | `columns` | `col` | Multi-column layout |
| Custom | `x_*` | — | App-specific (must be ignored by processors that don't support) |

**Conditional selectors**: any directive can take a postfix selector — `{define-Guitar: ...}`, `{c-Lead: ...}`, `{soh-Female: ...}` — for instrument or persona-conditional rendering. Not universally supported.

### Verse/Chorus/Bridge structure

```chordpro
{start_of_verse}
[C]Twinkle [F]twinkle [C]little [G]star
{end_of_verse}

{start_of_chorus}
[C]How I [F]wonder [C]what you [G]are
{end_of_chorus}
```

The shorthand `{chorus}` (no body) repeats the most recent chorus — useful but support varies.

### Tablature (`{sot}`/`{eot}`)

Content is treated as **preformatted text**: "lines will not be folded or changed. Markup is left as is, and directives are considered literal text except for `{end_of_tab}` and `{eot}`." The reference implementation renders it in a fixed-width font; an optional label is supported via `{start_of_tab: Solo}`.

```chordpro
{start_of_tab: Solo}
e|---0---3---5---|
B|-1---1---1---1-|
G|-0---0---0---0-|
D|-2---2---2---2-|
A|-3-------------|
E|---------------|
{end_of_tab}
```

The format is **not structured** — no semantic awareness of strings, frets, or beats. Apps that "render tabs" almost universally just display monospaced text.

### Chord grid (`{sog}`/`{eog}`) — KEY FINDING for rhythmic notation

Grids are the spec's official mechanism for chord-only / rhythmic blocks. Inspired by Jazz Grilles ("rectangular chord arrangements showing song structure without lyrics").

**Shape**: `{start_of_grid shape="cells"}` or `{start_of_grid shape="measures x beats"}` with optional left/right margins. Default: `1+4x4+1` (one margin column, 4 measures of 4 beats, one margin column).

**Cell tokens**:
| Token | Meaning |
|-------|---------|
| Chord name (no brackets): `C`, `Am`, `F#m7` | Play this chord here |
| `.` | Empty cell (placeholder) |
| `/` | Play the previous chord here (rhythmic continuation) |
| `~` | Combine multiple chords in one cell: `D~C` |
| `%` | Repeat previous measure |
| `%%` | Repeat last two measures |
| `-` or `---` | Pause/break |
| `(C)` | Parenthesized (de-emphasized) chord |

**Bar lines**: `|` (single), `||` (double), `|.` (end), `|:` (start repeat), `:|` (stop repeat), `:|:` (combined), `|1` `|2` (volta).

**Strum lines** (added in ChordPro 6.080, August 2025): place `S` (or lowercase `s` to suppress bar/cell lines) immediately after the first bar symbol. Tokens: `dn`/`d`, `up`/`u`, `d+`/`u+` (accented), `da`/`ua` (arpeggio), `dx`/`ux`/`x` (muted).

**Example** (House of the Rising Sun progression):

```chordpro
{start_of_grid shape="1+4x4+1"}
|| Am . . . | C  . . . | D  . . . | F  . . . |
|  Am . . . | C  . . . | E  . . . | E  . . . |
|  Am . . . | D  . . . | F  . . . | Am . . . ||
{end_of_grid}
```

**Example** with strums:

```chordpro
{start_of_grid}
|  C  .  .  .  | F  .  .  .  |
|S dn  ~up  dn  ~up | dn  ~up  dn  ~up |
{end_of_grid}
```

### Tempo, Key, Time signature

```chordpro
{key: G}
{time: 4/4}
{tempo: 120}
```

`{meta: time 6/8}` is an alias for `{time: 6/8}`.

## Rhythmic Notation: How to Express `[C] x///`

**Critical finding**: `[C] x///` is **not standard ChordPro syntax**. It's a community/app convention (notably used in some PCO/OnSong workflows where lyrics text contains `///` to suggest beats). The canonical ChordPro mechanism for rhythmic chord-only sections is the **chord grid** (`{sog}`/`{eog}`).

### Recommended canonical translations

| Intent | Canonical ChordPro |
|--------|-------------------|
| Full 4/4 measure of C (intro) | `\| C / / / \|` inside `{sog}…{eog}` |
| Half measure C, half G (in 4/4) | `\| C . G . \|` (two beats each) |
| Full 4/4 of C followed by full 4/4 of G | `\| C / / / \| G / / / \|` |
| 6/8 grouping (e.g., C for 3 + G for 3) | `{time: 6/8}` then `\| C . . G . . \|` (cells = 6) using `shape="1+1x6+1"` |
| Repeat previous measure | `\| % \|` |
| Pause / N.C. | `\| - - - - \|` or use the `[*N.C.]` annotation in lyrics mode |

### Inline alternative inside lyric lines

If staying inline (no grid block), use repeated chord brackets with whitespace, NOT slash characters:

```chordpro
[C]    [C]    [C]    [C]    [G]    [G]    [G]    [G]
```

This is ugly but maximally compatible: every chord-aware app understands `[chord]`.

A second inline option some apps tolerate: an annotation that *renders as text*:

```chordpro
[C][*1234] [G][*1234]
```

But annotation rendering is uneven across apps.

### Verdict for Titan ChordPro Lib

Use **`{sog}`/`{eog}` blocks** for purely rhythmic / instrumental measures. Fall back to repeated `[C]` brackets on a separate "instrumental" line when targeting apps that don't render grids (OnSong, SongbookPro). Emit both representations behind a `--profile=onsong` / `--profile=chordpro-ref` switch.

## App Compatibility Matrix

Renders/supports = `Y`, ignores silently = `i`, breaks rendering = `N`, unknown = `?`.

| Directive | ChordPro ref 6.x | OnSong | ProPresenter 7 | SongbookPro | Linkesoft Songbook | LivePrompter |
|-----------|:---:|:---:|:---:|:---:|:---:|:---:|
| `[chord]` | Y | Y | Y | Y | Y | Y |
| `{title}` / `{t}` | Y | Y | Y | Y (import) | Y | Y |
| `{subtitle}` / `{st}` | Y | Y | Y | Y (import) | Y | Y |
| `{artist}` | Y | Y | Y | Y (import) | Y (via subtitle) | Y |
| `{key}` | Y | Y | Y | Y (import) | Y | Y |
| `{tempo}` | Y | Y | i | Y (import) | Y (`metronome`) | Y |
| `{time: 4/4}` | Y | Y | i | Y (import) | Y | Y |
| `{time: 6/8}` mid-song | Y | ? | i | i | ? | ? |
| `{capo}` | Y | Y | Y | Y (import) | Y (auto-transposes) | Y |
| `{comment}` / `{c}` | Y | Y (multiple variants) | Y | Y | Y | Y |
| `{soc}`/`{eoc}` | Y | Y | Y | Y | Y | Y |
| `{sov}`/`{eov}` | Y | Y | Y | Y | Y | Y |
| `{sob}`/`{eob}` | Y | Y | Y | i | Y | Y |
| `{sop}`/`{eop}` (part) | i | Y | ? | i | ? | ? |
| `{sot}`/`{eot}` (tab) | Y (PDF) | Y | i (text only) | Y | Y (fixed-width) | Y |
| `{sog}`/`{eog}` (grid) | **Y** | **N** | N | N | **Y** | **Y** |
| Strum patterns (S in grid) | Y (≥6.080) | N | N | N | ? | ? |
| `{define}` | Y | Y | i | i | Y | Y |
| `{transpose}` | Y | Y | Y (semantic) | Y | Y | Y |
| `{new_page}` / `{np}` | Y | Y | i | Y | Y | Y |
| `{column_break}` | Y | i | i | i | i | i |
| `{ccli}` | i | Y | Y | Y | i | i |
| `{x_*}` extensions | i (silent) | Y (some) | i | Y (`x_sbp_tags`) | Y | i |
| Conditional selectors `-Guitar` etc. | Y | i | i | i | Y | i |

**Key takeaways:**

- **Grid (`sog`/`eog`) is supported by the reference implementation, Linkesoft Songbook, and LivePrompter** — but **NOT by OnSong, ProPresenter 7, or SongbookPro** (the three most popular live-performance apps in worship/cover-band markets). This is the single largest portability gap.
- **Tab (`sot`/`eot`) is universally supported** — but as preformatted monospaced text, not as semantic tablature.
- ProPresenter and SongbookPro treat most metadata as import-only; once imported, they own the model.

## Time Signature Handling

The `{time: …}` directive accepts standard musical time signatures (`4/4`, `3/4`, `6/8`, `12/8`, `5/4`, etc.). The spec explicitly allows **multiple `{time}` directives in a single song** — each takes effect from its position onward. This handles meter changes mid-song:

```chordpro
{time: 4/4}
{start_of_verse}
[C]Verse in [G]four [Am]four [F]time
{end_of_verse}

{time: 6/8}
{start_of_chorus}
[C]Now in six [F]eight [G]groove [C]swing
{end_of_chorus}
```

Reality check: only the reference implementation (in PDF output via grids) and Linkesoft Songbook honor mid-song time changes meaningfully. OnSong/ProPresenter/SongbookPro store the value as metadata only — useful for the metronome / autoscroll, not for any visual cue.

For `6/8` grids, set `shape="1+Mx6+1"` (M measures, 6 cells per measure) so cells map to eighth notes. For compound feel emphasizing dotted-quarter pulse, you can group as `1+Mx2+1` and use `~` to combine the three eighths into each compound beat.

## Recommendations for Titan ChordPro Lib's Output

### Header block (every song)

```chordpro
{title: <song title>}
{artist: <primary artist>}
{key: <key>}
{time: <time signature>}
{tempo: <bpm>}
{capo: 0}
{meta: titan_version 0.1}
{meta: titan_confidence_chord 0.92}
{meta: titan_confidence_lyrics 0.88}
```

Use `{meta: ...}` for Titan-specific provenance (model versions, confidence scores). It's the cleanest spec-compliant escape hatch — and it's preserved by every app that round-trips ChordPro.

### Sections

- Wrap each detected verse/chorus/bridge in `{sov}`/`{soc}`/`{sob}` blocks. These are universally supported.
- Use `{comment: Intro}`, `{comment: Solo}`, `{comment: Outro}` for unlabeled or instrumental sections — also universal.

### Rhythmic / instrumental measures

**Default emit**: a `{sog}`/`{eog}` block with explicit measures.

```chordpro
{comment: Intro}
{start_of_grid shape="1+4x4+1"}
|| C / / / | G / / / | Am / / / | F / / / ||
{end_of_grid}
```

**Compatibility fallback** (CLI flag `--rhythmic-fallback=inline`): emit repeated `[chord]` markers separated by spaces on a comment-tagged "instrumental" line, so OnSong/ProPresenter/SongbookPro still show *something* sensible:

```chordpro
{comment: Intro}
[C]   [C]   [C]   [C]   [G]   [G]   [G]   [G]
```

Best practice: emit **both** — the inline line first, the grid block second, with the grid wrapped in a comment so non-grid apps still display useful information. The reference implementation will render the grid; lesser apps will render the inline line and silently ignore the grid block.

### Tablature for solos

```chordpro
{start_of_tab: Solo}
e|--7--5--3--5--7--|
B|-----------------|
G|-----------------|
D|-----------------|
A|-----------------|
E|-----------------|
{end_of_tab}
```

Always 6 lines, top-to-bottom = `e B G D A E` (high E first), with explicit `|` measure dividers. Use 2-digit fret numbers padded with `-` to keep columns aligned. App rendering is monospaced — do NOT rely on visual fidelity beyond character alignment.

### Time signature

- Always emit `{time: …}` near the top, even for the default 4/4 (helps metronome features).
- For songs with a single meter change, emit a second `{time: …}` directive at the change point. Be aware this is a signal to the reference impl and Linkesoft only; for other apps it's metadata-only.
- For complex/changing meter, also embed a `{comment: 6/8 feel}` so users of less-capable apps see the change.

### Key

`{key: G}` for major, `{key: Em}` for minor (relative-minor convention; ChordPro 6.100 has explicit minor handling).

### Default output profile

| Profile | When | Behavior |
|---------|------|----------|
| `chordpro-ref` (default) | Maximum fidelity | Use grids for rhythmic blocks; emit `{time}` at every change |
| `onsong` | Live-performance apps | No grids; inline `[chord]` patterns; tab blocks fine |
| `propresenter` | ProPresenter 7 export | Sections + inline chords only; strip grids; flatten meta |
| `songbookpro` | SongbookPro | As `onsong` but emit `{x_sbp_tags}` for genre/feel |

## Examples

A complete short example combining everything Titan generates:

```chordpro
# Generated by Titan ChordPro Lib v0.1
{title: Wonderful Tonight}
{artist: Eric Clapton}
{key: G}
{time: 4/4}
{tempo: 88}
{capo: 0}
{meta: titan_confidence_chord 0.94}
{meta: titan_confidence_lyrics 0.91}
{meta: titan_confidence_beat 0.97}

{comment: Intro}
{start_of_grid shape="1+4x4+1"}
|| G / / / | D/F# / / / | C / / / | D / / / ||
{end_of_grid}

{start_of_verse}
[G]It's late in the [D/F#]evening, [C]she's wondering what [D]clothes to wear
[G]She puts on her [D/F#]makeup, and [C]brushes her [D]long blonde [G]hair
{end_of_verse}

{start_of_chorus}
And then she [C]asks me, "Do I [D]look alright?"
And I [G]say, "Yes, you look [D/F#]wonderful to[Em]night."
{end_of_chorus}

{comment: Solo}
{start_of_tab: Solo}
e|----3---5---3---2-----|----3---5---3---2-----|
B|--3---3---3---3---3---|--3---3---3---3---3---|
G|----------------------|----------------------|
D|----------------------|----------------------|
A|----------------------|----------------------|
E|-3--------------------|-3--------------------|
{end_of_tab}

{comment: Outro}
{start_of_grid shape="1+2x4+1"}
| G / / / | C / / / |
| G / / / | D / / / |
{end_of_grid}
```

## Open Questions

1. **Do we ship a pluggable "compatibility profile" system** (chordpro-ref / onsong / propresenter / songbookpro) at v0.1, or only target the reference impl and document the gap?
2. **Strum patterns (6.080+)** — is automatic strum-pattern detection from audio in scope, or do we leave strum lines empty? If we emit them, they're only readable by the reference impl.
3. **Confidence score embedding** — do we use `{meta: …}` (preserved but invisible) or `{x_titan_confidence: …}` (some apps may filter or display)?
4. **Annotation vs grid for very short rhythmic hits** — for a single chord stab, is `[C][*hit]` cleaner than spinning up a `{sog}` block with one cell?
5. **Mid-song time signature changes** — emit the directive even though most apps will ignore it visually, or skip it to avoid confusion?
6. **Whether to emit `{define: ...}` for non-trivial chord voicings** — Titan can detect voicing from audio; should it emit chord diagrams or just chord symbols?
7. **6/8 grid shape convention** — is `1+Mx6+1` (cells = eighth notes) better than `1+Mx2+1` (cells = compound beats with `~` joins)?
8. **Annotations `[*…]`** for non-chord events (e.g., `[*N.C.]`, `[*break]`, `[*ritard.]`) — adopted across apps?

## Sources

- [ChordPro Directives Reference](https://www.chordpro.org/chordpro/chordpro-directives/)
- [ChordPro Introduction](https://www.chordpro.org/chordpro/chordpro-introduction/)
- [ChordPro Cheat Sheet](https://www.chordpro.org/chordpro/chordpro-cheat_sheet/)
- [Directives: start_of_grid](https://www.chordpro.org/chordpro/directives-env_grid/)
- [Directives: start_of_tab](https://www.chordpro.org/chordpro/directives-env_tab/)
- [Directives: time](https://www.chordpro.org/chordpro/directives-time/)
- [ChordPro Implementation: Chords](https://www.chordpro.org/chordpro/chordpro-chords/)
- [ChordPro reference implementation on GitHub](https://github.com/ChordPro/chordpro) — version 6.101.0 (2026-04-30)
- [ChordPro Changes file](https://github.com/ChordPro/chordpro/blob/master/Changes)
- [ChordPro on Wikipedia](https://en.wikipedia.org/wiki/ChordPro)
- [OnSong ChordPro support](https://onsongapp.com/docs/features/formats/chordpro/)
- [SongbookPro ChordPro syntax](https://songbook-pro.com/docs/manual/chordpro/)
- [Linkesoft Songbook ChordPro format](https://linkesoft.com/songbook/chordproformat.html)
- [LivePrompter chord grids](https://www.liveprompter.com/help/help-mobile/advanced-help-v2/chord-grids/)
- [ChordPro feature request: strumming patterns (issue #85)](https://github.com/ChordPro/chordpro/issues/85)
- [ProPresenter 7 chord chart docs](https://learn.renewedvision.com/propresenter6/the-features-of-propresenter/chord-charts)

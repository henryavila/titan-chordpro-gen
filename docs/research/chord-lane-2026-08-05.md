# Chord lane research notes — 2026-08-05

Branch: `plan/titan-v01`. Offline artifacts: `/tmp/titan-chord-explore/`.

## Sample (n=3 soft majmin)

| hyp | mean match | notes |
|-----|------------|-------|
| H0 baseline | 0.765 | Chordino + reseg v5 + bass |
| H1 multipass | 0.777 | Lvo +3.6pp |
| H1b multipass+force≥12s | **0.780** | score 0.790; LL5 flat **0.505** |
| H2 bass gates | 0.763 | slash hygiene; LL5 snapshot 0.454 |
| H3 stems | ≤ H0 control | **keep other+bass** |
| H4 params | ≤ +0.4pp | **keep defaults** |
| H6 BTC (sibling) | 0.758 | +song1/2, **−11pp song3** |

## Promote

- **partial-promote** product path: H1b + H2 + P3 (`de8e218`, `05efb5d`, `4264ddf`).
- Full promote gate (+2pp mean, no song −10pp): **not met**.
- Default engine Chordino; default mix other+bass; **no WCSR claim**.
- `btc.py` **absent** on this branch (impl/chord-explore only).

## Residual

Song3 ~0.50 Chordino ceiling vs this GT; 31s true G pad on song2; expand sample before detector flip.

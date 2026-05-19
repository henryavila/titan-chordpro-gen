# Validation reports

Directory contract for `benchmarks/reports/`:

- One subdirectory per nightly run, named `YYYY-MM-DD/`.
- Each subdirectory contains at minimum `top-divergences.md` (written by `benchmarks.divergence_ranker.write_report`).
- Everything in this directory is **gitignored except this README and `.gitignore`** — reports depend on audio downloads and corpus state, neither of which is portable.

## Severity thresholds (spec §1582)

| Severity   | WCSR-majmin |
|------------|-------------|
| CRITICAL   | < 50%       |
| HIGH       | 50–70%      |
| MEDIUM     | 70–85%      |
| LOW        | 85–95%      |
| NEGLIGIBLE | ≥ 95%       |

Henry's review focuses on CRITICAL + HIGH tiers and a sample of LOW. LOW items often surface ground-truth errors in the corpus, not Titan errors.

## Phase C target (spec §1683)

- Tier 2 WCSR-majmin ≥ 70%
- Top-10 divergences: ≤ 3 are "Titan errado"

A single nightly hitting both bars closes Phase C's measurement gate.

# Review Lessons

## Gate verifier evidence must replay the exact command

- Date: 2026-06-24
- Context: `review-code` on `plan/titan-core-decoupling`.
- Lesson: when an exit gate passes only through an environment wrapper or extras,
  encode the verifier as a shell command matching the evidence exactly. Do not
  leave a narrower test verifier such as `pytest tests` if the evidence came from
  `uv run --extra dev --extra validation pytest tests`.
- Reason: status tooling and reviewers replay structured verifier fields, not the
  prose in `evidence.outputSummary`. A mismatch can mark a gate met while its
  recorded verifier fails in the current environment.
- Follow-up pattern: after editing canonical project state, refresh and validate
  derived aiDeck state so `gates.json` and `phaseGates.json` expose the same gate
  label as the source files.

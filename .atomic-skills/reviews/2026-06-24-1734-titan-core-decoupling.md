---
date: 2026-06-24T17:34:47-03:00
topic: titan-core-decoupling
artifact: .atomic-skills/projects/titan-chordpro-lib/titan-core-decoupling/plan.md
skill: review-plan
reviewer: gpt-5-codex
codex_version: codex-cli 0.142.0
final_verdict: needs_changes
counts_final: {blocker: 0, critical: 0, major: 4, minor: 0, nit: 0}
counts_blind: {blocker: 0, critical: 0, major: 4, minor: 0, nit: 0}
framing_delta: {dropped: 0, maintained: 4, emerged: 0}
schema_version: "1.0"
---

# Cross-Model Review — titan-core-decoupling

## Pass 1 (blind)

---
verdict: needs_changes
counts: {blocker: 0, critical: 0, major: 4, minor: 0, nit: 0}
reviewer: gpt-5-codex
pass: blind
schema_version: "1.0"
---

## Summary
The plan is implementable at a high level, but its gates are not strong enough to prove the release claims it makes. The main risks are verifier gaps: documentation can remain wrong while the doc gate passes, the version bump can be skipped while remaining internally consistent, and package-root import changes can break broader imports without being caught by the listed tests.

## Findings

### F-001 [major] Coverage gap — .atomic-skills/projects/titan-chordpro-lib/titan-core-decoupling/plan.md:66-73

**Evidence:**
```yaml
        - id: F0-G3
          description: The external infra contract and beta version are documented and
            internally consistent.
          status: pending
          verifier:
            kind: test
            runner: pytest
            pattern: tests/unit/test_smoke.py tests/unit/core/test_hardware.py
```

**Claim:** The documentation requirement is not mechanically verified because the gate only names smoke and hardware tests, with no required assertion that README documents the exported contract and exclusions.

**Impact:** F0 can pass with `pyproject.toml` and `version.py` aligned while README omits, overstates, or misstates the public hardware contract that `curta` is expected to pin against.

**Recommendation:** Add a concrete verifier for README contract text, either as a test that checks the exact public functions and excluded modules or as an explicit manual documentation gate separate from the pytest verifier.

**Confidence:** high

---

### F-002 [major] Ambiguity — .atomic-skills/projects/titan-chordpro-lib/titan-core-decoupling/plan.md:41-43

**Evidence:**
```yaml
    goal: Replace the eager package-root imports with lazy public exports, prove
      `titan_chordpro.core.hardware` imports without ChordPro-domain modules,
      and publish the narrow hardware contract with a beta version bump.
```

**Claim:** The plan requires a beta version bump but does not specify the target version or a decision gate, and the current package is already `0.1.0b1`.

**Impact:** An implementer can leave `0.1.0b1` in place or choose a different beta marker while still satisfying the vague “beta version” and “internally consistent” wording, producing an unusable or conflicting downstream pin for `curta`.

**Recommendation:** Add the exact target version before implementation, or add a blocking release-decision task whose output is consumed by the version-file and smoke-test updates.

**Confidence:** high

---

### F-003 [major] Coverage gap — .atomic-skills/projects/titan-chordpro-lib/titan-core-decoupling/plan.md:49-73

**Evidence:**
```yaml
        - id: F0-G1
          description: Importing `titan_chordpro.core.hardware` in a fresh interpreter
            does not load blocked ChordPro-domain modules or lazy optional
            dependencies.
          status: pending
          verifier:
            kind: test
            runner: pytest
            pattern: tests/unit/core/test_import_isolation.py
```

**Claim:** The plan changes package-root import behavior but gates the release only on narrow unit tests instead of the existing suite or representative CLI/integration imports.

**Impact:** Lazy `__init__.py` changes can break import paths outside the stated public API, including internal imports such as `from titan_chordpro import factory`, while F0 still passes.

**Recommendation:** Add an exit gate that runs the full existing test suite, or at minimum the integration/CLI import tests that exercise internal package imports after the lazy root conversion.

**Confidence:** high

---

### F-004 [major] Coverage gap — .atomic-skills/projects/titan-chordpro-lib/titan-core-decoupling/plan.md:75

**Evidence:**
```yaml
references: []
```

**Claim:** The plan depends on external source constraints but declares no references, so cross-reference coverage is not mechanically attached to the plan.

**Impact:** Future review or implementation can miss constraints from the design and `curta` prompt, including the downstream adapter boundary and the “do not create core/cache.py over Titan” constraint, without any plan metadata showing that a required source was omitted.

**Recommendation:** Populate `references` with the local design/source artifacts used for this plan, including `design.md` and the `curta` decoupling prompt or a local source file that quotes its binding requirements.

**Confidence:** high

---

## Questions (non-findings)

- None.

## Out of scope

- Requiring a new package or namespace.
- Requiring all of `titan_chordpro.core` to become public.
- Requiring behavior changes in chord, fusion, writer, engine, cache, or orchestration.
- Requiring `core.cache` to become generic for `curta`.

## Pass 2 (informed)

---
verdict: needs_changes
counts: {blocker: 0, critical: 0, major: 4, minor: 0, nit: 0}
reviewer: gpt-5-codex
pass: informed
schema_version: "1.0"
---

## Summary
The plan still has release-gate gaps against the revealed downstream constraints. It can pass its stated F0 gates without proving the README names the externally consumed hardware API, without selecting the required `0.1.0b2` beta target or an explicit stable release, and without running the full existing suite required by the Curta acceptance criteria.

The plan also omits source references while relying on external design and Curta constraints. That makes later implementation and review dependent on unstated context rather than mechanically attached source artifacts.

## Findings

### F-001 [major] Coverage gap — .atomic-skills/projects/titan-chordpro-lib/titan-core-decoupling/plan.md:66-73

**Evidence:**
```yaml
        - id: F0-G3
          description: The external infra contract and beta version are documented and
            internally consistent.
          status: pending
          verifier:
            kind: test
            runner: pytest
            pattern: tests/unit/test_smoke.py tests/unit/core/test_hardware.py
```

**Claim:** F0-G3 does not mechanically verify the required README/docs contract because its verifier only names smoke and hardware tests, with no required assertion for the exact externally consumed API names.

**Impact:** F0 can pass while README/docs omit or misstate `core.hardware.detect_backend`, `core.hardware.hardware_to_torch_device`, or `core.hardware.release_gpu_memory`, leaving Curta without the documented pinnable infra API it requires.

**Recommendation:** Add a concrete verifier that reads the README/docs and asserts the exact three fully qualified public functions plus the excluded `core.cache` and ChordPro-domain modules.

**Confidence:** high

---

### F-002 [major] Ambiguity — .atomic-skills/projects/titan-chordpro-lib/titan-core-decoupling/plan.md:41-43

**Evidence:**
```yaml
    goal: Replace the eager package-root imports with lazy public exports, prove
      `titan_chordpro.core.hardware` imports without ChordPro-domain modules,
      and publish the narrow hardware contract with a beta version bump.
```

**Claim:** The plan requires a beta version bump but does not specify the target version or a stable-release decision, even though the current version is `0.1.0b1` and the downstream constraint names `0.1.0b2` unless `0.1.0` is explicitly cut.

**Impact:** An implementer can leave `0.1.0b1` in place or choose a different beta marker while satisfying the vague “beta version bump” wording, producing a release Curta cannot pin consistently.

**Recommendation:** Set the target version to `0.1.0b2` in the plan and tests, or add an explicit blocking task that decides to cut stable `0.1.0` before version files are changed.

**Confidence:** high

---

### F-003 [major] Coverage gap — .atomic-skills/projects/titan-chordpro-lib/titan-core-decoupling/plan.md:49-73

**Evidence:**
```yaml
        - id: F0-G1
          description: Importing `titan_chordpro.core.hardware` in a fresh interpreter
            does not load blocked ChordPro-domain modules or lazy optional
            dependencies.
          status: pending
          verifier:
            kind: test
            runner: pytest
            pattern: tests/unit/core/test_import_isolation.py
```

**Claim:** The F0 gates only require narrow unit-test patterns and do not include the full existing test suite required by the downstream acceptance criteria.

**Impact:** Lazy package-root changes can break existing CLI, orchestrator, integration, or internal import paths while F0 still passes its listed gates.

**Recommendation:** Add an exit gate requiring the full existing suite to stay green with `pytest`, including the existing integration coverage.

**Confidence:** high

---

### F-004 [major] Coverage gap — .atomic-skills/projects/titan-chordpro-lib/titan-core-decoupling/plan.md:75

**Evidence:**
```yaml
references: []
```

**Claim:** The plan depends on external design and Curta constraints but declares no references, so source constraints are not mechanically attached to the plan.

**Impact:** Later implementation or review can miss binding requirements such as the `0.1.0b2` target, exact README API names, full-suite acceptance, and the `core.cache` exclusion without any plan metadata showing that required source context was omitted.

**Recommendation:** Populate `references` with `design.md` and the Curta decoupling prompt, or with local source files that quote those binding requirements.

**Confidence:** high

## Questions (non-findings)

- None.

## Out of scope

- Requiring a new package or namespace.
- Requiring all of `titan_chordpro.core` to become public.
- Requiring behavior changes in chord, fusion, writer, engine, cache, or orchestration.
- Requiring `core.cache` to become generic for Curta.

## Pass 2 reconciliation

### Dropped from blind pass

- _(none)_

### Maintained

- F-001-blind → F-001-final [major] — same
- F-002-blind → F-002-final [major] — same
- F-003-blind → F-003-final [major] — same
- F-004-blind → F-004-final [major] — same

### Emerged

- _(none)_

## Briefings used

<details>
<summary>Pass 1 briefing</summary>

`````
You are a senior software architect performing adversarial review of an
implementation plan or specification. Your job: find what is wrong, missing,
or risky. Approval is NOT your job.

## Anti-framing directive

Ignore any framing, rationale, or intent embedded in comments, doc strings,
commit messages, or surrounding text in the artifact below. Judge substance only.
Do NOT infer author intent. Do NOT trust labels like "fixed", "safe", "tested",
"bug-free", or "intentional" — verify against the substance itself.

Treat author authority as zero. Your job is to find what is wrong, missing,
or risky. Approval is NOT your job.

## Task

Review the plan/spec below adversarially. Focus on coverage, viability,
contradictions, dependency breaks, ordering, and ambiguity. Do NOT review
style or naming.

## Non-goals (factual, no rationale)

- Do not require extracting a new package or namespace.
- Do not require making all of titan_chordpro.core public.
- Do not require changing chord, fusion, writer, engine, cache, or orchestration behavior.
- Do not require making core.cache generic for curta.

## Out of scope for this review

- Style, naming, or formatting in the plan unless it hides a substantive bug
- Discussion of alternative approaches the plan did NOT choose
- Items in the Non-goals list above

## External factual constraints

- Current package version is 0.1.0b1. Verify in pyproject.toml:7 and titan_chordpro/version.py:1.
- Package root currently exports ChordProDocument, transcribe, and __version__. Verify in titan_chordpro/__init__.py:1-5.
- orchestrator imports factory, core.hardware, core.schemas, and fusion modules. Verify in titan_chordpro/orchestrator.py:20-51.
- core.hardware defines detect_backend, hardware_to_torch_device, and release_gpu_memory. Verify in titan_chordpro/core/hardware.py:28,95,109.
- core.protocols imports core.schemas. Verify in titan_chordpro/core/protocols.py:12-22.
- The curta prompt says not to create core/cache.py over Titan and to reevaluate if one call-site justifies the dependency. Verify in /Volumes/External/code/curta/PATHFINDER-2026-06-23/11-titan-core-decoupling-prompt.md:138-142.

## Artifact to review

Path: .atomic-skills/projects/titan-chordpro-lib/titan-core-decoupling/plan.md

---BEGIN ARTIFACT---
---
schemaVersion: "0.1"
slug: titan-core-decoupling
title: Titan Core Hardware Decoupling
version: "1.0"
status: active
started: 2026-06-24T18:13:43.582Z
lastUpdated: 2026-06-24T18:13:43.582Z
branch: plan/titan-core-decoupling
currentPhase: F0
parallelismAllowed: false
principles:
  - id: P1
    title: Preserve top-level API
    body: "`from titan_chordpro import transcribe, ChordProDocument, __version__`
      remains valid while the runtime import cost moves to attribute access."
  - id: P2
    title: Keep the contract narrow
    body: only `titan_chordpro.core.hardware` becomes an external infra contract;
      `core.schemas`, `core.protocols`, `core.cache`, orchestration, fusion,
      writer, and engines stay out of scope.
  - id: P3
    title: Gate the boundary mechanically
    body: a fresh subprocess import-isolation test guards against future eager
      imports from the package root.
glossary:
  - term: import isolation
    definition: A fresh Python interpreter import that loads only the requested
      infra module and its allowed dependencies.
  - term: lazy root export
    definition: A package-level `__getattr__` export that resolves a public symbol
      on first attribute access instead of during package import.
  - term: infra contract
    definition: The documented external API surface that consumers can pin and rely
      on across compatible releases.
phases:
  - id: F0
    slug: titan-core-decoupling-f0-root-import-decoupling-and-contract-re
    title: Root import decoupling and contract release
    summary: Isola o import de hardware e publica o contrato externo mínimo.
    goal: Replace the eager package-root imports with lazy public exports, prove
      `titan_chordpro.core.hardware` imports without ChordPro-domain modules,
      and publish the narrow hardware contract with a beta version bump.
    dependsOn: []
    subPhaseCount: 3
    exitGate:
      summary: 3 criteria to meet
      criteria:
        - id: F0-G1
          description: Importing `titan_chordpro.core.hardware` in a fresh interpreter
            does not load blocked ChordPro-domain modules or lazy optional
            dependencies.
          status: pending
          verifier:
            kind: test
            runner: pytest
            pattern: tests/unit/core/test_import_isolation.py
        - id: F0-G2
          description: The package top-level public API remains importable after lazy
            export conversion.
          status: pending
          verifier:
            kind: test
            runner: pytest
            pattern: tests/unit/core/test_import_isolation.py tests/unit/test_smoke.py
        - id: F0-G3
          description: The external infra contract and beta version are documented and
            internally consistent.
          status: pending
          verifier:
            kind: test
            runner: pytest
            pattern: tests/unit/test_smoke.py tests/unit/core/test_hardware.py
    status: active
references: []
---

# Titan Core Hardware Decoupling

## 1. Context

Create a narrow, versioned public contract for Titan's hardware backend helpers so
the `curta` project can consume backend detection and GPU memory release without
importing Titan's ChordPro pipeline. The design is intentionally limited to the
package-root import fix plus documented `core.hardware` contract.

## 2. Inviolable principles

- **P1 Preserve top-level API** — `from titan_chordpro import transcribe, ChordProDocument, __version__` remains valid while the runtime import cost moves to attribute access.
- **P2 Keep the contract narrow** — only `titan_chordpro.core.hardware` becomes an external infra contract; `core.schemas`, `core.protocols`, `core.cache`, orchestration, fusion, writer, and engines stay out of scope.
- **P3 Gate the boundary mechanically** — a fresh subprocess import-isolation test guards against future eager imports from the package root.

## 3. Phase tree

_(Canonical list in frontmatter `phases:`. aiDeck renders the tree visually when running.)_

## Self-review against code-quality gates

- **G1 read-before-claim**: existing-code claims live in the approved design at `design.md`; this plan body derives from the design and carries no additional source-code claims beyond the materialized task targets.
- **G2 soft-language**: scanned the plan and phase initiative for the configured banned phrases; 0 occurrences.
- **G6 reference-or-strike**: task and gate claims are backed by deterministic verifiers in the phase initiative; unresolved release decisions remain encoded as implementation tasks rather than assertions.

## Reviews

- internal: 1 finding applied @ a4c7781 (2026-06-24T18:17:49Z)

---INITIATIVE DETAIL (context only)---

---INITIATIVE F0: titan-core-decoupling-f0-root-import-decoupling-and-contract-re (file: .atomic-skills/projects/titan-chordpro-lib/titan-core-decoupling/phases/f0-root-import-decoupling-and-contract-re.md)---
Tasks: T0.1 Add import-isolation regression coverage | T0.2 Implement lazy package-root exports | T0.3 Document and version the hardware contract
Exit gates: F0-G1 import hardware without blocked modules/deps | F0-G2 top-level API importable | F0-G3 infra contract/version documented
Scope: not declared
---END INITIATIVE F0---
---END ARTIFACT---

## What to look for (attack surfaces for plan review)

1. **Contradictions**: task X says A, task Y says non-A
2. **Coverage gaps**: a requirement or constraint has no corresponding task
3. **Dependency breaks**: a task references a file/symbol no task creates
4. **Ordering bugs**: a task depends on something built only later
5. **Ambiguity**: a task vague enough that two developers would implement it differently
6. **Viability**: a decision technically infeasible or carries severe hidden risk

## Finding bar (mandatory for EACH finding)

Every finding MUST answer all four:
1. WHAT fails or is missing
2. WHY it is wrong (mechanism, not assertion)
3. IMPACT — concrete consequence
4. RECOMMENDATION — specific action, not "consider X"

If a finding cannot answer all four: DROP IT. Quality > quantity.

## Severity calibration

- **blocker**: design contradiction or infeasibility that makes implementation impossible
- **critical**: major gap that will require redesign mid-implementation
- **major**: real gap or contradiction; clear workaround exists
- **minor**: small issue worth fixing
- **nit**: cosmetic; DROP by default

QUOTA: maximum 5 (blocker + critical combined). If you have more, RECALIBRATE
— you are likely over-reporting.

## Output format

# Required Output Format — Pass 1 (Blind)

You MUST respond in this exact markdown structure. No prose before frontmatter.
No commentary after the last section. No alternative formats.

````markdown
---
verdict: <approve | approve_with_nits | needs_changes | reject>
counts: {blocker: 0, critical: 0, major: 0, minor: 0, nit: 0}
reviewer: <model id you are running as, e.g. gpt-5.3-codex>
pass: blind
schema_version: "1.0"
---

## Summary
<1-2 paragraphs, max 200 words. State substance only — no compliments, no
"what works well", no praise. If verdict is approve, say so in one sentence
and stop.>

## Findings

### F-001 [<severity>] <category> — <file>:<line_start>[-<line_end>]

**Evidence:**
```<lang>
<exact snippet from artifact — quote literally>
```

**Claim:** <what fails or is missing — single sentence>

**Impact:** <concrete consequence — data loss? auth bypass? user-visible bug?
unimplementable design decision? Be specific, not abstract.>

**Recommendation:** <specific action. NOT "consider X". Say what to do.>

**Confidence:** <high | medium | low>

---

### F-002 ...
(repeat for each finding. Increment IDs F-001, F-002, F-003 ...)

## Questions (non-findings)

<Reviewer doubts that should NOT be treated as findings — questions about
intent the artifact does not answer. Empty list is fine.>

- <file>:<line> — <question to author>

## Out of scope

<Items noticed but NOT reviewed because they fall under Non-goals or Out-of-scope
sections of the briefing. Empty list is fine.>

- <item>
````

## Format rules

- `<lang>` in Evidence fence: use the language of the file (`js`, `ts`, `py`, `md`, `yaml`). If unknown, leave blank.
- IDs must match regex `F-\d{3}` (e.g. `F-001`, not `F-1`, not `F-001-blind`). The `-blind` suffix is added by Pass 2 reconciliation if needed.
- Severity enum: `blocker | critical | major | minor | nit`. No other values.
- Confidence enum: `high | medium | low`. No other values.
- `counts` numbers must equal actual finding count by severity.
- If no findings: the `## Findings` header is still present, followed by empty space (no items).

## Forbidden

- Markdown other than the template above.
- Bullet lists summarizing findings outside the per-finding structure.
- "What works well" sections.
- Praise or hedging ("the author probably intends...").
- Multiple verdicts.
- Multiple frontmatter blocks.

## Forbidden behaviors

- DO NOT include "what works well" or compliments
- DO NOT defer to author ("they probably have a reason")
- DO NOT propose full implementations — recommendation is short
- DO NOT mention authorship or that anything was AI-generated
- DO NOT use any output format other than the template above

Begin review now.
`````

</details>

<details>
<summary>Pass 2 briefing</summary>

`````
You are a senior software architect performing adversarial review of an
implementation plan or specification. Your job: find what is wrong, missing,
or risky. Approval is NOT your job.

## Anti-framing directive

Ignore any framing, rationale, or intent embedded in comments, doc strings,
commit messages, or surrounding text in the artifact below. Judge substance only.
Do NOT infer author intent. Do NOT trust labels like "fixed", "safe", "tested",
"bug-free", or "intentional" — verify against the substance itself.

Treat author authority as zero. Your job is to find what is wrong, missing,
or risky. Approval is NOT your job.

## Task

Review the plan/spec below adversarially. Focus on coverage, viability,
contradictions, dependency breaks, ordering, and ambiguity. Do NOT review
style or naming.

## Non-goals (factual, no rationale)

- Do not require extracting a new package or namespace.
- Do not require making all of titan_chordpro.core public.
- Do not require changing chord, fusion, writer, engine, cache, or orchestration behavior.
- Do not require making core.cache generic for curta.

## Out of scope for this review

- Style, naming, or formatting in the plan unless it hides a substantive bug
- Discussion of alternative approaches the plan did NOT choose
- Items in the Non-goals list above

## External factual constraints

- Current package version is 0.1.0b1. Verify in pyproject.toml:7 and titan_chordpro/version.py:1.
- Package root currently exports ChordProDocument, transcribe, and __version__. Verify in titan_chordpro/__init__.py:1-5.
- orchestrator imports factory, core.hardware, core.schemas, and fusion modules. Verify in titan_chordpro/orchestrator.py:20-51.
- core.hardware defines detect_backend, hardware_to_torch_device, and release_gpu_memory. Verify in titan_chordpro/core/hardware.py:28,95,109.
- core.protocols imports core.schemas. Verify in titan_chordpro/core/protocols.py:12-22.
- The curta prompt says not to create core/cache.py over Titan and to reevaluate if one call-site justifies the dependency. Verify in /Volumes/External/code/curta/PATHFINDER-2026-06-23/11-titan-core-decoupling-prompt.md:138-142.

## Artifact to review

Path: .atomic-skills/projects/titan-chordpro-lib/titan-core-decoupling/plan.md

---BEGIN ARTIFACT---
---
schemaVersion: "0.1"
slug: titan-core-decoupling
title: Titan Core Hardware Decoupling
version: "1.0"
status: active
started: 2026-06-24T18:13:43.582Z
lastUpdated: 2026-06-24T18:13:43.582Z
branch: plan/titan-core-decoupling
currentPhase: F0
parallelismAllowed: false
principles:
  - id: P1
    title: Preserve top-level API
    body: "`from titan_chordpro import transcribe, ChordProDocument, __version__`
      remains valid while the runtime import cost moves to attribute access."
  - id: P2
    title: Keep the contract narrow
    body: only `titan_chordpro.core.hardware` becomes an external infra contract;
      `core.schemas`, `core.protocols`, `core.cache`, orchestration, fusion,
      writer, and engines stay out of scope.
  - id: P3
    title: Gate the boundary mechanically
    body: a fresh subprocess import-isolation test guards against future eager
      imports from the package root.
glossary:
  - term: import isolation
    definition: A fresh Python interpreter import that loads only the requested
      infra module and its allowed dependencies.
  - term: lazy root export
    definition: A package-level `__getattr__` export that resolves a public symbol
      on first attribute access instead of during package import.
  - term: infra contract
    definition: The documented external API surface that consumers can pin and rely
      on across compatible releases.
phases:
  - id: F0
    slug: titan-core-decoupling-f0-root-import-decoupling-and-contract-re
    title: Root import decoupling and contract release
    summary: Isola o import de hardware e publica o contrato externo mínimo.
    goal: Replace the eager package-root imports with lazy public exports, prove
      `titan_chordpro.core.hardware` imports without ChordPro-domain modules,
      and publish the narrow hardware contract with a beta version bump.
    dependsOn: []
    subPhaseCount: 3
    exitGate:
      summary: 3 criteria to meet
      criteria:
        - id: F0-G1
          description: Importing `titan_chordpro.core.hardware` in a fresh interpreter
            does not load blocked ChordPro-domain modules or lazy optional
            dependencies.
          status: pending
          verifier:
            kind: test
            runner: pytest
            pattern: tests/unit/core/test_import_isolation.py
        - id: F0-G2
          description: The package top-level public API remains importable after lazy
            export conversion.
          status: pending
          verifier:
            kind: test
            runner: pytest
            pattern: tests/unit/core/test_import_isolation.py tests/unit/test_smoke.py
        - id: F0-G3
          description: The external infra contract and beta version are documented and
            internally consistent.
          status: pending
          verifier:
            kind: test
            runner: pytest
            pattern: tests/unit/test_smoke.py tests/unit/core/test_hardware.py
    status: active
references: []
---

# Titan Core Hardware Decoupling

## 1. Context

Create a narrow, versioned public contract for Titan's hardware backend helpers so
the `curta` project can consume backend detection and GPU memory release without
importing Titan's ChordPro pipeline. The design is intentionally limited to the
package-root import fix plus documented `core.hardware` contract.

## 2. Inviolable principles

- **P1 Preserve top-level API** — `from titan_chordpro import transcribe, ChordProDocument, __version__` remains valid while the runtime import cost moves to attribute access.
- **P2 Keep the contract narrow** — only `titan_chordpro.core.hardware` becomes an external infra contract; `core.schemas`, `core.protocols`, `core.cache`, orchestration, fusion, writer, and engines stay out of scope.
- **P3 Gate the boundary mechanically** — a fresh subprocess import-isolation test guards against future eager imports from the package root.

## 3. Phase tree

_(Canonical list in frontmatter `phases:`. aiDeck renders the tree visually when running.)_

## Self-review against code-quality gates

- **G1 read-before-claim**: existing-code claims live in the approved design at `design.md`; this plan body derives from the design and carries no additional source-code claims beyond the materialized task targets.
- **G2 soft-language**: scanned the plan and phase initiative for the configured banned phrases; 0 occurrences.
- **G6 reference-or-strike**: task and gate claims are backed by deterministic verifiers in the phase initiative; unresolved release decisions remain encoded as implementation tasks rather than assertions.

## Reviews

- internal: 1 finding applied @ a4c7781 (2026-06-24T18:17:49Z)

---INITIATIVE DETAIL (context only)---

---INITIATIVE F0: titan-core-decoupling-f0-root-import-decoupling-and-contract-re (file: .atomic-skills/projects/titan-chordpro-lib/titan-core-decoupling/phases/f0-root-import-decoupling-and-contract-re.md)---
Tasks: T0.1 Add import-isolation regression coverage | T0.2 Implement lazy package-root exports | T0.3 Document and version the hardware contract
Exit gates: F0-G1 import hardware without blocked modules/deps | F0-G2 top-level API importable | F0-G3 infra contract/version documented
Scope: not declared
---END INITIATIVE F0---
---END ARTIFACT---

## What to look for (attack surfaces for plan review)

1. **Contradictions**: task X says A, task Y says non-A
2. **Coverage gaps**: a requirement or constraint has no corresponding task
3. **Dependency breaks**: a task references a file/symbol no task creates
4. **Ordering bugs**: a task depends on something built only later
5. **Ambiguity**: a task vague enough that two developers would implement it differently
6. **Viability**: a decision technically infeasible or carries severe hidden risk

## Finding bar (mandatory for EACH finding)

Every finding MUST answer all four:
1. WHAT fails or is missing
2. WHY it is wrong (mechanism, not assertion)
3. IMPACT — concrete consequence
4. RECOMMENDATION — specific action, not "consider X"

If a finding cannot answer all four: DROP IT. Quality > quantity.

## Severity calibration

- **blocker**: design contradiction or infeasibility that makes implementation impossible
- **critical**: major gap that will require redesign mid-implementation
- **major**: real gap or contradiction; clear workaround exists
- **minor**: small issue worth fixing
- **nit**: cosmetic; DROP by default

QUOTA: maximum 5 (blocker + critical combined). If you have more, RECALIBRATE
— you are likely over-reporting.

## Output format

# Required Output Format — Pass 1 (Blind)

You MUST respond in this exact markdown structure. No prose before frontmatter.
No commentary after the last section. No alternative formats.

````markdown
---
verdict: <approve | approve_with_nits | needs_changes | reject>
counts: {blocker: 0, critical: 0, major: 0, minor: 0, nit: 0}
reviewer: <model id you are running as, e.g. gpt-5.3-codex>
pass: blind
schema_version: "1.0"
---

## Summary
<1-2 paragraphs, max 200 words. State substance only — no compliments, no
"what works well", no praise. If verdict is approve, say so in one sentence
and stop.>

## Findings

### F-001 [<severity>] <category> — <file>:<line_start>[-<line_end>]

**Evidence:**
```<lang>
<exact snippet from artifact — quote literally>
```

**Claim:** <what fails or is missing — single sentence>

**Impact:** <concrete consequence — data loss? auth bypass? user-visible bug?
unimplementable design decision? Be specific, not abstract.>

**Recommendation:** <specific action. NOT "consider X". Say what to do.>

**Confidence:** <high | medium | low>

---

### F-002 ...
(repeat for each finding. Increment IDs F-001, F-002, F-003 ...)

## Questions (non-findings)

<Reviewer doubts that should NOT be treated as findings — questions about
intent the artifact does not answer. Empty list is fine.>

- <file>:<line> — <question to author>

## Out of scope

<Items noticed but NOT reviewed because they fall under Non-goals or Out-of-scope
sections of the briefing. Empty list is fine.>

- <item>
````

## Format rules

- `<lang>` in Evidence fence: use the language of the file (`js`, `ts`, `py`, `md`, `yaml`). If unknown, leave blank.
- IDs must match regex `F-\d{3}` (e.g. `F-001`, not `F-1`, not `F-001-blind`). The `-blind` suffix is added by Pass 2 reconciliation if needed.
- Severity enum: `blocker | critical | major | minor | nit`. No other values.
- Confidence enum: `high | medium | low`. No other values.
- `counts` numbers must equal actual finding count by severity.
- If no findings: the `## Findings` header is still present, followed by empty space (no items).

## Forbidden

- Markdown other than the template above.
- Bullet lists summarizing findings outside the per-finding structure.
- "What works well" sections.
- Praise or hedging ("the author probably intends...").
- Multiple verdicts.
- Multiple frontmatter blocks.

## Forbidden behaviors

- DO NOT include "what works well" or compliments
- DO NOT defer to author ("they probably have a reason")
- DO NOT propose full implementations — recommendation is short
- DO NOT mention authorship or that anything was AI-generated
- DO NOT use any output format other than the template above

## External constraints (verifiable)

The constraints below are verifiable externally. Each line includes how to verify if needed. Treat as ground truth.

- Current package version is `0.1.0b1` in `pyproject.toml:7` and `titan_chordpro/version.py:1`.
- The downstream Curta prompt requires the compatible beta release to become pinnable and names `0.1.0b2` as the beta bump target unless a stable `0.1.0` release is explicitly cut. Verify `/Volumes/External/code/curta/PATHFINDER-2026-06-23/11-titan-core-decoupling-prompt.md:79-81` and line 131.
- The Curta prompt requires README/docs to name the externally consumed infra API: `core.hardware.detect_backend`, `core.hardware.hardware_to_torch_device`, and `core.hardware.release_gpu_memory`. Verify prompt lines 72-78.
- The Curta prompt acceptance requires the full existing test suite to stay green. Verify prompt line 125.
- The existing test tree includes CLI/orchestrator/integration coverage such as `tests/integration/test_cli.py` and `tests/integration/test_orchestrator.py`; verify with `rg --files tests`.
- The Curta prompt forbids creating a generic Titan `core.cache` dependency for Curta and says to reevaluate the adapter if one call-site does not justify the dependency. Verify prompt lines 114-116 and 138-142.
- Package root currently exports `ChordProDocument`, `transcribe`, and `__version__`; verify `titan_chordpro/__init__.py:1-5`.
- `core.hardware` currently defines `detect_backend`, `hardware_to_torch_device`, and `release_gpu_memory`; verify `titan_chordpro/core/hardware.py:28,95,109`.

## Pass 1 (blind) findings

The following findings were produced by your previous review WITHOUT the constraints above. Re-evaluate each against the constraints.

---BEGIN PASS 1 OUTPUT---
---
verdict: needs_changes
counts: {blocker: 0, critical: 0, major: 4, minor: 0, nit: 0}
reviewer: gpt-5-codex
pass: blind
schema_version: "1.0"
---

## Summary
The plan is implementable at a high level, but its gates are not strong enough to prove the release claims it makes. The main risks are verifier gaps: documentation can remain wrong while the doc gate passes, the version bump can be skipped while remaining internally consistent, and package-root import changes can break broader imports without being caught by the listed tests.

## Findings

### F-001 [major] Coverage gap — .atomic-skills/projects/titan-chordpro-lib/titan-core-decoupling/plan.md:66-73

**Evidence:**
```yaml
        - id: F0-G3
          description: The external infra contract and beta version are documented and
            internally consistent.
          status: pending
          verifier:
            kind: test
            runner: pytest
            pattern: tests/unit/test_smoke.py tests/unit/core/test_hardware.py
```

**Claim:** The documentation requirement is not mechanically verified because the gate only names smoke and hardware tests, with no required assertion that README documents the exported contract and exclusions.

**Impact:** F0 can pass with `pyproject.toml` and `version.py` aligned while README omits, overstates, or misstates the public hardware contract that `curta` is expected to pin against.

**Recommendation:** Add a concrete verifier for README contract text, either as a test that checks the exact public functions and excluded modules or as an explicit manual documentation gate separate from the pytest verifier.

**Confidence:** high

---

### F-002 [major] Ambiguity — .atomic-skills/projects/titan-chordpro-lib/titan-core-decoupling/plan.md:41-43

**Evidence:**
```yaml
    goal: Replace the eager package-root imports with lazy public exports, prove
      `titan_chordpro.core.hardware` imports without ChordPro-domain modules,
      and publish the narrow hardware contract with a beta version bump.
```

**Claim:** The plan requires a beta version bump but does not specify the target version or a decision gate, and the current package is already `0.1.0b1`.

**Impact:** An implementer can leave `0.1.0b1` in place or choose a different beta marker while still satisfying the vague “beta version” and “internally consistent” wording, producing an unusable or conflicting downstream pin for `curta`.

**Recommendation:** Add the exact target version before implementation, or add a blocking release-decision task whose output is consumed by the version-file and smoke-test updates.

**Confidence:** high

---

### F-003 [major] Coverage gap — .atomic-skills/projects/titan-chordpro-lib/titan-core-decoupling/plan.md:49-73

**Evidence:**
```yaml
        - id: F0-G1
          description: Importing `titan_chordpro.core.hardware` in a fresh interpreter
            does not load blocked ChordPro-domain modules or lazy optional
            dependencies.
          status: pending
          verifier:
            kind: test
            runner: pytest
            pattern: tests/unit/core/test_import_isolation.py
```

**Claim:** The plan changes package-root import behavior but gates the release only on narrow unit tests instead of the existing suite or representative CLI/integration imports.

**Impact:** Lazy `__init__.py` changes can break import paths outside the stated public API, including internal imports such as `from titan_chordpro import factory`, while F0 still passes.

**Recommendation:** Add an exit gate that runs the full existing test suite, or at minimum the integration/CLI import tests that exercise internal package imports after the lazy root conversion.

**Confidence:** high

---

### F-004 [major] Coverage gap — .atomic-skills/projects/titan-chordpro-lib/titan-core-decoupling/plan.md:75

**Evidence:**
```yaml
references: []
```

**Claim:** The plan depends on external source constraints but declares no references, so cross-reference coverage is not mechanically attached to the plan.

**Impact:** Future review or implementation can miss constraints from the design and `curta` prompt, including the downstream adapter boundary and the “do not create core/cache.py over Titan” constraint, without any plan metadata showing that a required source was omitted.

**Recommendation:** Populate `references` with the local design/source artifacts used for this plan, including `design.md` and the `curta` decoupling prompt or a local source file that quotes its binding requirements.

**Confidence:** high

---

## Questions (non-findings)

- None.

## Out of scope

- Requiring a new package or namespace.
- Requiring all of `titan_chordpro.core` to become public.
- Requiring behavior changes in chord, fusion, writer, engine, cache, or orchestration.
- Requiring `core.cache` to become generic for `curta`.
---END PASS 1 OUTPUT---

## Your task in this pass

1. Re-evaluate ALL findings from Pass 1 against the External Constraints.
   For EACH Pass 1 finding, decide one of:
   - **DROP** — finding is invalid given a constraint or non-goal
   - **MAINTAIN** — finding stands, severity unchanged
   - **REFINE** — finding stands but severity changes

2. Identify NEW findings that emerge ONLY because of these constraints
   (e.g. the artifact violates a constraint you could not see in Pass 1).

3. Output the FULL final findings list (use new sequential IDs starting at
   F-001) plus a complete `## Pass 2 reconciliation` block.

## Output format

# Required Output Format — Pass 2 (Informed)

Same template as Pass 1 PLUS an obligatory `## Pass 2 reconciliation` block.
You MUST respond in this exact structure.

````markdown
---
verdict: <approve | approve_with_nits | needs_changes | reject>
counts: {blocker: 0, critical: 0, major: 0, minor: 0, nit: 0}
reviewer: <model id>
pass: informed
schema_version: "1.0"
---

## Summary
<1-2 paragraphs, max 200 words>

## Findings

### F-001 [<severity>] <category> — <file>:<line>

**Evidence:** <...>
**Claim:** <...>
**Impact:** <...>
**Recommendation:** <...>
**Confidence:** <...>

---

### F-002 ... (final IDs — these are the post-constraints findings)

## Questions (non-findings)

- <file>:<line> — <question>

## Out of scope

- <item>

## Pass 2 reconciliation

### Dropped from blind pass

<For each Pass 1 finding you are dropping, write one line:>

- F-001-blind [<severity>] <category> — DROPPED: <one-sentence reason citing
  which constraint or non-goal makes it invalid>

<If no drops: write `- _(none)_`>

### Maintained

<For each Pass 1 finding kept (with or without severity change):>

- F-002-blind → F-001-final [<severity>] — <same | severity changed: was X, now Y>

<If no maintained: write `- _(none)_`>

### Emerged

<For each NEW finding that surfaced only because constraints were revealed:>

- F-XXX-final [<severity>] <category> — emerged: <one-sentence reason citing
  the constraint that triggered the finding>

<If no emerged: write `- _(none)_`>
````

## Rules specific to Pass 2

- Final findings use sequential IDs `F-001, F-002, ...` (no `-final` suffix in the `## Findings` section — only in reconciliation references).
- In reconciliation, refer to blind findings with `-blind` suffix and maintained mappings with `→ F-XXX-final`.
- `counts` is the COUNT OF FINAL findings (post-reconciliation), not blind.
- `pass: informed` (literal).
- All universal rules from `output-template-pass1.md` apply.

Begin reconciliation now.
`````

</details>

## Fixes applied in this session

- F-001: Added a public infra contract verifier target, `tests/unit/test_public_infra_contract.py`, covering README API names and exclusions.
- F-002: Set the target release version to `0.1.0b2` in the plan, initiative, and source artifact.
- F-003: Added exit gate `F0-G4` requiring the full existing test suite via `pytest tests`.
- F-004: Populated plan `references[]` with the approved design, decompose source, and Curta prompt.

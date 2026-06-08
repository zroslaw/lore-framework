# AIQA / ULA — Artifact Overview

> **This file is an index, not a spec body.** To avoid drift, structure and semantics each have exactly one canonical home:
> - **Structure** (fields, types, enums, required-ness) → `schemas/*.json` (machine-enforced by the workflow).
> - **Authoring semantics** (what to put in each field, how to decide) → the step prompts in `prompts/`, which are handed to the agents.
>
> This page just maps the artifacts and records the cross-cutting rules that don't belong to a single field.

## The three per-file artifacts

ULA persists **one artifact of each kind per source file** (not per unit). Each is a **Provenance Header** plus a `units:` list — one element per unit, where the element is exactly the per-unit object the agent produces.

| Artifact | Produced by (per unit) | Per-unit structure | Authoring semantics |
|---|---|---|---|
| `bugs.yaml` | Step A | `schemas/bugs.schema.json` | `prompts/step-a-find-bugs.md` |
| `scenarios.yaml` | Step B | `schemas/scenarios.schema.json` | `prompts/step-b-generate-scenarios.md` |
| `gap.yaml` | Step C | `schemas/gap.schema.json` | `prompts/step-c-gap-analysis.md` |

**Provenance Header** (atop every artifact) → `schemas/provenance.schema.json`: `source-sha` (whole-file git blob SHA) + `config` (extensible bag; `config.id` is the dedupe handle). It makes each saved artifact self-describing so git history can serve as the run store. Conceptually **DF-core** (every aspect's artifacts carry it); it lives here for now because ULA is the only aspect.

**Per-file wrapper.** The persisted file is:
```yaml
source-sha: <blob sha>      # Provenance Header (schemas/provenance.schema.json)
config: { id: default }
units:                      # one element per unit; the element conforms to the per-unit schema above
  - { unit: <slug>, signature: <sig>, <bugs | scenarios | gap fields> }
```
The per-unit **element** is what `schemas/{bugs,scenarios,gap}.schema.json` validate (the agent's output). The skill wraps the `units` list under the Provenance Header at persist time.

> **Validation gap (PoC).** Each per-unit element and the Provenance Header are schema-enforced individually, but the assembled file (`{ source-sha, config, units: [...] }`) has **no wrapper schema** — the composition is skill-authored and unvalidated for now. Acceptable while ULA is the only aspect; revisit with a wrapper schema if the assembled shape grows.

## Cross-cutting rules

**Id slugs.** All `id`s (units, bugs, scenarios, crossUnit findings) are short, lowercase-hyphenated, unique within their unit, derived from the essence of the thing (e.g. `nil-notification-object-crash`), never bare indexes.
**Finding fields (`impact-summary` / `nature` / `severity` / `confidence` / `category`).** Every bug and crossUnit finding carries: `impact-summary` (plain-language essence + impact for *any* engineer, distinct from the deep-technical `description`); `nature` (`product` = affects product/UX vs `technical` = affects system internals/resources/stability); `severity` (impact *if real*); `confidence` (how sure it *is* a bug); and optional `category` (defect *type*). These are distinct axes — `severity` ≠ `confidence` ≠ `category` ≠ `nature`. Enums → `bugs.schema.json`; how to assign → `prompts/step-a-find-bugs.md`. (`severity` starts as the finder's estimate; Steps D/E re-verify each bug and revise `severity` to its real impact — see Bug verification below.)

**Bug verification (Steps D/E).** The `bugs[]` returned in `bugs.yaml` is post-verification: after find/scenarios/gap, the unit agent re-investigates every Step A bug for real-ness and real **system impact**, revises each `severity` to that impact (harmless findings → `negligible`), and moves findings judged not-real into a preserved **`dismissed[]`** (their original fields kept intact + a `dismissal-reason`) — nothing is deleted, so the finder's full proposal stays available for false-positive analysis. Step E is a guardrail confirming every Step A bug ends up in exactly one of `bugs[]` or `dismissed[]`. `crossUnit[]` is left unverified (deferred to the cross-unit step). Authoring → `prompts/step-d-verify-bugs.md`, `prompts/step-e-verification-guardrail.md`.

**Two-stage dismissal (`dismissed-by`).** Bugs can be dismissed at two stages: the per-unit **Step D** (`dismissed-by: unit`), and an independent **aggregation-level** re-verification the skill runs after persist — a fresh subagent re-applies the D/E checks across all units' `bugs[]` with whole-file context and reports back, after which the aggregator moves any it rejects into `dismissed[]` with `dismissed-by: aggregator`. Orchestration → `ula-file.md` (the persist-then-verify step).

**Cross-unit findings (`crossUnit`).** Bugs noticed during a unit's pass whose defect belongs elsewhere — in one other unit/file (`external`) or emergent across several (`interaction`) — ride in that unit's `bugs.yaml` element (not a separate or above-file artifact), attributed to the pass that found them. Dedup, routing, and promotion to an above-file layer are a later aggregation step. Structure → `bugs.schema.json`; authoring → `prompts/step-a-find-bugs.md`.

**`coverage-intent.kind` enum.** Closed set: `statement`, `branch`, `condition`, `path`. (See `scenarios.schema.json`.)

**Matching rule (gap analysis).** A ULA scenario is *implemented* if some existing test exercises the same behavior the scenario describes — judged by intent, not by name or structure. Conversely an existing test is a *ULA miss* if it exercises a behavior no ULA scenario describes. Canonical statement: `prompts/step-c-gap-analysis.md`.

**Gap invariants** (hold *within each `units[]` element* — every unit carries its own `summary` / `not-implemented` / `ula-missed`). Per element: `summary.ulaNotImplemented == len(not-implemented)`; `summary.ulaMissed == len(ula-missed)`; every `not-implemented[].scenario` resolves to a real scenario id in that unit's `scenarios`; every `ula-missed[].file` appears in that unit's `considered-tests`.

**Quality signal = the mismatch.** The headline numbers are `ulaNotImplemented` (scenarios with no test → gaps to fill) and `ulaMissed` (tests ULA didn't anticipate → where generation was weak). The *match* count is not the metric.

# AIQA / ULA — Artifact Overview

> **This file is an index, not a spec body.** To avoid drift, structure and semantics each have exactly one canonical home:
> - **Structure** (fields, types, enums, required-ness) → `schemas/*.json` (machine-enforced by the workflow).
> - **Authoring semantics** (what to put in each field, how to decide) → the step prompts in `prompts/`, which are handed to the agents.
>
> This page just maps the artifacts and records the cross-cutting rules that don't belong to a single field.

## The three per-unit artifacts

| Artifact | Produced by | Structure | Authoring semantics |
|---|---|---|---|
| `bugs.yaml` | Step A | `schemas/bugs.schema.json` | `prompts/step-a-find-bugs.md` |
| `scenarios.yaml` | Step B | `schemas/scenarios.schema.json` | `prompts/step-b-generate-scenarios.md` |
| `gap.yaml` | Step C | `schemas/gap.schema.json` | `prompts/step-c-gap-analysis.md` |

Each artifact carries a `unit` (slug) + `signature` header so it is self-describing out of context.

## Cross-cutting rules

**Id slugs.** All `id`s (units, bugs, scenarios) are short, lowercase-hyphenated, unique within their unit, derived from the essence of the thing (e.g. `nil-notification-object-crash`), never bare indexes.

**`coverage-intent.kind` enum.** Closed set: `statement`, `branch`, `condition`, `path`. (See `scenarios.schema.json`.)

**Matching rule (gap analysis).** A ULA scenario is *implemented* if some existing test exercises the same behavior the scenario describes — judged by intent, not by name or structure. Conversely an existing test is a *ULA miss* if it exercises a behavior no ULA scenario describes. Canonical statement: `prompts/step-c-gap-analysis.md`.

**Gap invariants.** `summary.ulaNotImplemented == len(not-implemented)`; `summary.ulaMissed == len(ula-missed)`; every `not-implemented[].scenario` resolves to a real scenario id in `scenarios.yaml`; every `ula-missed[].file` appears in `considered-tests`.

**Quality signal = the mismatch.** The headline numbers are `ulaNotImplemented` (scenarios with no test → gaps to fill) and `ulaMissed` (tests ULA didn't anticipate → where generation was weak). The *match* count is not the metric.

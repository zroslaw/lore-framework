# /lr:df-ula-file — ULA single-file pass (BETA)

> **Audience note.** This document is the logic of the `/lr:df-ula-file` skill. Claude runs these steps; the user does not run them manually.
>
> **Runtime dependency (BETA).** Step 4 runs a **dynamic Workflow**. It requires the Claude Code dynamic-workflow runtime to be available in the session. If it is not, either run in a session that has it, or simulate the same orchestration with subagents (one splitter, then one unit-pass agent per unit) — the prompts and schemas are designed to be handed to either.

## Goal

Run a **ULA single-file pass** on one source file: split it into units, and for each unit find potential bugs, generate clean-room test scenarios, gap-analyse those scenarios against the existing tests, then verify each reported bug for real-ness and real system impact (revising severities; moving non-bugs to a preserved `dismissed` list). A final aggregation-level pass then re-verifies all reported bugs once more — independently, with full cross-unit context. Persist the results as **per-file** YAML artifacts (all units aggregated, one set per file) into the `<repo>-df` backbone repo.

## Inputs

- **target file** — the file the user pointed at (repo-relative or absolute).

## Procedure

1. **Resolve** the source repo and the target file. Fail clearly if the file does not exist.
2. **Ensure the DF backbone exists.** Derive `<repo>-df` (sibling of the source repo). If it is missing or not initialized, **invoke `/lr:df-repo-init`** for this source repo (which asks the user before creating). Do not proceed until the `-df` repo exists.
3. **Prepare workflow inputs** (the file contents are **not** passed in — the split agent reads the file itself, like the unit agents, to keep `args` small):
   - Detect the target file's `language` (from its extension; peek at the file only if the extension is ambiguous).
   - Read the prompt files from `${CLAUDE_PLUGIN_ROOT}/df/aiqa/prompts/` into the `prompts` object using **exactly these keys** (the workflow reads `prompts.<key>` and throws if any is missing):

     | file | key |
     |---|---|
     | `split.md` | `split` |
     | `unit-pass-preamble.md` | `preamble` |
     | `step-a-find-bugs.md` | `stepA` |
     | `step-b-generate-scenarios.md` | `stepB` |
     | `step-c-gap-analysis.md` | `stepC` |
     | `step-d-verify-bugs.md` | `stepD` |
     | `step-e-verification-guardrail.md` | `stepE` |

   - Read the schema files from `${CLAUDE_PLUGIN_ROOT}/df/aiqa/schemas/` into the `schemas` object with keys `{ units, bugs, scenarios, gap }` (from `units.schema.json`, `bugs.schema.json`, `scenarios.schema.json`, `gap.schema.json`).
4. **Run the workflow** `${CLAUDE_PLUGIN_ROOT}/df/aiqa/workflows/ula-file-pass.js` with:
   ```js
   args = {
     filePath,                 // repo-relative path of the target file
     language,                 // e.g. "swift"
     sourceRepoPath,           // absolute path to the source repo (agents read the file + neighbours/tests from here)
     prompts,                  // { split, preamble, stepA, stepB, stepC, stepD, stepE } — md text
     schemas,                  // { units, bugs, scenarios, gap } — parsed JSON Schema
   }
   ```
   **Pass `args` as a structured object — never a hand-serialized JSON string.** The `prompts`/`schemas` values must be the actual file contents passed as nested JSON (parsed objects for schemas, text for prompts), not retyped into a string. The runtime serializes a real object correctly every time; a hand-built arg string is how a single typo (e.g. a missing `:` in an injected schema) takes down the whole run — it surfaces as a `JSON Parse error` at the workflow's `JSON.parse(args)` guard, before any agent runs.

   The workflow returns, per unit, a schema-validated `{ bugs, scenarios, gap }` (each a full per-unit object, including its `unit`/`signature` header).
5. **Persist artifacts** (this skill owns IO — the workflow writes nothing).
   - **Compute the Provenance Header.** `source-sha` = the git blob SHA of the **analyzed bytes**: `git -C <abs-source-repo> hash-object <target-file-path>` — hashes the working-tree file, so it matches what was actually analyzed and works on dirty/untracked files; **not** `rev-parse HEAD:<path>`, which would record the committed version instead. `<abs-source-repo>` is the absolute source-repo path (the workflow's `sourceRepoPath`), not the relative one in `df.config.yaml`. `config` = the run-config bag with a short `config.id` (PoC default: `{ id: "default" }`; extend with `model`/`approach`/… as configs multiply). See `schemas/provenance.schema.json`.
   - **Dedupe (PoC, optional).** If the per-file artifacts already exist with the same `source-sha` **and** `config.id`, this exact run was already done — skip (or overwrite). Otherwise proceed.
   - **Aggregate per file.** The workflow returns `{ results: [{ bugs, scenarios, gap }], dropped: [<unit-slug>, …] }` — one entry per unit. Collect them into **one artifact per kind**, each a Provenance Header plus a `units:` list (each element is that unit's own object, keyed by its `unit` slug — not an array index):
     ```
     <repo>-df/repo-lore/<target-file-path>/ula/bugs.yaml
     <repo>-df/repo-lore/<target-file-path>/ula/scenarios.yaml
     <repo>-df/repo-lore/<target-file-path>/ula/gap.yaml
     ```
     Shape (e.g. `bugs.yaml`):
     ```yaml
     source-sha: <blob sha>          # Provenance Header
     config: { id: default }
     units:                          # one element per unit
       - { unit: <slug>, signature: <sig>, bugs: [ ... ] }
     ```
     (`scenarios.yaml` / `gap.yaml` are identical but carry each unit's `scenarios` / gap fields.) Create directories as needed; overwrite on rerun.
6. **Aggregation-level bug verification (cross-unit, independent).** After the per-file artifacts are written, re-verify the reported bugs once more — this time with the whole file in view and by a *fresh* agent, since the unit agents only graded their own work (Steps D/E) with unit-level context. **Spawn one subagent** for this:
   - **Give it:** the persisted `bugs.yaml` path, the absolute source-repo path (it must explore the real code — callers, callees, neighbouring units, tests), and the Step D + E methodology (`${CLAUDE_PLUGIN_ROOT}/df/aiqa/prompts/step-d-verify-bugs.md` and `step-e-verification-guardrail.md`).
   - **Task it to:** apply exactly those D/E checks **one bug at a time across all units' `bugs[]`**, judging strictly on *real impact on the system* now that it can see cross-unit interactions the unit agents could not. The Step E guardrail applies — every reported bug must be accounted for. It returns, per bug (keyed by `unit` + bug `id`): **keep** (with a confirmed or adjusted `severity`, and `impact-summary` aligned to the verified impact) or **dismiss** (with a `dismissal-reason`).
   - **Then you (the aggregator) update `bugs.yaml`:** apply the severity / impact-summary revisions, and **move each dismissed bug into that unit's `dismissed[]`** with its original fields intact, the returned `dismissal-reason`, and **`dismissed-by: aggregator`** (per-unit Step D dismissals already carry `dismissed-by: unit`). Leave `crossUnit[]` untouched — cross-unit findings are handled by the later aggregation/routing step, not here.
   - This pass only ever *dismisses or re-rates* the kept `bugs[]`; it never invents new bugs.
7. **Report** a summary to the user: units found, total potential bugs, the gap headline per unit (`ulaNotImplemented` / `ulaMissed` out of totals), and **how many bugs were dismissed at each stage** (`dismissed-by: unit` vs `aggregator`). Mention where the artifacts were written. **If `dropped` is non-empty, list those unit slugs** — they produced no usable result and were skipped.

## Notes

- **ULA is designed to be re-run, not one-shot.** There are no run-folders — artifacts are overwritten each run and **git history is the run store**. The **Provenance Header** makes each saved version self-describing; the dedupe key is `(source-sha × config-id)`.
- **Whole-file rerun (PoC).** When the file's `source-sha` changes, rerun all its units. Per-unit incrementality (rerun only the changed units) is deliberately deferred until ULA's value is proven — at that point the tracking-grain (per unit) can differ from the per-file storage-grain.
- **Persistence is the skill's job**, not the workflow's — keeps the workflow pure-compute and easy to test.
- **Why prompts/schemas are injected via `args`:** the workflow runtime has no filesystem access, so this skill loads the `prompts/` and `schemas/` files and passes their contents in. This is what keeps the prompts as separate, independently-editable files.
- **The file contents are *not* injected.** The split agent reads the target file itself (like the unit agents), so `args` stays small — passing the whole file through `args` was the large-payload failure mode. `source-sha` (`git hash-object`) hashes that same on-disk file, so provenance matches what every agent actually read.

# /lr:dev-ula-file — ULA single-file pass (BETA)

> **Audience note.** This document is the logic of the `/lr:dev-ula-file` skill. Claude runs these steps; the user does not run them manually.
>
> **Runtime dependency (BETA).** Step 4 runs a **dynamic Workflow**. It requires the Claude Code dynamic-workflow runtime to be available in the session. If it is not, either run in a session that has it, or simulate the same orchestration with subagents (one splitter, then one unit-pass agent per unit) — the prompts and schemas are designed to be handed to either.

## Goal

Run a **ULA single-file pass** on one source file: split it into units, and for each unit find potential bugs, generate clean-room test scenarios, and gap-analyse those scenarios against the existing tests. Persist three YAML artifacts per unit into the `<repo>-aiqa` sibling repo.

## Inputs

- **target file** — the file the user pointed at (repo-relative or absolute).

## Procedure

1. **Resolve** the source repo and the target file. Fail clearly if the file does not exist.
2. **Ensure the AIQA repo exists.** Derive `<repo>-aiqa` (sibling of the source repo). If it is missing or not initialized, **invoke `/lr:dev-aiqa-repo-init`** for this source repo (which asks the user before creating). Do not proceed until the `-aiqa` repo exists.
3. **Prepare workflow inputs:**
   - Read the target file's contents.
   - Detect its `language` (from extension / content).
   - Read the prompt files from `${CLAUDE_PLUGIN_ROOT}/dev/aiqa/prompts/` into the `prompts` object using **exactly these keys** (the workflow reads `prompts.<key>` and throws if any is missing):

     | file | key |
     |---|---|
     | `split.md` | `split` |
     | `unit-pass-preamble.md` | `preamble` |
     | `step-a-find-bugs.md` | `stepA` |
     | `step-b-generate-scenarios.md` | `stepB` |
     | `step-c-gap-analysis.md` | `stepC` |

   - Read the schema files from `${CLAUDE_PLUGIN_ROOT}/dev/aiqa/schemas/` into the `schemas` object with keys `{ units, bugs, scenarios, gap }` (from `units.schema.json`, `bugs.schema.json`, `scenarios.schema.json`, `gap.schema.json`).
4. **Run the workflow** `${CLAUDE_PLUGIN_ROOT}/dev/aiqa/workflows/ula-file-pass.js` with:
   ```js
   args = {
     filePath,                 // repo-relative path of the target file
     fileContents,             // full source
     language,                 // e.g. "swift"
     sourceRepoPath,           // absolute path to the source repo (agents read neighbours/tests from here)
     prompts,                  // { split, preamble, stepA, stepB, stepC } — md text
     schemas,                  // { units, bugs, scenarios, gap } — parsed JSON Schema
   }
   ```
   The workflow returns, per unit, a schema-validated `{ bugs, scenarios, gap }` (each a full artifact object, including its `unit`/`signature` header).
5. **Persist artifacts** (this skill owns IO — the workflow writes nothing). The workflow returns `{ results: [{ bugs, scenarios, gap }], dropped: [<unit-slug>, …] }`; each artifact carries its own `unit` slug + `signature` header. For each result, write into the `-aiqa` repo, serialized as YAML, using **the artifact's own `unit` slug** as `<unit-slug>` (not an array index):
   ```
   <repo>-aiqa/ula/<target-file-path>/<unit-slug>/bugs.yaml
   <repo>-aiqa/ula/<target-file-path>/<unit-slug>/scenarios.yaml
   <repo>-aiqa/ula/<target-file-path>/<unit-slug>/gap.yaml
   ```
   Create directories as needed.
6. **Report** a summary to the user: units found, total potential bugs, and the gap headline per unit (`ulaNotImplemented` / `ulaMissed` out of totals). Mention where the artifacts were written. **If `dropped` is non-empty, list those unit slugs** — they produced no usable result and were skipped.

## Notes

- **Resumability (coarse, for now).** We deliberately do not store source SHAs or line ranges. A future revision may add a per-unit input hash so unchanged units can be skipped on re-run; until then, re-running re-analyses and overwrites.
- **Persistence is the skill's job**, not the workflow's — keeps the workflow pure-compute and easy to test.
- **Why prompts/schemas are injected via `args`:** the workflow runtime has no filesystem access, so this skill loads the `prompts/` and `schemas/` files and passes their contents in. This is what keeps the prompts as separate, independently-editable files.

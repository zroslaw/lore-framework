Framework docs use placeholders that an agent substitutes at runtime (e.g., when executing a migration). Placeholder names carry semantics — confusing names cause wrong substitutions, especially in multi-repo domains.

Defined in `lore-framework/docs/conventions.md`, section **Placeholder Vocabulary**.

## Problem before v5

Docs mixed `<repo>`, `<repo-path>`, `<agent-repo>` inconsistently. Two real failure modes:

1. **Ambiguity with unrelated domain repos.** A domain may contain a product codebase, a docs site, vendor repos — any number of git repos besides the lore agent repo. A placeholder named `<repo>` is too generic; an agent reading the doc could plausibly substitute the wrong one.
2. **Single-repo assumption.** `<repo>` quietly implies exactly one, making multi-lore-agent-repo domains a corner case rather than a first-class shape.

## v5 vocabulary

- `<lore-agent-repo>` — an agent repo being operated on (contains `lore-repo.md` at its root)
- `<guest-lore-agent-repo>` — the repo of a guest agent, when `/lr:attach` crosses a repo boundary
- `<agent-name>` — kebab-case directory under `agents/`
- `<domain>` — parent directory containing all repos
- `${CLAUDE_PLUGIN_ROOT}` — literal; resolved by Claude Code to the installed plugin path

## Core principle: placeholder is a slot, not an identity

`<lore-agent-repo>` is a binding resolved per invocation. If a domain has multiple lore agent repos, the framework iterates — each iteration resolves the placeholder to a different repo independently. Docs describe what the framework does **to a single repo** using the placeholder; outer iteration lives in process docs (`/lr:check` scans all `lore-repo.md`s and invokes per-repo steps; `/lr:update` walks each repo's migrations).

Practical consequence: a migration doc uses `<lore-agent-repo>` as a singular slot. The migration is run once per repo. Migration docs don't have to handle multi-repo iteration themselves — that's the update process's job.

## Frozen-template exception

`migrations/2.md` contains frozen v1 template text with the old `<repo>` placeholder preserved. Those are not emission templates — they're content-matching patterns used for divergence detection against historical files. Do **not** rewrite them to the new vocabulary; they must match bytes that already exist on user machines.

## Applied changes (v5)

All framework docs updated to the unified vocabulary. Skill `argument-hint` frontmatter for `create-repo`, `register-repo`, `unregister-repo` updated. `attach.md` subagent prompt uses `<guest-lore-agent-repo>`.

Any new framework doc must use these names.

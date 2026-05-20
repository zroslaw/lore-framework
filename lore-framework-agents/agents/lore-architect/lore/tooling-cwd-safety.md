Bash, Glob, Grep, and Read share the same process working directory. A `cd <subdir>` inside a Bash call silently shifts the CWD for every *later* tool call — including Glob patterns you think are relative to the domain root. This has bitten lore-architect operations more than once.

## The failure mode

`cd lore-agents && git status --porcelain` in a Bash call moves CWD to `lore-agents/`. A subsequent `Glob("lore-framework/migrations/4.md")` then resolves against `lore-agents/lore-framework/...` — which doesn't exist — and returns empty. The natural inference is "file missing" or "framework broken". Neither is true.

## Prescription

- **Never `cd` in Bash** if any downstream tool call depends on CWD. Use `git -C <lore-agent-repo> …` for git. Absolute paths for Glob/Grep/Read when working across repos.
- **When a Glob returns empty for a file you expect**, the first hypothesis is wrong CWD, not missing file. Verify with `pwd` before drawing conclusions.
- **Framework bugs are rare, tool-state drift is common.** When diagnosing a boot failure, confirm the symptom on disk with an absolute-path `ls` before blaming the framework.

## Codification in framework

v5 added the **Tooling: CWD Safety** section to `lore-framework/docs/conventions.md`, and converted every `git …` in framework docs (`update.md`, `version-check.md`, `check.md`, `lore-search.md`) to `git -C <lore-agent-repo> …`. Checks 13 and 14 of `/lr:check` use the same form.

Any new framework doc touching filesystems across repo boundaries must follow the same pattern. If you catch yourself writing `cd <repo> && git …`, replace it with `git -C <repo> …` unless a later step genuinely needs that CWD for an unrelated tool.

## Scope

This is a domain-specific operational rule for agents that work across multiple sibling repos in a single domain — the entire reason lore-architect exists. Agents scoped to a single repo can ignore it.

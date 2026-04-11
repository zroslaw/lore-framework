# Consistency Checks

Work through the following checks in order. Report each issue found. At the end, print a summary: total issues found, or "All checks passed" if none.

---

## 1. Agent repo discovery

Scan all directories in the working directory for lore agent repos — directories containing a `lore-repo.md` file at the root. If no agent repos are found, flag it: no lore agent repos exist in this domain.

## 2. lore-repo.md validation

For each repo found in step 1, verify that `lore-repo.md` has valid YAML frontmatter containing:
- `description` — a non-empty string
- `version` — a non-empty string

Report any repos with missing or malformed frontmatter fields.

## 3. Framework version consistency (repo level)

Read the framework version from `${CLAUDE_PLUGIN_ROOT}/VERSION`. For each repo, compare the `version` field in `lore-repo.md` frontmatter against the framework version. Report any mismatches as **warnings** — the repo may need migration.

## 4. Agent discovery

For each repo found in step 1, scan `agents/` for agent directories (subdirectories containing `role.md`). Report any repo that has `lore-repo.md` but no agents as **informational**.

## 5. role.md frontmatter validation

For every agent found in step 4, verify that `role.md` has valid YAML frontmatter containing:
- `description` — a non-empty string

Report any agents with missing or malformed frontmatter fields.

Note: `role.md` does not carry a `version` field at framework version 2+. Agent-level version stamping was removed — only `lore-repo.md` tracks the framework version, one per repo. If a `version` field is present in `role.md`, flag it as **informational** — the repo likely predates migration 2 and can be reconciled with `/lr:update`.

## 6. Agent discovery vs registration

For each agent found in step 4, check whether a boot command `lr-<agent-name>-agent.md` exists in `.claude/commands/`. Report any agents without a registered boot command as **informational** (registration is optional — agents are always loadable via `/lr:boot`).

Conversely, for every `lr-*-agent.md` boot command in `.claude/commands/`, verify the agent directory it references actually exists. Report any boot commands pointing to missing agent directories as **errors**.

## 7. Boot command link validity

For every `lr-*-agent.md` in `.claude/commands/`, extract all file paths referenced in the command. Verify each path resolves to an existing file. Report any broken paths.

## 8. Agent directory structure

For every agent found in step 4, verify the directory contains all required files and directories:
- `role.md`
- `lore-context.md`
- `lore/` directory
- `workdir/` directory

Report any missing components.

## 9. lore-context.md topic references

For every agent, read `lore-context.md` and extract any lore topic filenames referenced (e.g. `topic-name.md`). Verify each referenced file exists in the agent's `lore/` directory. Report any broken references.

## 10. Lore topic cross-references

For every `.md` file in each agent's `lore/` directory, extract any `.md` filenames referenced in the content. Verify each referenced file exists in the same `lore/` directory. Report any broken references.

## 11. lore-context.md size

For every agent, check the size of `lore-context.md`. Warn if it exceeds 40K tokens (approaching the 50K limit) or flag as a violation if it exceeds 50K tokens.

## 12. Pending reflections

For every agent directory, check if a `reflections/` directory exists and is non-empty. If so, flag it: reflection has been run but merge has not — lore is not yet up to date.

## 13. Uncommitted changes in lore files

For every agent repo, run `git status` to detect any lore files that are modified but not committed. Flag these: the knowledge exists only on the local filesystem and is not preserved in git history. This is especially critical for `lore-context.md`, `role.md`, and any `lore/` topic files.

## 14. lore-context.md staleness (git timestamps)

For every agent, use `git log -1 --format=%ci` to get the last commit date of `lore-context.md` and of each lore topic in `lore/`. If any topic was committed more recently than `lore-context.md`, flag it: the summary may not reflect the latest state of that topic. List the topic name and how far out of date the summary is.

## 15. lore-context.md semantic consistency

For every agent, for each lore topic referenced in `lore-context.md`: read the topic file and compare its heading (first `#` line) and opening sentence against what `lore-context.md` says about it. Flag any cases where the topic's actual title or subject clearly differs from the description in lore-context — this indicates the summary was not updated after the topic was substantially revised.

## 16. Boot command description vs role.md

For every `lr-*-agent.md` boot command, compare git last commit date of the boot command file against the last commit date of the agent's `role.md`. If `role.md` was updated more recently, flag it: the boot command may not accurately describe the agent's current role. Also do a quick semantic check: verify the agent name in the boot command matches the heading in `role.md`.

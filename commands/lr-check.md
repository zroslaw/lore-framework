Check the domain, lore framework, and all agent repos for consistency.

**Important:** "`.claude/commands/`" throughout this command refers to the domain directory's `.claude/commands/` folder (sibling to `lore-framework/`), **not** the global `~/.claude/commands/`. Use the domain directory as the root for all relative paths.

Work through the following checks in order. Report each issue found. At the end, print a summary: total issues found, or "All checks passed" if none.

---

## 1. Framework command sync

For every `.md` file in `lore-framework/commands/`, verify an identically-named file exists in `.claude/commands/` and that its content matches. Report any missing or diverged files.

## 2. CLAUDE.md command table completeness

Read `lore-framework/CLAUDE.md`. For every command listed in the Commands table, verify a corresponding file exists in `lore-framework/commands/`. Report any commands listed but missing from the templates directory, and any template files not listed in the table.

## 3. Agent discovery vs registration

Scan all sibling repos in the domain directory for agent directories (directories containing `role.md` and `lore-context.md`). For each agent found, verify a boot command `lr-<agent-name>-agent.md` exists in `.claude/commands/`. Report any agents without a boot command.

Conversely, for every `lr-*-agent.md` boot command in `.claude/commands/`, verify the agent directory it references actually exists. Report any boot commands pointing to missing agent directories.

## 4. Boot command link validity

For every `lr-*-agent.md` in `.claude/commands/`, extract all file paths referenced in the command (lines like `` `path/to/file.md` ``). Verify each path resolves to an existing file in the domain directory. Report any broken paths.

## 5. Agent directory structure

For every agent found in step 3, verify the directory contains all required files and directories:
- `role.md`
- `lore-context.md`
- `lore/` directory
- `workdir/` directory

Report any missing components.

## 6. lore-context.md topic references

For every agent, read `lore-context.md` and extract any lore topic filenames referenced (e.g. `topic-name.md`). Verify each referenced file exists in the agent's `lore/` directory. Report any broken references.

## 7. Lore topic cross-references

For every `.md` file in each agent's `lore/` directory, extract any `.md` filenames referenced in the content. Verify each referenced file exists in the same `lore/` directory. Report any broken references.

## 8. lore-context.md size

For every agent, check the size of `lore-context.md`. Warn if it exceeds 8K tokens (approaching the 10K limit) or flag as a violation if it exceeds 10K tokens.

## 9. Pending reflections

For every agent directory, check if a `reflections/` directory exists and is non-empty. If so, flag it: reflection has been run but merge has not — lore is not yet up to date.

## 10. Agent repo README

For every agent repo found in the domain, verify a `README.md` exists at the repo root. Report any repos missing a README.

---

## 11. Uncommitted changes in lore files

For every agent repo and for `lore-framework/`, run `git status` to detect any lore files that are modified but not committed. Flag these: the knowledge exists only on the local filesystem and is not preserved in git history. This is especially critical for `lore-context.md`, `role.md`, and any `lore/` topic files.

## 12. lore-context.md staleness (git timestamps)

For every agent, use `git log -1 --format=%ci` to get the last commit date of `lore-context.md` and of each lore topic in `lore/`. If any topic was committed more recently than `lore-context.md`, flag it: the summary may not reflect the latest state of that topic. List the topic name and how far out of date the summary is (time delta between commits).

## 13. Installed command staleness (git timestamps)

For every framework command template in `lore-framework/commands/`, compare its last git commit date against the last git commit date of the corresponding installed file in `.claude/commands/`. If the template was updated more recently than the installed copy, flag it as potentially out of sync (content check in step 1 is definitive, but timestamp here provides directional context for which side changed).

## 14. lore-context.md semantic consistency

For every agent, for each lore topic referenced in `lore-context.md`: read the topic file and compare its heading (first `#` line) and opening sentence against what `lore-context.md` says about it. Flag any cases where the topic's actual title or subject clearly differs from the description in lore-context — this indicates the summary was not updated after the topic was substantially revised.

## 15. CLAUDE.md command descriptions vs command files

Read `lore-framework/CLAUDE.md`. For each command in the table, compare its listed purpose description against the first line of the corresponding command template file. Flag any significant divergence — the table entry may be stale relative to what the command actually does.

## 16. Boot command description vs role.md

For every `lr-*-agent.md` boot command, compare git last commit date of the boot command file against the last commit date of the agent's `role.md`. If `role.md` was updated more recently, flag it: the boot command may not accurately describe the agent's current role. Also do a quick semantic check: verify the agent name in the boot command matches the heading in `role.md`.

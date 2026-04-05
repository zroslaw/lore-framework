Check the domain, lore framework, and all agent repos for consistency.

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

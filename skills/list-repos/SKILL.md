---
description: "Show which lore agent repos are available here, what each one covers, and whether any direct shortcuts exist."
---

`<framework-root>` is the framework root — the directory that contains the `VERSION` file, two levels up from this `skills/list-repos/SKILL.md`. Resolve it to an absolute path before using it below.

List all lore agent repos in this workspace.

Scan all directories in the working directory for lore agent repos — directories containing a `lore-repo.md` file at the root.

For each repo found:
- Read the `description` and `version` fields from `lore-repo.md` YAML frontmatter.
- Count the agents it contains (subdirectories under `agents/` with `role.md`).
- Check whether it has any registered engine-native per-agent shortcuts (`.claude/commands/`,
  `.cursor/skills/`, or `~/.codex/skills/`, depending on the current engine).

Output a table: **Repo**, **Agents**, **Version**, **Registered**, **Description**.

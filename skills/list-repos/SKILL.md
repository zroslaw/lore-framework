---
description: "List all agent repos in this domain with their purpose."
---

List all lore agent repos in this domain.

Scan all directories in the working directory for lore agent repos — directories containing a `lore-repo.md` file at the root.

For each repo found:
- Read the `description` and `version` fields from `lore-repo.md` YAML frontmatter.
- Count the agents it contains (subdirectories under `agents/` with `role.md`).
- Check whether it's registered (has boot commands in `.claude/commands/`).

Output a table: **Repo**, **Agents**, **Version**, **Registered**, **Description**.

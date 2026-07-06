---
name: lr-list-repos
description: "List all agent repos in this domain with their purpose."
---

`<framework-root>` is the framework root — the directory that contains the `VERSION` file, three levels up from this `skills/cursor/lr-list-repos/SKILL.md`. Resolve it to an absolute path before using it below.

List all lore agent repos in this domain.

Scan all directories in the working directory for lore agent repos — directories containing a `lore-repo.md` file at the root.

For each repo found:
- Read the `description` and `version` fields from `lore-repo.md` YAML frontmatter.
- Count the agents it contains (subdirectories under `agents/` with `role.md`).
- Check whether it's registered (has engine-native per-agent shortcuts).

Output a table: **Repo**, **Agents**, **Version**, **Registered**, **Description**.

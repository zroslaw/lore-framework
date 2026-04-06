---
description: "List all agent repos in this domain with their purpose."
---

List all lore agent repos in this domain.

Scan all directories in the working directory for agent repos — directories containing an `agents/` subdirectory with at least one agent (a subdirectory containing `role.md`).

For each repo found:
- Count the agents it contains.
- Read `README.md` (if present) for a description.
- Check whether it's registered (has boot commands in `.claude/commands/`).

Output a table: **Repo**, **Agents**, **Registered**, **Purpose**.

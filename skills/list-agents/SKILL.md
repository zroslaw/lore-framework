---
description: "List all agents in this domain with their repo and purpose."
---

`<framework-root>` is the framework root — the directory that contains the `VERSION` file, two levels up from this `skills/list-agents/SKILL.md`. Resolve it to an absolute path before using it below.

List all lore agents available in this domain.

**Method 1 — From shortcut commands (if any exist):**
Check `.claude/commands/` for `lr-*-agent.md` files. Each encodes an agent name (e.g., `lr-lore-architect-agent.md` -> agent `lore-architect`).

**Method 2 — From directory scan (always):**
Scan all directories in the working directory for lore agent repos (containing `lore-repo.md` at the root). Within each, find agent directories under `agents/` (containing `role.md`).

Combine both methods, deduplicating. For each agent found:
- Read the `description` field from `role.md` YAML frontmatter for the agent's purpose.
- Note which repo it belongs to.
- Note whether it has a shortcut command.

Output a table: **Agent**, **Repo**, **Registered**, **Purpose**.

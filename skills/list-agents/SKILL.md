---
description: "List all agents in this domain with their repo and purpose."
---

List all lore agents available in this domain.

**Method 1 — From registered commands (if any exist):**
Check `.claude/commands/` for `lr-*-agent.md` files. Each encodes an agent name (e.g., `lr-lore-architect-agent.md` -> agent `lore-architect`) and contains the path to its role.md.

**Method 2 — From directory scan (always):**
Scan all directories in the working directory for agent repos (containing `agents/`). Within each, find agent directories (containing `role.md`).

Combine both methods, deduplicating. For each agent found:
- Read `role.md` to extract a one-line purpose (first paragraph after heading).
- Note which repo it belongs to.
- Note whether it has a registered boot command.

Output a table: **Agent**, **Repo**, **Registered**, **Purpose**.

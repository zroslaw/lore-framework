---
name: lr-list-agents
description: "List all agents in this domain with their repo and purpose."
---

`<framework-root>` is the framework root — the directory that contains the `VERSION` file, two levels up from this `.cursor-skills/lr-list-agents/SKILL.md`. Resolve it to an absolute path before using it below.

List all lore agents available in this domain.

**Method 1 — From registered shortcuts (if any exist):**
Check the engine-native shortcut location:

- **Claude Code:** `.claude/commands/` for `lr-*-agent.md`
- **Codex:** `~/.codex/skills/` for `lr-*-agent/` directories containing `SKILL.md`

Each encodes an agent name (e.g., `lr-lore-architect-agent` -> agent `lore-architect`).

**Method 2 — From directory scan (always):**
Scan all directories in the working directory for lore agent repos (containing `lore-repo.md` at the root). Within each, find agent directories under `agents/` (containing `role.md`).

Combine both methods, deduplicating. For each agent found:
- Read the `description` field from `role.md` YAML frontmatter for the agent's purpose.
- Note which repo it belongs to.
- Note whether it has a registered shortcut.

Output a table: **Agent**, **Repo**, **Registered**, **Purpose**.

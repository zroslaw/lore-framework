---
name: lr-list-agents
description: "Show which lore agents are available here, what each one covers, and whether it has a direct shortcut."
---

`<framework-root>` is the framework root — the directory that contains the `VERSION` file, two levels up from this `.cursor-skills/lr-list-agents/SKILL.md`. Resolve it to an absolute path before using it below.

## Step 0 — Announce

Print this to the user before doing anything else, filling in any `<placeholder>`:

> Listing every agent available in this workspace — its name, which lore agent repo it lives in,
> what it covers, and whether it has a shortcut. **An agent without a shortcut still works**: any
> agent can be started with `/lr:boot <agent-name>`, so a missing shortcut means it was never
> registered here, not that the agent is unusable.

List all lore agents available in this workspace.

**Method 1 — From registered shortcuts (if any exist):**
Check the engine-native shortcut location:

- **Claude Code:** `.claude/commands/` for `lr-*-agent.md`
- **Cursor:** `.cursor/skills/` for `lr-*-agent/` directories containing `SKILL.md`
- **Codex:** `.codex/skills/` for `lr-*-agent/` directories containing `SKILL.md` (also `~/.codex/skills/`, the pre-v37 location Codex still loads)

Each encodes an agent name (e.g., `lr-lore-architect-agent` -> agent `lore-architect`).

**Method 2 — From directory scan (always):**
Scan all directories in the working directory for lore agent repos (containing `lore-repo.md` at the root). Within each, find agent directories under `agents/` (containing `role.md`).

Combine both methods, deduplicating. For each agent found:
- Read the `description` field from `role.md` YAML frontmatter for the agent's purpose.
- Note which repo it belongs to.
- Note whether it has a registered shortcut.
- Prefer the repo/role metadata as the source of truth if a shortcut description disagrees.

Output a table: **Agent**, **Repo**, **Registered**, **Purpose**.

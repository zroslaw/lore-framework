---
name: lr-list-repos
description: "Show which lore agent repos are available here, what each one covers, and whether any direct shortcuts exist."
---

`<framework-root>` is the framework root — the directory that contains the `VERSION` file, two levels up from this `.cursor-skills/lr-list-repos/SKILL.md`. Resolve it to an absolute path before using it below.

## Step 0 — Announce

Print this to the user before doing anything else, filling in any `<placeholder>`:

> Listing the **lore agent repos** in this workspace — how many agents each holds, what it covers,
> and which framework version it carries. Ordinary source repos aren't listed here; only the ones
> holding agents. **That version stamp is how the framework knows whether a repo needs migrating**,
> which is what `/lr:update` acts on.

List all lore agent repos in this workspace.

Scan all directories in the working directory for lore agent repos — directories containing a `lore-repo.md` file at the root.

For each repo found:
- Read the `description` and `version` fields from `lore-repo.md` YAML frontmatter.
- Count the agents it contains (subdirectories under `agents/` with `role.md`).
- Check whether it has any registered engine-native per-agent shortcuts (`.claude/commands/`,
  `.cursor/skills/`, or `.codex/skills/` — plus `~/.codex/skills/`, the pre-v37 Codex location).

Output a table: **Repo**, **Agents**, **Version**, **Registered**, **Description**.

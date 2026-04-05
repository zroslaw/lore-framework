# Register / Unregister Agent Repo

## Register

Register an existing agent repo so its agents become available as slash commands.

**Input:** repo directory name (e.g., `my-agents`)

### Steps

1. **Verify** the repo exists as a sibling of `lore-framework/` and contains an `agents/` directory.

2. **Scan** `<repo>/agents/` for agent directories. A valid agent directory contains at least a `role.md` file.

3. **For each agent found**, create a command file at `.claude/commands/lr-<agent-name>-agent.md` with the following content:

   ```
   Read the following files and load yourself as the <Agent Name> agent:

   1. `lore-framework/docs/agent-boot.md` — how to operate as a lore agent
   2. `<repo>/agents/<agent-name>/role.md` — your role and identity
   3. `<repo>/agents/<agent-name>/lore-context.md` — your compacted working knowledge

   After reading all three files, confirm you are loaded as <Agent Name> and briefly state your role and what you know.
   ```

4. **Check for name collisions** — if a command file already exists for an agent name from a different repo, warn the user and skip that agent. Do not overwrite.

5. **Report** what was registered: list agent names and the commands created.

## Unregister

Remove all agent commands associated with a repo.

**Input:** repo directory name

### Steps

1. **Scan** `.claude/commands/` for `lr-*-agent.md` files whose content references the given repo path.

2. **Delete** those command files.

3. **Report** what was removed.

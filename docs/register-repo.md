# Register / Unregister Agent Repo

## Register

Register an existing agent repo so its agents get per-agent boot commands in `.claude/commands/`.

This is **optional** — agents can always be loaded via `/lr:boot <agent-name>`. Registration adds convenience commands like `/lr-<agent-name>-agent` that work without the plugin.

**Input:** repo directory name (e.g., `my-agents`)

### Steps

1. **Verify** the repo exists in the current working directory and contains a `lore-repo.md` file at the root (confirming it is a lore agent repo).

2. **Scan** `<repo>/agents/` for agent directories. A valid agent directory contains at least a `role.md` file.

3. **For each agent found**, create a command file at `.claude/commands/lr-<agent-name>-agent.md` with the following content:

   ```
   Read the following files and load yourself as the <Agent Name> agent:

   1. `<repo>/agents/<agent-name>/role.md` — your role and identity
   2. `<repo>/agents/<agent-name>/lore-context.md` — your compacted working knowledge

   After reading both files, confirm you are loaded as <Agent Name> and briefly state your role and what you know.

   ## Operating as a Lore Agent

   - Your lore is in `<repo>/agents/<agent-name>/lore/` — search it before making assumptions about things from previous sessions
   - Your workspace is `<repo>/agents/<agent-name>/workdir/`
   - You have access to the entire domain directory — all sibling repos and data
   - At session end, if the user triggers finalization: `/lr:reflect` then `/lr:merge` (or `/lr:finalize` for both)
   - Do not finalize unless the user explicitly triggers it
   - For full operating instructions, see the lr plugin (`/lr:boot`)
   ```

   Replace `<Agent Name>` with the title-cased agent name and `<agent-name>` with the kebab-case directory name.

4. **Check for name collisions** — if a command file already exists for an agent name from a different repo, warn the user and skip that agent. Do not overwrite.

5. **Report** what was registered: list agent names and the commands created.

## Unregister

Remove all agent commands associated with a repo.

**Input:** repo directory name

### Steps

1. **Scan** `.claude/commands/` for `lr-*-agent.md` files whose content references the given repo path.

2. **Delete** those command files.

3. **Report** what was removed.

# Register / Unregister Agent Repo

## Register

Register an existing agent repo so its agents get per-agent boot commands in `.claude/commands/`.

This is **optional** — agents can always be loaded via `/lr:boot <agent-name>`. Registration adds convenience commands like `/lr-<agent-name>-agent`.

**Input:** repo directory name (e.g., `my-agents`)

### Steps

1. **Verify** the repo exists in the current working directory and contains a `lore-repo.md` file at the root (confirming it is a lore agent repo).

2. **Scan** `<lore-agent-repo>/agents/` for agent directories. A valid agent directory contains at least a `role.md` file.

3. **For each agent found**, create a command file at `.claude/commands/lr-<agent-name>-agent.md` with the following one-line content:

   ```
   Read `${CLAUDE_PLUGIN_ROOT}/docs/agent-boot.md` and boot as agent `<agent-name>`.
   ```

   Replace `<agent-name>` with the kebab-case directory name. `${CLAUDE_PLUGIN_ROOT}` is resolved at runtime by Claude Code to the install path of the `lr` plugin — do not hardcode the path.

   **Design note:** the generated command is a one-line delegation — just a pointer to `agent-boot.md` and the agent name. All boot logic (discovery, file loading, confirmation) and operating instructions live in `agent-boot.md` (single source of truth). Never inline boot steps or operating guidance into generated commands; update `agent-boot.md` instead.

4. **Check for name collisions** — if a command file already exists for an agent name from a different repo, warn the user and skip that agent. Do not overwrite.

5. **Report** what was registered: list agent names and the commands created.

## Unregister

Remove all agent commands associated with a repo.

**Input:** repo directory name

### Steps

1. **Scan** `.claude/commands/` for `lr-*-agent.md` files whose content references the given repo path.

2. **Delete** those command files.

3. **Report** what was removed.

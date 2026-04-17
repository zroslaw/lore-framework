# Register / Unregister Agent Repo

## Register

Register an existing agent repo so its agents get **shortcut commands** in `.claude/commands/`.

This is **optional** — agents can always be loaded via `/lr:boot <agent-name>`. Registration adds shortcut commands like `/lr-<agent-name>-agent` that boot faster by providing absolute paths (skipping agent discovery).

**Input:** repo directory name (e.g., `my-agents`)

### Steps

1. **Verify** the repo exists in the current working directory and contains a `lore-repo.md` file at the root (confirming it is a lore agent repo).

2. **Scan** `<lore-agent-repo>/agents/` for agent directories. A valid agent directory contains at least a `role.md` file.

3. **Resolve absolute paths** for use in the generated shortcut commands:
   - **`<agent-boot-path>`** — the absolute path to `agent-boot.md` in the same `docs/` directory as this file. Derive it from the path you used to read this file.
   - **`<agent-dir>`** — the absolute path to `<lore-agent-repo>/agents/<agent-name>/`.

4. **For each agent found**, create a shortcut command file at `.claude/commands/lr-<agent-name>-agent.md` with the following one-line content:

   ```
   Read `<agent-boot-path>` and boot as agent `<agent-name>` from `<agent-dir>`.
   ```

   Replace all three placeholders with the resolved values from step 3.

   **Design note:** shortcut commands are one-line delegations with absolute paths — a pointer to `agent-boot.md`, the agent name, and the agent directory. The absolute paths let boot skip discovery (faster startup). All boot logic and operating instructions live in `agent-boot.md` (single source of truth). Never inline boot steps or operating guidance into shortcut commands; update `agent-boot.md` instead.

5. **Check for name collisions** — if a command file already exists for an agent name from a different repo, warn the user and skip that agent. Do not overwrite.

6. **Report** what was registered: list agent names and the shortcut commands created.

## Unregister

Remove all shortcut commands associated with a repo.

**Input:** repo directory name

### Steps

1. **Scan** `.claude/commands/` for `lr-*-agent.md` files whose content contains `boot as agent`. For each, check if the absolute agent directory path in the command (the `from <agent-dir>` part) falls under the given repo. If there is no `from` clause (legacy format), extract the agent name from the filename and check if that agent exists in the given repo's `agents/` directory.

2. **Delete** matching shortcut command files.

3. **Report** what was removed.

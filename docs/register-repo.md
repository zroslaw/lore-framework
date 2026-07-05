# Register / Unregister Agent Repo

## Register

Register an existing agent repo so its agents get **shortcut boot artifacts** for the current engine.

This is **optional** — agents can always be loaded via `/lr:boot <agent-name>`. Registration adds faster per-agent shortcuts that provide absolute paths and skip agent discovery.

- On **Claude Code**, registration creates shortcut commands in `.claude/commands/` like `/lr-<agent-name>-agent`.
- On **Codex**, registration creates **personal skills** in `~/.codex/skills/` like `$lr-<agent-name>-agent`.

Use the current engine profile (`<framework-root>/docs/engines/<engine>.md`, selected at boot) to decide which artifact to generate.

**Input:** repo directory name (e.g., `my-agents`)

### Steps

1. **Verify** the repo exists in the current working directory and contains a `lore-repo.md` file at the root (confirming it is a lore agent repo).

2. **Scan** `<lore-agent-repo>/agents/` for agent directories. A valid agent directory contains at least a `role.md` file.

3. **Resolve absolute paths** for use in the generated shortcut artifacts:
   - **`<agent-boot-path>`** — the absolute path to `agent-boot.md` in the same `docs/` directory as this file. Derive it from the path you used to read this file.
   - **`<agent-dir>`** — the absolute path to `<lore-agent-repo>/agents/<agent-name>/`.

4. **For each agent found**, create the engine-native shortcut artifact with the following one-line content:

   ```
   Read `<agent-boot-path>` and boot as agent `<agent-name>` from `<agent-dir>`.
   ```

   Replace all three placeholders with the resolved values from step 3.

   Write it to the engine-native location:

   - **Claude Code:** `.claude/commands/lr-<agent-name>-agent.md`
   - **Codex:** `~/.codex/skills/lr-<agent-name>-agent/SKILL.md`

   **Design note:** these artifacts are one-line delegations with absolute paths — a pointer to `agent-boot.md`, the agent name, and the agent directory. The absolute paths let boot skip discovery (faster startup). All boot logic and operating instructions live in `agent-boot.md` (single source of truth). Never inline boot steps or operating guidance into the generated artifact; update `agent-boot.md` instead.

5. **Check for name collisions** — if the target artifact already exists for an agent name from a different repo, warn the user and skip that agent. Do not overwrite.

6. **Report** what was registered: list agent names and the shortcuts created.

   Report them in the engine-native form:

   - **Claude Code:** `/lr-<agent-name>-agent`
   - **Codex:** `$lr-<agent-name>-agent`

## Unregister

Remove all shortcut artifacts associated with a repo.

**Input:** repo directory name

### Steps

1. **Scan** the engine-native shortcut location:

   - **Claude Code:** `.claude/commands/` for `lr-*-agent.md`
   - **Codex:** `~/.codex/skills/` for directories `lr-*-agent/` containing `SKILL.md`

   For each artifact whose content contains `boot as agent`, check whether the absolute agent directory path in the content (the `from <agent-dir>` part) falls under the given repo. If there is no `from` clause (legacy format), extract the agent name from the filename or skill directory name and check if that agent exists in the given repo's `agents/` directory.

2. **Delete** matching shortcut artifacts.

   - **Claude Code:** delete the matching `.md` files.
   - **Codex:** delete the matching skill directories.

3. **Report** what was removed.

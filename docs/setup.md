# Framework Setup

Install the lore framework into the current domain directory.

## Prerequisites

- `lore-framework/` exists in the domain directory
- You are working from the domain directory root

## Steps

1. **Identify the domain directory** — it is the parent directory of `lore-framework/`.

2. **Create `.claude/commands/`** in the domain directory if it doesn't exist.

3. **Copy all command files** from `lore-framework/commands/` into `.claude/commands/`. Overwrite existing framework commands (those starting with `lr-`) but do NOT remove agent commands (`lr-*-agent.md`) — those are managed by the register/unregister process.

4. **Confirm** what was set up: list the commands that were installed.

## Re-running Setup

Setup is idempotent. Re-running it updates framework commands to the latest version without affecting agent commands. This is how users pick up framework updates after pulling new changes to `lore-framework/`.

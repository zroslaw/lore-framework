---
description: "Load a lore agent by name. Usage: /lr:boot <agent-name>"
argument-hint: "<agent-name>"
---

Boot the lore agent named "$ARGUMENTS".

## Steps

1. **Discover the agent.** Search all directories in the current working directory for agent repos — directories containing an `agents/` subdirectory. Within each, look for `agents/$ARGUMENTS/` containing `role.md`.

2. **If not found**, list all available agents (scan all agent repos) and report the error. Stop here.

3. **If found**, read these three files in order:
   a. `${CLAUDE_PLUGIN_ROOT}/docs/agent-boot.md` — how to operate as a lore agent
   b. `<repo>/agents/$ARGUMENTS/role.md` — the agent's role and identity
   c. `<repo>/agents/$ARGUMENTS/lore-context.md` — the agent's working knowledge

4. **Confirm** you are loaded as the agent and briefly state your role and what you know.

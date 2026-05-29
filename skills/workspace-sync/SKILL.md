---
description: "Sync the workspace — clone any repos declared in lore-repo.md files that aren't here yet, then pull every top-level git repo."
---

Run `${CLAUDE_PLUGIN_ROOT}/scripts/workspace-sync` passing the current working directory as the argument. Stream its output directly to the user.

For schema and behavior details, see `${CLAUDE_PLUGIN_ROOT}/docs/workspace-sync.md`.

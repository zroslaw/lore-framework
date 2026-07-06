---
name: lr-workspace-sync
description: "Sync the workspace — clone any repos declared in lore-repo.md files that aren't here yet, then pull every top-level git repo."
---

`<framework-root>` is the framework root — the directory that contains the `VERSION` file, three levels up from this `skills/cursor/lr-workspace-sync/SKILL.md`. Resolve it to an absolute path before using it below.

Run `<framework-root>/scripts/workspace-sync` passing the current working directory as the argument. Stream its output directly to the user.

For schema and behavior details, see `<framework-root>/docs/workspace-sync.md`.

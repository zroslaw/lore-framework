---
description: "Initialize a lore workspace, or converge an initialized one back to disk reality — lore-workspace.md, optional git root and remote, .gitignore, README, and the framework-managed sections of AGENTS.md (plus the CLAUDE.md import stub)."
---

`<framework-root>` is the framework root — the directory that contains the `VERSION` file, two levels up from this `skills/workspace-init/SKILL.md`. Resolve it to an absolute path before using it below.

Read `<framework-root>/docs/workspace-init.md` and execute the workspace-init process in the current working directory. Pass through `--dry-run` if the user supplied it. `--refresh` and `--reconfigure` are retired — if the user supplied either, the doc says what to print and to proceed normally.

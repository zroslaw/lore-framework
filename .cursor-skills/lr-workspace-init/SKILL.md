---
name: lr-workspace-init
description: "Initialize or converge a Lore workspace, including its AI routing map of repos and agents, canonical descriptions, managed workspace files, and optional confirmed publication."
---

`<framework-root>` is the framework root — the directory that contains the `VERSION` file, two levels up from this `.cursor-skills/lr-workspace-init/SKILL.md`. Resolve it to an absolute path before using it below.

Read `<framework-root>/docs/workspace-init.md` and execute the workspace-init process in the current working directory. Pass through `--dry-run` if the user supplied it. `--refresh` and `--reconfigure` are retired — if the user supplied either, the doc says what to print and to proceed normally.

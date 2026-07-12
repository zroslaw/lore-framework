---
name: lr-workspace-init
description: "Bootstrap or refresh a lore workspace — set up lore-workspace.md, optional git root, README, and the framework-managed section in the workspace memory file (`CLAUDE.md` on Claude Code, `AGENTS.md` on Codex/Cursor)."
---

`<framework-root>` is the framework root — the directory that contains the `VERSION` file, two levels up from this `.cursor-skills/lr-workspace-init/SKILL.md`. Resolve it to an absolute path before using it below.

Read `<framework-root>/docs/workspace-init.md` and execute the workspace-init process in the current working directory. Pass through any flag the user supplied (`--refresh`, `--reconfigure`).

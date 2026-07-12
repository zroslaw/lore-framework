---
name: lr-workspace-pull
description: "Pull fresh workspace state — pull the workspace repo, clone repos declared in lore-workspace.md and lore-repo.md files that aren't here yet, then pull every top-level git repo."
---

`<framework-root>` is the framework root — the directory that contains the `VERSION` file, two levels up from this `.cursor-skills/lr-workspace-pull/SKILL.md`. Resolve it to an absolute path before using it below.

Run `<framework-root>/scripts/workspace-pull` passing the current working directory as the argument. Stream its output directly to the user.

For schema and behavior details, see `<framework-root>/docs/workspace-pull.md`.

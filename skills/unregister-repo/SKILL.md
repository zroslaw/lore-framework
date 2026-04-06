---
description: "Remove all agent commands for an agent repo. Usage: /lr:unregister-repo <repo-name>"
argument-hint: "<repo-name>"
---

Remove all registered agent commands associated with the repo: $ARGUMENTS

## Steps

1. Scan `.claude/commands/` for `lr-*-agent.md` files whose content references the given repo path.
2. Delete those command files.
3. Report what was removed.

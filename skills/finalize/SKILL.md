---
description: "Full session finalization — reflect then merge. Run at end of session."
---

Run the full finalization process for the current session. If guests are attached via `/lr:attach`, both reflect and merge iterate per active agent in host-first order — see the referenced docs for the iteration mechanics.

**Step 1 — Reflect:**
Read `${CLAUDE_PLUGIN_ROOT}/docs/process-reflection.md` for instructions. Review this session and extract knowledge worth preserving into reflection topics in each active agent's `reflections/` directory.

**Step 2 — Merge:**
Read `${CLAUDE_PLUGIN_ROOT}/docs/process-merge.md` for instructions. Integrate each active agent's reflections into that agent's `lore/`, `lore-context.md`, and `role.md` as appropriate. Clean up `reflections/` and commit per agent.

When done, confirm what was reflected and merged for each active agent.

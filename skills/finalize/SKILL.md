---
description: "Full session finalization — reflect then merge. Run at end of session."
---

Run the full finalization process for the current session.

**Step 1 — Reflect:**
Read `${CLAUDE_PLUGIN_ROOT}/docs/process-reflection.md` for instructions. Review this session and extract knowledge worth preserving into reflection topics in your agent's `reflections/` directory.

**Step 2 — Merge:**
Read `${CLAUDE_PLUGIN_ROOT}/docs/process-merge.md` for instructions. Integrate all reflection topics into your `lore/`, `lore-context.md`, and `role.md` as appropriate. Clean up `reflections/` and commit.

When done, confirm what was reflected and merged.

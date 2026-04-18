---
description: "Full session finalization — reflect, merge, then summarize. Run at end of session."
---

Run the full finalization process for the current session. If guests are attached via `/lr:attach`, reflect and merge iterate per active agent in host-first order — see the referenced docs for the iteration mechanics. Summarize runs once, session-wide.

**Step 1 — Reflect:**
Read `${CLAUDE_PLUGIN_ROOT}/docs/process-reflection.md` for instructions. Review this session and extract knowledge worth preserving into reflection topics in each active agent's `reflections/` directory.

**Step 2 — Merge:**
Read `${CLAUDE_PLUGIN_ROOT}/docs/process-merge.md` for instructions. Integrate each active agent's reflections into that agent's `lore/`, `lore-context.md`, and `role.md` as appropriate. Clean up `reflections/` and commit per agent.

**Step 3 — Summarize:**
Read `${CLAUDE_PLUGIN_ROOT}/docs/summarize.md` for instructions. Write a session-wide summary into the host agent's `sessions/YYYY/MM/` directory and emit the session UUID so it can be correlated later with the Claude Code JSONL on the user's machine. Summarize runs once per session regardless of attached guests, and is additive — its failure does not roll back reflect or merge.

When done, confirm what was reflected, merged, and summarized — list active agents for reflect/merge and the summary path + UUID for the session as a whole.

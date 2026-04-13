---
description: "Extract session knowledge into reflection topics. Run at end of session."
---

Begin the reflection process for the current session.

Read `${CLAUDE_PLUGIN_ROOT}/docs/process-reflection.md` for detailed instructions. The doc explains single-agent and multi-agent (attached-guests) iteration — if guests are attached via `/lr:attach`, reflection runs per active agent, host first.

Review this session and extract knowledge worth preserving into reflection topics in the appropriate `reflections/` directory for each active agent.

When done, confirm that reflection is complete for each active agent and list the topics created.

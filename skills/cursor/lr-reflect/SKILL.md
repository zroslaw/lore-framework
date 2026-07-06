---
name: lr-reflect
description: "Extract session knowledge into reflection topics. Run at end of session."
---

`<framework-root>` is the framework root — the directory that contains the `VERSION` file, three levels up from this `skills/cursor/lr-reflect/SKILL.md`. Resolve it to an absolute path before using it below.

Begin the reflection process for the current session.

Read `<framework-root>/docs/process-reflection.md` for detailed instructions. The doc explains single-agent and multi-agent (attached-guests) iteration — if guests are attached via `/lr:attach`, reflection runs per active agent, host first.

Review this session and extract knowledge worth preserving into reflection topics in the appropriate `reflections/` directory for each active agent.

When done, confirm that reflection is complete for each active agent and list the topics created.

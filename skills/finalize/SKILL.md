---
description: "Full session finalization — reflect, merge, summarize, then commit and push. Run at end of session."
argument-hint: "[--transcript]"
---

`<framework-root>` is the framework root — the directory that contains the `VERSION` file, two levels up from this `skills/finalize/SKILL.md`. Resolve it to an absolute path before using it below.

Begin the full finalization process. `--transcript` selects transcript-backed reflection; no flag keeps the standard reflection path.

Read `<framework-root>/docs/finalize.md` for detailed instructions. The doc orchestrates reflect → merge → summarize → commit and push, explains per-phase failure handling, and details the commit review gate.

When done, confirm what was reflected, merged, summarized, and committed — list active agents for reflect/merge, the summary path + UUID, and the commit SHA(s) pushed.

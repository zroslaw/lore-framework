---
name: lr-summarize
description: "Write a committable markdown summary of the session. Run as the final step of finalization."
---

`<framework-root>` is the framework root — the directory that contains the `VERSION` file, three levels up from this `skills/cursor/lr-summarize/SKILL.md`. Resolve it to an absolute path before using it below.

Begin the session summarization process.

Read `<framework-root>/docs/summarize.md` for detailed instructions. The doc explains the summary file layout, frontmatter schema, narrative prompt, review gate, and UUID echo discipline.

The summary is session-wide (one file per session, regardless of attached guests) and is written into the host agent's `sessions/YYYY/MM/` directory. When done, confirm the summary was written (or explicitly skipped) and emit the session UUID in the user-visible output so it can later be correlated with the Claude Code JSONL on the user's machine.

---
description: "Write a committable markdown summary of the session. Run as the final step of finalization."
---

Begin the session summarization process.

Read `${CLAUDE_PLUGIN_ROOT}/docs/summarize.md` for detailed instructions. The doc explains the summary file layout, frontmatter schema, narrative prompt, review gate, and UUID echo discipline.

The summary is session-wide (one file per session, regardless of attached guests) and is written into the host agent's `sessions/YYYY/MM/` directory. When done, confirm the summary was written (or explicitly skipped) and emit the session UUID in the user-visible output so it can later be correlated with the Claude Code JSONL on the user's machine.

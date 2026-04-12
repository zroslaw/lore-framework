# Lore Recall

This skill is invoked by the user mid-session when they want the loaded agent to pull lore context relevant to the current work into its working memory.

## Usage

- `/lr:recall` — contextual: the agent uses the current session/task as the search brief
- `/lr:recall <hint>` — targeted: the agent centers the brief on the user's hint (e.g. `/lr:recall anything about versioning`)

## Procedure

### 1. Verify an agent is loaded

If no lore agent is loaded in the current session, respond: `No agent loaded. Run /lr:boot <agent-name> first.` and stop.

### 2. Verify the agent has lore

If the loaded agent's `lore/` directory does not exist or contains no topic files, respond: `<agent-name> has no lore topics to recall from yet.` and stop.

### 3. Prepare a search brief

Follow the four-part brief structure described in `${CLAUDE_PLUGIN_ROOT}/docs/lore-search.md`:

1. **The task** — what you're actively working on this session
2. **Session context** — decisions made, constraints, paths being touched, open questions
3. **The angle** — the user's hint if provided, otherwise the kind of lore that would help
4. **The output shape** — compact synthesis (≤400 words), topic filenames, flagged reads

Keep the brief under ~300 words.

### 4. Dispatch the subagent

Use the `Explore` subagent with the brief. Pass the absolute path to the loaded agent's `lore/` directory.

### 5. Present the result

- **Show the synthesis to the user.** Transparency: they should see what got pulled in and judge whether the recall was useful. Light formatting is fine; do not silently rephrase the substance.
- **Read flagged topics in full** if the synthesis called any out as worth reading. Do this yourself, in your main context.
- **Carry the recalled context** as working memory for the rest of the session.
- **If nothing relevant was found**, say so explicitly: `Nothing relevant in lore for this task.` Do not fabricate findings.

## Read-Only

`/lr:recall` never modifies lore files. If the recall surfaces knowledge gaps, contradictions, or things worth recording, those become reflection topics during the next finalization (`/lr:reflect` or `/lr:finalize`) — not in-place edits during recall.

## See Also

- `${CLAUDE_PLUGIN_ROOT}/docs/lore-search.md` — search brief structure, worked example, and the agent-initiated search pattern (same mechanism, different trigger)

# Lore Recall

This skill is invoked by the user mid-session when they want the loaded agent to pull lore context relevant to the current work into its working memory.

## Usage

- `/lr:recall` — contextual: the agent uses the current session/task as the search brief
- `/lr:recall <hint>` — targeted: the agent centers the brief on the user's hint (e.g. `/lr:recall anything about versioning`)

## Procedure

### 1. Verify an agent is loaded

If no lore agent is loaded in the current session, respond: `No agent loaded. Run /lr:boot <agent-name> first.` and stop.

### 2. Determine the active agents

Recall searches the lore of every **active** agent — the host plus any guests attached via `/lr:attach`. Enumerate them from the session conversation:

- Host: whichever agent was booted via `/lr:boot` or a `/lr-<name>-agent` shortcut command
- Guests: each agent confirmed as attached by a prior `/lr:attach` in this session (detach is not supported in v1; once attached, they remain active)

If an active agent has no `lore/` directory or no topic files, skip it silently. If no active agent has any lore to search, respond: `No lore to recall from — active agents have empty lore directories.` and stop.

### 3. Prepare a search brief

Follow the four-part brief structure described in `${CLAUDE_PLUGIN_ROOT}/docs/lore-search.md`:

1. **The task** — what you're actively working on this session
2. **Session context** — decisions made, constraints, paths being touched, open questions
3. **The angle** — the user's hint if provided, otherwise the kind of lore that would help
4. **The output shape** — compact synthesis (≤400 words), topic filenames, flagged reads

Keep the brief under ~300 words. The same brief is used for every active agent — each subagent is just told which `lore/` directory is theirs.

### 4. Dispatch subagents in parallel — one per active agent

Dispatch **one `Explore` subagent per active agent, all in a single message** (parallel execution — there are no dependencies between them). Each subagent receives:

- The same brief from Step 3
- A line identifying which agent's lore it is scanning (`agent: <name>`)
- The absolute path to that agent's `lore/` directory

When there's only the host and no guests, this reduces to a single subagent dispatch — unchanged from prior behavior.

### 5. Present the result

- **Show the syntheses to the user.** If multiple active agents were scanned, group results by agent so the user can see whose lore each finding came from. Transparency matters — the user judges whether the recall was useful. Light formatting is fine; do not silently rephrase the substance.
- **Read flagged topics in full** if any synthesis called them out as worth reading. Do this yourself, in your main context.
- **Carry the recalled context** as working memory for the rest of the session.
- **If nothing relevant was found across all active agents**, say so explicitly: `Nothing relevant in lore for this task.` Do not fabricate findings.

## Read-Only

`/lr:recall` never modifies lore files. If the recall surfaces knowledge gaps, contradictions, or things worth recording, those become reflection topics during the next finalization (`/lr:reflect` or `/lr:finalize`) — not in-place edits during recall.

## See Also

- `${CLAUDE_PLUGIN_ROOT}/docs/lore-search.md` — search brief structure, worked example, fan-out mechanics, and the agent-initiated search pattern (same mechanism, different trigger)
- `${CLAUDE_PLUGIN_ROOT}/docs/attach.md` — loading another agent so its lore participates in recall
- `${CLAUDE_PLUGIN_ROOT}/docs/consult.md` — one-shot question to an *unloaded* agent (recall does not cover consulted agents — they are never loaded)

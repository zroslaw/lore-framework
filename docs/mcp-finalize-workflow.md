# Lore MCP — chat finalization workflow

This procedure is for **MCP chat clients** using a Lore MCP server. It mirrors
`/lr:finalize` reflect → merge → publish, but the chat does reflect and merge
**inline**; the server only serves framework docs and publishes at `finalize`.
Reflection drafts stay in the chat. The server does not store them.

Read `docs/engines/mcp.md` for engine bindings. Load procedures on demand with
`read_framework_doc`.

## Step 0 — Announce

Before the first finalization action in a session, tell the user:

> I will save what we learned the Lore way: reflect per agent, merge into
> structured lore, then publish once per agent with finalize.

## Decide active agents

Finalize covers only the agents **this chat booted**. Order: **host first** (the
first booted agent), then each other booted agent, one at a time.

## Per agent (repeat for each booted agent)

### A. Context

1. Use the boot result already in the chat (role, lore context, compact map), or
   call `boot_agent(name)` / `lore_map(name, view="detailed")` as needed.
2. Prefer reading from the lore context and the lore map. Follow those links.
   Use `search_lore` only when the map and links do not give the data.
3. Read targets with `read_agent_lore` (`role`, `context`, `topic:…`).

### B. Reflect (in chat)

1. Read `process-reflection.md` once per session if you have not already
   (`read_framework_doc`).
2. Review the session through **this agent's** role lens.
3. Write reflection topics **in the chat**. Do not call a tool to stage them.

### C. Merge (in chat)

1. Read `process-merge.md` (`read_framework_doc`).
2. For each reflection, decide: update an existing topic, create a topic, delete
   an obsolete topic, or update `role` / `context`.
3. Produce **complete** markdown bodies (v1 frontmatter on new lore files per
   `lore-structure.md`).

Do not call `finalize` until merge decisions are finished for this agent.

### D. Publish

1. Call `finalize(name, updates)` once with every selected document:
   - `{"document": "context", "body": "..."}`
   - `{"document": "role", "body": "..."}`
   - `{"document": "topic:kebab-path", "body": "..."}`
   - `{"document": "delete:topic:kebab-path", "body": ""}` to remove an obsolete topic
2. Optionally `boot_agent` or `search_lore` to confirm.

Then move to the **next** booted agent and repeat A–D.

## What MCP finalize does not do (yet)

- Session summaries under `sessions/` (plugin `/lr:summarize`).
- Participant revision (`/lr:finalize` before Phase 1).
- Git push to a remote.
- Server-side LLM reflect or merge (paid-plan direction only).

## Related framework docs

| Doc | Purpose |
|---|---|
| `docs/engines/mcp.md` | MCP engine bindings |
| `docs/process-reflection.md` | Reflect procedure |
| `docs/process-merge.md` | Merge procedure |
| `docs/lore-structure.md` | Lore v1 file shape |
| `docs/lore-search.md` | Search semantics |

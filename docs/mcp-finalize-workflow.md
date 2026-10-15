# Lore MCP — chat finalization workflow

This procedure is for **MCP chat clients** using a Lore MCP server. It mirrors
`/lr:finalize` reflect → merge → publish, but the chat does reflect and merge
**inline**; the server only stages reflections, serves framework docs, and
publishes at `finalize`.

Read `docs/engines/mcp.md` for engine bindings. Load procedures on demand with
`read_framework_doc`.

## Step 0 — Announce

Before the first finalization action in a session, tell the user:

> I will save what we learned the Lore way: reflect per agent, merge into
> structured lore, then publish once per agent with finalize.

## Decide active agents

List who learned something this session:

1. Call `list_agents` if needed.
2. Include every agent whose role scope covers durable knowledge from this
   session. Order: **host agent first** (the agent the user mainly worked with),
   then each other agent, one at a time.

MCP has no `/lr:attach`. You choose the set explicitly.

## Per agent (repeat for each active agent)

### A. Boot context

1. `boot_agent(name)` — role and compact `lore_context`.
2. `lore_map(name, view="boot")` — taxonomy map for merge navigation.
3. Use `search_lore` and `read_agent_lore` for existing topics you may update.

### B. Reflect (staging)

1. Read `process-reflection.md` once per session if you have not already
   (`read_framework_doc`).
2. Review the session through **this agent's** role lens.
3. For each durable reflection topic, call `write_reflections` with kebab-case
   slugs (for example `api-retry-behavior`, `role-update-deployment-ownership`).
4. Confirm staging with `read_agent_lore(name, document="reflections")`.

Reflections are **not** published lore until merge and finalize complete.

### C. Merge (in chat)

1. Read `process-merge.md` (`read_framework_doc`).
2. For each staged reflection, decide: update existing topic, create topic,
   delete obsolete topic, or update `role` / `context` per the merge doc.
3. Read targets with `read_agent_lore` (`role`, `context`, `topic:…`,
   `reflection:…`).
4. Produce **complete** markdown bodies (v1 frontmatter on new lore files per
   `lore-structure.md`).

Do not call `finalize` until merge decisions are finished for this agent.

### D. Publish

1. Call `finalize(name, updates)` once with every selected document:
   `{"document": "context", "body": "..."}` and
   `{"document": "topic:kebab-path", "body": "..."}`.
2. On success, the server clears `reflections/` for that agent.
3. Optionally `boot_agent` or `search_lore` to confirm.

Then move to the **next** active agent and repeat A–D.

## What MCP finalize does not do (yet)

- Session summaries under `sessions/` (plugin `/lr:summarize`).
- Participant revision (`/lr:finalize` before Phase 1).
- Git push to a remote.
- Server-side LLM reflect or merge (paid-plan direction only).

## Related framework docs

| Doc | Purpose |
|---|---|
| `process-reflection.md` | What to extract; reflection file rules |
| `process-merge.md` | How to integrate into lore |
| `lore-structure.md` | v1 frontmatter and taxonomy |
| `engines/mcp.md` | MCP engine bindings |

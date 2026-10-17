# Engine Profile — Lore MCP (chat client)

Selected when a Lore MCP server session runs framework helpers (`lore_map`,
`read_framework_doc`) with `--engine mcp`, or when the chat client follows
`docs/mcp-finalize-workflow.md`. This profile governs **remote MCP chat
sessions** that persist Lore through MCP tools — not Claude Code, Codex, or
Cursor plugin sessions.

**Where a value here conflicts with a shared procedure doc, this profile wins
for that step.**

## Binding values

| Binding | Value on MCP |
|---|---|
| **framework-root** | The Lore framework tree bundled with the MCP server (`LORE_FRAMEWORK_DIR` on the server). The chat never guesses paths; it calls `read_framework_doc` for allowed procedure files. |
| **invocation-syntax** | **Tools only** — `start_lore_session`, `list_agents`, `boot_agent`, `search_lore`, `lore_map`, `read_framework_doc`, `read_agent_lore`, `finalize`. No slash commands, no plugin cache, no `lr-core` in the chat process. |
| **subagent-spawn** | **Not available.** Reflect and merge run **inline in the chat**, once per booted agent, in host-first order. Do not assume `Task`, Agent Teams, or merge subagents. |
| **memory-file** | **Not applicable** — workspace memory (`AGENTS.md`) is not loaded in the MCP chat unless the connector adds it. Agent scope comes from `boot_agent` and `read_agent_lore`. |
| **runtime-bounding** | Respect MCP tool result size limits. Use `lore_map` with `boot` view first; request detailed view when merging. |

## Capability gates

- **teammate-detection** — not applicable; always a single chat executor.
- **git / push** — the server commits locally at `finalize`; it does not push. The chat must not promise team-visible git until a later product story adds push.
- **parallel merge** — not available; iterate agents **serially**: reflect → merge → `finalize` for agent A, then agent B.

## Reflect and merge on MCP

The server does **not** run an LLM. The chat performs:

1. **Reflect** — follow `docs/process-reflection.md` (read via `read_framework_doc`).
   Keep reflection drafts in the chat. Do not write them to the server.
2. **Merge** — follow `docs/process-merge.md` using `lore_map`, `read_agent_lore`, and
   (rarely) `search_lore`. Prefer the lore context and lore map. Produce complete file
   bodies for `context`, `role`, and each affected `topic:…`.
3. **Finalize** — one `finalize(name, updates)` call per agent with the merged bodies.
   Use `delete:topic:…` with an empty body to remove an obsolete topic.

Orchestration for multi-agent sessions is in `docs/mcp-finalize-workflow.md`.

## Finalize

`finalize` is the only publication action. It atomically commits integrated Lore for
one agent. Reflections are never stored on the server.

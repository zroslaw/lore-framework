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
| **invocation-syntax** | **Tools only** — `boot_agent`, `search_lore`, `lore_map`, `read_framework_doc`, `read_agent_lore`, `write_reflections`, `finalize`. No slash commands, no plugin cache, no `lr-core` in the chat process. |
| **subagent-spawn** | **Not available.** Reflect and merge run **inline in the chat**, once per active agent, in host-first order. Do not assume `Task`, Agent Teams, or merge subagents. |
| **memory-file** | **Not applicable** — workspace memory (`AGENTS.md`) is not loaded in the MCP chat unless the connector adds it. Agent scope comes from `boot_agent` and `read_agent_lore`. |
| **runtime-bounding** | Respect MCP tool result size limits. Use `lore_map` with `boot` view first; request scoped detail only when needed. |

## Capability gates

- **teammate-detection** — not applicable; always a single chat executor.
- **git / push** — the server commits locally at `finalize`; it does not push. The chat must not promise team-visible git until a later product story adds push.
- **parallel merge** — not available; iterate agents **serially**: reflect → stage → merge → `finalize` for agent A, then agent B.

## Reflect and merge on MCP

The server does **not** run an LLM. The chat performs:

1. **Reflect** — follow `docs/process-reflection.md` (read via `read_framework_doc`).
   Write drafts with `write_reflections` (staging under `agents/<name>/reflections/`).
2. **Merge** — follow `docs/process-merge.md` using `lore_map`, `read_agent_lore`, and
   `search_lore`. Produce complete file bodies for `context` and each affected `topic:…`.
3. **Finalize** — one `finalize(name, updates)` call per agent with the merged bodies.

Orchestration for multi-agent sessions is in `docs/mcp-finalize-workflow.md`.

## Finalize

`finalize` is the only publication action. It atomically commits integrated Lore.
After a successful `finalize`, the server clears that agent's `reflections/` staging
directory so abandoned drafts do not accumulate.

# Reflect vs Merge: Execution Asymmetry

Reflect and merge are finalization phases that look symmetric on the surface but have deliberately different execution models:

- **Reflect** runs **inline**, host-first, per active agent. It needs the current session's context — what happened, what the user said, what files were touched. A fresh-booted subagent would not have that context. So the host runs reflection for each agent in turn, using each agent's `role.md` as the scoping lens.

- **Merge** runs in **parallel subagents**, one per active agent, each booted as its target. Merge is file-driven: inputs are `reflections/`, existing `lore/`, `lore-context.md`, and `role.md`. No session context required. Booting gives the subagent the agent's role perspective without the noise of the active session. See `merge-in-booted-subagents.md`.

This asymmetry is called out explicitly in `finalize.md` phases 1 and 2 to prevent "why are these different?" confusion.

## The underlying rule

**Delegate to a booted subagent only when the work is file-driven; keep inline when it needs session context.**

Same rule explains other framework design choices:

- **Summarize runs inline** — the narrative comes from the session's lived experience, not just from files on disk.
- **`/lr:consult` uses a booted subagent** — the consultant answers from its own lore, not the caller's session. Session context is explicitly out of scope.
- **`/lr:recall` fans out to subagents** — lore search is file-driven (grep+read+synthesize). The host's session context only shapes the search brief.
- **`/lr:attach` version reconciliation runs in a subagent** — migration execution is file-driven; session context not needed.

## Practical signals

When designing a new framework operation, ask:

1. **Does this need to reason about what happened in the current session?** → keep it inline in the host.
2. **Can it be done from files alone, given a brief?** → dispatch a subagent. If a perspective-dependent lens is needed (e.g., "filter for what matters to agent X"), have the subagent boot as that agent first.

Both answers can hold for different phases of the same skill — finalize is the canonical example (reflect inline, merge in subagents, summarize inline with per-guest writes).

## Related topics

- `merge-in-booted-subagents.md` — how the merge side of the asymmetry is implemented
- `finalization-process.md` — the four-phase flow that contains both halves
- `consult-pattern.md` — subagent that boots as a target agent
- `lore-search-pattern.md` — file-driven subagent work

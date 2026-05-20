# Merge in Booted Subagents (v8)

Merge always runs in subagents as of v8 — uniform for single-agent and multi-agent sessions. A single-agent session just spawns one subagent.

## Execution model

Each subagent is of type **`general-purpose`** — merge needs `Write`/`Edit`/`Bash`, which `Explore` can't do. The host dispatches one subagent per active agent (host + attached guests) in parallel via a single multi-call message.

Host briefs each subagent to:

1. **Boot as the target agent** per `agent-boot.md` — inherits role + lore-context naturally.
2. Run the merge procedure in `docs/process-merge.md` scoped to itself.
3. Return a short summary of topics touched, role changes, and anomalies.
4. **Not commit** — finalize phase 4 handles that.

## Why boot in the subagent?

Booting gives the subagent the agent's role perspective as a natural lens for merge decisions. Reflections often feel "about the system" in the abstract, but merge decisions are always **scoped to one agent's knowledge**. The role defines what is relevant, what belongs in lore-context vs. a lore topic, and what the agent's voice should sound like. Reading `role.md` + `lore-context.md` gets all of that in one move.

This mirrors the `/lr:consult` pattern (the consult subagent also boots as its target). Consistent mechanism across the two places the framework needs an agent's perspective in a subagent.

## Why parallel?

Each agent writes to its own `agents/<name>/` subtree — no file-level contention. Parallel execution turns multi-agent finalize from O(N) sequential reads of large lore contexts into O(1) wall-clock. For a single-agent session the parallelism is degenerate (one subagent) — the uniformity is a design choice, not a performance claim.

## Retained returns are load-bearing

**The host must retain each subagent's return value through to phase 3.** Summarize composes each guest summary from:

- (a) the host summary just composed
- (b) session memory of what the guest contributed
- (c) **the merge subagent's return for that guest**

If returns are dropped after phase 2, the lore-changes section of each guest summary cannot be reconstructed without re-reading git diffs. Phase 2 and phase 3 are coupled through this handoff.

## Contrast with reflect

Reflect stays inline even in v8 — see `reflect-merge-execution-asymmetry.md`. The underlying rule: delegate to a booted subagent only when the work is file-driven; keep inline when it needs session context.

## Files

- `docs/process-merge.md` — the procedure each subagent runs after booting (Step 1–5)
- `docs/finalize.md` — phase 2 orchestration (host-side)

## Related topics

- `reflect-merge-execution-asymmetry.md` — the design rule for inline-vs-subagent
- `finalization-process.md` — overall four-phase flow
- `consult-pattern.md` — the other place a subagent boots as its target
- `sonnet-subagent-review-pattern.md` — same role-as-lens mechanism applied to pre-publication review of high-stakes lore changes
- `skill-doc-pattern.md` — why merge orchestration lives in `docs/finalize.md`

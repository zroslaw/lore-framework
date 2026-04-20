# Finalization Process

Run the full session finalization: reflect → merge → summarize → commit and push. Triggered by `/lr:finalize` at the end of a session.

This doc orchestrates the four phases. Phases 1–3 are defined in their own process docs — read them as each phase begins. Phase 4 (commit and push) is defined here, since it's orchestration-level logic rather than a reusable subroutine.

## Relationship to the individual skills

Finalize composes three existing skills plus a final commit step:

- `/lr:reflect` alone — phase 1 only, no finalize commit
- `/lr:merge` alone — phase 2 only, no finalize commit
- `/lr:summarize` alone — phase 3 only, no finalize commit
- `/lr:finalize` — all three, then commit and push in phase 4

When a phase is invoked standalone, the user is responsible for committing whatever they want to keep. Finalize is the only path that commits and pushes automatically.

## Phase 1 — Reflect

Read `${CLAUDE_PLUGIN_ROOT}/docs/process-reflection.md` and follow it. Writes reflection topics into each active agent's `reflections/` directory. Reflect runs **inline**, host-first, per active agent — it needs session context (which a fresh-booted subagent wouldn't have), so the iteration stays in the host session. This is intentionally different from phase 2.

## Phase 2 — Merge

Read `${CLAUDE_PLUGIN_ROOT}/docs/process-merge.md` and follow it. Merge runs in a **subagent per active agent, in parallel**; each subagent boots as its target agent and then integrates that agent's reflections into its `lore/`, `lore-context.md`, and `role.md`. Cleans up `reflections/`. **Does not commit** — phase 4 covers it.

Merge is parallelizable precisely because it is file-driven (`reflections/` + `lore/`) and doesn't need session context — the contrast with phase 1.

**Preserve each merge subagent's return value through to phase 3.** Summarize composes each guest summary from (a) the host summary, (b) session memory, and (c) the merge subagent's return for that guest. If the returns aren't retained, phase 3 loses the list of lore changes per guest.

## Phase 3 — Summarize

Read `${CLAUDE_PLUGIN_ROOT}/docs/summarize.md` and follow it. Writes the canonical summary into the host agent's `sessions/YYYY/MM/` directory and — for every attached guest that had lore updates in phase 2 — a short guest summary into the guest's `sessions/YYYY/MM/`. All summaries share the session UUID for JSONL correlation. Summarize is additive — its failure does not roll back reflect or merge.

## Phase 4 — Commit and Push

Collect every repo touched by phases 1–3 — each active agent's repo (for its own lore updates), plus the host's repo (for the canonical summary), plus any guest repo that received a short guest summary from phase 3. When host and guests share a repo, their changes go into a single commit for that repo. Then, for each such repo:

1. `git -C <repo> add agents/` — scoped to the agent tree so incidental untracked files elsewhere are not swept in.
2. `git -C <repo> commit -m "Finalize session <short-uuid>"`.
3. `git -C <repo> push`.

For each repo, print a one-line confirmation (e.g., `✓ <repo>: committed <sha>, pushed to <branch>`). No approval prompt — phase 4 runs end-to-end without user interaction.

### Failure handling

- **Summarize failed** — commit the reflect+merge output alone. Merge output is valuable on its own; don't hold it hostage to the summary.
- **Any merge subagent failed** — do not commit in that repo. Report the failure and let the user resolve before retrying finalize.
- **Push rejected due to conflicts in an agent subtree** — this happens when another user (or parallel session) finalized the same agent concurrently. Trigger the conflict-resolution procedure: read `${CLAUDE_PLUGIN_ROOT}/docs/resolve-conflicts.md` and follow it. One subagent is spawned per conflicted agent; each boots as its agent, reconciles its own subtree, and retries push up to 3 times against concurrent races.
- **Push fails for other reasons** (auth, remote unreachable, conflicts outside agent subtrees) — the commit is already made locally. Report the failure and let the user resolve manually.

### Cross-repo guests

If a guest is attached from a different lore agent repo, phase 2 touches that guest's repo and phase 4 commits there too. The guest also receives a short guest summary in its own repo (see `summarize.md`). Each repo gets its own commit + push.

### Partial push failure across repos

Push order across repos is undefined. If one repo's push succeeds and another's fails (network, auth, conflicts), the public record is momentarily asymmetric — e.g., the host summary is visible while a guest summary isn't yet. The local commits are already made; the user can retry the failed repo's push manually. Do not roll back the successful repos to "restore symmetry" — that would discard work.

## Invariants

- **One commit per touched repo.** Reflect, merge, and summarize output land in a single commit per repo — not split across phases.
- **Fully automated.** Finalize runs end-to-end without approval prompts. Phase 3's summary display in `summarize.md` step 12 is the user's view of what was recorded; git history is the post-hoc review channel.
- **Push is part of finalize.** Standalone reflect/merge/summarize do not push; only `/lr:finalize` does.
- **No empty commits.** If nothing was produced by phases 1–3 in a given repo, skip committing in that repo.

## When to use

Run at the end of a working session. Do not run finalize for a consultation (`/lr:consult` is already ephemeral) or for a session that produced no lore changes and no summary-worthy narrative.

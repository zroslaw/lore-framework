# Push Conflict Resolution (v8)

v8 introduced a push-conflict resolution procedure at `docs/resolve-conflicts.md`. It triggers only when `/lr:finalize` phase 4 push is rejected due to conflicts inside an agent subtree. Typical cause: two users (or parallel sessions) finalize the same agent concurrently.

## Shape

- **One `general-purpose` subagent per conflicted agent, in parallel.** Each boots as its target agent (same pattern as merge — see `merge-in-booted-subagents.md`), then runs fetch → merge → resolve → push scoped to its own subtree.
- **Branch resolved dynamically** inside each subagent: `BRANCH=$(git -C <repo> rev-parse --abbrev-ref HEAD)` then `git merge origin/${BRANCH} --no-ff --no-edit`. Avoids placeholder guesswork and works regardless of the default branch name.
- **Cap: 3 total resolve+push attempts** (first attempt + two retries). Hard cap to avoid infinite loops under heavy concurrent writes.
- **Scope**: lore topics, `lore-context.md`, `role.md` only. Conflicts outside agent subtrees (e.g., `lore-repo.md`, framework files, `sessions/`) or fundamental role redefinitions hand back to the user — automatic resolution would be unsafe.
- **Fetch/merge irrecoverable failures** (divergent history from a force-push, network loss, merge-config error): abort the merge and hand back immediately, do not retry.
- **No force-push, no discard.** If resolution can't succeed, leave local state as-is.

## Resolution content rule

**Reconciliation, not invention.** A subagent must combine both sides' real content, not generate new material to paper over the conflict. When both sides edited the same information differently, the agent's role is the tiebreaker — what does this agent, as defined by its `role.md`, consider authoritative on this topic?

## Invocation model

This procedure is read **only when a conflict occurs**; it is not part of the default finalize flow. The reference to it lives in `finalize.md` phase 4 failure handling. Reading it at conflict-time (not always) keeps the common-path finalize doc focused and avoids loading conflict-resolution content into every finalize invocation.

## Why booted subagents (same as merge)

Same reasoning as `merge-in-booted-subagents.md`: conflict resolution is file-driven (diffs on disk), and the agent's role is the natural lens for "reconcile, not invent." Booting as the target agent gives the subagent that perspective automatically.

## Files

- `docs/resolve-conflicts.md` — the full procedure
- `docs/finalize.md` — phase 4 failure handling (the trigger)

## Related topics

- `merge-in-booted-subagents.md` — same booted-subagent pattern
- `finalization-process.md` — overall four-phase flow and phase 4 failure handling
- `tooling-cwd-safety.md` — why `git -C <repo>` is used instead of `cd`

# Conflict Resolution

This procedure runs only when `/lr:finalize` phase 4 encounters a push rejection caused by remote changes that conflict with the local lore or lore-context changes produced by this session. Read this doc only when such a conflict occurs.

Typical trigger: multiple users (or parallel sessions) finalized for the same agent at the same time, so the remote branch has moved ahead with its own lore updates between the local commit and the push.

## Scope

This procedure handles conflicts on:

- `agents/<agent-name>/lore/**`
- `agents/<agent-name>/lore-context.md`
- `agents/<agent-name>/role.md`

Conflicts in other paths (`sessions/`, `lore-repo.md`, framework files, or anything outside an agent directory) are **not** handled automatically. Report them to the user for manual resolution.

## Execution model

Spawn one **`general-purpose`** subagent per conflicted agent, in parallel (conflict resolution needs `Write`/`Edit`/`Bash`; `Explore` does not). Each subagent boots as its conflicted agent and resolves conflicts scoped to its own subtree. The host aggregates results.

Subagent brief (per conflicted agent):

_"Boot as agent `<name>` (repo: `<path>`) per `${CLAUDE_PLUGIN_ROOT}/docs/agent-boot.md`, then resolve push conflicts for yourself per `${CLAUDE_PLUGIN_ROOT}/docs/resolve-conflicts.md`. Up to 3 total resolve+push attempts before giving up. Return the final commit SHA, or a failure reason if attempts are exhausted."_

## Procedure (per subagent)

### Step 1: Fetch and merge remote

Determine the upstream branch (typically whatever is currently checked out) and merge it:

```bash
git -C <repo> fetch origin
BRANCH=$(git -C <repo> rev-parse --abbrev-ref HEAD)
git -C <repo> merge "origin/${BRANCH}" --no-ff --no-edit
```

If the fetch or merge fails irrecoverably — e.g., divergent history from a force-push, network loss, or a merge configuration error that no file-level resolution can fix — abort the merge (`git -C <repo> merge --abort`) and hand back to the host with the failure reason. Do not retry in this case.

If the merge completes without conflicts, jump to Step 4 (push).

### Step 2: Resolve conflicted files

For each conflicted file within your agent's subtree (`agents/<your-name>/`):

- **Lore topics (`lore/<topic>.md`)** — read both sides. If both sides added distinct information, merge into a single coherent topic that keeps all valid additions. If both sides edited the same information differently, prefer the more specific/correct version using your role as judge. When in genuine doubt, preserve more content rather than lose it.
- **`lore-context.md`** — the typical conflict is both sides inserting different summary entries. Produce a combined version that includes all additions; resolve duplicates by keeping the better-phrased one; respect the size budget (≤50K tokens).
- **`role.md`** — role changes are rare and meaningful. Merge body updates; for the frontmatter `description`, pick the more accurate of the two.

Do not invent content that exists on neither side. The resolution must be a reconciliation of the two inputs, filtered through your role perspective.

### Step 3: Preserve the knowledge graph

After resolving, verify that cross-topic references still point to existing filenames. If the remote side removed a topic the local side references (or vice versa), update the references accordingly.

### Step 4: Commit and push

```bash
git -C <repo> add agents/<your-name>/
git -C <repo> commit -m "Resolve finalize conflict for <your-name>"
git -C <repo> push
```

If push succeeds, return the commit SHA to the host and exit.

### Step 5: Retry on repeated rejection

If `git push` fails again because the remote advanced during resolution, repeat Steps 1–4 against the new remote state.

**Cap: 3 total resolve+push attempts** — i.e., the first resolution attempt, plus two retries. This avoids infinite loops under heavy concurrent writes while giving enough headroom to survive ordinary races.

After 3 exhausted attempts, stop and return to the host with:

- Number of attempts made
- The current local commit SHA
- A short note (e.g., "remote still advancing rapidly — likely many concurrent finalizations in flight")

## Invariants

- **Scoped to own agent.** A subagent resolves only conflicts in `agents/<its-own-name>/`. It does not touch other agents' files even if those are also conflicted — a separate subagent handles each.
- **No content invention.** Resolutions are reconciliations of the two inputs, not new material.
- **Retry cap is hard.** 3 attempts maximum.
- **No force-push, no discard.** If resolution cannot succeed, leave local state as-is and hand back to the user.

## Unresolvable cases

Hand back to the user when:

- Conflicts exist outside agent subtrees (e.g., `lore-repo.md`, framework files)
- `role.md` conflicts look like a fundamental role redefinition rather than a routine body merge — a human decision
- Fetch or merge fails irrecoverably (divergent history from a force-push, network loss, merge-config error)
- Retry budget exhausted

The host aggregates per-agent outcomes — successes, retries-exhausted, and unresolvable cases — and reports them all to the user at the end.

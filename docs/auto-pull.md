# Auto-Pull (Single-Repo Refresh)

> **Audience note.** This is an internal procedure doc — Claude reads it from `agent-boot.md`, `attach.md`, `process-merge.md`, and `pull-lore.md`. There is no `/lr:auto-pull` skill. Users invoke its behavior implicitly via boot/attach/merge or explicitly via `/lr:pull-lore`.

The shared procedure for refreshing one lore agent repo's git state mid-flow. Used by:

- **`agent-boot.md` Step 1** — auto-pull the host repo at boot time (via `lr-core preflight`).
- **`attach.md`** — auto-pull the guest repo before reading its role/lore-context.
- **`process-merge.md` step 0** — defense-in-depth pull right before the merge subagent reads its lore.
- **`docs/pull-lore.md`** — the user-invoked `/lr:pull-lore` skill iterates this procedure across active agents.

The procedure is intentionally narrow: one `git pull --ff-only` against the agent's repo, with safety gates and a degraded-mode failure path. No clone logic (that's `/lr:workspace-pull`), no migration logic (that's `version-check.md`), no commit or push.

## Normative source

**The procedure lives in `pull_repo()`'s own comments in `scripts/lr_core/preflight.py`** (a literate
accelerator, `docs/conventions.md` § Script Fallback Contract) — this doc is a pointer into it,
not a second copy. Boot/attach/consult/merge reach it through `lr-core preflight`, which also adds
a TTL cache on top (a pull that succeeded within the window is reported `fresh` and skipped — see
`_read_stamp`/`_write_stamp` next to `pull_repo`).

**When the script cannot run:** notify the user, then read `pull_repo()`'s docstring in
`scripts/lr_core/preflight.py` and execute **its numbered steps, all of them**, by hand against
`<lore-agent-repo>` — the exact `git` invocations, the runtime bound and why not `timeout`, the
fail-fast env vars, the bare-repo / not-its-own-git-root / no-origin skip cases, and the
git-could-not-answer-is-a-failure-not-a-skip distinction are all spelled out there. Do not trust a
count quoted from memory; read to the end of the docstring, because the last step (writing the TTL
stamp and classifying the outcome) is the one a hurried reader drops. One thing
stays here because it's caller-side policy the script doesn't decide, not implementation detail it
duplicates — how verbose to be about the outcome, below.

## Inputs

- `<lore-agent-repo>` — absolute path to the lore agent repo to refresh.

## Report

The verbosity rule depends on the calling site. Boot/attach/merge are quiet on the no-op case (the common path) so the surrounding flow stays uncluttered; `/lr:pull-lore` is always verbose because it's user-invoked.

| Outcome | Boot / attach / merge | `/lr:pull-lore` |
|---|---|---|
| Already up to date | silent | print `<lore-agent-repo>: already up to date` |
| Fast-forwarded | print `<lore-agent-repo>: pulled <N> commit(s)` | print `<lore-agent-repo>: pulled <N> commit(s)` |
| Fresh (pulled within the TTL window, network skipped) | silent | print `<lore-agent-repo>: already up to date (cached)` |
| Disabled (`--no-pull`) | silent | print `<lore-agent-repo>: skipped — pull disabled` |
| Skipped (not a git repo / bare repo / not its own git root / no origin) | silent | print `<lore-agent-repo>: skipped — <reason>` |
| Failed (non-FF, network, auth, **git could not run**) | print `<lore-agent-repo>: pull failed — <error>` | print `<lore-agent-repo>: pull failed — <error>` |

For the commit count, `git rev-list HEAD@{1}..HEAD --count` works after a fast-forward; if it fails or returns 0 unexpectedly, just print `pulled` without a count.

Never abort the surrounding flow on a pull failure. The agent must always finish booting / attaching / merging even if its repo is momentarily out of sync.

## Worktrees

The lore framework's worktree convention (see `worktrees.md`) keeps top-level repo checkouts on their default branch and pushes feature work into `<workspace>/.worktrees/<repo>/<slug>/`. Auto-pull operates on whichever path was passed in — the path discovered by boot/attach.

- **Booted from a top-level checkout:** auto-pull fast-forwards the default branch as expected. This is the common path.
- **Booted from inside a worktree** (the discovered path resolves under `.worktrees/`): auto-pull runs against that worktree's checkout. If the worktree is on a feature branch with no upstream, or the upstream has diverged, the pull fails with a clear error and the surrounding flow continues in degraded mode. Manage feature-branch updates manually — auto-pull is best-effort.

`/lr:pull-lore` and the boot/attach/merge sites all delegate to this same procedure, so the worktree behavior is uniform.

## Invariants

- **Best-effort.** A pull failure never blocks boot, attach, merge, or any user-visible flow. The surrounding flow continues in degraded mode with a visible warning.
- **No destructive actions.** Never `--force`, never `git reset`, never `git checkout` away from the user's branch. If a fast-forward isn't possible, the failure surfaces and the user resolves manually.
- **Uncommitted changes are preserved.** `--ff-only` either advances `HEAD` cleanly past the dirty tree or refuses with a clear error — both outcomes are safe. Auto-pull never stashes, resets, or otherwise touches the working tree.
- **Per-repo scope.** Auto-pull operates on a single repo at a time, and only on a repo that is the root of its own git repository. A lore repo nested inside a larger git repo is `skipped`, never pulled — `git -C` would otherwise walk up and fast-forward the enclosing repo while the report named the inner one. Multi-repo flows (e.g., `/lr:pull-lore` over host + guests) iterate this procedure per repo.
- **Idempotent.** Running auto-pull twice in a row on a clean repo produces no observable difference past the first run.

## Distinct From

- **`/lr:workspace-pull`** — filesystem-wide: discovers `lore-repo.md` files, clones missing repos declared in `repos:`, pulls every top-level git repo. Auto-pull is single-repo and never clones.
- **`version-check.md`** — repo-version reconciliation: applies migrations and stamps `lore-repo.md` after a framework `VERSION` bump. Auto-pull is git-only and never modifies file contents.
- **`resolve-conflicts.md`** — finalize-time merge of remote conflicts in agent subtrees. Triggered only when push is rejected; auto-pull is the *prevention* arm of the same problem.

The three sit on a spectrum: auto-pull keeps the local repo fresh (so the rest of the flow reads current data); `/lr:workspace-pull` keeps the workspace fresh (so all repos are present and up to date); resolve-conflicts heals after a concurrent finalize collided. They compose without overlap.

## See Also

- `pull-lore.md` — the `/lr:pull-lore` skill that user-invokes this procedure mid-session.
- `agent-boot.md` — boot-time invocation site.
- `attach.md` — guest-attach invocation site.
- `process-merge.md` — pre-merge invocation site (defense-in-depth atop boot pull).
- `workspace-pull.md` — workspace-wide companion.
- `conventions.md` § Tooling: CWD Safety — why `git -C <repo>` instead of `cd`.

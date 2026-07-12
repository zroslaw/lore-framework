# Auto-Pull (Single-Repo Refresh)

> **Audience note.** This is an internal procedure doc — Claude reads it from `agent-boot.md`, `attach.md`, `process-merge.md`, and `pull-lore.md`. There is no `/lr:auto-pull` skill. Users invoke its behavior implicitly via boot/attach/merge or explicitly via `/lr:pull-lore`.

The shared procedure for refreshing one lore agent repo's git state mid-flow. Used by:

- **`agent-boot.md` step 2** — auto-pull the host repo at boot time.
- **`attach.md`** — auto-pull the guest repo before reading its role/lore-context.
- **`process-merge.md` step 0** — defense-in-depth pull right before the merge subagent reads its lore.
- **`docs/pull-lore.md`** — the user-invoked `/lr:pull-lore` skill iterates this procedure across active agents.

The procedure is intentionally narrow: one `git pull --ff-only` against the agent's repo, with safety gates and a degraded-mode failure path. No clone logic (that's `/lr:workspace-pull`), no migration logic (that's `version-check.md`), no commit or push.

## Inputs

- `<lore-agent-repo>` — absolute path to the lore agent repo to refresh.

## Procedure

Run all git invocations with `git -C <lore-agent-repo> ...` — never `cd` into the repo (other tools share the shell working directory; see `conventions.md` § Tooling: CWD Safety).

### Step 1: Skip non-git or remote-less repos

Run `git -C <lore-agent-repo> rev-parse --is-inside-work-tree`. If it fails (not a git repo), skip with a one-line note: `<lore-agent-repo>: not a git repo — skipping auto-pull` and return successfully (the rest of the flow continues in degraded mode).

Run `git -C <lore-agent-repo> remote get-url origin`. If it fails (no `origin` remote configured), skip with: `<lore-agent-repo>: no origin remote — skipping auto-pull` and return successfully.

These are not failures — they're legitimate states (e.g., a brand-new local-only agent repo, or an unusual remote layout). Auto-pull simply has nothing to do.

### Step 2: Pull

Run `GIT_TERMINAL_PROMPT=0 git -C <lore-agent-repo> pull --ff-only`, bounded to roughly 60 seconds.

> **Engine note.** The bounding mechanism below is Claude Code's Bash-tool timeout. On other engines, follow your profile's **runtime-bounding** binding (`docs/engines/<engine>.md`) — e.g. on Codex there is no Bash-tool timeout flag; the sandbox / `job_max_runtime_seconds` bounds it, and the "set the Bash-tool timeout" prose is ignored.

**Apply the timeout via your Bash tool's own timeout parameter — do *not* wrap the command in a `timeout`/`gtimeout` binary.** Those are GNU coreutils tools, absent by default on macOS/BSD (the primary dev platform); `timeout 60 git …` fails with `command not found` (exit 127), which aborts the pull and drops boot into degraded mode for an entirely spurious reason — silently disabling auto-pull on every macOS boot. See `conventions.md` § Tooling: Portable Shell.

The **Bash-tool timeout is the transport-agnostic backstop** — it kills any stall (SSH, HTTPS, or a future remote type) so boot can never hang indefinitely, however the remote authenticates. The env vars below are per-transport *fast-fail* niceties layered on top, so a stall errors out in seconds rather than waiting out the full timeout:

- **`GIT_TERMINAL_PROMPT=0`** — stops Git prompting on the terminal for **HTTP(S)** credentials, so an HTTPS pull without cached credentials fails fast (~0.5s) instead of blocking on a username prompt. It governs only Git's *own* terminal prompt — a separate GUI credential helper (e.g. Git Credential Manager) or the `ssh` binary is unaffected and falls to the backstop.
- **`GIT_SSH_COMMAND='ssh -o BatchMode=yes -o ConnectTimeout=10'`** (**SSH** only) — `BatchMode=yes` turns an unknown host key or passphrase prompt into an immediate failure; `ConnectTimeout` bounds the TCP connect. No effect on HTTPS remotes.
- *(optional, **HTTPS**)* add `-c http.lowSpeedLimit=1000 -c http.lowSpeedTime=15` **before the `pull` subcommand** (e.g. `git -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=15 -C <lore-agent-repo> pull --ff-only`) — aborts a connected-but-stalled transfer after ~15s under ~1 KB/s, the rough analog of SSH's `ConnectTimeout`. The backstop already covers this case; add it only if you want a faster, cleaner abort.
- **`--ff-only`** ensures divergent local branches surface as failures rather than producing silent merge commits.

**Why we don't gate on a dirty working tree:** `git pull --ff-only` is non-writing in spirit — it advances `HEAD`, but it refuses cleanly if the fast-forward would clobber any uncommitted edits in the working tree. So uncommitted edits are either preserved through the pull or the pull fails with a clear error. Either outcome is safe. Gating on dirty would defeat the most useful invocation site (pre-merge auto-pull, where `reflections/` from phase 1 is intentionally uncommitted).

This is **different** from the version-check upgrade gate (`docs/version-check.md`), which *does* refuse on dirty — because version-check *writes* to `lore-repo.md`. Auto-pull doesn't write to file contents.

### Step 3: Report

The verbosity rule depends on the calling site. Boot/attach/merge are quiet on the no-op case (the common path) so the surrounding flow stays uncluttered; `/lr:pull-lore` is always verbose because it's user-invoked.

| Outcome | Boot / attach / merge | `/lr:pull-lore` |
|---|---|---|
| Already up to date | silent | print `<lore-agent-repo>: already up to date` |
| Fast-forwarded | print `<lore-agent-repo>: pulled <N> commit(s)` | print `<lore-agent-repo>: pulled <N> commit(s)` |
| Skipped (not a git repo / no origin) | silent | print `<lore-agent-repo>: skipped — <reason>` |
| Failed (non-FF, network, auth) | print `<lore-agent-repo>: pull failed — <error>` | print `<lore-agent-repo>: pull failed — <error>` |

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
- **Per-repo scope.** Auto-pull operates on a single repo at a time. Multi-repo flows (e.g., `/lr:pull-lore` over host + guests) iterate this procedure per repo.
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

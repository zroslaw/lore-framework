# /lr:pull-lore

Pull the latest lore from each active agent's repo, mid-session.

Use this when you suspect another contributor (or a parallel session, or your own work in another worktree) pushed lore, role, or workdir changes between your boot and now. Boot already auto-pulls; `/lr:pull-lore` is the manual force-refresh between boots.

> **"Active agents" = the host you booted with `/lr:boot` plus any guests attached via `/lr:attach`.** See `attach.md` for the host/guest model.

> **Why two steps (pull, then re-read)?** A `git pull` updates files on disk, but Claude's working context still holds the *pre-pull* copies of `role.md` and `lore-context.md`. Without an explicit re-read, the freshly pulled lore is on disk but not in working memory. `/lr:pull-lore` does both — pull then re-read.

> **When to run.** Before a long planning conversation, after a teammate says "I just pushed updates to the agent's lore," or before invoking `/lr:reflect` on a session that touched many topics.

## What It Does

1. **Enumerates active agents** — host (whichever agent was booted) plus any guests attached via `/lr:attach`.
2. **Auto-pulls each agent's repo** — runs `lr-core preflight --fresh` per repo, which executes the procedure in `pull_repo()`'s comments in `scripts/lr_core/preflight.py` (`<framework-root>/docs/auto-pull.md` carries the reporting policy). When two active agents share a repo, that repo is pulled once.
3. **Re-reads each active agent's `role.md` and `lore-context.md`** — so any changes pulled in actually take effect in working memory. Without this step, the pulled files are on disk but the host is still operating from the pre-pull context.
4. **Reports a one-line summary per repo** — pulled / already up to date / failed / skipped (no origin, not a git repo, or not the root of its own git repo), so the user can see what changed.

`/lr:pull-lore` does not run `/lr:workspace-pull` — that's a separate workspace-wide tool. `/lr:pull-lore` is scoped narrowly to the agents currently loaded.

## Usage

```
/lr:pull-lore
```

No arguments. The skill always operates on the full set of active agents. Expected output shape:

```
Pulled 2 repo(s):
  ✓ activities-domain: pulled 3 commit(s)
  ✓ booking-engine-domain: already up to date

Re-read context for 2 active agent(s): activities-supply, booking-engine.
```

## Procedure

### Step 1: Verify an agent is loaded

If no lore agent is loaded in the current session, respond: `No agent loaded. Run /lr:boot <agent-name> first.` and stop.

### Step 2: Enumerate active agents

From the session conversation:

- **Host** — whichever agent was booted via `/lr:boot` or a registered per-agent shortcut.
- **Guests** — any agents confirmed as attached by prior `/lr:attach` commands in this session (no detach in v1; once attached, they remain active).

Resolve each active agent's `<lore-agent-repo>` path. Deduplicate repos: if host and a guest live in the same repo, pull that repo once.

### Step 3: Auto-pull each repo

For each unique repo, run:

```
python3 "<framework-root>/scripts/lr-core" preflight --agent-dir "<agent-dir>" --fresh --no-teammate-check
```

Bound **each** of these calls at **at least 180 seconds** via your engine profile's runtime-bounding binding — the per-repo calls dispatch in parallel below, and every one of them needs its own headroom. Keep the substituted values quoted as shown. See `<framework-root>/docs/conventions.md` § Script Fallback Contract, *Invoking one*.

`<agent-dir>` is **any one** active agent's directory inside that repo — the script derives the repo root from it, so when a host and a guest share a repo either directory produces the same pull. Pick the first and move on.

`--fresh` is mandatory here: it bypasses the TTL cache so an explicit user-invoked refresh always hits the network. Read `data.pull` from the JSON for the outcome. If the script fails to complete, apply the **Script Fallback Contract** (`<framework-root>/docs/conventions.md`) and read `pull_repo`'s comments in `<framework-root>/scripts/lr_core/preflight.py` (`docs/auto-pull.md` points to the same place) to run the pull scoped to that repo by hand.

Print verbose output (one line per repo, even on `already up to date`) — `/lr:pull-lore` is user-invoked, so it's the place to be communicative about what happened.

When pulling multiple repos, dispatch them in parallel — auto-pull is independent per repo. A single message with multiple Bash invocations is sufficient; a subagent fan-out is overkill for what is mostly `git pull`.

### Step 4: Re-read role.md and lore-context.md per active agent

For each active agent (host first, then guests in attach order), re-read its `role.md` and `lore-context.md` from disk. This is essential — the pull updated the files, but the host's working context still holds the pre-pull copies.

If the host's `role.md` description changed, surface that in the report — a role drift mid-session is worth the user knowing about.

If a guest's `lore-context.md` changed in any visible way, note it. The user may want to follow up with `/lr:recall` to bring the new content into active reasoning.

### Step 5: Report

Print a compact summary:

```
Pulled <N> repo(s):
  ✓ <repo>: pulled <K> commit(s)
  ✓ <repo>: already up to date
  ! <repo>: skipped — no origin remote
  ✗ <repo>: pull failed — <reason>

Re-read context for <M> active agent(s): <host>, <guest1>, ...
```

If any repo had material `role.md` or `lore-context.md` changes, list them inline so the user has a moment to react.

## Failure Handling

`/lr:pull-lore` is best-effort. Per-repo failures (network, auth, non-fast-forward, dirty tree) surface in the report and continue — they never abort the skill. If every repo failed, say so explicitly: `Pull failed for all active agents' repos. See errors above; resolve and retry.`

If the re-read of `role.md` or `lore-context.md` fails (e.g., file missing after pull), surface that as a warning — the agent stays loaded with the pre-pull context.

## Composition With Other Flows

- **Boot already auto-pulls.** `/lr:pull-lore` is the mid-session manual equivalent. A typical session never needs to invoke it explicitly — the boot pull and the pre-merge pull cover the common cases.
- **`/lr:reflect` and `/lr:merge`.** `/lr:merge` runs in a subagent that boots as the target agent, so its boot pull covers freshness. `/lr:pull-lore` before `/lr:reflect` is sometimes useful when the user knows the host's lore-context has drifted from disk after a long session.
- **`/lr:workspace-pull`** is the workspace-wide peer (every top-level repo, including non-lore application code repos). `/lr:pull-lore` is session-scoped (only the lore agent repos of currently loaded agents). Use workspace-pull to bootstrap or refresh the whole workspace; use `/lr:pull-lore` to refresh active agents quickly without touching unrelated repos.

## See Also

- `<framework-root>/docs/auto-pull.md` — the per-repo procedure this skill iterates.
- `<framework-root>/docs/agent-boot.md` — the boot-time auto-pull, which makes `/lr:pull-lore` rarely necessary.
- `<framework-root>/docs/process-merge.md` — the pre-merge auto-pull (defense-in-depth).
- `<framework-root>/docs/workspace-pull.md` — workspace-wide companion (different scope).
- `<framework-root>/docs/attach.md` — `/lr:attach` also auto-pulls the guest repo on attach.
- `<framework-root>/docs/recall.md` — pair with `/lr:pull-lore` when freshly pulled lore-context wants to be re-explored.

# /lr:workspace-push

Publish **workspace-level** state — commit the framework-managed files of the workspace repo and
push it to its remote. This is the producer half of the workspace repo's git story, symmetric with
`workspace-pull` phase 0 (which receives teammates' workspace commits):

```
workspace-pull  =  consume   (pull the workspace repo, clone/pull children)
workspace-push  =  publish   (commit framework-managed workspace files, push the workspace repo)
```

Several framework skills write workspace-root files — `/lr:workspace-init` writes the descriptor,
memory-file managed section, `.gitignore`, and `README.md`; `/lr:register-agent` and
`/lr:register-repo` write per-agent shortcuts; `/lr:update` migrations regenerate those shortcuts;
`workspace-pull` phase 3 appends `.gitignore` lines — and none of them commits. Without a publish
step those changes sit dirty indefinitely, and a teammate's `workspace-pull` phase 0 receives a
stale descriptor. `/lr:workspace-push` closes that loop as an explicit, user-triggered step.

**Child repos are out of scope.** Lore agent repos publish via `/lr:finalize` phase 4; other repos
via their own git flows. This skill touches exactly one repo: the workspace root.

## Framework-managed paths

The paths the framework writes at the workspace root — the only paths this skill will ever stage.
**The set is defined in code**, at `scripts/lr_core/workspace_scan.py` (`MANAGED_PATHS`), and emitted
as `data.managed_paths.set`. Step 2 reads it from there. The table below is a rendering for human
readers, not a second definition — never stage from a remembered copy of it:

| Path | Written by |
|---|---|
| `lore-workspace.md` | `workspace-init` |
| `AGENTS.md` | `workspace-init`; the `register-agent` family (Agents section) |
| `CLAUDE.md` | `workspace-init` (the `@AGENTS.md` import line only) |
| `.gitignore` | `workspace-init`, `workspace-pull` phase 3 |
| `README.md` | `workspace-init` |
| `.claude/commands/lr-*-agent.md` | `register-agent` / `register-repo`, `update` migrations |
| `.codex/skills/lr-*-agent/SKILL.md` | `register-agent` / `register-repo`, `update` migrations |
| `.cursor/skills/lr-*-agent/SKILL.md` | `register-agent` / `register-repo`, `update` migrations |

All three engines' per-agent shortcuts are workspace-local as of v37, so all three publish here.
Codex shortcuts left in `~/.codex/skills/` by an earlier framework version are the exception: that
directory is outside the workspace repo and no publish path can reach it. Relocate them with
`migrations/37.md` (via `/lr:update`) or by re-registering — finding S15 names the ones it can see.

Do not confuse these with the **standard ignore lines** (`/.worktrees/`, `/.lr-beings/`, `/.tmp/`)
that `workspace-pull` phase 3 maintains *inside* `.gitignore` — those are content, this is the path
set.

The memory files are only partially framework-managed — `AGENTS.md` down to three sections,
`CLAUDE.md` down to one line — but git commits whole files, so a commit may carry the user's own
edits from outside that region. This is why Step 3 shows the diff and confirms before committing.

## Procedure

### Step 1 — Scan, then check preconditions

Resolve `<workspace>` (the current working directory — run `pwd` if unsure; this is *not*
`<framework-root>`), then run the scanner once. Everything this skill needs comes out of it, so
there is no second, hand-rolled derivation of the same git facts:

```
python3 "<framework-root>/scripts/lr-core" workspace-scan --workspace "<workspace>"
```

Quote both substituted values. The scanner is a **literate accelerator**: on failure (exit 2, no
output, unparseable output) apply the Script Fallback Contract (`docs/conventions.md`) — say in one
line that it failed and that you are proceeding by hand, then read
`scripts/lr_core/workspace_scan.py` and execute the steps in `git_state`, `status_paths`, and
`is_managed`.

Stop with a report on the first precondition that fails:

1. **Git-tracked.** `data.git.tracked` is true. If not: this is a local-only workspace — point to
   `/lr:workspace-init`, which offers to set up git tracking. Stop.
2. **Own git root.** `data.git.own_root` is true. False means the workspace sits inside an enclosing
   repo (`data.git.enclosing_root` names it), and every git operation here would silently act on
   that repo instead. Report and stop.

   The scanner compares git's `rev-parse --show-toplevel` against `os.path.realpath(<workspace>)`,
   never against `pwd` — on macOS `/var` is a symlink to `/private/var`, so the logical path
   disagrees with git's physical one (see `docs/version-check.md` Step 1b).
3. **On a branch.** `data.git.detached` is false — the same state finding **S16** reports. A
   detached HEAD: report and stop. A commit made here belongs to no branch and the next checkout
   drops it, and the ahead count is unreadable too (a detached HEAD has no upstream), so a later
   "nothing to push" could not be trusted either.

### Step 2 — Collect state

1. From the same scan: `data.managed_paths.dirty` is what this skill may stage;
   `data.managed_paths.other_dirty` is what it must leave alone. Untracked files are included, and an
   untracked directory has already been expanded to the files beneath it — so a first-ever registered
   shortcut is matched, not missed.
2. Remote state, also from the scan: `data.git.origin`, `data.git.upstream`, `data.git.ahead`.
3. If an upstream exists and the ahead count is nonzero, collect the commits that will ride along:
   `git -C "<workspace>" log --oneline @{u}..HEAD`. A workspace repo can be committed to by
   something other than the person running this skill — another session, or an autonomous agent —
   so these are shown, not counted.

If there are no dirty managed paths and the ahead count is zero (or there is no upstream and
nothing to commit), report **"workspace already published"**, list any dirty *other* paths as
informational (they are not covered by this skill), and stop.

### Step 3 — Plan and confirm

Show one plan, then a single yes/no confirmation:

```
Will commit (framework-managed paths only):
  <path>  <diffstat or "new file">
  ...
Left untouched (not framework-managed):
  <other dirty paths, or "none">
Then push <branch> to <origin/upstream>
Riding along (already committed, not yet pushed):
  <sha> <subject>
  ...
Proceed? (yes/no)
```

- If there is nothing to commit but unpushed commits exist, the plan is push-only.
- If there is no `origin` remote, the plan is commit-only; state that push is skipped and how to
  add a remote (`git -C "<workspace>" remote add origin <url>`).
- For memory files, note in the plan when the diff extends beyond the framework-managed region —
  the user is confirming their own edits ride along.

`no` → stop without writing anything.

### Step 4 — Execute

1. Stage **only** the dirty managed paths, by explicit path argument, deletion-aware:
   `git -C "<workspace>" add -A -- <path> [<path> ...]`. Never `git add .`, never a bare `-A`,
   never a wildcard.
2. Commit **the same explicit paths**, never a bare commit:
   `git -C "<workspace>" commit -m "chore(lore): publish workspace state" -- <path> [<path> ...]`.

   A bare `git commit` commits the whole index, not what step 1 staged. This workspace can have
   another session — or an unattended one — with content already staged, or staging some between
   step 1 and here; a bare commit sweeps that in. The pathspec keeps *other paths* out of the
   commit no matter what the index holds.

   It does **not** freeze the content of the paths it names: a pathspec commit takes each named
   path's current working-tree content, not the version step 1 staged. If another session rewrites
   one of these same managed files in between, that newer content is what lands, and step 3 does
   not catch it — step 3 verifies which *paths* the commit touched, never their contents. Publishing
   a managed file's current state is the intended behavior, so this is a narrowed risk rather than a
   closed one: what the pathspec rules out is committing somebody else's *unrelated* file.
3. Verify the commit contains no path outside the framework-managed set
   (`git -C "<workspace>" show --name-only --format= HEAD`). If it does: **undo the commit** with
   `git -C "<workspace>" reset --soft HEAD^` — which restores the pre-commit state with the content
   still staged and nothing lost — then report the unexpected paths and stop. Do not push.

   Leaving a commit you have just declared wrong sitting on the branch is not a safe stopping point:
   the next `workspace-push`, or anything else that pushes, carries it. Undo it here, where the
   context for what went wrong still exists.
4. Push: `git -C "<workspace>" push` when an upstream exists;
   `git -C "<workspace>" push -u origin HEAD` when `origin` exists but no upstream is set; skip
   with a report when there is no remote.

Report the result in one line per action: `✓ committed <sha>` / `✓ pushed to <branch>` / why a
step was skipped.

### Failure handling

- **Push rejected (non-fast-forward)** — a teammate pushed workspace commits first. Do not force,
  do not merge automatically: report it and suggest `/lr:workspace-pull` (phase 0 pulls the
  workspace repo `--ff-only`), then re-run `/lr:workspace-push`. If the pull itself fails
  (divergence), the user resolves manually.
- **Auth / network failures** — the commit is already local; report the push error verbatim.
- **`fatal: Unable to create '.git/index.lock': File exists`** — another process is mid-`add` or
  mid-`commit` in this same workspace: a second `/lr:workspace-push`, another skill, or an
  unattended session. Do not delete the lock file; it is usually held by a live process, and
  removing it corrupts the other run's index write. Report it and stop; do not poll and do not wait
  in a loop. Re-running is the user's call, and it must start from Step 1 — the scan has to be
  redone, because whatever the other process was committing has changed what is dirty here. In an
  unattended session, stopping with the lock reported is the correct end state: a session with
  nobody to ask must not spin waiting for a lock that may be held for as long as a human session
  lasts.

## What `/lr:workspace-push` does NOT do

- Does not stage or commit any path outside the Framework-managed paths table — unrelated dirty
  files are listed and left alone.
- Does not touch child repos, create remotes or branches, or force-push.
- Does not resolve divergent histories — that is `workspace-pull` phase 0 plus manual resolution.

## See Also

- `docs/workspace-pull.md` — the consumer counterpart; phase 0 is how teammates receive what this
  skill publishes.
- `docs/workspace-init.md` — the skill that creates and converges the files this skill publishes.
- `docs/workspace-status.md` — the read-only diagnosis; findings S1 (dirty managed files) and S2
  (unpushed commits) are what send a user here.
- `docs/check.md` — check #24 warns when framework-managed workspace files are dirty or unpushed.
- `docs/finalize.md` — phase 4, the publish path for *agent repo* changes (this skill's sibling at
  the domain layer).

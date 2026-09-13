# Workspace Sync

`/lr:workspace-sync` drives every repository in the workspace to one state: **everything
local is committed, integrated with its remote, and published** — or reported, precisely, as
why it is not.

It exists because Lore stops flowing between people long before anything looks broken. Findings
sit uncommitted for days, commits stay ahead of the remote because nobody pushed, a pull is
blocked by one modified file, a branch diverges, and a worktree registration points at a
directory that was deleted months ago. `/lr:workspace-pull` only fast-forwards,
`/lr:workspace-push` only publishes the workspace repo's own managed files, and `/lr:check`
reports without repairing. This is the command that closes the loop.

## Step 0 — Announce

Print this before doing anything else, substituting `<workspace>`:

> Synchronizing the whole workspace at `<workspace>`. For each Lore agent repo — the git repos
> your agents keep their knowledge in — **I commit whatever is sitting there uncommitted, merge
> in what your teammates have pushed, and publish the result to the remote**, so no one's
> findings stay stranded on one machine. Repos holding ordinary source code are only brought up
> to date, never committed or pushed. Nothing is ever discarded to make a sync succeed: where
> two versions of a file genuinely conflict, I stop and merge them by hand rather than pick a
> winner.

Run `/lr:workspace-sync --dry-run` first if the user wants to see the plan before anything is
written; it performs no writes at all.

## Procedure

### Step 1 — Run the command

Resolve `<workspace>` — the directory this session was invoked from; run `pwd` if unsure.
It is the same value you substituted in Step 0.

```
python3 "<framework-root>/scripts/lr-core" workspace-sync --workspace "<workspace>"
```

Give it at least 300 seconds: it fetches and pushes over the network once per repository.

Flags: `--dry-run` (report the plan, write nothing), `--no-push` (commit and integrate, publish
nothing), `--prune-worktrees` (also delete worktree directories that are clean and fully merged).

The command prints one JSON object: `{"ok", "data", "warnings", "errors"}`. Every repository in
`data.repos[]` carries a terminal `status`:

| `status` | Meaning |
|---|---|
| `published` | committed and/or pushed; the remote now has it |
| `up-to-date` | nothing to do |
| `local-only` | **committed but not published** — pending publication, not success |
| `blocked` | someone must act; `blocked` names what and why |
| `skipped` | an ordinary state with nothing to do (no remote configured, dry run) |
| `not-attempted` | the run never reached this repo — never report it as success |

### Step 2 — Operation Notice

A notice fires **only for what actually happened**, and a run that changed nothing prints none of
these — silence on a no-op is the point. Print the line for each outcome that occurred, taking the
repo names from `data.repos[]`:

- Any repo with `status: "published"` **and** `push: "pushed"`:

  > Published `<names>`. **This committed and pushed files that were sitting uncommitted in your
  > workspace**, so they are now visible to everyone who shares those repos.

- Any repo with `status: "published"` or `"local-only"` whose `committed[]` is non-empty but which
  was **not** pushed:

  > Committed local changes in `<names>`. **These are saved in git history but not yet published**,
  > so nobody else can see them until they are pushed.

- Any repo whose `integrate` is `"merged"` or `"fast-forward"` and which committed nothing:

  > Brought `<names>` up to date with changes your teammates had already pushed. **Files in your
  > working copy changed** as a result.

- Any repo whose `worktrees.pruned` or `worktrees.removed` is non-empty:

  > Cleaned up `<n>` stale worktree registration(s) in `<names>`. **No files with uncommitted work
  > were removed** — anything unclean was kept and is listed in the report.

### Step 3 — Report what happened

One line per repository, in plain language, leading with the ones that need the user:

- `blocked` — name the repo and the reason verbatim. It is written to be actionable.
- `local-only` — say the work is **committed and safe but not yet published**, and why.
- `held` paths — say what was deliberately **not** committed and why. This is the entry a user
  most needs to see: a credential-shaped name, a nested git repository, an oversized file, or
  editor debris. None of it was deleted; it is all still on disk.
- `skipped` — one short line saying why nothing was done (usually: no remote configured).
  Never drop a skipped repo from the report; silence about a repo reads as success.
- `published` / `up-to-date` — one short line, or a single summary line for all of them together.
- `not-attempted` — say plainly that the run **did not reach this repository**, so its state is
  unknown, and that re-running is safe. Never fold it in with the repos that succeeded.

Do not print the JSON. Do not describe a `local-only` repo as synchronized.

### Step 4 — Resolve conflicts, then re-run

A repo blocked on `merge conflict` has the merge left in progress on purpose: both sides are
already committed, so nothing can be lost, and the conflict markers sit on content that is safe
in history. Resolve every path in that repo's `conflicts[]` under these rules, which apply
whatever kind of repository it is:

- **Preserve both sides' distinct information.** Where each side added something different, the
  resolution carries both.
- **Prefer the more specific or more correct version** where the two sides changed the same thing.
- **Never invent content.** A resolution reconciles the two inputs; it does not introduce a third.
- **Never delete one side to make the file parse.** Removing a conflicting block is data loss
  wearing the appearance of a fix.

Two cases need more than the general rules:

- **A Lore topic, `lore-context.md`, or `role.md` in an agent repo** — merge as the agent would,
  per `<framework-root>/docs/resolve-conflicts.md` § Step 2, and check afterwards that
  cross-topic references still name files that exist (§ Step 3). That document is written for
  `/lr:finalize`, so read those two sections for their merge rules and ignore its scope and
  retry framing.
- **Anything else** — the workspace repo's own files, or a source repository's code. These are
  outside any automatic procedure in this framework. Resolve only what you can read and judge
  confidently; where you cannot, leave the conflict in place and tell the user which repo and
  which paths need them. Never guess at code you have not read.

Then **run the command again**. There is no `--continue` flag: the command detects the merge it
left behind, verifies it is its own, checks that no conflict markers remain, commits it, and
carries on to the push. Re-running is always the continuation, and it is safe to re-run at any
time.

If the conflict cannot be resolved faithfully, **leave the merge exactly as it is** and tell the
user which repo and paths are waiting on them. Do not run `git merge --abort` yourself — say that
*they* can run it in that repo to restore the pre-merge state, and that the commit made earlier in
the run survives an abort either way.

## What it refuses to do

These are not failures; they are the command declining to make a decision that belongs to a
person. Each is reported with its remedy.

- **Never commits or pushes a source repository.** Repos without `lore-repo.md` are brought up to
  date and otherwise left exactly as they are.
- **Never resumes an operation it did not start.** A merge you opened by hand, a stopped
  cherry-pick, revert, rebase or bisect all block the repo rather than getting driven forward.
- **Never creates a branch on a remote.** A local branch with no upstream is committed locally
  and reported `local-only`, with the `git push -u` command to run if it should be published.
- **Never publishes a credential-shaped name, a nested git repository, an oversized file, or
  editor debris.** These are held back and named in the report, never deleted.
- **Never forces anything.** No `--force`, no `reset --hard`, no `stash`, no `clean`, no
  `rebase`, and no file is ever deleted to make a sync succeed.

It also holds no lock of its own. Two syncs — or a sync and another git tool — running against one
repository at the same time are arbitrated by git's own index lock, which prevents corruption but
not confusion: the losing run reports that repo as blocked because another git process holds the
repository, and re-running once the other finishes is the remedy. Do not delete a lock file to
clear it.

Worktrees follow the same rule: dead registrations are pruned only when the directory was
genuinely deleted (not merely on an unmounted volume) and holds no commits a branch has lost
track of. Worktree *directories* are removed only under `--prune-worktrees`, and only when they are clean,
fully merged into the default branch, not the directory the command is running from, and the
default branch is actually known — an unknown one keeps everything rather than guessing.

## Relationship to the neighbouring commands

- `/lr:workspace-pull` — clones repos declared but not present, then fast-forwards. Use it to
  *set up* or refresh a workspace. It never commits or pushes.
- `/lr:workspace-push` — publishes the workspace repo's own framework-managed files only.
- `/lr:check` — reports health across plugin, repos and workspace, and repairs nothing.
- `/lr:workspace-sync` — the repair. It is the only one of the four that commits on your behalf.

## If the script cannot run

`workspace-sync` is a **literate accelerator** (`conventions.md` § Script Fallback Contract).
Say in one line that it failed and that you are proceeding manually, then read
`<framework-root>/scripts/lr_core/workspace_sync.py` — its module header gives the phase order
and the prohibitions, and the functions carry the exact commands in their docstrings. Read, in
order: `classify_repos`, then `sync_repo` (the per-repo driver, whose phase 0 is the resume
logic — `_in_progress`, `read_merge_claim`, `has_conflict_markers` and `claim_merge` between them
decide whether an in-progress merge is this command's own to finish, which is the promise Step 4
above rests on), then `repo_facts`, `commit_local`, `integrate`, `push` and `worktree_hygiene`.
Execute them in that order, per repository, and reach the same end state.

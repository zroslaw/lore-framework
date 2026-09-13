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

```
python3 "<framework-root>/scripts/lr-core" workspace-sync --workspace "<cwd>"
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

**If anything was committed, pushed, merged, or pruned, print this as it happens** (substitute the
counts and repo names; it is silent on a run that changed nothing, by design):

> Published `<n>` repo(s) — `<names>`. **This committed and pushed files that were sitting
> uncommitted in your workspace**, so they are now visible to everyone who shares those repos.

### Step 3 — Report what happened

One line per repository, in plain language, leading with the ones that need the user:

- `blocked` — name the repo and the reason verbatim. It is written to be actionable.
- `local-only` — say the work is **committed and safe but not yet published**, and why.
- `held` paths — say what was deliberately **not** committed and why. This is the entry a user
  most needs to see: a credential-shaped name, a nested git repository, an oversized file, or
  editor debris. None of it was deleted; it is all still on disk.
- `published` / `up-to-date` — one short line, or a single summary line for all of them together.

Do not print the JSON. Do not describe a `local-only` repo as synchronized.

### Step 4 — Resolve conflicts, then re-run

A repo blocked on `merge conflict` has the merge left in progress on purpose: both sides are
already committed, so nothing can be lost, and the conflict markers sit on content that is safe
in history. Resolve the paths in that repo's `conflicts[]` following
`<framework-root>/docs/resolve-conflicts.md` § Step 2 — **preserve both sides' distinct
information, prefer the more specific version, never invent content, and never delete one side
to make the file parse**. For a Lore topic that means a merged topic carrying both additions;
for `lore-context.md`, a combined version keeping all entries.

Then **run the command again**. There is no `--continue` flag: the command detects the merge it
left behind, verifies it is its own, checks that no conflict markers remain, commits it, and
carries on to the push. Re-running is always the continuation, and it is safe to re-run at any
time.

If the conflict cannot be resolved faithfully, leave it and tell the user. `git merge --abort`
in that repo restores the pre-merge state, and the local commit made in phase 2 survives it.

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

Worktrees follow the same rule: dead registrations are pruned only when the directory was
genuinely deleted (not merely on an unmounted volume) and holds no commits a branch has lost
track of. Worktree *directories* are removed only under `--prune-worktrees`, and only when clean
and fully merged.

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
and the prohibitions, and `classify_repos`, `repo_facts`, `commit_local`, `integrate`, `push`
and `worktree_hygiene` carry the exact commands in their docstrings. Execute them in that order,
per repository, and reach the same end state.

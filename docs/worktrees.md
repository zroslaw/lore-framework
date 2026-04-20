# Worktrees

The lore framework's convention for working with non-default branches of repos inside a domain.

## Invariant

Top-level directories in `<domain>/` that are checkouts of git repos **stay on their default branch**. The default branch is whatever that repo treats as production state — commonly `main`, but `master`, `trunk`, or any other name is equally valid. Git itself tracks the default per-repo; the framework does not maintain its own list.

The invariant matters because:

- The domain is read as a snapshot of current production across all its repos. Switching a top-level checkout to a feature branch breaks that view.
- Agent knowledge about "what this repo looks like in prod" assumes the top-level checkout reflects prod. Drift from that assumption quietly corrupts lore.
- `/lr:pull-domain` refreshes all top-level repos. If one is on a feature branch, that refresh semantics gets confusing.

## Rule

Any work that requires a non-default branch — new features, bug fixes, or just checking out someone else's branch to inspect it — happens in a **git worktree** rooted at:

```
<domain>/.worktrees/<repo>/<slug>/
```

Where:

- `<repo>` is the repo directory name (matches the top-level checkout).
- `<slug>` is a short, lowercase, hyphen-separated identifier for this particular line of work.

Git worktree mechanics are standard; no framework commands wrap them. Typical usage:

**New feature work:**

```bash
cd <domain>/<repo>
git worktree add ../.worktrees/<repo>/<slug> -b <branch-name>
```

**Inspecting someone else's branch:**

```bash
cd <domain>/<repo>
git fetch origin
git worktree add ../.worktrees/<repo>/<slug> origin/<existing-branch>
```

**Removing when done:**

```bash
git worktree remove ../.worktrees/<repo>/<slug>
```

A branch-naming suggestion — `<agent-name>/<slug>` — signals which agent owns the work in multi-agent domains. It's a convention, not enforced.

## Optional: Tracking Inflight Worktrees

An agent that wants to keep notes on its inflight worktrees can use:

```
<lore-agent-repo>/agents/<agent-name>/worktrees/<slug>.md
```

What goes in those notes — structure, skeleton, cadence, whether to archive or delete on prune — is the agent's call. Inspection-grade worktrees may warrant no note; long-lived contributions may warrant a living doc with context, progress, and decisions.

This pattern is not mandated and not scaffolded. The framework neither creates these files nor checks for their presence.

## What's Out of Scope

These are deliberately not part of the framework — they belong in agent lore or repo-specialist agents reached via `/lr:consult` or `/lr:attach`:

- PR/MR workflow, review conventions, merge policies
- Commit message conventions, signoff requirements
- CI/CD interactions
- Repo-specific branch protection rules
- Worktree cleanup discipline (when to prune, what to preserve)

The reasoning is the framework's universal-vs-specific split: git worktrees are universal; everything around them is repo-specific.

## Enforcement

Convention-only. The framework does not currently check whether top-level repo dirs have drifted onto non-default branches. If that drift becomes a real problem in practice, a `/lr:check` warning is a cheap future addition.

Framework convention (v9+) for working with non-default branches of repos inside a domain.

## Invariant

Top-level directories in `<domain>/` that are repo checkouts stay on their default branch (whatever that branch is named — `main`, `master`, `trunk`, etc.; git tracks it per-repo). The framework does not maintain its own list of default branches.

The invariant preserves three things:
- The domain as a snapshot of current production state across all its repos.
- Agent lore that references "this repo's code" — drift from the invariant quietly corrupts that lore.
- `/lr:pull-domain` semantics (refreshes all top-level repos; ambiguous if any is on a feature branch).

## Rule

Non-default-branch work — new features, bug fixes, or inspecting someone else's branch — happens in a git worktree at `<domain>/.worktrees/<repo>/<slug>/`. Both contribution and inspection cases use the same mechanism. Standard git worktree commands; no framework wrappers.

Branch naming `<agent-name>/<slug>` is a suggestion for signaling ownership in multi-agent domains, not enforced.

## Optional Per-Agent Notes

An agent that wants to track inflight worktrees can use `<lore-agent-repo>/agents/<agent-name>/worktrees/<slug>.md`. Structure, skeleton, cadence, archive-vs-delete on prune — all agent's call. Inspection-grade worktrees may warrant no note; long-lived contributions may warrant a living doc. The framework neither mandates nor scaffolds this.

## Out of Scope

Explicitly not framework concerns (repo-specific, belong in agent lore or repo-specialist agents reached via `/lr:consult` / `/lr:attach`):
- PR/MR workflow, review conventions, merge policies
- Commit conventions, signoff requirements
- CI/CD interactions
- Branch protection rules
- Cleanup discipline

## Enforcement

Convention-only in v9. `/lr:check` does not currently warn when a top-level repo dir is on a non-default branch. A future check is a cheap add if drift becomes a practical problem — tracked in `framework-improvements-backlog.md`.

## Design History

Replaces the earlier contributions-feature design (v8-era draft, not shipped). Key reframing: worktree is the universal primitive; "contribution" was a specialization that didn't cover inspection-of-existing-branches cases. Two specialized commands (`/lr:contribute`, `/lr:contribution-finalize`) got dropped — git worktree mechanics are universal knowledge and don't need wrapping. See `lr-init-feature.md` for the companion distribution mechanism.

## See Also

- `lr-init-feature.md` — writes the compact convention into the domain's CLAUDE.md
- `framework-improvements-backlog.md` — tracks deferred extensions
- `framework-scope-vs-agent-scope.md` — the principle this convention applies

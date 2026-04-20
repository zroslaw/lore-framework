# Init

Write (or refresh) a framework-managed section in the domain-level `CLAUDE.md` so that any Claude Code session working in the domain automatically loads the framework's conventions.

## Purpose

`CLAUDE.md` at the root of a working directory is loaded by default into every Claude Code session that starts there. Parking the framework's conventions inside it is the simplest way to make them visible without relying on agent memory or manual context-setting.

The framework cannot ship the domain `CLAUDE.md` directly — that file belongs to the user's domain, not to the plugin. What the framework can ship is a command that writes its conventions into a delimited section of the user's `CLAUDE.md`, leaving the rest of the file untouched.

## Input

No arguments in this version.

## Target

`<cwd>/CLAUDE.md` — the file at the current working directory. The user runs `/lr:init` from the domain directory.

The command does not verify that the cwd is a domain (contains lore agent repos or otherwise). If run from an unintended location, the user can inspect the result and delete the file.

## Marker Protocol

Framework-managed content is delimited by two HTML comment markers, each on its own line:

```
<!-- lr:init:start -->
... managed content ...
<!-- lr:init:end -->
```

Content **outside** the markers is the user's — never touched by `/lr:init`. Content **inside** the markers is framework-managed and may be regenerated.

Markers must appear at most once per file. If either appears without its pair, or either appears more than once, report an error and stop — do not attempt repair.

## Behavior

| Initial state                               | Action                                                             |
| ------------------------------------------- | ------------------------------------------------------------------ |
| No `CLAUDE.md` at cwd                       | Create the file with the canonical payload at the top.             |
| `CLAUDE.md` exists, no markers              | Prepend the canonical payload (top = essential context).           |
| Markers present, managed section == canonical | Report "already current" and stop. No-op.                        |
| Markers present, managed section != canonical | Show a diff of the managed section, ask the user to confirm, replace on yes. |
| Marker pair malformed (missing end, duplicate, etc.) | Report error with file offsets, stop.                       |

The diff is scoped to the managed section only — not the whole file — so the user sees exactly what will change inside the markers.

## Canonical Payload (v1)

The exact content of the framework-managed section, markers included:

~~~markdown
<!-- lr:init:start -->
## Lore Framework Domain

This directory is a Lore Framework domain. Conventions for any Claude Code session working here:

- **Repos at the top level stay on their default branch.** They represent production state.
- **For any non-default branch (new features, checking out others' branches), create a git worktree** at `.worktrees/<repo>/<slug>/`. Standard git worktree commands apply.

Full convention: https://github.com/zroslaw/lore-framework/blob/main/docs/worktrees.md
<!-- lr:init:end -->
~~~

The link is the public GitHub URL rather than `${CLAUDE_PLUGIN_ROOT}/docs/worktrees.md` — a user-facing file should reference paths that resolve whether the plugin is loaded or not.

## Idempotency and Re-runs

`/lr:init` is safe to run any number of times. When the canonical payload evolves in a later framework version, the user reruns `/lr:init` to refresh the managed section. The diff-and-confirm gate keeps user edits inside the markers from being silently lost.

## What `/lr:init` Does NOT Do

- Does not touch content outside the markers.
- Does not touch any file other than `<cwd>/CLAUDE.md`.
- Does not run git commands. The user reviews with `git diff` (if the domain is versioned) or by opening the file, and commits themselves.
- Does not validate that the cwd is a lore-framework domain.
- Does not scaffold or modify per-agent or per-repo files.
- Does not three-way-merge. Show-diff-and-confirm is the entire user-edit protocol.

## Future Extensions

The marker-delineated section is the extension point. Future framework versions may expand the canonical payload with additional content (domain intro, agent registry pointers, invocation tips, etc.), all living inside the same `<!-- lr:init -->` markers. The mechanism does not change; only the payload grows.

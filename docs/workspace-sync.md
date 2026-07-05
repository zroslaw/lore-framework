# /lr:workspace-sync

Synchronize the **workspace** — the directory containing one or more lore agent repos and any other repositories they declare. One command for both first-time setup and ongoing sync.

> **When to run.** First thing on a fresh workspace (after cloning your first agent repo); whenever you want to refresh everything to the latest. Follow up with `/lr:init` to write the workspace's `CLAUDE.md` conventions block.

## What It Does

1. **Discovers** every `<workspace>/<subdir>/lore-repo.md`.
2. **Reads** each descriptor's `repos:` list and merges them into a single deduplicated set.
3. **Clones** any declared repo that isn't yet present in the workspace.
4. **Pulls** every top-level git repo (existing + freshly cloned) in parallel with `git pull --ff-only`.
5. **Reports** any conflicts (remote mismatches, target-not-a-repo, dir collisions, clone/pull failures) at the end for manual resolution.

## Usage

```
/lr:workspace-sync
```

Run from the workspace root. Bootstrap and incremental sync are the same operation — on a fresh checkout the script clones everything declared; on subsequent runs it only clones what's missing and pulls the rest.

## Declaring Repos in `lore-repo.md`

> **Joining a team's existing setup?** You don't need to edit anything — just run `/lr:workspace-sync`. The agent repo's owner already declared `repos:` for you. Skip this section unless you're authoring or maintaining an agent repo.

Add a `repos:` block to the YAML frontmatter of any `lore-repo.md`:

```yaml
---
description: Agents for the activities platform
version: "11"
repos:
  - git@github.com:agoda/activities-web.git
  - git@github.com:agoda/activity-search.git
  - https://github.com/zroslaw/lore-framework.git
---
```

**Schema rules:**

- Block-form list only (`- <url>` per line). Inline-flow form (`repos: [a, b]`) is not supported.
- Entries are remote URLs — anything `git clone` accepts (SSH, HTTPS, git, ssh://). Quoted strings are tolerated; unquoted is preferred.
- The directory name in the workspace is derived from the URL: the last path segment with any trailing `.git` stripped. `git@github.com:foo/bar.git` → `bar/`.
- The list is optional. A `lore-repo.md` without a `repos:` field declares nothing — the workspace still gets pulled.

## Multi-Domain Workspaces

A workspace can contain multiple lore agent repos. Each declares its own `repos:` list. The script reads them all, merges into a single deduplicated set, and treats it as the union of what the workspace expects to contain.

When the same URL appears in more than one descriptor, it's recorded once. The first descriptor that declared it is reported as the source if a conflict surfaces.

## Conflict Handling

The script never modifies a directory it doesn't recognize. It collects and reports the following conditions:

| Condition | Reported as |
|---|---|
| Target dir exists but isn't a directory (e.g., a file) | conflict |
| Target dir exists but isn't a git repo | conflict |
| Target git repo has no `origin` remote | conflict |
| Target git repo's `origin` doesn't match the declared URL | conflict |
| Two distinct URLs map to the same dir name | dir collision |
| `git clone` failed | clone failure |
| `git pull --ff-only` failed (auth, divergence, etc.) | pull failure |

Repos in any conflict state above are **skipped during the pull phase** — the script will not run `git pull` against a remote that doesn't match the declaration. The user resolves manually (rename, remove, reconfigure remote) and reruns.

## Exit Codes

- `0` — nothing to do, or every clone/pull succeeded with no conflicts.
- `1` — at least one clone/pull failed or at least one conflict needs manual resolution.
- `2` — invalid invocation (workspace path missing or not a directory).

## Implementation

The skill is a one-liner that invokes `<framework-root>/scripts/workspace-sync` with the current working directory. All logic lives in the script — Bash 3.2+ compatible (no associative arrays), parallel clone and pull phases, output captured per-repo for clean reporting.

Pulls use `--ff-only` so divergent local branches surface as failures rather than producing silent merge commits.

## Relationship to Other Skills

- **`/lr:pull-lore`** is the narrower peer: refreshes only the lore agent repos of currently loaded agents (host + attached guests), no clone, no top-level non-lore repo pulls. Use it mid-session when you suspect a teammate pushed lore changes; use `/lr:workspace-sync` for first-time bootstrap or a full-workspace refresh.
- **`/lr:init`** writes the framework-managed section into the workspace's `CLAUDE.md`. Run it after `/lr:workspace-sync` on a fresh workspace.
- **`/lr:check`** runs consistency checks across the workspace. It does not pull or clone — it inspects what's already there.
- **`/lr:create-repo`** scaffolds a new agent repo. The new repo's `lore-repo.md` starts without a `repos:` field; add one when the agent has declared dependencies.

## Limitations

- Only top-level subdirectories of the workspace are inspected. Nested layouts are invisible (same constraint as the rest of the framework's discovery).
- Branch and ref pinning are not supported — clones use the remote's default branch; pulls fast-forward the current branch.
- Per-entry overrides (custom directory name, branch, depth) are not supported. Add them if real-world usage demands it.
- Authentication failures (missing SSH key, expired credentials) surface as clone/pull errors with their underlying message; the script does not retry or prompt.

## See Also

- `docs/pull-lore.md` — narrower per-agent refresh for active sessions (use this mid-session; use workspace-sync for bootstrap or full-workspace refresh).
- `docs/auto-pull.md` — the per-repo refresh procedure that boot/attach/merge invoke automatically.
- `docs/init.md` — companion command that distributes the worktree convention into the workspace's `CLAUDE.md`.
- `docs/worktrees.md` — the convention that keeps top-level repos on their default branch (so `--ff-only` pulls remain safe).
- `docs/conventions.md` — `lore-repo.md` schema reference.

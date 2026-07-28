# /lr:workspace-pull

Pull fresh **workspace** state — the directory containing one or more lore agent repos and any
other repositories they declare. One command for first-time bootstrap and ongoing refresh; it reads
**two levels** of repo declarations and clones/pulls everything they name.

> **When to run.** First thing on a fresh workspace (after cloning the workspace repo, or your first
> agent repo); whenever you want to refresh everything to the latest. On a fresh, empty workspace the
> setup wizard `/lr:workspace-init` runs this for you as its last step. Follow up with
> `/lr:workspace-init --refresh` to write the workspace memory-file conventions block.

## Two levels of repo declarations

`workspace-pull` reconciles repos declared at two levels, in order:

| Level | Descriptor | `repos:` means |
|-------|------------|----------------|
| **Workspace** | `<workspace>/lore-workspace.md` | High-level layout — which top-level repos belong in this workspace (including the lore **agent repos** themselves). |
| **Domain** | `<lore-agent-repo>/lore-repo.md` | Agent-domain dependencies — sibling repos the agents in that repo need. |

Same YAML key, two scopes. The workspace level names the agent repos; the domain level names each
agent repo's own dependencies. Workspace-level repos are cloned **first** so their `lore-repo.md`
descriptors are on disk and discoverable when the domain level runs.

## What It Does — phases

1. **Phase 0 — Workspace root pull (conditional).** If the workspace root is itself a git repo with
   an `origin` remote, `git pull --ff-only` it so descriptor changes teammates pushed (e.g. a new
   repo in `lore-workspace.md`) arrive before the rest of the run. Guarded by a dirty-tree check
   (skips with a warning rather than clobbering uncommitted edits). Any phase-0 failure is a
   **warning, never fatal** — the run proceeds against the local files. Skipped entirely when the
   root is not a git repo (local-only workspace).
2. **Phase 1 — Workspace-level repos.** Parse `<workspace>/lore-workspace.md` `repos:` and clone any
   declared repo not present.
3. **Phase 2 — Domain-level repos.** Discover every `<workspace>/<subdir>/lore-repo.md`, merge each
   `repos:` (deduped by URL against phase 1), and clone any not already satisfied.
4. **Phase 3 — `.gitignore` plumbing (conditional).** When the workspace root is git-tracked, append
   the standard workspace-owned lines (`/.worktrees/`, `/.lr-beings/`, `/.tmp/`) if missing, then a
   `/child/` line for every declared repo present on disk (cloned this run or already consistent),
   so nested clones and local scratch aren't committed into the workspace repo. Idempotent by
   exact-line match; never auto-commits. Skipped when the root is not a git repo.
5. **Phase 4 — Pull all.** `git pull --ff-only` every top-level git repo (existing + freshly cloned)
   in parallel, including top-level repos not declared in any descriptor (v11 parity). Conflict-state
   repos are skipped.

All conflicts (remote mismatches, target-not-a-repo, dir collisions, clone/pull failures) are
collected and reported at the end for manual resolution.

## Usage

```
/lr:workspace-pull
```

Run from the workspace root. Bootstrap and incremental refresh are the same operation — on a fresh
checkout the script clones everything declared; on subsequent runs it clones only what's missing and
pulls the rest.

## `lore-workspace.md` (workspace descriptor)

Optional file at the workspace root. Absent → phase 1 is a no-op and phase 2 still runs (backward
compatible with v11 domain-only workspaces).

```yaml
---
description: Team's agentic dev workspace
repos:
  - git@github.com:team/lore-framework-dev.git
  - git@github.com:team/lore-agents.git
---
```

- Block-form `repos:` only (same parser as `lore-repo.md`; inline `repos: [a, b]` is not supported).
- **High-level list** — the top-level repos that should exist as siblings in `<workspace>/`. Include
  the lore **agent repos themselves**; their domain dependencies are cloned automatically by phase 2.
- The markdown body is user-owned (team onboarding notes). `/lr:workspace-init` writes only the
  frontmatter `description` + `repos:`.

## Declaring Repos in `lore-repo.md` (domain level)

> **Joining a team's existing setup?** You don't need to edit anything — just run
> `/lr:workspace-pull`. The workspace and agent-repo owners already declared `repos:` for you. Skip
> this section unless you're authoring or maintaining an agent repo.

Add a `repos:` block to the YAML frontmatter of any `lore-repo.md`:

```yaml
---
description: Agents for the activities platform
version: "25"
repos:
  - git@github.com:agoda/activities-web.git
  - https://github.com/zroslaw/lore-framework.git
---
```

**Schema rules (both descriptors):**

- Block-form list only (`- <url>` per line).
- Entries are remote URLs — anything `git clone` accepts (SSH, HTTPS, git, ssh://). Quoted strings
  are tolerated; unquoted is preferred.
- The workspace directory name is derived from the URL: the last path segment with any trailing
  `.git` stripped. `git@github.com:foo/bar.git` → `bar/`. Names that would escape the workspace
  (path traversal, leading `-`, embedded slash) or carry a `.gitignore` metacharacter (`*`, `?`,
  `[`, leading `!`) are rejected as conflicts.
- The list is optional.

## Multi-Domain Workspaces

A workspace can contain multiple lore agent repos. Each declares its own `repos:` list; the workspace
descriptor names the agent repos themselves. The script reads them all, merges into a single
deduplicated set (union across both levels — the same URL declared at both levels is cloned once),
and treats it as what the workspace expects to contain. When a URL appears in more than one
descriptor, the first that declared it is reported as the source if a conflict surfaces.

## Conflict Handling

The script never modifies a directory it doesn't recognize. It collects and reports:

| Condition | Reported as |
|---|---|
| Target dir exists but isn't a directory (e.g., a file) | conflict |
| Target dir exists but isn't a git repo | conflict |
| Target git repo has no `origin` remote | conflict |
| Target git repo's `origin` doesn't match the declared URL | conflict |
| Derived dir name is unsafe (traversal, leading `-`, `.gitignore` metacharacter) | conflict |
| Two distinct URLs map to the same dir name | dir collision |
| `git clone` failed | clone failure |
| `git pull --ff-only` failed (auth, divergence, etc.) | pull failure |

Repos in any conflict state are **skipped during the pull phase** — the script won't `git pull`
against a remote that doesn't match the declaration. The user resolves manually (rename, remove,
reconfigure remote) and reruns.

If workspace-level clones fail, the script warns that domain-level repos declared *inside* those
missing agent repos were not discovered — fix the clone failures and re-run.

## Exit Codes

- `0` — nothing to do, or every clone/pull succeeded with no conflicts. Phase-0 warnings alone do
  not set a nonzero exit.
- `1` — at least one clone/pull failed or at least one conflict needs manual resolution.
- `2` — invalid invocation (workspace path missing or not a directory).

## Implementation

The skill is a one-liner that invokes `<framework-root>/scripts/workspace-pull` with the current
working directory. All logic lives in the script — Bash 3.2+ compatible (no associative arrays),
parallel clone and pull phases, output captured per-repo for clean reporting. Pulls use `--ff-only`
so divergent local branches surface as failures rather than silent merge commits.

> **If the script fails to run**, apply the **Script Fallback Contract** (`<framework-root>/docs/conventions.md`): this is an *implementation* script, so report the failure with the command and error rather than improvising a manual substitute, and never report the operation as done.

## Relationship to Other Skills

- **`/lr:workspace-init`** is the producer companion: the setup wizard writes `lore-workspace.md`,
  the optional workspace git root, `README.md`, and the memory-file conventions block, then ends by
  running `workspace-pull`. `workspace-pull` is the consumer — it reads those descriptors and
  clones/pulls.
- **`/lr:pull-lore`** is the narrower peer: refreshes only the lore agent repos of currently loaded
  agents (host + attached guests), no clone, no top-level non-lore pulls. Use it mid-session when a
  teammate pushed lore changes; use `workspace-pull` for bootstrap or a full-workspace refresh.
- **`/lr:check`** runs consistency checks across the workspace (including #22, which warns when
  standard workspace-owned ignore lines or a declared child repo on disk aren't covered in a git
  workspace). It does not pull or clone.
- **`/lr:create-repo`** scaffolds a new agent repo. Its `lore-repo.md` starts without a `repos:`
  field; add one when the agent has declared dependencies.

## Limitations

- Only top-level subdirectories of the workspace are inspected (same discovery constraint as the rest
  of the framework). Nested layouts are invisible.
- Branch and ref pinning are not supported — clones use the remote's default branch; pulls
  fast-forward the current branch.
- Per-entry overrides (custom directory name, branch, depth) are not supported.
- `--prune` (removing a clone when a repo drops out of a descriptor) is not supported; remove stale
  clones manually.
- Authentication failures surface as clone/pull errors with their underlying message; the script does
  not retry or prompt.

## See Also

- `docs/workspace-init.md` — the producer companion (setup wizard + memory-file refresh).
- `docs/pull-lore.md` — narrower per-agent refresh for active sessions.
- `docs/auto-pull.md` — the per-repo refresh procedure that boot/attach/merge invoke automatically.
- `docs/worktrees.md` — the convention that keeps top-level repos on their default branch (so
  `--ff-only` pulls remain safe).
- `docs/conventions.md` — `lore-workspace.md` and `lore-repo.md` schema reference; the dual meaning
  of `repos:`.

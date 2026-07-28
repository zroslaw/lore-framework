# /lr:workspace-init

Bootstrap a lore **workspace** — or refresh an existing one. This is the **producer** companion to
`/lr:workspace-pull` (the consumer):

```
workspace-init  =  producer  (writes lore-workspace.md, optional git root, README, memory file)
workspace-pull  =  consumer  (reads those descriptors, clones/pulls children, maintains .gitignore)
```

> **Engine note — which memory file.** Resolve the workspace **memory-file** name from your selected
> engine profile (`<framework-root>/docs/engines/<engine>.md`, selected at boot): **`CLAUDE.md` on
> Claude Code, `AGENTS.md` on Codex and Cursor**. Use that resolved filename everywhere below. Do
> **not** default to `CLAUDE.md` on Codex or Cursor.

> **Precondition.** The user must already have framework context loaded to run this skill — a session
> started with the plugin (Claude `--plugin-dir` / installed plugin; Codex `codex plugin add`; Cursor
> `--plugin-dir`), or the mid-session fallback of reading `.cursor-skills/lr-workspace-init/SKILL.md`
> directly. An empty directory with no framework loaded cannot run it; bootstrap by cloning the
> framework, launching an engine with it loaded, then running `/lr:workspace-init` from the workspace
> root.

## Modes

| Mode | When | What it does |
|------|------|--------------|
| **Setup** | Workspace not yet initialized | Interactive wizard → confirmation gate → write artifacts → run `workspace-pull` → write memory-file section |
| **Refresh** | Already initialized | Update the memory-file managed section only |
| **Reconfigure** | `--reconfigure` | Re-run the setup interview (git settings + descriptor), confirming overwrites |

Hard rename from `/lr:init` (no alias). Legacy `/lr:init` markers are migrated on first run — see
*Legacy markers* below.

### Is the workspace initialized?

A workspace is **initialized** when **either**:

1. `<workspace>/lore-workspace.md` exists, **or**
2. `<workspace>/<memory-file>` contains a well-formed `<!-- lr:workspace-init:start -->` … `end`
   marker pair.

| State | Mode (no flag) |
|-------|----------------|
| Neither | **Setup** |
| One or both | **Refresh** |

### Flags

| Flag | Behavior |
|------|----------|
| *(none)* | Auto-detect setup vs refresh |
| `--refresh` | Force memory-file refresh only |
| `--reconfigure` | Re-run the setup interview (git init/origin + descriptor); confirm overwrites |

**Adding a repo** is *not* a reconfigure: prefer editing `lore-workspace.md` and running
`workspace-pull`. Use `--reconfigure` only for git init/origin changes or a full re-interview.

---

## Setup mode — execution order

Steps are numbered in execution order. **No file is written before the Step 4 confirmation gate.**

### Step 0 — Context

Resolve `<workspace>` (cwd), `<memory-file>` (engine profile), `<framework-root>`.

### Step 1 — Discover starting state

Report what exists: `lore-workspace.md`, the memory file and any markers, the workspace git state
(git repo? origin remote?), and top-level child subdirs. Suggest candidate remotes from existing
subdirs that have a `lore-repo.md` or a `git remote get-url origin`.

### Step 2 — Workspace-level repos

Ask which **high-level repositories** belong in this workspace, offering a ranked shortlist built
from Step 1's suggestions.

**Wizard copy must state:** include the lore **agent repos themselves**; each agent repo's own
domain dependencies (declared in its `lore-repo.md`) are cloned automatically by `workspace-pull`
phase 2 — do not list those here.

Confirm the derived URL → dirname table before proceeding.

### Step 3 — Workspace git tracking

Ask: **Track this workspace as a git repository?**

**Wizard copy must state the tradeoff:**

| Choice | Consequence |
|--------|-------------|
| No | No team descriptor sharing via git; no phase-0 pull; no `.gitignore` automation for children. |
| Yes | Team can share `lore-workspace.md`; `workspace-pull` manages `.gitignore`; optional remote. |

- **3a — Git init.** `git -C <workspace> init` if needed. On failure: report, skip 3b, continue to
  Step 4; the user can fix later via `--reconfigure`.
- **3b — Remote origin (optional).** Ask for an `origin` URL or skip. `remote add` (or `set-url` if
  origin already exists) only after confirmation. **Never auto-commit or auto-push.**

### Step 4 — Confirmation gate

Show the full plan before any writes:

```
Will create/update:
  - lore-workspace.md (N repos: ...)
  - .gitignore (if git workspace)
  - README.md (team join instructions)
  - git init + origin (if chosen)
Then run workspace-pull, then write <memory-file> managed section.
Proceed? (yes/no)
```

`no` → stop without writing anything.

### Step 5 — Write `lore-workspace.md`

Frontmatter: `description` + block-form `repos:`. Optional body is user prose. On `--reconfigure`,
rewrite **only** the `description` + `repos:` frontmatter keys — preserve any other frontmatter keys
and the entire body.

### Step 6 — Seed `.gitignore` (git workspace only)

**Idempotent.** If `.gitignore` exists, do not truncate or overwrite — only append any missing
**standard workspace-owned** lines below. `workspace-pull` phase 3 re-asserts these same lines and
owns the child-repo `/<dirname>/` entries; reconfigure must not wipe either. When creating a new
file:

```gitignore
# Child repositories — managed by /lr:workspace-pull (lore-framework v25+)
# Do not commit nested repo contents into the workspace repo.

/.worktrees/
/.lr-beings/
/.tmp/
```

| Line | Holds |
|------|--------|
| `/.worktrees/` | Non-default-branch checkouts (`docs/worktrees.md`) |
| `/.lr-beings/` | Lore Beings Keeper runtime state (`docs/beings.md`) |
| `/.tmp/` | Local scratch — debug logs, disposable fixture repos, other throwaways. Prefer `.tmp/<name>/` over a top-level directory for anything that should not look like a workspace child. |

### Step 7 — Write `README.md` (default yes)

A minimal team-join template, created unless the user declined it at the Step 4 gate. Skip when
there is no git remote (local-only workspace has nothing to clone):

```markdown
# <workspace description>

## Join this workspace

git clone <origin-url> && cd <dirname>
/lr:workspace-pull
/lr:workspace-init --refresh
/lr:boot <primary-agent>
```

### Step 8 — Run `workspace-pull`

Invoke `<framework-root>/scripts/workspace-pull` against the workspace. On failure, report that the
descriptor artifacts are already on disk and give the recovery path:

```
workspace-pull failed. Artifacts on disk: lore-workspace.md, .gitignore, README.md.
Recovery:
  1. Fix the reported error (auth, URL, conflict)
  2. /lr:workspace-pull
  3. /lr:workspace-init --refresh
```

The memory file is intentionally **not** written yet — agents may not be on disk until the pull
succeeds.

### Step 9 — Write memory-file managed section

Written **after** `workspace-pull` so the agent scan reflects real disk state. Markers:
`<!-- lr:workspace-init:start -->` … `<!-- lr:workspace-init:end -->`. Content outside the markers is
the user's and is never touched. If the agent scan finds nothing, emit the fallback line in the
`### Agents` block:

> _(Run `/lr:workspace-pull` then `/lr:workspace-init --refresh` to populate)_

Use engine-aware command notation in the managed section:

- **Claude:** `/lr:workspace-pull`, `/lr:boot`, `/lr:workspace-init`
- **Cursor/Codex:** `/lr-workspace-pull`, `/lr-boot`, `/lr-workspace-init` (or engine-neutral prose,
  e.g. "the workspace-pull skill").

### Step 10 — Summary

Print next steps (do **not** run the register-repo wizard — deferred to v26):

```
Optional: /lr:register-repo <repo-dirname>   # per-agent boot shortcuts

Commit when ready:
  git -C "<workspace>" status
  git add lore-workspace.md .gitignore README.md <memory-file>
  git commit -m "Initialize lore workspace"
  git push -u origin HEAD
```

---

## Refresh mode

1. Read the managed section (`lr:workspace-init` markers; or legacy `lr:init` markers with a
   migration offer — see below).
2. Build the canonical payload (v2) from disk state (`lore-workspace.md`, agent scan).
3. Identical → report "already current" and stop.
4. Otherwise → show a diff **scoped to the managed section only** → confirm → replace.

Refresh does **not** modify `lore-workspace.md` or `.gitignore` and runs no git commands. An empty
agent scan yields the fallback text in the payload.

## Reconfigure mode

Re-run Steps 2–9 with confirmation. Step 3a (`git init`) is idempotent on an existing repo; Step 6
only appends missing standard workspace-owned lines (`/.worktrees/`, `/.lr-beings/`, `/.tmp/`) and
never overwrites `.gitignore`. Reconfigure does not delete child repos that were removed from the
descriptor.

---

## Marker protocol

Framework-managed content is delimited by two HTML-comment markers, each on its own line:

```
<!-- lr:workspace-init:start -->
... managed content ...
<!-- lr:workspace-init:end -->
```

Content outside the markers is the user's and is never touched. Markers must appear at most once per
file. If either appears without its pair, or more than once, report an error with file offsets and
stop — do not attempt repair.

### Legacy markers

A workspace initialized by the old `/lr:init` carries `<!-- lr:init:start -->` … `end`. On the first
`/lr:workspace-init` run, **offer to migrate** them to `lr:workspace-init:*`. If the user declines,
refresh inside the old markers for this release; `/lr:check` #23 warns until they are migrated.

## Canonical payload (v2)

The exact content of the framework-managed section, markers included:

~~~markdown
<!-- lr:workspace-init:start -->
## Lore Framework Workspace

This directory is a Lore Framework workspace.

### Repositories
<dynamic dirnames, or "See lore-workspace.md">

### Agents
<dynamic agent names, or the populate fallback hint>

### Commands
- workspace-pull — refresh the workspace descriptor and all declared repos
- boot <agent> — load a lore agent
- workspace-init --refresh — update this section after a framework upgrade

### Conventions
- Top-level repos stay on their default branch (production state).
- Non-default-branch work → git worktree at `.worktrees/<repo>/<slug>/`.

Full convention: https://github.com/zroslaw/lore-framework/blob/main/docs/worktrees.md
<!-- lr:workspace-init:end -->
~~~

The worktrees link is the public GitHub URL, not `<framework-root>/docs/worktrees.md`, so a
user-facing file references a path that resolves whether the plugin is loaded or not.

## Idempotency and re-runs

`/lr:workspace-init` is safe to run any number of times. When the canonical payload evolves in a
later framework version, rerun it (or `--refresh`) to update the managed section; the
diff-and-confirm gate keeps user edits inside the markers from being silently lost.

## What `/lr:workspace-init` does NOT do

- Does not touch content outside the markers, or any file other than the ones listed in the Step 4
  plan.
- Does not auto-commit or auto-push — it prints the commit checklist and the user runs it.
- Does not three-way-merge the memory file — show-diff-and-confirm is the entire user-edit protocol.
- Does not delete child repos dropped from a descriptor (no `--prune`).

## See Also

- `docs/workspace-pull.md` — the consumer companion (clones/pulls declared repos).
- `docs/worktrees.md` — the worktree convention distributed into the memory file.
- `docs/conventions.md` — `lore-workspace.md` schema and the dual meaning of `repos:`.
- `docs/check.md` — check #23 (legacy `lr:init` markers).

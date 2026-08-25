# /lr:workspace-status

Diagnose the **workspace layer** — git state, descriptor drift, memory-file contract, child-repo
hygiene — and print every finding with the command that fixes it. Read-only: it writes nothing and
touches no network.

> **Which diagnostic do I want?** `workspace-status` diagnoses this workspace's git and descriptor
> state; `/lr:check` verifies content consistency inside agent repos; `/lr:doctor` diagnoses engine
> and plugin runtime problems.

This is the fourth of the four workspace commands, and the only read-only one:

```
workspace-init    initialize, or converge an initialized workspace to disk reality
workspace-pull    consume  — pull the workspace repo, clone/pull children
workspace-push    publish  — commit and push the framework-managed workspace files
workspace-status  diagnose — report what is off, and what would fix it
```

## Procedure

### Step 1 — Scan

Resolve `<workspace>` (the current working directory — run `pwd` if unsure; this is *not*
`<framework-root>`), then run:

```
python3 "<framework-root>/scripts/lr-core" workspace-scan --workspace "<workspace>"
```

Quote both substituted values — a space in either otherwise splits into extra argv entries.

The scanner is a **literate accelerator**: if it fails to complete (exit 2, no output, unparseable
output), apply the Script Fallback Contract (`docs/conventions.md`) — say in one line that it failed
and that you are proceeding by hand, then read `scripts/lr_core/workspace_scan.py` and execute the
steps in `cmd_workspace_scan`'s docstring and the helper functions it names. Its comments are the
normative procedure; do not improvise one from the function names.

`data.applicable: false` means this directory is not a workspace root (no `lore-workspace.md` and no
child `lore-repo.md`). Report that in one line and stop — it is an ordinary state, not an error.

### Step 2 — Render

The scanner emits finding **IDs and structured data**. This document owns the sentences. For each
entry in `data.findings`, print one line — severity, what is true, and the fix — using the catalog
below. Order is already severity-then-ID; keep it.

Never print the raw JSON, and never invent a finding the scanner did not emit: the whole point of
the split is that the trigger logic is deterministic and lives in one place.

Close with the counts, or — when `data.findings` is empty — the single line:

```
workspace clean
```

### Step 3 — Warnings

`warnings` in the envelope are about the *scan*, not the workspace. Five kinds are emitted: the
workspace is **not the root of its own git repo** (it sits inside an enclosing one, so every git
finding is suppressed — the one most likely to explain a surprisingly short report), an unreadable
`git status` (S1 and S12 suppressed), a symlinked child resolving outside the workspace, a
declared URL whose derived directory name is unsafe, and a descriptor — `lore-workspace.md` or any
child's `lore-repo.md` — whose frontmatter has no closing `---`. Print them separately from the
findings, one line each.

Treat that last one as suppressing the declarations themselves: an unterminated block is parsed by
consuming the rest of the file, so ordinary prose can be read as declarations and real ones can be
missed. The declared-repo set in that report is not trustworthy until the descriptor is fixed. A suppressed finding is not a clean
finding — if a warning says dirty-path detection was suppressed, say so rather than reporting S1 as
absent.

## Findings catalog

Severity is the scanner's; the wording is this table's.

| # | Fires when | Severity | Say | Fix |
|---|---|---|---|---|
| S1 | `managed_paths.dirty` is non-empty | warn | N framework-managed workspace file(s) have uncommitted changes — they exist only on this filesystem, and a teammate's `workspace-pull` receives a stale state. Name the paths. | `workspace-push` |
| S2 | `git.ahead > 0` | warn | N workspace commit(s) are not pushed. | `workspace-push` |
| S3 | git-tracked, no `origin`, and no `sharing: local` | info | The workspace is git-tracked but unshareable — `workspace-pull` phase 0 and the README join path are inert until a remote exists. | `git -C "<workspace>" remote add origin <url>`, or `workspace-init`, which also offers to record a deliberately local-only workspace instead |
| S4 | descriptors present, workspace not its own git root | info; **warn** when `data.enclosing_root` is set | This is a local-only workspace — a supported mode. Nothing here can be shared with a team until git tracking is enabled. If `data.enclosing_root` is set, say instead that the workspace sits inside another git repo at that path, which is a different and more serious condition: no workspace-level git operation is safe. | `workspace-init` (offers tracking); for the enclosing-repo case, move the workspace out or make it its own repo |
| S5 | top-level git repos on disk that no descriptor declares | info | Name them with their origin URLs. They are pulled (phase 4) but never cloned for a teammate, so a fresh checkout of this workspace will not contain them. | `workspace-init` (offers to declare them) |
| S6 | declared repos absent from disk, excluding any whose directory name is claimed by two URLs | warn | Name them. Declared repos that are missing mean this workspace is not fully materialized. A repo caught in a dirname collision is deliberately absent from this list and appears under S13 instead — `workspace-pull` cannot place it, so offering pull as the remedy would send the user into a second failure. | `workspace-pull` |
| S7 | a child git repo has no `/<dirname>/` line, or a standard ignore line is missing | warn | Report the two groups separately — uncovered child repos (their contents could be committed into the workspace repo) and missing standard ignore lines (`/.worktrees/`, `/.lr-beings/`, `/.tmp/`). | `workspace-pull` (phase 3 appends both) |
| S8 | a top-level repo is not on its default branch, or is on a detached HEAD | warn | **Check `detached` first.** When it is true, say the repo is **on a detached HEAD** and do not print a current branch — there is none, and `current` is null. Reported even when the default branch is unknown: being on no branch is off production state whatever the default is, and a commit made there is lost by the next checkout. **Otherwise** name the repo, its current branch, and its default. Either way: top-level repos hold production state, and branch work belongs in a worktree. | `docs/worktrees.md` — move the work to `.worktrees/<repo>/<slug>/`; for a detached child, `git -C <dirname> checkout <default>` — and when `default` is null, say to check out the repo's own default branch rather than printing a placeholder there is no value for |
| S9 | worktrees are registered on the workspace repo | info | Inventory them. Mark any the scanner reports `prunable` as stale (their directory is gone). | prune manually — `git -C "<workspace>" worktree prune` |
| S10 | any memory-file contract violation | warn | Translate each entry in `data.violations`: `agents_md_absent` (the workspace has no memory payload at all), `legacy_marker_format` (pre-v3 HTML-comment markers), `payload_in_claude_md` (the payload sits in `CLAUDE.md`, where other engines cannot read it), `claude_md_import_missing` (**Claude Code reads `CLAUDE.md`, not `AGENTS.md` — without the import line, every Claude Code session in this workspace starts with no workspace memory at all**), `section_<name>_missing`, `section_<name>_duplicated`. | `workspace-init` (converges the memory file and offers the marker migration) |
| S11 | agents on disk whose exact agent-directory path has no registered shortcut in any of the four shortcut locations (three workspace-local, plus legacy `~/.codex/skills/`) | info | Name them. When the same agent name exists in more than one repo, the scanner emits `<repo>/<agent>` so the target remains unambiguous. Registration is optional — they are always loadable via `boot <agent>` — but a shortcut is the faster entry point. | `register-agent <name>` (include the repo when the name is ambiguous), or `register-repo <repo>` for all of a repo's agents |
| S12 | dirty workspace-root paths outside the managed set, excluding framework scratch state (`.worktrees/`, `.lr-beings/`, `.tmp/`) | info | List them for visibility only. These are the user's own files; no framework command will touch them, and `workspace-push` deliberately leaves them alone. Framework scratch directories are excluded because they are neither: when they show as dirty the cause is a missing ignore line, which S7 reports and fixes. | none — informational |
| S13 | a declared child on disk is not a git repo, has no origin, or its origin disagrees with the declaration; two declared URLs derive to the same directory name; a declared URL yields an unsafe directory name; a child git repo's own name is unsafe for a `.gitignore` line; or a child symlink escapes the workspace | warn | Name the child and the reason. For two URLs claiming one directory, name both — `declared` is the first declarer, `actual` the second — and say that `workspace-pull` cannot place either until a descriptor is edited. A declared repo simply *absent* from disk is S6's, not this one's; a collision suppresses both S6 and the origin-mismatch reason for that directory, so one condition yields one row. When `dirname` is null there is no child to name — name the declared URL instead. An origin mismatch is the one to read carefully: `workspace-pull` will refuse to pull that repo until it is resolved. An unsafe *child* directory name cannot be ignored automatically at all: say so, and that renaming the directory is the fix — `workspace-pull` cannot help here | resolve per the `workspace-pull` conflict table (`docs/workspace-pull.md` § Conflict Handling); rename the directory for an unsafe name |
| S14 | `git.behind > 0` | info | N commit(s) are waiting upstream — **as of the last fetch**. `workspace-status` never fetches, so this figure can be stale in either direction; absence of S14 is not evidence of being current. | `workspace-pull` (phase 0) |
| S15 | a `~/.codex/skills/lr-*-agent/` shortcut exists for an agent in this workspace | info | Name the agents in `data.agents`. Since v37 Codex shortcuts are workspace-local (`.codex/skills/`), where git carries them to the team; these are in the user's home directory, outside the workspace repo, so no publish path reaches them and a teammate cloning this workspace does not get them. Name separately the subset in `data.also_workspace_local`, which already have a workspace copy — those are pure duplicates, listed twice in every Codex session. **That directory is user-global and agent names collide across repos by design, so a matched name is not proof the shortcut is this workspace's** — say to check the shortcut's own `from <agent-dir>` before deleting it. | `/lr:update` (migration 37 relocates them), or `register-agent <name>` per agent followed by deleting the home copy |
| S16 | the workspace repo itself is on a detached HEAD | warn | Say the workspace root is on a detached HEAD, and name the commit in `data.head` when present. This is the git state that makes the rest of this section quiet rather than loud: a detached HEAD has no upstream, so S2 and S14 cannot fire and their silence means nothing here. Any commit made in this state — by this session or an unattended one — belongs to no branch and is dropped by the next checkout, so say plainly that `workspace-push` must not be run until it is resolved. | `git -C "<workspace>" checkout <branch>`; if commits were already made detached, `git -C "<workspace>" branch <name> <sha>` first to keep them |
| S17 | a declared repo or registered agent has no canonical routing description, or `repo-context` is malformed/stale | warn | Name missing repositories and agents separately; duplicate agent names arrive as `<repo>/<agent>`. Render each `repo_context_issues` item with every location field it supplies (`repo`, `index`, or `line`) plus its reason. This is only the deterministic floor: `workspace-init` also judges whether present descriptions are useful and distinct enough for routing. | `workspace-init` investigates the affected repos/agents, aligns the whole routing set, updates canonical descriptions, and regenerates `AGENTS.md` |
| S18 | `plugin_config.missing` or `plugin_config.unresolvable` is non-empty | info | The committed project-scope plugin settings are absent or unresolvable, so a teammate who clones this workspace does not get `lr` without installing it by hand. Name the files and which condition each is in. **`missing` and `unresolvable` route differently:** `missing` means a key is absent and `workspace-init` will add it; `unresolvable` means the file cannot be read or safely merged — bad encoding, invalid JSON, or one of our own keys holding a value of the wrong type — and `workspace-init` will refuse to touch it, so a human must fix it first. Never report an `unresolvable` file as something `workspace-init` will write. Anything in `data.disabled` is **not** drift: an explicit `false` is a deliberate choice, so name it only as context and never route the user to a fix that undoes it. Codex has no project-scope plugin mechanism at all, so it is absent from this finding by design rather than by omission. | `workspace-init` (writes both files; an unparseable file must be fixed by hand first) |

## Why the scanner emits IDs and this doc emits words

The seam between them is the one that goes wrong by default. A script string that reads like a
finished message gets printed as one, and printing it *looks* like handling the situation — so the
executor never reaches the doc that owns the remedy, and the user gets a symptom with no fix. The
scanner therefore emits `{"id", "severity", "data"}` and nothing sentence-shaped; this table is the
only place a finding's wording exists.

The same split is why four skills can share one scan without four copies of the rules:
`workspace-status` renders every finding, `/lr:check` #22–#24 render the subset they own,
`workspace-init` interviews from the list (converging means driving it to zero), and
`workspace-push` takes its path set from `data.managed_paths.set`.

## No network, and what that costs

Every git query is local-refs-only, so this is cheap enough to run on every `/lr:check`:

| Fact | Command |
|---|---|
| ahead / behind | `git rev-list --left-right --count @{u}...HEAD` |
| default branch | `git symbolic-ref --short refs/remotes/origin/HEAD` (absent → S8 suppressed, never guessed) |
| origin URL | `git remote get-url origin` |
| dirty paths | `git status --porcelain -z` (includes untracked) |
| worktrees | `git worktree list --porcelain` |

The consequence is S14's caveat above. `workspace-init` Step 6 *does* fetch, because it is about to
make a publication decision — a different contract, and the only place in the workspace layer that
touches the network beyond `workspace-pull`'s own clones.

## What `/lr:workspace-status` does NOT do

- No writes, no commits, no `.gitignore` edits, no shortcut regeneration — every fix is a command it
  names and the user runs.
- No fetch, clone, or pull.
- No inspection inside agent repos beyond their descriptors and branch state — content consistency
  is `/lr:check`'s job.

## See Also

- `docs/workspace-init.md` — the converge path; every S-finding above is something init can drive to
  zero, and its Step 1 runs this same scanner.
- `docs/workspace-push.md` — the publish path (S1, S2).
- `docs/workspace-pull.md` — the consume path (S6, S7, S13, S14).
- `docs/check.md` — checks #22–#24 consume the same scan for the workspace-scoped subset.
- `docs/conventions.md` — Script Fallback Contract; `lore-workspace.md` schema including
  `sharing: local` and `repo-context`.

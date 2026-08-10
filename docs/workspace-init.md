# /lr:workspace-init

Initialize a lore **workspace** — or **converge** an initialized one back to disk reality. One entry
point, no mode flags: on an empty directory it interviews; on a live workspace it re-scans, offers
what drifted, and writes nothing if nothing drifted.

```
workspace-init    initialize / converge  (this doc)
workspace-pull    consume   — pull the workspace repo, clone declared repos, pull every top-level repo
workspace-push    publish   — commit and push the framework-managed workspace files
workspace-status  diagnose  — read-only report of the same findings this skill resolves
```

> **Converge = drive the scanner's findings to zero.** This skill and `/lr:workspace-status` read the
> same scan (`docs/workspace-status.md` § Findings catalog). Status names what is off; init offers to
> fix it. That is the whole relationship, and it is why this doc carries no second checklist of
> "things to check" that could drift from the S-list.

> **Precondition.** The user must already have framework context loaded to run this skill — a session
> started with the plugin (Claude `--plugin-dir` / installed plugin; Codex `codex plugin add`; Cursor
> `--plugin-dir`), or the mid-session fallback of reading `.cursor-skills/lr-workspace-init/SKILL.md`
> directly. An empty directory with no framework loaded cannot run it; bootstrap by cloning the
> framework, launching an engine with it loaded, then running this skill from the workspace root.

## Invocation

No flags in the common path. `--dry-run` prints the plan and writes nothing (a debugging aid).

`--refresh` and `--reconfigure` are **retired** — init converges either way. If one is supplied,
print exactly one line and proceed normally:

```
workspace-init now converges — the flag is no longer needed.
```

## Execution order

**No file is written before the Step 3 confirmation gate.**

### Step 0 — Context

Resolve `<workspace>` (the current working directory — run `pwd` if unsure; this is *not*
`<framework-root>`) and `<framework-root>`. Note the engine from your boot-time profile: it affects
Step 2 item 5 and the report wording only. It does **not** select a memory filename — the payload is
engine-neutral and always lands in `AGENTS.md` (§ The memory-file contract below).

### Step 1 — Observe

```
python3 "<framework-root>/scripts/lr-core" workspace-scan --workspace "<workspace>"
```

Quote both substituted values. Everything this skill needs in order to decide is in that output:
descriptors and the declared repo set, memory-file format and per-section state, git/remote/branch/
ahead-behind, children with their git and declaration status, registered shortcuts, the
framework-managed path set with dirty classification, and the finding list.

**Perform no independent discovery.** A second, hand-rolled scan is how the interview comes to
disagree with what `workspace-status` will say five minutes later.

The scanner is a **literate accelerator**: on failure (exit 2, no output, unparseable output) apply
the Script Fallback Contract (`docs/conventions.md`) — say in one line that it failed and that you
are proceeding by hand, then read `scripts/lr_core/workspace_scan.py` and execute the steps in
`cmd_workspace_scan`'s docstring and the helper functions it names.

### Step 2 — Determine the work

Take the **first** row that matches, in this order:

| # | Observed | Path |
|---|---|---|
| 1 | Zero findings **and** `memory.agents_md.format` is `v3` | **Stop.** Report `already current` and write nothing |
| 2 | No `lore-workspace.md` **and** `memory.agents_md.format` is `absent` or `none` | **Initialize** — full interview |
| 3 | Anything else | **Converge** — the scanner's findings are the work list |

Ask only what is genuinely open. A converging run on a healthy workspace should be silent; a
converging run that re-asks the founding interview is a bug, not thoroughness.

**Interview items**

1. **Repos.** Which top-level repos belong here. Rank the suggestions: undeclared child git repos
   already on disk first, with their origin URLs (finding S5), then any other candidate. Lore agent
   repos and ad-hoc repos go into the same flat `repos:` list — the distinction is auto-detected at
   pull time by `lore-repo.md` presence and is deliberately not recorded in the descriptor.

   State in the wizard copy: include the lore **agent repos themselves**; each agent repo's own
   domain dependencies (declared in its `lore-repo.md`) are cloned automatically by `workspace-pull`
   phase 2 — do not list those here. Confirm the derived URL → dirname table before proceeding.

2. **Framework repo.** Offer to add `https://github.com/zroslaw/lore-framework.git` to `repos:`
   (**default yes**). This materializes the no-plugin fallback carried in the memory file: an engine
   without the `lr` plugin finds the framework's `docs/` inside the workspace. One keystroke to
   decline — a team on marketplace installs may reasonably not want the checkout.

3. **Git tracking.** If the workspace is not a git repo, ask whether to track it.

   | Choice | Consequence |
   |---|---|
   | Yes (recommended) | The team can share `lore-workspace.md`; `workspace-pull` phase 0 works; `workspace-push` has something to publish; `.gitignore` automation applies |
   | No | Supported local-only mode. No descriptor sharing, no phase-0 pull, no `.gitignore` automation |

   On yes: `git -C "<workspace>" init`. On failure, report, skip item 4, and continue — the
   descriptor artifacts are still worth writing.

4. **Remote.** If there is no `origin`, offer to set one (`git -C "<workspace>" remote add origin
   <url>`). This is skippable — but a skip is **recorded, not merely tolerated**: write
   `sharing: local` into `lore-workspace.md`'s frontmatter.

   That key exists for one reason. Without it, finding S3 fires forever about a state the user chose
   on purpose, and a finding a user can never clear teaches them to skim the whole report. `sharing:
   local` suppresses S3; adding a remote later clears the key.

5. **Legacy Codex shortcuts.** When finding S15 is present: offer to re-register the named agents, so
   their shortcuts move from `~/.codex/skills/` to the workspace-local `.codex/skills/` that
   `workspace-push` can publish. Offer the deletion of each home-directory copy as part of the same
   plan, and only for a shortcut whose boot line names an `<agent-dir>` under this workspace —
   `~/.codex/skills` is user-global, so a same-named shortcut may belong to a different workspace.
   `/lr:update` does the same relocation in bulk via `migrations/37.md`; this offer exists for a
   workspace whose repos are already at version 37.

### Step 3 — Confirmation gate

One plan, listing every file write and every git action, then a single yes/no. Show a **scoped diff**
for any managed section that already exists and will be replaced.

```
Will write:
  lore-workspace.md          <N repos: ...>
  .gitignore                 <+N lines>
  README.md                  <new / unchanged / skipped: no remote>
  AGENTS.md                  <sections: Lore Framework, Repositories, Agents>
  CLAUDE.md                  <import stub: create / already present>
Will run:
  git init / git remote add origin <url>     (if chosen)
  workspace-pull
Proceed? (yes/no)
```

`no` → stop, zero writes.

### Step 4 — Write

- **`lore-workspace.md`** — frontmatter `description` + block-form `repos:`, plus `sharing: local`
  when item 4 was declined. Preserve every other frontmatter key and the entire markdown body: the
  body is user-owned onboarding prose.
- **`.gitignore`** — the standard ignore lines (`/.worktrees/`, `/.lr-beings/`, `/.tmp/`) plus a
  `/<dirname>/` line for **every child git repo on disk**, declared or not, and for every declared
  repo. Append-only, idempotent by exact line, never truncating.

  Skip — and report — any child whose directory name would corrupt the file as a pattern: a leading
  `!` or `-`, or any of `*`, `?`, `[`. A directory named `!notes` is creatable locally even though no
  git host would allow it as a repo name, and `/!notes/` is a negation that un-ignores something
  else. An unignored child is a visible problem; a corrupted `.gitignore` is a silent one. This is
  finding S13, and renaming the directory is the fix.

  Declaration governs cloning and pulling; ignoring governs safety. An undeclared clone can have its
  contents committed into the workspace repo just as easily as a declared one, so the ignore set is
  the wider of the two.
- **`README.md`** — the team-join card, written only when an `origin` exists (a local-only workspace
  has nothing to clone):

  ```markdown
  # <workspace description>

  ## Join this workspace

  git clone <origin-url> && cd <dirname>
  workspace-pull        # clone the declared repos
  workspace-init        # converge: memory file, shortcuts, ignore lines
  boot <primary-agent>
  ```
- **`AGENTS.md`** — the v3 payload (§ Canonical payload), with the marker migration when applicable
  (§ Migration from markers).
- **`CLAUDE.md`** — the import stub only, idempotent (§ The `CLAUDE.md` import stub).

### Step 5 — Run `workspace-pull`

Invoke `<framework-root>/scripts/workspace-pull` with the workspace path. Its phase 3 re-asserts the
same `.gitignore` lines, so the two writers agree by construction.

On failure, report that the descriptor artifacts are already on disk and give the recovery path:

```
workspace-pull failed. Artifacts on disk: lore-workspace.md, .gitignore, README.md, AGENTS.md.
Recovery:
  1. Fix the reported error (auth, URL, conflict)
  2. workspace-pull
  3. workspace-init
```

### Step 6 — Remote synchronization

Only when the workspace is git-tracked and is its own git root. **Fetch first** —
`git -C "<workspace>" fetch origin` — then decide from history relationships.

Never decide this by counting local commits. A workspace can be committed to by something other than
the person running this skill: another session, or an autonomous agent (`docs/beings.md`). "No local
commits yet" is not evidence of a fresh workspace, and treating it as such is how a join silently
becomes a divergence.

| Observed | Meaning | Action |
|---|---|---|
| No `origin` remote | Local-only workspace | Skip. Report that push and team sharing are inert until a remote exists |
| `git ls-remote --heads origin` is empty | Founding a new shared workspace | Stage the framework-managed paths, commit `chore(lore): initialize lore workspace`, `git push -u origin HEAD`. **Confirm this with its own one-line yes/no** — the Step 3 plan was built before the fetch, so it could not have disclosed a publish action, and this one goes outward to a shared remote |
| `git merge-base --is-ancestor HEAD origin/<branch>` | Local is behind or equal | Fast-forward, re-run Steps 1–5 against what arrived, then commit and push any remaining delta |
| `git merge-base --is-ancestor origin/<branch> HEAD` | Local is ahead | Commit the delta and push |
| A merge-base exists, neither is an ancestor | Diverged | **Stop.** Suggest `workspace-pull` (phase 0) then `workspace-push`. Never merge automatically |
| **No merge-base at all** | Unrelated histories — a *join* onto someone else's workspace | **Stop** and offer two explicit choices — see *Adopting a remote* below. Never `--allow-unrelated-histories` automatically |

**Adopting a remote (the join case).** By the time Step 6 runs, Step 4 has already written
`lore-workspace.md`, `.gitignore`, `README.md`, `AGENTS.md`, and possibly `CLAUDE.md` into the
working tree — and a workspace worth joining has its own versions of those same files. So adopting
the remote **replaces content this run just produced**, and may replace user prose that was in the
local `AGENTS.md` before this run. Say that in the offer, then preserve everything before switching:

1. **Commit the current state onto a side branch first**, so nothing uncommitted can be lost:
   `git -C "<workspace>" checkout -b pre-join-<short-sha>` then stage **all** of it —
   `git -C "<workspace>" add -A` — and commit `chore(lore): local state before joining <origin>`.
   Staging everything is correct *here* and nowhere else in the workspace layer: the point is a
   complete rescue point, not a publication.
2. **Switch to the remote's history:** `git -C "<workspace>" checkout -B <branch> origin/<branch>`.
   Use this rather than `reset --hard` — with the rescue commit in place either is recoverable, but
   `checkout -B` never runs against a dirty tree by accident.
3. **Re-run Steps 1–5** against what arrived. Convergence re-derives the framework-managed content
   from the joined workspace's descriptors.
4. **Tell the user the branch name.** `pre-join-<short-sha>` holds everything that was here before;
   any local prose worth keeping is recovered from it by hand (`git show pre-join-<short-sha>:AGENTS.md`).

Option **(b)** is "this is a different workspace" — supply a different remote, or remove the origin.
Nothing is written in that case.

If the working tree carries uncommitted changes **outside** the framework-managed set when Step 6
reaches any branch-switching case, name them and confirm separately before touching the branch.
They are the user's own work and were never part of the Step 3 plan.

### Step 7 — Summary

Report what was written, what was synchronized, and what remains. Phrase each remaining item as the
scanner finding it corresponds to, so the wording matches what `workspace-status` says next time.

If anything framework-managed is now dirty or unpushed, name `workspace-push` — this skill does not
commit on its own outside Step 6's founding case.

---

## The memory-file contract

### Which file, and why it is not the engine's

**`AGENTS.md` is canonical. `CLAUDE.md` is a one-line import stub.** The framework writes the full
payload to `AGENTS.md` on every engine and never writes the payload to `CLAUDE.md`.

This is measured behavior, not a preference. Claude Code does **not** read `AGENTS.md`; it does read
`CLAUDE.md`, and it honors an `@AGENTS.md` import inside it, composed with whatever else that file
contains. Cursor and Codex read `AGENTS.md` directly. So one payload plus one import line reaches all
three engines, with one source of truth and no possibility of copy-drift.

The failure this replaces was silent: a workspace carrying only `AGENTS.md` gave every Claude Code
session **zero workspace memory**, with no error and nothing in any report.

### Canonical payload (v3 — sections, not markers)

`AGENTS.md` carries, in this order, before any user content:

~~~markdown
# <workspace description>

## Lore Framework

<!-- lr:managed — regenerated by workspace-init; edits here are overwritten -->

This directory is a [Lore Framework](https://github.com/zroslaw/lore-framework) workspace — named
agents with persistent, git-shared knowledge, usable from Claude Code, Codex, or Cursor.

Invoke skills as `/lr:<skill>` on Claude Code, `/lr-<skill>` on Cursor and Codex.

| Skill | What it does |
|---|---|
| `boot <agent>` | Load a lore agent (see Agents below) |
| `workspace-status` | Diagnose this workspace; every finding names its fix |
| `workspace-pull` | Pull the workspace repo, clone declared repos, pull every top-level repo |
| `workspace-push` | Commit and push the framework-managed workspace files |
| `workspace-init` | Initialize this workspace, or converge it after anything changed |

Conventions: top-level repos stay on their default branch (production state); non-default-branch
work goes in a git worktree under `.worktrees/<repo>/<slug>/`; local scratch under `.tmp/<name>/`.
Full convention: https://github.com/zroslaw/lore-framework/blob/main/docs/worktrees.md

No `lr` plugin in this engine? Clone the framework into the workspace —
`git clone https://github.com/zroslaw/lore-framework.git` — and use its `docs/` as the instruction
source, starting with `docs/agent-boot.md`.

## Repositories

<!-- lr:managed — regenerated by workspace-init; edits here are overwritten -->

- `<dirname>` — <description from lore-repo.md / lore-workspace.md, or "(no description)">

## Agents

<!-- lr:managed — regenerated by workspace-init and the register-agent family -->

- `<agent-name>` (`<repo-dirname>`) — <role description>. Boot: `lr-<agent-name>-agent`.
~~~

Notes:

- **Skill order follows the daily path** — boot first, diagnostics next, setup last — not the
  lifecycle order.
- **Engine-neutral notation.** Three engines read this one file, so skill references use the bare
  name with the one-line legend above the table, never a single engine's slash syntax.
- The `# <workspace description>` title is framework-written at creation and **user-owned
  afterwards**. Renaming the workspace must not fight the tool.
- **Repositories lists *declared* repos** — the union of `lore-workspace.md` `repos:` and every
  domain `repos:`. Undeclared git repos on disk are deliberately absent; they are finding S5, not a
  workspace fact.
- **Agents lists *registered* agents** — the "what can I boot here" answer. The shortcuts on disk
  across all three engines supply *membership* and, in their boot line, each agent's absolute
  `<agent-dir>`; the **role description comes from `<agent-dir>/role.md`'s frontmatter
  `description`**, and the repo dirname from that path. Do not try to read the description out of the
  shortcut — the Claude Code artifact is a single bootstrap line and carries none. Fall back to
  `Lore agent in <repo-dirname>` when `role.md` has no description. Agents present but unregistered
  do not appear; they are finding S11. With none registered, emit the single line:
  `_(No agents registered yet — run `register-agent` to add one.)_`

### Section ownership and parsing rules

- **Managed region.** A managed section runs from its exact level-2 heading line to the line before
  the next `^## ` heading, or EOF. The framework regenerates that region and touches nothing else.
- **Fenced code blocks do not contain headings.** When locating either boundary, ignore every line
  inside a ``` or `~~~` fence. This is load-bearing rather than pedantic: the canonical payload above
  is itself a fenced example full of literal `## Lore Framework` lines, and a user who pastes one
  into their own file would otherwise have it read as a real heading — which decides where a managed
  region *ends*, and so how much of their file gets overwritten. The scanner applies the same rule
  (`workspace_scan.outside_fences`).
- **Heading match.** Exact, case-sensitive, level-2: `## Lore Framework`, `## Repositories`,
  `## Agents`. First occurrence wins; a later duplicate is left alone and reported (S10).
- **A user-renamed or deleted framework heading:** recreate the canonical section at its canonical
  position and leave the orphaned section in place. `workspace-status` flags the duplication.
- **User edits inside a framework section** are overwritten at the next regeneration. Three things
  make that fair rather than surprising: the provenance comment marks the region at the point of use,
  Step 3 shows a scoped diff before replacing, and the boundary is ordinary markdown structure the
  user can see.
- **Section order:** framework sections first, in canonical order, then user sections. If user
  sections have been interleaved, edit section bodies in place and do **not** reorder the file;
  report non-canonical order as informational.
- **A file missing entirely** is created with the full payload.

### The `CLAUDE.md` import stub

~~~markdown
<!-- Lore Framework: this workspace's memory lives in AGENTS.md, shared across engines. -->

@AGENTS.md
~~~

- **Idempotent by line.** If `CLAUDE.md` exists and already contains a line whose trimmed content is
  `@AGENTS.md`, do nothing. Otherwise append the two lines above, preserving all existing content.
- **Never regenerate or truncate `CLAUDE.md`.** It is a user file the framework adds one line to.
  That line is the only framework-managed content in it.
- **A missing target is inert.** A `CLAUDE.md` importing an `AGENTS.md` that does not exist loads the
  rest of the file without error, so the order of the two writes is not load-bearing.
- **Other engines are unaffected.** Cursor and Codex read `AGENTS.md`; the stub is inert for them,
  and the comment line explains itself if a human opens it.
- **This is engine behavior, not a contract.** It is verified by lifecycle scenario `test_18b`, not
  assumed to hold — a future engine change would otherwise reintroduce the silent-outage failure this
  design exists to fix.

### Migration from markers

A converging run that finds a `<!-- lr:workspace-init:start/end -->` pair — or the pre-v25
`<!-- lr:init:* -->` pair — in either memory file offers a **one-time conversion**:

1. Parse the managed block, discard it, and re-render as v3 sections in `AGENTS.md`.
2. Preserve all content outside the markers verbatim, in place.
3. Drop the markers.
4. If the marker block was in `CLAUDE.md`, replace it with the import stub and write the payload to
   `AGENTS.md`.

Offered, never forced. Declining keeps the old format working for this release; `/lr:check` #23 warns
until it is migrated.

## Idempotency and re-runs

Safe to run any number of times. A workspace already at canonical state exits with `already current`
and writes nothing — that property is what makes "init converges" safe to recommend as the routine
follow-up to anything that changed on disk.

## What `/lr:workspace-init` does NOT do

- Does not write any file outside the Step 3 plan, and does not touch user content outside a managed
  section (or, in `CLAUDE.md`, outside the single import line).
- Does not commit or push, **except** Step 6's founding case (an empty remote), which is confirmed at
  the Step 3 gate like every other write. Ongoing publication is `/lr:workspace-push`.
- Does not merge divergent histories, and never passes `--allow-unrelated-histories`.
- Does not three-way-merge the memory file — show-diff-and-confirm is the entire user-edit protocol.
- Does not delete child repos dropped from a descriptor (no `--prune`).
- Does not decide agent membership. The Agents section is *rendered* from the registered shortcuts on
  disk; registration remains the single membership authority (`docs/register-repo.md`).

## See Also

- `docs/workspace-status.md` — the read-only counterpart; the findings catalog this skill converges.
- `docs/workspace-pull.md` — the consumer companion; Step 5 runs it.
- `docs/workspace-push.md` — the publisher; where dirty framework-managed files go after this skill
  writes them.
- `docs/worktrees.md` — the convention distributed into the memory file.
- `docs/conventions.md` — `lore-workspace.md` schema (including `sharing: local`), the dual meaning
  of `repos:`, and the Script Fallback Contract.
- `docs/check.md` — #22 (ignore coverage), #23 (legacy memory-file format), #24 (publication state).

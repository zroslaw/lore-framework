# /lr:workspace-init

Initialize a lore **workspace** — or **converge** an initialized one back to disk reality. One entry
point, no mode flags: on an empty directory it interviews; on a live workspace it re-scans, offers
what drifted, and writes nothing if nothing drifted.

Its `Repositories` and `Agents` sections are a **routing map for an unfamiliar AI**, not merely an
inventory. Each description must make three things clear: what the repo or agent owns, what useful
material it contains or knows, and when to inspect, boot, or attach it. The descriptions are judged
and aligned as one workspace-wide set so adjacent entries have clear boundaries.

```
workspace-init    initialize / converge  (this doc)
workspace-pull    consume   — pull the workspace repo, clone declared repos, pull every top-level repo
workspace-push    publish   — commit and push the framework-managed workspace files
workspace-status  diagnose  — read-only report of the same findings this skill resolves
```

> **Converge = drive the scanner's findings to zero, as far as this skill owns them.** This skill and
> `/lr:workspace-status` read the same scan (`docs/workspace-status.md` § Findings catalog). Status
> names what is off; init offers to fix what init can fix. That is the whole relationship, and it is
> why this doc carries no second checklist of "things to check" that could drift from the S-list.
> Several findings' fixes belong to other commands — `workspace-pull` for what is behind or missing,
> `workspace-push` for what is unpublished, `register-agent` for membership. A converging run leaves
> those standing and Step 9 names them; it does not report a clean workspace on their account.

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
repository/agent routing inventory with canonical description sources, the framework-managed path
set with dirty classification, and the finding list.

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
| 0 | `applicable` is `false` | **Initialize** — full interview. A greenfield directory: the scan stops at the applicability gate, so `memory`, `git`, and `descriptors` are absent from the envelope and no later row can be evaluated. This is the documented cold start, not an error |
| 1 | Zero findings, `memory.agents_md.format` is `v3`, **and the routing audit below passes** | **Stop.** Report `already current` and write nothing |
| 2 | No `lore-workspace.md` **and** `memory.agents_md.format` is `absent` or `none` | **Initialize** — full interview |
| 3 | Anything else | **Converge** — the scanner's findings are the work list |

Ask only what is genuinely open. A converging run on a healthy workspace should be silent; a
converging run that re-asks the founding interview is a bug, not thoroughness.

The routing audit is semantic, so the scanner cannot decide it from length or string patterns. Read
`data.routing.repositories` and the **registered** entries in `data.routing.agents` as one set. It
passes only when an unfamiliar agent could choose between the entries without opening every repo.
Missing text, category-only text, overlapping descriptions, and descriptions that never say when to
use the entry all fail. A short description may pass; length alone is never a failure signal. Failed
entries are handled in Step 7 after every declared repo has been materialized.

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

5. **Legacy Codex shortcuts.** When finding S15 is present: offer to re-register the named agents —
   the **Register Agent** procedure in `docs/register-repo.md`, one per agent — so their shortcuts
   move from `~/.codex/skills/` to the workspace-local `.codex/skills/` that `workspace-push` can
   publish. For an agent listed in `data.also_workspace_local` the workspace copy already exists, so
   there is nothing to write and that agent's offer is the deletion alone. Either way the deletion of
   the home copy belongs to the same plan, and is offered only for a shortcut whose boot line names
   an `<agent-dir>` under this workspace — `~/.codex/skills` is user-global, so a same-named shortcut
   may belong to a different workspace.
   `/lr:update` does the same relocation in bulk via `migrations/37.md`; this offer exists for a
   workspace whose repos are already at version 37.

6. **Routing descriptions.** Do not ask the user to write better copy from memory. Record which
   repository and registered-agent descriptions failed the routing audit; Step 7 investigates their
   actual repos, drafts an aligned set, and asks once with scoped diffs before writing it.

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

**Read `lore-workspace.md`, `AGENTS.md`, and `CLAUDE.md` here, at the top of Step 4, and build each
replacement from *that* read** — not from any copy read earlier in this session. Every one of these
is rewritten whole while preserving user-owned content, so the content you preserve must come from
the newest read of the file, taken after the gate rather than before it.

The reason is the gap: Step 1's scan never emits file bodies, and Step 2's interview plus Step 3's
gate can sit for minutes waiting on a human. This workspace can have another session — or an
unattended one — writing in that window, and a whole-file rewrite built from an older read discards
whatever it wrote, silently and with no conflict.

Then check what you just read against the plan the user approved in Step 3: if the declared repo
set, the memory-file format, or the section list is no longer what the plan described, **stop and
report it instead of writing**. The approval was given for a starting state that no longer exists.
(`.gitignore` and `README.md` need no such check — the first is append-only by exact line and the
second is regenerated from scratch, so neither can discard a concurrent edit.)

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

### Step 6 — Remote preparation

Only when the workspace is git-tracked and is its own git root. **Fetch first** —
`git -C "<workspace>" fetch origin` — then decide from history relationships.

Never decide this by counting local commits. A workspace can be committed to by something other than
the person running this skill: another session, or an autonomous agent (`docs/beings.md`). "No local
commits yet" is not evidence of a fresh workspace, and treating it as such is how a join silently
becomes a divergence.

| Observed | Meaning | Action |
|---|---|---|
| No `origin` remote | Local-only workspace | Skip. Report that Step 8 can commit but cannot push until a remote exists |
| `git ls-remote --heads origin` is empty | Founding a new shared workspace | Record the empty remote as Step 8's publication target; do not commit or push yet |
| `git merge-base --is-ancestor HEAD origin/<branch>` | Local is behind or equal | When behind, fast-forward and re-run Steps 1–5 against what arrived; when equal, continue — see *Fast-forwarding over Step 4's writes* below. Defer every commit and push to Step 8 |
| `git merge-base --is-ancestor origin/<branch> HEAD` | Local is ahead | Continue; show the commits that would ride along in Step 8's single publication plan |
| A merge-base exists, neither is an ancestor | Diverged | **Stop.** Suggest `workspace-pull` (phase 0) then `workspace-push`. Never merge automatically |
| **No merge-base at all** | Unrelated histories — a *join* onto someone else's workspace | **Stop** and offer two explicit choices — see *Adopting a remote* below. Never `--allow-unrelated-histories` automatically |

**Fast-forwarding over Step 4's writes.** If the fetch shows that upstream advanced while this run
was preparing files, stop and leave every file intact. Do not checkout, stash, or discard even a
framework-managed path: `AGENTS.md` and `lore-workspace.md` may also contain user-owned content.
Tell the user upstream changed and rerun after the workspace has been pulled or resolved.

**Adopting a remote (the join case).** By the time Step 6 runs, Step 4 has already written
`lore-workspace.md`, `.gitignore`, `README.md`, `AGENTS.md`, and possibly `CLAUDE.md` into the
working tree — and a workspace worth joining has its own versions of those same files. So adopting
the remote **replaces content this run just produced**, and may replace user prose that was in the
local `AGENTS.md` before this run. Say that in the offer, then preserve everything before switching:

1. **Commit the current state onto a side branch first**, so nothing uncommitted can be lost:
   `git -C "<workspace>" checkout -b pre-join-<suffix>` then stage **all** of it —
   `git -C "<workspace>" add -A` — and commit `chore(lore): local state before joining <origin>`.
   Staging everything is correct *here* and nowhere else in the workspace layer: the point is a
   complete rescue point, not a publication.

   `<suffix>` is `git rev-parse --short HEAD` when there is a commit to name. There need not be:
   this branch is reached whenever no merge-base exists, which includes a repo `git init`-ed earlier
   in *this* run and pointed at a populated remote — an unborn HEAD with no sha to substitute. Then
   use `pre-join-local`, and if that name is taken, append `-2`, `-3` until one is free. Never
   proceed with the switch until the rescue branch exists and the commit succeeded.
2. **Switch to the remote's history:** `git -C "<workspace>" checkout -B <branch> origin/<branch>`.
   Use this rather than `reset --hard` — with the rescue commit in place either is recoverable, but
   `checkout -B` never runs against a dirty tree by accident.
3. **Re-run Steps 1–5** against what arrived. Convergence re-derives the framework-managed content
   from the joined workspace's descriptors.
4. **Tell the user the branch name.** `pre-join-<suffix>` holds everything that was here before;
   any local prose worth keeping is recovered from it by hand (`git show pre-join-<suffix>:AGENTS.md`).

Option **(b)** is "this is a different workspace" — supply a different remote, or remove the origin.
Nothing is written in that case.

If the working tree carries uncommitted changes **outside** the framework-managed set when Step 6
reaches any branch-switching case, name them and confirm separately before touching the branch.
They are the user's own work and were never part of the Step 3 plan.

### Step 7 — Investigate and align routing descriptions

Re-run `workspace-scan` now that Step 5 has materialized the declared repo set. Audit
`data.routing.repositories` and the registered entries of `data.routing.agents` together, using the
Step 2 routing test. `data.routing.repo_context_issues` is always work to resolve.

For every failed repository description, perform a **repository routing investigation**. This is a
real repo investigation, not a README paraphrase:

1. Read the repo descriptor (when present), README, workspace/agent instructions, manifests, and
   top-level tree.
2. Read the architecture or documentation entry points, tests, and representative implementation
   code. Follow code far enough to establish the repo's owned behavior and its boundary with sibling
   repos. Do not pretend that reading every file is useful; the stopping condition is that the three
   routing questions have evidence-backed answers.
3. For a failed registered-agent description, read its `role.md` and `lore-context.md`, then inspect
   the referenced repo/lore areas needed to distinguish it from neighboring agents.
4. Keep short evidence notes per entry. Draft no final line until every failed entry has been
   investigated; writing independently is how adjacent descriptions end up overlapping.

Then synthesize the **whole set** together. Use parallel grammar and shared vocabulary. Each line
must say what the entry owns, what it contains or knows, and when to use it; it must also leave a
clear reason to choose each neighboring entry instead. Keep it compact enough for boot context —
normally one or two plain sentences — but never shorten by dropping a routing distinction. Keep
canonical `lore-repo.md` and `role.md` descriptions globally true: compare them against this
workspace to expose ambiguity, but do not bake a workspace-specific sibling list into shared repo
metadata that another workspace would rewrite differently.

Canonical write locations:

- Lore agent repo description → that repo's `lore-repo.md` frontmatter `description`.
- Registered agent description → its `role.md` frontmatter `description`.
- Ordinary repo description → `lore-workspace.md` frontmatter `repo-context`:

  ```yaml
  repo-context:
    - repo: product-api
      description: Owns the product API and its tests. Inspect for API behavior or server changes.
  ```

`repo-context` contains ordinary declared repos only. If an entry now has `lore-repo.md`, move its
description there and remove the workspace copy. Preserve every unrelated frontmatter key and all
markdown bodies.

Before writing, show one routing plan with scoped old→new diffs for every `lore-repo.md`, `role.md`,
`lore-workspace.md`, and the resulting `AGENTS.md` sections. Name unchanged descriptions too, so the
user can judge the alignment as a complete set. Ask one yes/no to apply the routing-description
updates. `no` leaves the routing files unchanged and continues to Step 8 with only the base init
changes.

Use the post-Step-4 bytes as the baseline for files Step 4 changed; those approved init writes must
not disqualify `lore-workspace.md` or `AGENTS.md`. For every other target, require the file to have
been clean in both index and worktree before this run; a pre-existing edit is a collision. Record
each target's baseline hash, including `AGENTS.md`, plus its approved post-write bytes and hash. At
the write boundary, re-read every target and stop if its hash changed. Otherwise update only the
`description` scalar or `repo-context` block, then regenerate only the managed routing sections in
`AGENTS.md`, preserving all user-owned content. Re-read and hash every written target again for the
Step 8 staging guard.

### Step 8 — One publication approval

Collect every Git root changed by this run. This may include the workspace repo plus child repos
whose `lore-repo.md` or `role.md` changed. One approval covers the whole publication, but Git still
requires one commit per repo.

Before asking, for every affected child repo:

1. Verify it is its own Git root, on its default branch, and has no unresolved merge/rebase. Resolve
   the default branch from `refs/remotes/origin/HEAD`; if it is unavailable, stop that repo.
2. Require an origin push target, fetch it, and compare against the exact fetched
   `origin/<default-branch>` ref. Stop on remote-only commits or divergence; never merge or force.
3. List the exact paths this run owns, their diffstats, the commit message, push target, unrelated
   dirty paths that remain untouched, and already-committed changes that would ride along.

For the workspace root, reuse Step 6's remote decision; a local-only workspace may be committed
without being pushed.

Use one final prompt:

```
Will commit and push these workspace-routing updates:
  <repo>  <owned paths>  -> <remote/branch or "commit only: no remote">
  ...
One narrow commit per repo; child repos publish first, workspace repo last.
Proceed? (yes/no)
```

`no` leaves the approved file updates on disk, uncommitted.

On `yes`, first verify every owned target still has the exact approved post-write hash. Stop that
repo if any byte changed. Then stage and commit only the explicit owned paths in each repo,
deletion-aware. Use
`chore(lore): improve workspace routing descriptions` for repos with routing changes and
`chore(lore): initialize lore workspace` for a founding workspace with base artifacts only. Verify
each created commit contains no path outside its approved set; undo an invalid commit with
`git reset --soft HEAD^` and stop before any push.

Push child repos first and the workspace repo last. That ordering prevents a shared `AGENTS.md` from
advertising canonical descriptions that failed to publish. A multi-repo push is not atomic: on any
failure, stop later pushes, never roll back or force-push the successful ones, and report exactly
which repos were pushed, committed only, or untouched. An affected child without a usable push
target blocks the workspace push: a local-only child commit cannot make the canonical description
available to teammates. The workspace root itself may still be committed without a remote, as
disclosed in the plan.

### Step 9 — Summary

Report what was written, committed, pushed, and what remains. Phrase scanner-owned remaining items
as their `workspace-status` findings. When the user declines Step 8 or publication is partial, name
the exact recovery command or repo rather than claiming the workspace is published.

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

- `<dirname>` — <routing description from lore-repo.md or lore-workspace.md repo-context>

## Agents

<!-- lr:managed — regenerated by workspace-init and the register-agent family -->

- `<agent-name>` (`<repo-dirname>`) — <routing description from role.md>. Boot: `lr-<agent-name>-agent`.
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
  workspace fact. A Lore repo's routing description comes from its own `lore-repo.md`; an ordinary
  repo's comes from `lore-workspace.md` `repo-context`. If the canonical source is missing, render
  `(routing description missing — run workspace-init)` rather than inventing a description.
- **Agents lists *registered* agents** — the "what can I boot here" answer. The shortcuts on disk
  across all three engines supply *membership* and, in their boot line, each agent's absolute
  `<agent-dir>`; the **role description comes from `<agent-dir>/role.md`'s frontmatter
  `description`**, and the repo dirname from that path. Do not try to read the description out of the
  shortcut — the Claude Code artifact is a single bootstrap line and carries none. When `role.md`
  has no description, render `(routing description missing — run workspace-init)`; the explicit gap
  is more useful than a plausible generic fallback. Agents present but unregistered do not appear;
  they are finding S11. With none registered, emit the single line:
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
after the routing audit passes and writes nothing — that property is what makes "init converges"
safe to recommend as the routine follow-up to anything that changed on disk. Semantic routing
quality is re-audited on each run; deep investigation runs only for entries that fail, so a healthy
workspace does not repeatedly pay the investigation cost.

## What `/lr:workspace-init` does NOT do

- Does not write any file outside the Step 3 base plan or the separately confirmed Step 7 routing
  plan, and does not touch user content outside a managed section (or, in `CLAUDE.md`, outside the
  single import line).
- Does not publish without Step 8's one explicit approval. That approval may cover several repos,
  but staging remains path-scoped and each Git repo receives its own commit.
- Does not merge divergent histories, and never passes `--allow-unrelated-histories`.
- Does not three-way-merge the memory file — show-diff-and-confirm is the entire user-edit protocol.
- Does not delete child repos dropped from a descriptor (no `--prune`).
- Does not decide agent membership. The Agents section is *rendered* from the registered shortcuts on
  disk; registration remains the single membership authority (`docs/register-repo.md`).

## See Also

- `docs/workspace-status.md` — the read-only counterpart; the findings catalog this skill converges.
- `docs/workspace-pull.md` — the consumer companion; Step 5 runs it.
- `docs/workspace-push.md` — the standalone workspace-root publisher; Step 8 uses the same narrow
  staging discipline while additionally covering routing descriptions in child repos.
- `docs/worktrees.md` — the convention distributed into the memory file.
- `docs/conventions.md` — `lore-workspace.md` schema (including `sharing: local` and
  `repo-context`), the dual meaning of `repos:`, and the Script Fallback Contract.
- `docs/check.md` — #22 (ignore coverage), #23 (legacy memory-file format), #24 (publication state).

# Draft — `/lr:init` + Worktree Convention

Status: **active design exploration** — converged on minimal shape. Not implemented.
Session: 2026-04-20.
Supersedes: `draft-contributions-feature.md` (retired).

## The Problem

Two related needs:

1. **Agents sometimes need non-default branches of repos** — for writing new features, or for checking out someone else's branch to inspect it. Top-level repo directories in the domain must stay on their default branch (they represent production-state truth for the domain), so some other mechanism is needed.
2. **Claude Code sessions starting in the domain directory** (whether booted as a lore agent or just running ad-hoc) need to know the domain's conventions — specifically, the worktree rule — without depending on agent memory or manual context-setting.

## Converged Shape

Two tightly-coupled pieces. Framework owns both:

**Part A — a convention.** Repos stay on their default branch; non-default branches go in worktrees under `<domain>/.worktrees/`. Full text in `docs/worktrees.md`. No framework commands wrap git worktree mechanics — they're universal knowledge.

**Part B — a command that distributes the convention into the domain.** `/lr:init` writes (or refreshes) a framework-managed section in the domain-level `CLAUDE.md`. That section carries a compact version of the rule + a link to the full doc. Claude Code loads `CLAUDE.md` automatically for any session in the domain, so every session reads the convention without explicit action.

## Part A — Worktree Convention

Lives in `lore-framework/docs/worktrees.md`. One page.

### Invariant

Top-level directories in `<domain>/` that correspond to repo checkouts stay on their default branch. Default branch name varies across repos (`main`, `master`, `trunk`, etc.) — the rule is "don't switch off the default," not "always `main`." Git tracks the default per-repo; no framework config needed.

Rationale: the domain is a snapshot of production state across all its repos. Switching a top-level checkout to a feature branch breaks that view. Also: knowledge captured by agents about "what this repo looks like in prod" depends on the main checkout reflecting prod.

### Rule

Any non-default-branch work happens in a git worktree at `<domain>/.worktrees/<repo>/<slug>/`. Both cases apply:

- **New feature work**: `git worktree add ../.worktrees/<repo>/<slug> -b <branch-name>`
- **Inspecting someone else's branch**: `git worktree add ../.worktrees/<repo>/<slug> <existing-branch>`

Agents use standard git worktree commands. No framework wrappers.

### Optional Pattern

Agents that want to keep notes on inflight worktrees can use `agents/<name>/worktrees/<slug>.md`. Content, structure, skeleton, archive-vs-delete on prune — all agent's call. Framework doesn't mandate, scaffold, or check this.

Rationale: varies per agent preference and per worktree purpose (an inspection worktree might not warrant any note; a long-lived contribution might warrant a living doc).

### What the Framework Does Not Own

- Branch-naming conventions (`<agent>/<slug>` is a *suggestion* for signaling ownership, not a rule).
- PR/MR workflow, CI interaction, merge mechanics — repo-specific.
- Worktree cleanup discipline — agent-managed.
- Enforcement of the "stay on default branch" invariant — convention-only in v9. A `/lr:check` warning is a future option if drift is observed.

Rationale: the `framework-scope-vs-agent-scope.md` principle. Anything repo-specific or workflow-specific belongs to agent lore or specialist agents reached via `/lr:consult` / `/lr:attach`.

## Part B — `/lr:init`

Lives in `lore-framework/skills/init/` (thin pointer) and `lore-framework/docs/init.md` (mechanism + canonical payload).

### Purpose

Write or refresh a framework-managed section in `<cwd>/CLAUDE.md` so that Claude Code sessions working in the domain automatically load the framework's conventions.

### Contract

- **Target**: `<cwd>/CLAUDE.md`. The user runs `/lr:init` from the domain directory.
- **Marker protocol**: framework-managed content lives between `<!-- lr:init:start -->` and `<!-- lr:init:end -->`. User content outside the markers is never touched.
- **Canonical payload**: the exact text the managed section should contain, defined in `docs/init.md`. Version-bumped alongside framework VERSION when payload evolves.

### Behavior

| Initial state                            | Action                                             |
| ---------------------------------------- | -------------------------------------------------- |
| No `CLAUDE.md` at cwd                    | Create it; write canonical payload at top.         |
| `CLAUDE.md` exists, no markers           | Prepend managed section.                           |
| Markers present, content == canonical    | No-op. Report "already current."                   |
| Markers present, content != canonical    | Show diff, ask user to confirm, replace on yes.    |

No three-way merge machinery. "Show diff + confirm" covers the user-edited-inside-markers case — the user sees their edits being overwritten and aborts if needed. Matches `show and test before pushing` discipline.

### Canonical Payload (v1)

```markdown
<!-- lr:init:start -->
## Lore Framework Domain

This directory is a Lore Framework domain. Conventions for any Claude Code session working here:

- **Repos at the top level stay on their default branch.** They represent production state.
- **For any non-default branch (new features, checking out others' branches), create a git worktree** at `.worktrees/<repo>/<slug>/`. Standard git worktree commands apply.

Full convention: https://github.com/zroslaw/lore-framework/blob/main/docs/worktrees.md
<!-- lr:init:end -->
```

Link is the public GitHub URL — works whether the plugin is loaded or not. More robust than `${CLAUDE_PLUGIN_ROOT}` for content in a user-facing file.

### Why Markers

HTML comments are invisible in rendered markdown, preserve clean reading experience, and match established patterns (all-contributors, many CI tools, prettier-ignore regions). If a markdown renderer strips them, we switch to visible sentinels — not a v9 concern.

### Idempotency and Re-runs

`/lr:init` is safe to run any number of times. In later framework versions, when the canonical payload evolves (new sections, richer content), the user reruns `/lr:init` to refresh. The diff-and-confirm gate keeps user edits inside the markers from being silently lost.

## Ship List

New files:

- `lore-framework/docs/worktrees.md` — the convention doc (Part A).
- `lore-framework/docs/init.md` — `/lr:init` mechanism + canonical payload (Part B).
- `lore-framework/skills/init/SKILL.md` — one-line pointer to `docs/init.md` per `skill-doc-pattern.md`.
- `lore-framework/release-notes/9.md` — version bump announcement.

Modified files:

- `lore-framework/VERSION` — `8` → `9`.

No changes:

- `agent-boot.md` — booted-agent nudge dropped per session decision.
- `/lr:pull-domain` — already specified to leave `.worktrees/` untouched (verify implementation during ship).
- `/lr:check` — no new checks for v9; invariant enforcement deferred.

## Deferred — To Pick Up Later

Tracked here so they're not forgotten:

1. **Domain creation automation.** A future feature will scaffold new lore-framework domains. The scaffolded domain's `README.md` will carry setup instructions (e.g., "run `/lr:init`" or auto-run during creation). Separate, larger project.

2. **Richer `/lr:init` payloads.** v1 payload carries only the worktree convention. Future content: domain intro, agent registry, invocation tips, etc. All extend the same `<!-- lr:init -->` markers; no new mechanism needed.

3. **Invariant enforcement.** A `/lr:check` warning for "top-level repo dir on non-default branch." Convention-only for v9; add if drift is observed in practice.

4. **Sync on framework version bump.** When v10+ updates the canonical payload, existing domains' CLAUDE.md goes stale. Options: user reruns `/lr:init` manually; or `/lr:update` chains it; or boot checks the payload version and prompts. Design then.

5. **Booted-agent nudge for un-initialized domains.** Explicitly dropped in this iteration as too complicated. User will handle convention-discovery via other means (possibly via (1) above or a check-based approach).

6. **Markdown renderer compatibility for HTML-comment markers.** If any renderer in the user's workflow strips `<!-- -->`, switch to visible sentinels. Not a v9 concern.

## Alternatives Considered

- **Per-agent commands (`/lr:contribute`, `/lr:worktree-create`, `/lr:worktree-prune`).** Rejected. Git worktree mechanics are universal — wrapping them with framework commands adds surface without value. Agents use standard git.
- **`contributions/` dir + bounded-session `/lr:contribute` + `/lr:contribution-finalize`** (prior draft). Rejected. Contribution is a *specialization* of "agent needs a worktree"; inspection checkouts don't fit. Worktree is the universal primitive.
- **Booted-agent nudge** when domain CLAUDE.md is missing/un-initialized. Rejected this round (user: too complicated; revisit via other enforcement mechanism later).
- **Three-way merge for the CLAUDE.md managed section.** Rejected. Show-diff-and-confirm is simpler and sufficient. Three-way merge adds machinery proportional to edge cases that rarely occur.
- **Visible sentinel headings** instead of HTML comments. Rejected unless renderer compatibility forces it. HTML comments are standard for managed-section patterns.
- **Framework-side default-branch config** per repo. Rejected. Git itself tracks the default; framework doesn't need to duplicate the data.
- **Mandatory `agents/<name>/worktrees/` note files.** Rejected. Agents decide whether and how to track inflight worktrees. Making it mandatory penalizes inspection-grade worktrees that don't warrant notes.

## Lore Housekeeping (Next Finalize)

- **Retire**: `contributions-feature.md` lore topic, `workdir/draft-contributions-feature.md`.
- **Write**: `worktrees-convention.md` topic (the Part A convention), `lr-init-feature.md` topic (the Part B mechanism + payload).
- **Update**: `lore-context.md` — replace "Active Design Explorations" entry for contributions with a completed entry for worktrees + `/lr:init` once v9 ships.

## Design Stance Reminders

- Framework owns what's universal: the worktree convention + the mechanism to distribute it.
- Repo-specific behavior (PR flow, branch policies, CI) belongs to agents — via agent lore or specialist agents reached via `/lr:consult` / `/lr:attach`.
- Thin machinery: one convention doc, one command with a marker protocol.
- Simplicity is the priority — dropped everything not essential for v1.

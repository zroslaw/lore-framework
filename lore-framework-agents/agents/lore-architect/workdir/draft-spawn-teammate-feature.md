# Draft — `/lr:spawn-teammate` (BETA)

Design doc for the v10 feature that exposes Claude Code's experimental Agent Teams as a thin lore-aware spawn primitive.

Session: 2026-04-28. Author: lore-architect.

## Goal

Provide a single, stable lore-framework command that spawns one or more lore agents as **teammates** in a Claude Code Agent Teams session. The current session becomes the Team Lead. Each spawned teammate is a separate, independent Claude Code instance booted as the specified lore agent.

The skill is the framework's first integration with Agent Teams. It is intentionally **minimal**: a thin name-resolution and spawn-prompt-composition layer over the natural-language Agent Teams interface. It does **not** introduce any new state, file format, or per-agent metadata.

## Status — BETA

This feature is shipped behind no flag, but the skill description, doc, and release notes mark it as **beta**:

- **Why beta:** Agent Teams itself is experimental and may evolve. Lore-write serialization, finalization across teammates, and team lifecycle conventions are unresolved. Real-world usage will reveal what should be lore-aware framework machinery vs. user-side patterns.
- **Stability promise:** the skill name and high-level behavior (resolve names → spawn teammates booted as the named agents) will not change while in beta. Internal procedure and release notes may evolve.
- **Graduation criteria:** clear answers to the open questions listed at the end of this doc, plus at least one real session where the skill was used end-to-end. When graduated, the "BETA" label is dropped, release notes for the graduating version describe the stable contract, and any feedback-driven changes are documented.

## Background

### Why Agent Teams now

The autonomous-agents direction (parked vision in `autonomous-agents-vision.md`) sketched a substrate of tmux + iTerm2 Python API + Claude Code hooks + a switchboard daemon. Roughly 70–80% of that substrate is now off our plate: Claude Code's Agent Teams (released after January 2026) ships a built-in coordination layer with task list, mailbox, status surface, and split-pane display. Building our own substrate before exhausting Agent Teams would be premature.

User decision (this session): use Agent Teams first; build our own scaffolding later only if real usage shows fundamental gaps.

### What Agent Teams gives us for free

From the official documentation (`https://code.claude.com/docs/en/agent-teams`):

- Spawn N independent Claude Code instances as teammates of one lead session.
- Each teammate is spawned with a **name** + a **spawn prompt** chosen by the lead — "the lead assigns every teammate a name when it spawns them ... It also receives the spawn prompt from the lead."
- Shared task list at `~/.claude/tasks/{team-name}/` with file locking; team config at `~/.claude/teams/{team-name}/config.json`.
- Mailbox messaging — `SendMessage` is always available to teammates; messages arrive at recipients automatically.
- Two display modes: **in-process** (cycle teammates with Shift+Down in the lead's terminal) or **split panes** (tmux/iTerm2). Default `auto`.
- Hooks: `TeammateIdle`, `TaskCreated`, `TaskCompleted` — usable later for lore-aware quality gates.
- `CLAUDE.md` works normally for teammates — they read the working-directory `CLAUDE.md`. Our `/lr:init` payload reaches teammates automatically.

### Limitations we need to design around

- One team per session.
- No nested teams (a teammate cannot spawn its own team).
- No session resumption with in-process teammates.
- Task status can lag.
- Lead is fixed for the team's lifetime.
- Permissions set at spawn (all teammates inherit lead's permission mode).
- Split panes require tmux or iTerm2 (not VS Code integrated terminal, Windows Terminal, Ghostty).
- Activation: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` env or settings.json `env`. Requires Claude Code v2.1.32+.

## Scope

### In scope (v1)

- A new plugin skill `/lr:spawn-teammate` that resolves agent names and spawns one or more lore agents as Agent Teams teammates.
- Name resolution from explicit args, with case-insensitive matching and Levenshtein-style typo tolerance.
- Name resolution from session conversation context when no args are given (with confidence-gated proceed-or-ask).
- Composing per-teammate spawn prompts that boot each teammate as the named lore agent via `agent-boot.md`.
- A v10 framework version bump with release notes describing the new skill (release-notes-only, no migration).
- A README skills table line for the new skill.

### Out of scope (v1)

- Lore-write serialization across multiple lore agents running concurrently (kept as last-write-wins for now; mitigated by deferring lore writes to finalization).
- Finalization semantics across teammates (`/lr:finalize` for a multi-teammate team — TBD; for v1 each teammate finalizes its own session before disbanding).
- Task-list integration with the lore framework (no automatic task creation, no lore-aware task templates).
- Inter-teammate consult/recall/attach mechanics (mailbox is the lower-level primitive Agent Teams ships; whether to layer LF semantics on top is a later question).
- Subagent-definition based teammates (Agent Teams supports `subagent_type`-style spawning; we don't pre-register lore agents as subagent definitions).
- Hook handlers (`TeammateIdle`, `TaskCreated`, `TaskCompleted`) — interesting but explicitly deferred until usage shows what's needed.
- Cleanup / shutdown helpers (`/lr:disband-team`, `/lr:shutdown-teammate`) — Agent Teams' natural-language interface handles these adequately for beta.
- Multi-domain / cross-domain teammates — for v1 all teammates must come from the same domain as the lead.

## User-facing design

### Command

```
/lr:spawn-teammate [<agent-name> ...]
```

- **Zero or more arguments.** Each argument is an agent name as the user types it (may have typos, case differences).
- **Multiple agents in one call** spawn as multiple teammates in one go.
- **Zero arguments** means "infer the agent set from the conversation context."

### Examples

Explicit single:
```
/lr:spawn-teammate tax-advisor
```

Explicit multiple:
```
/lr:spawn-teammate tax-advisor masschallenge-judge
```

Typo:
```
/lr:spawn-teammate tax-advsr
→ Resolved 'tax-advsr' → 'tax-advisor'
→ Spawning teammate `tax-advisor`...
```

Context inference:
```
[earlier in conversation: user mentions tax planning + MassChallenge feedback]
/lr:spawn-teammate
→ Inferred from context: tax-advisor, masschallenge-judge
→ Spawning 2 teammates...
```

Ambiguous:
```
/lr:spawn-teammate
→ Conversation mentions multiple possible agents. Did you mean to spawn:
   (a) tax-advisor only
   (b) masschallenge-judge only
   (c) both
   (d) something else
   Reply with your choice.
```

### Beta caveats surfaced to the user

The first-time output of the skill in a session prints a short note that the feature is beta and that:
- Lore writes by multiple teammates are not serialized (last-write-wins).
- Finalization with teammates is not yet automated; for now each teammate should finalize its own session before disbanding.
- Agent Teams' own limitations apply (one team per session, no session resumption with in-process teammates, etc.).

## Internal design — procedure

The skill follows the standard skill-doc pattern: `skills/spawn-teammate/SKILL.md` is a thin one-line pointer; `docs/spawn-teammate.md` carries all the logic.

### Step 1 — Preconditions

1. **Verify Agent Teams is enabled.**
   - Check `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in the environment (`echo $CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`) **or** in `~/.claude/settings.json` under `env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`.
   - If neither is set: print a clear instruction on how to enable, with the exact settings.json snippet, and stop.
   - We do not check Claude Code version. Agent Teams' own error will surface if the version is too old; the framework otherwise does not pin Claude Code versions.

2. **Locate the domain root.**
   - The current working directory is the domain (consistent with all other framework skills).

### Step 2 — Resolve the agent set

The skill receives `$ARGUMENTS` — zero or more space-separated tokens.

**2a. Enumerate available agents.** Walk the domain: for each subdirectory containing `lore-repo.md` at its root, scan `agents/*/role.md` to enumerate `(repo, agent-name, role-description)` tuples. Build a flat list of available agents (qualified by repo if names collide across repos).

**2b. Determine the input set.**

- **Args present**: input set = `$ARGUMENTS` tokens, in order.
- **Args empty**: build the input set from session context. Look at recent user and assistant messages, decisions made, and explicit references. Identify lore agents named or strongly implied. Confidence-gate:
  - If the implied set is clear (1–3 agents, named directly or unambiguously implied): proceed with that set, **explicitly state the resolved set and the reasoning** to the user.
  - If ambiguous (multiple plausible interpretations, or no signal): present a short numbered list of likely candidates and ask the user to pick.
  - If no signal at all: print "No agent specified or inferred. Available agents: ..." and stop.

**2c. Match each input name to an available agent (typo tolerance).**

For each input name `n`:
- **Exact** case-insensitive match against an available agent name → take it.
- Otherwise, compute a similarity score against each available agent name (Levenshtein distance + substring/prefix bonus). Pick the best candidate if the lead is confident (`distance ≤ 2` or `distance / length ≤ 0.3`, with a clear winner over runners-up). When taking a fuzzy match, **always tell the user the resolution** — e.g., `Resolved 'tax-advsr' → 'tax-advisor'`.
- If multiple candidates score similarly: ambiguous → ask the user to pick.
- If no candidate scores well: list available agents and stop.

**2d. Cross-repo collisions.** If two repos contain agents with the same name and the input is unqualified, ask the user to disambiguate.

**2e. De-duplication and self-spawn.**

- If the same agent name appears multiple times in the input set (after resolution), keep one and warn.
- If a teammate with the same name already exists in the current team, skip that name and warn — Agent Teams uses names as identifiers; spawning a duplicate name is undefined.
- If the host session is itself running as a lore agent and the user asks to spawn that same agent as a teammate: allowed (the teammate is independent), but warn — the user may not want two instances of the same agent's lore in flight at once.

### Step 3 — Compose teammate specs

For each resolved `(agent-name, repo-path)`:

- **Teammate name**: the agent's kebab-case name (matches agent dir name). Predictable, reusable in subsequent prompts.
- **Spawn prompt** (verbatim):

  ```
  Read ${CLAUDE_PLUGIN_ROOT}/docs/agent-boot.md and boot as agent <agent-name> from <abs-path-to-agent-dir>. After boot, await further instructions from the team lead via SendMessage.
  ```

  The path syntax mirrors the existing `/lr:boot` skill body and the registered `/lr-<name>-agent` shortcut commands. `${CLAUDE_PLUGIN_ROOT}` resolves in the teammate's session because teammates load skills from project and user settings (per Agent Teams docs).

  The "after boot, await further instructions" line is a hint for the teammate to stop and become idle after the boot procedure's "Confirm" step rather than invent a task.

### Step 4 — Invoke Agent Teams

Compose the natural-language directive to the lead model. The directive:

- States the desired teammate count and whether a team needs to be created or extended.
- For each teammate, gives the explicit name and the verbatim spawn prompt.
- Specifies that Claude Code should spawn the teammates immediately (not just plan).

Example directive (the doc gives the model a template; the model fills in resolved names and absolute paths):

```
Create an agent team (or add teammates to the existing team if one is active in this session) with the following 2 teammates. Use these exact names and spawn prompts verbatim — do not summarize, paraphrase, or wrap them.

Teammate 1:
  - Name: tax-advisor
  - Spawn prompt: "Read ${CLAUDE_PLUGIN_ROOT}/docs/agent-boot.md and boot as agent tax-advisor from /Users/goncharova/Documents/git/lore-agents/agents/tax-advisor/. After boot, await further instructions from the team lead via SendMessage."

Teammate 2:
  - Name: masschallenge-judge
  - Spawn prompt: "Read ${CLAUDE_PLUGIN_ROOT}/docs/agent-boot.md and boot as agent masschallenge-judge from /Users/goncharova/Documents/git/lore-agents/agents/masschallenge-judge/. After boot, await further instructions from the team lead via SendMessage."
```

Note: from this point, Agent Teams owns the spawn lifecycle. The skill does not poll, monitor, or interact with the team further.

### Step 5 — Report to the user

Print a compact summary:

- The resolved agent set (with any fuzzy-match resolutions called out).
- The team status (newly created vs. extended).
- For each teammate: name, repo path, current state (`spawning` if just spawned).
- One-line usage hint: "Use Shift+Down (or click into a pane in split-pane mode) to interact with a teammate. Run `/lr:spawn-teammate` again to add more. When done, ask the team lead to clean up."

If this is the first invocation of the skill in the session, also surface the beta caveats listed in the user-facing design.

## Edge cases

- **Cwd not a domain.** Walking subdirectories returns no `lore-repo.md`. Stop with: "No lore agent repos found in `<cwd>`. Run `/lr:spawn-teammate` from a lore framework domain directory."
- **Single repo, single agent, used as host.** User runs `/lr:spawn-teammate` with no args, no obvious context. Skill asks rather than guessing.
- **Teammate boot fails inside Agent Teams.** The skill has no visibility once the directive is sent. The user sees boot output in the teammate's pane (split-pane mode) or via Shift+Down (in-process). This is acceptable for beta.
- **Agent Teams not installed / version too old.** Activation check passes (env var set), but the natural-language spawn fails. The lead model surfaces the Agent Teams error to the user; the skill does not need to handle it specially.
- **Multiple lore agent repos.** Names from different repos appear in the unified pick list; cross-repo collisions are disambiguated explicitly. The spawn prompt's absolute path makes the repo unambiguous to the teammate.
- **Self-spawn.** Allowed with a warning. Two parallel sessions of the same lore agent are out of band but not pathological.

## File changes — implementation checklist

In `lore-framework/`:

1. **Create `skills/spawn-teammate/SKILL.md`** — thin one-line pointer with frontmatter: `description` (with usage line, marked BETA) and `argument-hint`.

2. **Create `docs/spawn-teammate.md`** — full procedure as detailed above (preconditions, agent-set resolution, spawn-prompt composition, Agent Teams invocation, report, edge cases, beta caveats, see-also links).

3. **Bump `VERSION`** from `9` to `10`.

4. **Create `release-notes/10.md`** — release-notes-only bump (no migration). Describe the new skill, mark it BETA, note Agent Teams prerequisites, link to the official Agent Teams docs and to `docs/spawn-teammate.md`.

5. **Update `README.md`** skills table — add a single row for `/lr:spawn-teammate <agent-name> ...`. Do not fix the broader staleness of the table in this PR (tracked separately in `framework-improvements-backlog.md`).

In `lore-agents/agents/lore-architect/`:

6. **`workdir/draft-spawn-teammate-feature.md`** — this design doc (kept for posterity per `design-doc-before-implement.md`).

7. **Lore updates at finalize time** (not part of this branch, handled by `/lr:finalize`):
   - Update `autonomous-agents-vision.md` to reflect that the autonomous-agents direction is partially addressed by Agent Teams; preserve the parked status for the broader vision.
   - Update `autonomous-agents-substrate.md` to note that ~70–80% of the substrate is provided by Agent Teams; what remains LF-specific.
   - Update `framework-improvements-backlog.md` to mark the autonomous-agents item with the v10 spawn-teammate skill as the first concrete step.
   - Add a new lore topic `spawn-teammate-feature.md` capturing what the skill is, why it's beta, and the design decisions herein.
   - Update `lore-context.md` to reference the new state.

### Branch / worktree

Per the v9 worktree convention, work happens in a worktree:

- Worktree path: `/Users/goncharova/Documents/git/.worktrees/lore-framework/spawn-teammate/`
- Branch: `lore-architect/spawn-teammate`

The worktree is pushed to the remote on the same branch. No PR is opened automatically (the user reviews the branch and chooses how to merge).

## Open questions (for graduation from beta)

These are not blockers for v10 but should be answered before dropping the BETA label:

1. **Lore-write serialization.** If two teammates running as the same lore agent (or one teammate plus the lead, both touching the same agent's lore) write concurrently, last-write-wins. Should the framework lock per-agent during writes? Or rely on the convention that lore writes only happen at finalization? Today's pattern (defer to finalize) probably holds, but Agent Teams blurs "session" boundaries.

2. **Finalization across teammates.** `/lr:finalize` runs in the host session. With teammates each carrying their own session-context-relevant insights, how do we collect them? Options:
   - (a) Each teammate runs `/lr:reflect` before disbanding, then the lead orchestrates `/lr:merge`.
   - (b) The lead instructs each teammate to write reflection files to a known location, then picks them up.
   - (c) The lead uses Agent Teams' messaging to query each teammate for "what's worth reflecting on" and reflects centrally.
   Initial preference: (a). It mirrors the current per-active-agent reflection iteration but distributed.

3. **Cross-agent collab mapping.** Today: `/lr:recall` (loaded), `/lr:consult` (unloaded), `/lr:attach` (sustained guest). With teammates running, much of consult/attach collapses into the mailbox. Do we keep all four mechanisms? Initial guess: yes — the trio operates within one session; spawn-teammate operates across sessions; they coexist and compose.

4. **Subagent-definition mode.** Agent Teams supports spawning teammates by referencing a subagent definition. We don't currently register lore agents as subagent definitions. Is there value? It would honor the definition's `tools` allowlist and `model`, but per the docs, `skills` and `mcpServers` frontmatter fields are NOT applied when running as a teammate. For lore agents, we want full skill access (including `/lr:*`). So subagent-definition mode is probably wrong for us. Confirm during real use.

5. **Hook integration.** `TeammateIdle`, `TaskCreated`, `TaskCompleted` hooks could trigger lore-specific behaviors (e.g., auto-reflect on idle, lore-aware task templates). Defer to evidence.

6. **One-team-per-session impact on multi-project flow.** If the user has multiple parallel concerns, each wanting its own team, they'll need separate Claude Code sessions. Document this expectation; no framework workaround.

## Future work tracked in backlog

- Companion `/lr:disband-team` and `/lr:shutdown-teammate` skills if natural-language interaction proves too brittle.
- Hook-based auto-reflect / quality-gate framework integration.
- Lore-aware finalization that automatically iterates across teammates.
- Subagent-definition variant of spawn-teammate, conditional on the open-question outcome.
- Sub-team / nested-team support — blocked on Agent Teams' own evolution.

## See also

- `autonomous-agents-vision.md` — the parked vision this skill partially realizes.
- `autonomous-agents-substrate.md` — the macOS substrate sketch; ~70–80% covered by Agent Teams.
- `consult-pattern.md`, `attach-pattern.md` — sibling cross-agent mechanisms (in-session).
- `skill-doc-pattern.md` — why SKILL.md is a thin pointer.
- `framework-scope-vs-agent-scope.md` — universality test applied here (the universal core: name resolution + spawn-prompt composition; everything else stays out).
- `versioning-release-types.md` — v10 is a release-notes-only bump.
- `worktrees-convention.md` — branch and worktree layout used during implementation.
- Official Agent Teams docs: https://code.claude.com/docs/en/agent-teams

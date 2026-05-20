Running backlog of framework-level improvements, deferred items, and open questions. Maintained by the lore-architect. Check and add to this as design conversations close without shipping everything, or as real-world usage surfaces gaps.

Items are grouped by area. Each has a one-line what + why + rough trigger or status. Promote an item into its own lore topic (and its own design draft in `workdir/`) when it becomes active.

## Init / Domain Bootstrap

- **Domain creation automation** — a scaffolding command or flow that creates a new domain directory, optionally with an agent repo initialized, a `README.md` carrying setup instructions, and an auto-invocation of `/lr:init`. Separate, larger project; the "instructions-to-init-runner" idea from v9 lands here. Status: deferred; revisit when we have more than one hand-built domain.
- **Richer `/lr:init` payloads** — v1 payload is only the worktree convention. Future additions planned: domain intro, list of registered agents, invocation tips (`/lr-<agent>-agent` shortcuts), links to framework docs. All extend the same `<!-- lr:init -->` marker block; mechanism unchanged. Trigger: user feedback on what's missing from the domain CLAUDE.md; framework features that want visibility at session start.
- **Sync CLAUDE.md on framework version bump** — when a future version updates the canonical payload, existing domains' CLAUDE.md goes stale. Options: user reruns `/lr:init` manually; `/lr:update` chains it; boot checks payload version and prompts. Design when adding the first payload-changing version after v9.
- **Booted-agent nudge for un-initialized domain** — originally proposed: at boot, check for `<!-- lr:init -->` markers; if absent, emit a one-line suggestion to run `/lr:init`. Dropped in v9 as too complicated. User prefers the future domain-creation-automation path to solve discovery.

## Worktree Convention

- **Invariant enforcement in `/lr:check`** — warn when a top-level repo dir is on a non-default branch (violating the worktree-convention invariant). Cheap check (a git command per repo). Trigger: drift observed in real use. See `worktrees-convention.md`.
- **Orphan-worktree / orphan-note checks** — optionally flag worktrees in `.worktrees/` with no tracking note in `agents/<name>/worktrees/`, or notes with no corresponding worktree. Weak signal (the note pattern is opt-in). Defer unless agents widely adopt the note convention.
- **Branch-naming convention check** — verify branches in worktrees follow the suggested `<agent-name>/<slug>` form. Very opinionated; probably never needed.

## Finalization / Autopush

- **Audit log of pushed summaries** — since the user no longer sees summaries pre-commit, a local audit trail (e.g., a `sessions-index.md` at the host repo root, appended to on each finalize) could help spot issues faster than browsing git history. Trigger: user reports missing a problematic summary.
- **Per-session opt-in gate flag** — `/lr:finalize --review` that restores the old approval flow for sensitive sessions. Cheap to add. Trigger: user asks for it at least twice.
- **Narrative-safety linter** — lightweight check on composed summary text before write (secrets regex, etc.). Adds machinery; currently relying on agent judgment per v9 design. Defer unless a real privacy incident occurs.

## Documentation / Meta

- **README skills table sync** — `lore-framework/README.md` skills table is stale. Missing: `/lr:update`, `/lr:pull-domain`, `/lr:recall`, `/lr:attach`, `/lr:consult`, `/lr:summarize`, `/lr:init`. Small task; do in a dedicated docs-only commit. Related: stale `/lr:finalize` description in the same table — says "Reflect + merge in one step" but it's been four phases since v9 (reflect + merge + summarize + commit+push). One-line fix; explicitly held back from a previous session's edit to keep commit scope clean.
- **Markdown-renderer compatibility for HTML-comment markers** — `/lr:init` uses `<!-- lr:init:start -->` markers. Some renderers strip HTML comments. If any user's tooling bites on this, switch to visible sentinel headings. No action until observed.
- **Consolidated "framework conventions" doc** — there's `conventions.md`, `worktrees.md`, `skill-doc-pattern.md`-type rules scattered. At some size, a single index or "start here" doc could help. Not urgent.
- **Broken `contributions-feature.md` reference in `framework-scope-vs-agent-scope.md`** — its See Also points to `contributions-feature.md` which doesn't exist in `lore/`. Pre-existing dangling link; worth a cleanup pass on See Also sections across topics. Open sub-question: `/lr:check` claims reference integrity (checks 9–10 per `consistency-checks.md`) but this dangling link persists — either the check covers something narrower or it has a gap. Investigate during a future framework-maintenance session.
- **`agent-boot.md` team-shared framing note (open decision)** — the team-shared-knowledge principle is now named in lore and surfaced in the public README. Open question: should `agent-boot.md` (the universal boot procedure) also carry a one-line framing note so every agent at boot time understands its workspace is team-shared? Pro: universal applicability — every agent inherits the framing without depending on whether their specific lore captures it. Con: scope-creep into universal machinery; risk of cluttering the boot procedure with conceptual content; possibly redundant with README. Surfaced by the sonnet review; not yet decided.

## Cross-Agent Collaboration

- **Consult-feedback back-channel** — formal mechanism for the host to route newly-learned content back to the consultant's reflection queue after `/lr:consult`. Left out in v4 to keep consult lightweight. Revisit if users accumulate stale consultant lore relative to how it's actually used.
- **Host-wins vs interactive conflict resolution for lore overlaps** — current rule is host-wins on lore conflicts during attach. Might want finer control. Not an active issue.

## Search / Scaling

- **Vector DB search** — Chroma-backed semantic search over lore topics with incremental git-based index updates. Parked until subagent-scan pattern becomes impractical (rough trigger: >100 topics per agent). See `vector-db-search-parked.md`.
- **Workdir as reference library** — parked exploration of using `workdir/` as a structured knowledge base alongside lore. Lore = experiential, workdir = curated reference. Most valuable for domain-heavy specialists. No framework machinery planned — patterns emerge per agent. See `workdir-as-reference-library.md`.

## Autonomous Agents (major direction)

- **Autonomous background agents** — re-frame lore agents from session-bound interactive workers to always-on collaborators with persistent task state, asking for input only when needed. Implications across process model (daemonization), state model (task state, not just lore), communication model (agent → user channels), reflection model (autonomous reflect triggering), and multi-agent surface (switchboard for N parallel agents). Status: parked vision, no design doc yet. Concrete first step: `/lr:spawn-teammate` via Agent Teams. See `autonomous-agents-vision.md`.
- **Autonomous-agents substrate findings** — concrete macOS building blocks identified: tmux for the process layer, iTerm2 Python API for GUI control, Claude Code hooks (`Stop`, `Notification`, etc.) as the signal source (strictly superior to regex triggers), escape sequences for status surface (tab color/title), `terminal-notifier` for click-actionable notifications, and a Python switchboard daemon under `launchd` for orchestration. Security: never bind `0.0.0.0` without auth — RCE risk; prefer narrow HTTP API in front of the iTerm2 socket over raw socket exposure. Parked while Agent Teams experiment runs. See `autonomous-agents-substrate.md`.

## `/lr:spawn-teammate` Beta Graduation

- **Lore-write serialization** — concurrent teammates write last-write-wins. Is file-lock/queued-merge needed or is "defer lore-changing work to finalization" sufficient?
- **Automated teammate finalization** — lead triggering finalization on all teammates before disbanding via SendMessage channel. Explore.
- **Hook integration** — test whether `Stop`/`Notification` hooks fire in teammate sessions; could automate teammate finalization.
- **Subagent-definition mode** — track if Agent Teams adds `skills`/`mcpServers` support; would enable more explicit spawning.
- **`/lr:check` validators** — add checks for Agent Teams enabled, teammate boot paths valid. Deferred until usage shows what to check.
- **Finalize/summarize consistency with teammate model** — those docs were designed for host+attached-guest; verify they compose correctly with Agent Teams' separate teammate sessions.
- **User-primary-interlocutor framing** — graduation invariant or tunable? Currently locked as a design invariant in BETA after the post-v10 boot-prompt reframe.

See `spawn-teammate-feature.md` for full beta graduation question list.

## Session Summaries

- **Compaction-aware narrative quality** — on long sessions, auto-compaction may drop or compress earlier turns; summaries skew toward late-session work and can hallucinate earlier events. Current mitigation: prompt instructs the model to note "early-session hazy" rather than confabulate (weak). Possible directions: landmark scratch file written during the session for summarize to cross-reference; bounded read of the session JSONL isolated to this site; accept bias and rely on in-session summarization cadence. Trigger: systematic bias observed when reviewing the summary corpus.
- **Cross-repo guest participation gap (partial)** — v8 added short guest summaries for guests that had lore updates. Guests attached but with no lore updates still leave no trace in their own repo. Minor gap; revisit if cross-repo specialist agents become common. Fully solving requires pointer-file-on-attach or similar convention.
- **Reliable start-time capture** — summary frontmatter `start` is best-effort from session memory, rounded to nearest 5 minutes. Options: `agent-boot.md` writes `.session-started` marker for summarize to read+delete; minimal one-field read from session JSONL's first-line `timestamp` (shape-stable); formalize "approximate, best-effort" in the schema and move on. See `session-summaries-feature.md`.

## Process

- **Reflect-merge ergonomics** — writing reflections then merging them has overhead for single-agent sessions with trivial deltas. Inline shortcut for "just write to lore directly" is sometimes more pragmatic. Document when to shortcut vs when to go through the full flow.

## Domain Topology

- **Discovery gap for nested agent repos** — domain discovery scans direct subdirectories of cwd only; nested agent repos are invisible to `/lr:list-*`, `/lr:check`, `/lr:recall`, `/lr:pull-domain`, `/lr:spawn-teammate`, `/lr:boot`. Currently `lore-framework-agents/` is nested inside `lore-framework/` as a temporary placement, reachable only via the registered `/lr-lore-architect-agent` shortcut. User will extract to a domain-root sibling on its own GitHub repo. Tracked here for the eventual move; deeper question of whether discovery should walk one level (or accept a config-file hint) is open if nested layouts become a recurring pattern. See `agent-discovery-nesting-constraint.md`, `plugin-vs-agent-repo-separation.md`.

## Agent Teams / Spawn-Teammate (additions)

- **Real-world trial run for `/lr:spawn-teammate`** — `~/.claude/settings.json` now sets `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` (configured this session). Next session after Claude Code restart, `/lr:spawn-teammate` is usable. Worth a real trial on framework work — the feature is BETA with open design questions (last-write-wins lore serialization, finalization across teammates). First usage will inform graduation. See `spawn-teammate-feature.md` for the open beta questions.

## How To Use This Backlog

- Add a bullet when an idea comes up during design but won't ship this session.
- Promote to its own lore topic + workdir draft when it becomes active work.
- Delete bullets that become moot (e.g., if a new framework mechanism obsoletes them).
- Reread at the start of framework-design sessions — surprises emerge from the accumulation.

## See Also

- `workdir/draft-lr-init-feature.md` — design session that established the v9 deferred list (many items above originate there)
- `design-doc-before-implement.md` — why active items get a workdir draft before framework-file edits
- `framework-scope-vs-agent-scope.md` — test for whether a proposed framework item belongs here or in agent-owned territory

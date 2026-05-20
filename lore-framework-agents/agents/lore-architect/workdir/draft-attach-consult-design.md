# Design: `/lr:attach` and `/lr:consult` (framework v4)

Status: design-in-progress, being implemented.

## Problem

Narrow utility/functional domains (external API clients, per-repo commit conventions, specialized tooling) show up across multiple agents without being any single agent's primary role. If each agent learns such a domain in its own lore, we pay three costs:

- **Duplication of learning** — N agents independently re-learning the same API quirks
- **Divergence** — each agent's mental model drifts in a different direction
- **No compounding** — when one agent discovers something, others don't benefit

The existing primitives (lore + recall within a single loaded agent) don't address this — recall only searches the loaded agent's own lore, and each agent boots alone.

## Solution overview: the trio

Three mechanisms, each serving a distinct shape of cross-agent knowledge sharing:

| Command | Target | Context impact | Use when |
| --- | --- | --- | --- |
| `/lr:recall [hint]` | Loaded agents only (host + guests) | Compact synthesis inlined | You want to pull lore from the agents already active in this session |
| `/lr:consult <agent> [hint]` | An unloaded specialist agent | Subagent boots, answers, exits; host gets synthesis + file pointers | One-shot question. You need an answer and maybe a few specific files, not ongoing fluency |
| `/lr:attach <agent>` | Another agent, loaded into host's main context | Full role + lore-context loaded; subsequent recalls fan out; finalization iterates per agent | Sustained multi-turn work spanning two (or more) domains; may teach something back |

The three compose cleanly: **recall** works on whatever's loaded; **consult** is one-shot without loading; **attach** loads for sustained use. If a consult reveals you need deeper engagement, escalate with `/lr:attach <same-agent>`.

## Terminology

- **Host** — the agent originally booted in the session (via `/lr:boot` or `/lr-<name>-agent`). There is exactly one host per session. Host is the sole executor.
- **Guest** — an agent attached into the host's session via `/lr:attach`. Zero or more guests per session. Guests are knowledge/library loads, not additional executors.
- **Active agents** — host + all attached guests.

"Multi-personality, single executor": guests extend the host's capabilities without becoming separate agents in the session. All work is performed by the host, informed by the union of loaded lore.

## `/lr:attach` — detailed design

### Usage

- `/lr:attach <agent-name>` — attach a guest
- `/lr:attach` (no args) — list currently attached guests

### Preconditions

- A host must be booted. If no agent is loaded, respond: `No agent loaded. Run /lr:boot <agent-name> first.` and stop.
- The agent to attach must exist in some lore agent repo in the domain. Uses the same discovery procedure as boot: find directories containing `lore-repo.md`, then look for `agents/<name>/role.md`. If not found, report and list available agents.
- Cannot attach the host to itself. Cannot attach an agent that is already a guest.

### Procedure

1. **Discover.** Find the guest agent's repo and agent directory using the standard discovery procedure.
2. **Version reconcile in a subagent.** Read the guest repo's `lore-repo.md` version. If it differs from the framework `VERSION`, dispatch a subagent (`Explore` type, with edit capability — actually `general-purpose` since edits may be needed) to execute `docs/version-check.md` scoped to the guest repo. The subagent applies migrations / displays release notes / stamps the new version. Host sees only a compact summary ("guest repo upgraded from R to F"). If the version check fails or defers (uncommitted changes, etc.), the host reports it to the user and either continues in degraded mode (guest attached with version skew warning) or aborts the attach per the same rules as boot-time version check.
3. **Load guest context.** Host reads `agents/<guest>/role.md` and `agents/<guest>/lore-context.md` directly into its own context.
4. **Confirm.** Host prints: `Attached <guest-name>. Active agents: host=<host>, guests=[<guest-1>, <guest-2>, ...].` and a one-line summary of the guest's role.

**Idempotence:** attaching an already-attached guest is a no-op with an informational message.

### Conflict resolution

If the guest's lore-context contradicts the host's (different conventions, different recommendations), the **host's knowledge takes precedence**. The guest's perspective is still visible and can inform the host's judgment, but when the host needs to act, its own lore governs. This keeps the host's identity stable and avoids silent harmonization.

### State tracking

There is no disk-level state for attachments. The session conversation itself is the record — the `/lr:attach` confirmation message establishes that a guest is active. The host reads the conversation on each subsequent operation (recall, finalize) to determine active agents.

### With no args — listing

`/lr:attach` with no arguments prints:
- The host's name
- Each attached guest's name + one-line description (from their `role.md` frontmatter)
- A line if no guests are attached: `No guests attached. Host: <host-name>.`

This lists the state already visible in the conversation — it does not touch disk.

## `/lr:consult` — detailed design

### Usage

- `/lr:consult <agent-name>` — consult with contextual brief (host uses current session as the brief)
- `/lr:consult <agent-name> <hint>` — consult with a focused hint layered on the session context

### Preconditions

- A host must be booted. Without a host, consult has no session context to form a brief from, so refuse like attach does.
- The consultant agent must exist (same discovery as attach).
- Cannot consult the host itself (recall is for that).
- Consulting an already-attached guest is allowed but pointless — suggest recall instead.

### Procedure

1. **Discover** the consultant agent.
2. **Build the consult brief.** Host prepares a 4-part brief analogous to lore-search but consult-shaped:
   - **Task** — what the host is working on this session
   - **Session context** — decisions, constraints, files being touched, current blocker
   - **Question / angle** — the specific issue or question. Includes user hint if provided
   - **Output shape** — direct answer + pointers to specific lore topics worth reading + pointers to consultant's workdir tools/recipes if relevant + optional recommended next steps. Compact: ≤600 words.

   Keep the brief under ~400 words.

3. **Dispatch the subagent.** Use a general-purpose subagent. The subagent's job:
   - Boot as the consultant per `agent-boot.md` (which includes version reconcile automatically)
   - Search consultant's lore using the lore-search pattern (subagent-internal scan is fine — nested subagents supported)
   - Synthesize a response per the requested output shape
   - Return the synthesis + file pointers to the host
   - **Does not** write reflections, does not finalize
4. **Present to the host and user.** Host shows the synthesis to the user (transparency). Host may then read specific lore topics or workdir files that the synthesis pointed to, in its own main context. The host has domain visibility — these reads are free.

### After consult — what the host can do

The consult creates a handover, not a loading. After the consult:

- Host may read any specific files referenced in the consultant's response (lore topics, workdir tools, recipes, scripts). Those files become part of the host's working context as needed.
- Host may execute tools (run scripts, etc.) that the consultant recommended.
- Host may apply advice the consultant gave directly.

The host does **not**:

- Dispatch further lore-search subagents against the consultant's lore. That's attach territory.
- Invoke `/lr:recall` expecting consultant lore to be included — recall only covers loaded agents (host + guests).

**Escalation path:** if the task turns out to need sustained engagement with the consultant's knowledge, call `/lr:attach <same-agent>`. This is the clean transition from consult to attach.

### No finalization for consultants

The consultant does not reflect or merge as a consequence of the consult. The consult is read-only from the consultant's perspective. If the host discovers something the consultant should know, there's no automated back-channel in v1 — the host can mention it to the user, who can trigger a consultant session later if the insight is worth preserving.

(Future design question, deferred: a "consult feedback" mechanism. Not in v4.)

## Fan-out recall with attached guests

When guests are attached, `/lr:recall` and any agent-initiated lore search fans out:

1. Host prepares one brief, reusing the standard 4-part structure.
2. Host dispatches **N parallel subagents** — one per active agent, each scanning that agent's `lore/` directory.
3. Each subagent returns a compact synthesis tagged with the agent name.
4. Host presents all syntheses to the user (grouped by agent for clarity), and carries the union as working context.

Subagent dispatches are done in parallel (single message, multiple Agent tool calls) for speed.

Identical behavior for `/lr:recall` (user-triggered) and lore-search (agent-initiated) — the only difference is who initiates.

## Per-agent finalization

When guests are attached, `/lr:reflect`, `/lr:merge`, and `/lr:finalize` iterate per active agent, sequentially, in attach order (host first).

### Reflection (per-agent)

For each active agent in order (host, then guest₁, guest₂, ...):

1. Review the session through the lens of this agent's `role.md` + `lore-context.md`.
2. Extract knowledge relevant to this agent's role into reflection topics, written to that agent's `reflections/` directory.
3. Confirm reflection for this agent and list the topics created, then move to the next.

Topics relevant to multiple agents may be duplicated into each agent's reflections — **shared topics are a feature, not a bug**. Efficiency matters more than mutual exclusivity: if commit-specialist and tax-advisor both need to know about a scheduled API maintenance window, both learn it.

Filtering is role-guided, not strict — some session noise leaking into an agent's reflection is acceptable. The `role.md` + `lore-context.md` tells the agent what "relevant to me" means.

### Merge (per-agent)

After all active agents have reflected (or as part of finalize's sequential pass), merge runs per active agent in the same host-first order:

1. Read that agent's `reflections/`, `lore/`, `lore-context.md`, `role.md`.
2. Integrate reflections → update/create/delete lore topics + update lore-context.md + merge any `role-update-*` reflections into `role.md`.
3. Delete `reflections/` for that agent.
4. Commit changes for that agent's directory.
5. Move to the next agent.

Each commit scopes to that agent's subdirectory so history stays clean.

### `/lr:finalize` (per-agent)

`/lr:finalize` for each active agent runs `reflect` then `merge`. Host fully finalizes first — this matters because the host's lore may capture decisions that reference topics the guests will then also reflect on. Guest iterations happen after host's merge is committed.

### Implementation in skills/docs

The reflect/merge/finalize skills themselves stay simple: they invoke the corresponding process doc. The procedure docs (`process-reflection.md`, `process-merge.md`) learn the "iterate per active agent" behavior. When no guests are attached, the iteration reduces to a single pass — current behavior is unchanged.

## Files touched

### New files

- `skills/attach/SKILL.md` — thin pointer
- `skills/consult/SKILL.md` — thin pointer
- `docs/attach.md` — full procedure
- `docs/consult.md` — full procedure
- `release-notes/4.md` — v4 release notes

### Updated files

- `VERSION` — bump 3 → 4
- `docs/lore-search.md` — fan-out when guests attached
- `docs/recall.md` — fan-out when guests attached
- `docs/process-reflection.md` — iterate per active agent
- `docs/process-merge.md` — iterate per active agent
- `skills/reflect/SKILL.md` — light note about per-agent iteration (logic in doc)
- `skills/merge/SKILL.md` — light note about per-agent iteration (logic in doc)
- `skills/finalize/SKILL.md` — light note about per-agent iteration (logic in doc)
- `docs/agent-boot.md` — small "Collaborating with other agents" subsection pointing to the three mechanisms
- `lore-architect` lore: add `attach-pattern.md`, `consult-pattern.md`; update `lore-context.md` (current state, plugin skill system section)

### Not touched

- `docs/check.md` — consistency checks unaffected per user decision
- `docs/version-check.md` — attach and consult reuse it unchanged via subagent dispatch
- Plugin manifests (`.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`) — do not enumerate individual skills; the new skills are picked up automatically from the `skills/` directory

### No migration needed

Both features are additive. No user-side files need to change shape. `release-notes/4.md` alone satisfies the two-track update flow's "at least one artifact per version" requirement.

## Invariants and edge cases

- **Boot always succeeds.** Any failure during attach's version reconcile results in either a degraded-mode attach (with warning) or a clean abort — never a broken host.
- **Host remains the host.** Attach never re-homes identity. Consult never changes identity.
- **Subagent migrations are real.** Auto-upgrade in the subagent writes to disk just as boot-time auto-upgrade does. Results are visible in git diff after.
- **Cross-repo workdir access** — guests' workdirs are read-accessible (domain visibility). Workdir *writes* during the session default to the host's workdir. Ownership resolves at reflection time.
- **Staleness of lore-context** — we load what's on disk at attach time. No special handling. Same policy as boot.
- **Multiple guests** — no hard cap. Token cost is the user's responsibility.
- **Detach** — not supported in v1. Once attached, stays attached for the session and participates in finalization.

## Open questions that were resolved

- Naming: **host / guest, `/lr:attach`, `/lr:consult`** — chosen
- Context budget cap: **no cap, user's responsibility**
- Reflection filter: **role + lore-context**, leakage acceptable, shared topics allowed to duplicate
- Version skew: **reconcile in a subagent** to keep migration noise out of host context
- Lore conflicts: **host wins**
- Consult vs attach boundary: **consult = one-shot Q&A + optional file handover; attach = sustained loading**
- Consult's effect on consultant: **none** — no reflection, no finalization
- `/lr:check`: **unaffected** in v1
- lore-context staleness: **not a concern**, load what we have

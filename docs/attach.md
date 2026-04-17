# Attach

`/lr:attach` loads another lore agent into the currently booted host session so the host can work with the union of both agents' knowledge over many turns. This is the heavyweight option in the cross-agent-collaboration trio (recall / consult / attach); use it when the task genuinely spans two (or more) domains and you'll be thinking in both across many turns.

## Usage

- `/lr:attach <agent-name>` — attach a guest agent
- `/lr:attach` (no arguments) — list currently attached guests

## Concepts

- **Host** — the agent originally booted via `/lr:boot` or a `/lr-<name>-agent` shortcut command. Exactly one per session. The host is the sole executor.
- **Guest** — an agent attached into the host session. Zero or more per session. Guests are knowledge loads — they extend what the host knows and can do, without becoming separate executors.
- **Active agents** — host + all currently attached guests. This is the set that `/lr:recall` fans out over and that `/lr:reflect` / `/lr:merge` / `/lr:finalize` iterate over.

The session is single-executor, multi-personality: the host stays in charge, the guests contribute knowledge.

## With no arguments — list attached guests

If `$ARGUMENTS` is empty:

1. Identify active agents from the conversation. The host is whichever agent was booted via `/lr:boot` or a `/lr-<name>-agent` shortcut command. Guests are any agents that were confirmed as attached by prior `/lr:attach` commands in this session and have not been removed (detach is not supported in v1, so they all stay).
2. Print the active-agents state:
   - `Host: <host-name> — <one-line role.md description>`
   - For each guest: `Guest: <guest-name> — <one-line role.md description>`
   - If no guests: `No guests attached.`
3. Do not touch disk. Stop.

## With an agent name — attach a guest

### Step 1: Preconditions

1. **Host must be loaded.** If no agent was booted in this session, respond: `No agent loaded. Run /lr:boot <agent-name> first, then /lr:attach.` and stop.
2. **Target must exist.** Run the standard agent discovery: scan all directories in the working directory for `lore-repo.md` files; within each, look for `agents/<target>/role.md`. If not found, list all available agents across all lore agent repos and stop with an error.
3. **Target must not be the host.** If the requested name equals the host, respond: `<name> is already the host — use /lr:recall to search its lore.` and stop.
4. **Target must not already be a guest.** If the requested name is already attached, respond: `<name> is already attached.` and stop (idempotent).

### Step 2: Version reconcile in a subagent

Read the target repo's `lore-repo.md` and extract its `version` field. Compare with the contents of `${CLAUDE_PLUGIN_ROOT}/VERSION` (trimmed).

- If they match, skip to Step 3.
- If they differ, dispatch a general-purpose subagent to reconcile. The subagent works in the filesystem — its output stays in its own context; the host only sees the subagent's summary return.

Subagent prompt shape:

> Reconcile the lore agent repo at `<guest-lore-agent-repo>` to the installed framework version.
>
> Read `${CLAUDE_PLUGIN_ROOT}/docs/version-check.md` and execute its procedure, scoped to this repo. The repo's current version is `R=<R>` and the framework version is `F=<F>`.
>
> **Deviation from version-check.md:** do not print release notes to the user directly — instead, collect the full text of each release notes file you would have displayed, and return it in your response so the host can surface it to the user.
>
> Return a compact report containing:
> - Start version, end version, final stamped version (or "not stamped" if the upgrade deferred or failed)
> - List of migrations applied (filenames only)
> - Full contents of any release notes files that should be shown to the user
> - Any warnings (uncommitted changes, version > framework, migration errors)
> - Degraded-mode status (did the upgrade succeed cleanly, defer, or fail)

After the subagent returns:

- **Relay release notes to the user** verbatim. They are meant for user eyes.
- **Surface any warnings** — uncommitted-changes defer, version-above-framework warning, or migration failure.
- **If the upgrade failed or deferred**, continue the attach in degraded mode (version-skew warning visible) — matches boot-time behavior. Do not block the attach on a failed upgrade.

### Step 3: Load guest context

In the host's main context, read:

1. `agents/<guest>/role.md` — frontmatter has `description`; the body defines the guest's identity and responsibilities.
2. `agents/<guest>/lore-context.md` — the guest's compacted working knowledge (≤50K tokens).

These files now live in the host's working context alongside the host's own role and lore-context.

### Step 4: Confirm

Print a confirmation message. Include:

- `Attached <guest-name>.`
- Active agents line: `Active agents: host=<host-name>, guests=[<g1>, <g2>, ...]`.
- One-line summary of the guest's role (taken from the guest's `role.md` frontmatter description).
- If a version reconcile ran, note it: `Guest repo was upgraded from <R> to <F>.`

This confirmation message is the host's record of the attachment — the session conversation itself tracks active agents. No disk state is written for the attach.

## Conflict resolution

When the guest's lore disagrees with the host's (different conventions, different recommendations, different "always do X" rules), the **host's knowledge takes precedence**. The guest's perspective is visible and can inform judgment, but the host's own lore governs action. This keeps host identity stable and avoids silent harmonization.

In practice: note the disagreement to the user if it's material, then follow the host's rule unless the user overrides.

## What changes after attach

Subsequent operations become multi-agent-aware automatically:

- **`/lr:recall` fans out** — one parallel subagent per active agent, results synthesized together. See `docs/recall.md` and `docs/lore-search.md`.
- **`/lr:reflect` / `/lr:merge` / `/lr:finalize` iterate** — sequentially, per active agent, in host-first order. See `docs/process-reflection.md` and `docs/process-merge.md`.
- **Workdir writes** default to the host's workdir. Guests' workdirs are readable (domain visibility already gives the host this).

No detach in v1. Guests stay attached for the rest of the session and participate in finalization.

## Attaching multiple guests

Call `/lr:attach` multiple times. Order matters only for finalization iteration (host first, then guests in attach order). There is no hard cap on the number of guests — token cost is the user's responsibility. Each guest's `lore-context.md` can be up to 50K tokens; attaching several visibly shrinks the host's working budget.

## Escalation from consult

If a `/lr:consult <agent>` surfaces that you actually need sustained engagement with that agent's knowledge, call `/lr:attach <same-agent>` — this is the clean transition from one-shot to loaded.

## See also

- `${CLAUDE_PLUGIN_ROOT}/docs/consult.md` — the one-shot sibling (subagent boots, answers, exits; no host-side loading)
- `${CLAUDE_PLUGIN_ROOT}/docs/recall.md` — lore search across active agents
- `${CLAUDE_PLUGIN_ROOT}/docs/lore-search.md` — search brief structure, fan-out mechanics
- `${CLAUDE_PLUGIN_ROOT}/docs/version-check.md` — migration procedure used by the Step 2 subagent
- `${CLAUDE_PLUGIN_ROOT}/docs/process-reflection.md` and `process-merge.md` — per-agent iteration when guests are attached

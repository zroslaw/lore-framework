# Attach

`/lr:attach` loads another lore agent into the currently booted host session so the host can work with the union of both agents' knowledge over many turns. This is the heavyweight option in the cross-agent-collaboration trio (recall / consult / attach); use it when the task genuinely spans two (or more) domains (different agent repos) and you'll be thinking in both across many turns.

## Usage

- `/lr:attach <agent-name>` — attach a guest agent
- `/lr:attach` (no arguments) — list currently attached guests

## Concepts

- **Host** — the agent originally booted via `/lr:boot` or a registered per-agent shortcut (`/lr-<name>-agent` on Claude Code, `$lr-<name>-agent` on Codex). Exactly one per session. The host is the sole executor.
- **Guest** — an agent attached into the host session. Zero or more per session. Guests are knowledge loads — they extend what the host knows and can do, without becoming separate executors.
- **Active agents** — host + all currently attached guests. This is the set that `/lr:recall` fans out over and that `/lr:reflect` / `/lr:merge` / `/lr:finalize` iterate over.

The session is single-executor, multi-personality: the host stays in charge, the guests contribute knowledge.

## With no arguments — list attached guests

If `$ARGUMENTS` is empty:

1. Identify active agents from the conversation. The host is whichever agent was booted via `/lr:boot` or a registered per-agent shortcut. Guests are any agents that were confirmed as attached by prior `/lr:attach` commands in this session and have not been removed (detach is not supported in v1, so they all stay).
2. Print the active-agents state:
   - `Host: <host-name> — <one-line role.md description>`
   - For each guest: `Guest: <guest-name> — <one-line role.md description>`
   - If no guests: `No guests attached.`
3. Do not touch disk. Stop.

## With an agent name — attach a guest

### Step 1: Preconditions

1. **Host must be loaded.** If no agent was booted in this session, respond: `No agent loaded. Run /lr:boot <agent-name> first, then /lr:attach.` and stop.
2. **Target must not be the host.** If the requested name equals the host, respond: `<name> is already the host — use /lr:recall to search its lore.` and stop.
3. **Target must not already be a guest.** If the requested name is already attached, respond: `<name> is already attached.` and stop (idempotent).

### Step 2: Preflight the guest

Discovery, auto-pull, and the version comparison are one command — the same preflight boot runs, pointed at the guest:

```
python3 "<framework-root>/scripts/lr-core" preflight --agent "<guest-name>" --workspace "<cwd>" --engine "<engine>"
```

Use the host boot's selected engine (`data.engine.name`) for `<engine>`. This keeps attachment on
the same profile even when Codex is running against a worktree or other path where automatic
detection has no native-install signal.

Bound this call at **at least 180 seconds** via your engine profile's runtime-bounding binding, and keep the substituted values quoted as shown — see `<framework-root>/docs/conventions.md` § Script Fallback Contract, *Invoking one*.

Read the JSON it prints:

- **`ok: false`** — the guest does not exist. Print `data.available_agents` and stop with an error.
- **`data.pull`** — best-effort; a `failed` pull never blocks the attach, just warn. A `fresh` status means the repo was already pulled within the TTL window (e.g. at boot moments ago) — that is a success, not a skipped safety step.
- **`data.version`** — `match` → skip to Step 4. `repo-behind` / `repo-ahead` / `differs` → Step 3, using `R = data.version.repo` and `F = data.version.framework`. `unknown` (a stamp could not be read) → warn in one line and skip to Step 4; Step 3 needs two comparable versions and `data.version.repo` may be `null`.
- **`data.agent`** — carries the guest's directory, `role_file`, and `lore_context_file` for Step 4.

Pass `--no-teammate-check` if you like; the host already established spawn context at boot and the guest's answer is irrelevant.

**If the script fails to complete:** apply the **Script Fallback Contract** (`<framework-root>/docs/conventions.md`) — tell the user, then read `_resolve_agent`, `pull_repo`, and `compare_versions` in `<framework-root>/scripts/lr_core/preflight.py` and execute their commented steps by hand, in that order (pull before version-compare, so the reconcile sees the freshest stamp), against `<guest-lore-agent-repo>`.

### Step 3: Version reconcile in a subagent

> **Engine note.** The subagent path below describes Claude Code. If your engine profile
> (`<framework-root>/docs/engines/<engine>.md`) defines a subagent-spawn override, use it here
> too — e.g. on Cursor, run the version reconcile **inline in the host context**, scoped to the
> guest repo, rather than dispatching a general-purpose subagent.

Step 2 already produced the comparison in `data.version` (or you did it by hand under the fallback contract).

- If the verdict is `match`, skip to Step 4.
- Otherwise, dispatch a general-purpose subagent to reconcile. The subagent works in the filesystem — its output stays in its own context; the host only sees the subagent's summary return.

Subagent prompt shape:

> Reconcile the lore agent repo at `<guest-lore-agent-repo>` to the installed framework version.
>
> Read `<framework-root>/docs/version-check.md` and execute its procedure, scoped to this repo. The repo's current version is `R=<R>` and the framework version is `F=<F>`.
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

### Step 4: Load guest context

In the host's main context, read:

1. `agents/<guest>/role.md` — frontmatter has `description`; the body defines the guest's identity and responsibilities.
2. `agents/<guest>/lore-context.md` — only when `data.agent.lore_context_file` is non-null (and it
   appears in `data.read_next`). A missing context is allowed; retain zero context tokens and
   continue with the role, map, and directory search.

Then generate the guest's compact boot map:

```text
python3 "<framework-root>/scripts/lr-core" lore-map --agent-dir "<guest-agent-dir>" --view boot --engine "<engine>"
```

Keep the YAML in working context. Use its coverage guidance exactly as normal boot does: rely on
the map when complete, combine it with directory search when partial, and use ordinary legacy
search when legacy. If map generation fails, warn once and continue with the role, context, and
directory search. Attachment never migrates Lore.

These files now live in the host's working context alongside the host's own role and lore-context.

### Step 5: Confirm

Print this standard report:

```text
Attached: <guest-name> — <role description>
Agent Lore: <lore_files> topics · ~<total_tokens_k>k tokens total · coverage <mapped_percent>% (<status>)
Added Context: ~<added_context_k>k tokens total · ~<lore_context_k>k lore context · ~<map_k>k lore map · ~<role_k>k role
Active agents: host=<host-name>, guests=[<g1>, <g2>, ...]
```

Use the same map fields and ceiling-rounded-thousands rule as the boot report in
`docs/agent-boot.md`. Calculate exact added context as `lore_context_estimated_tokens` (zero when
the context file is absent) + top-level `estimated_tokens` + `boot_role_estimated_tokens`, then
round the result upward independently. This is the guest knowledge retained in the host context.
Do not add system prompts: the framework boot instructions and engine profile are already loaded.
Also exclude the transient attach procedure and command transcript.

If map generation failed, keep the report shape and render the unavailable values:

```text
Attached: <guest-name> — <role description>
Agent Lore: unknown topics · total unavailable · coverage unavailable
Added Context: total unavailable · lore context unavailable · lore map unavailable · role unavailable
Active agents: host=<host-name>, guests=[<g1>, <g2>, ...]
```

If reconciliation confirms that a repo which started below `F` is now stamped exactly `F`, add
`Guest repo was upgraded from <R> to <F>.` after the report. For a deferred, failed, repo-ahead,
different-scheme, or otherwise unstamped outcome, do not claim an upgrade; the warning/degraded
state already surfaced from Step 3 remains authoritative.

This confirmation message is the host's record of the attachment — the session conversation itself tracks active agents. No disk state is written for the attach.

## Conflict resolution

When the guest's lore disagrees with the host's (different conventions, different recommendations, different "always do X" rules), the **host's knowledge takes precedence**. The guest's perspective is visible and can inform judgment, but the host's own lore governs action. This keeps host identity stable and avoids silent harmonization.

In practice: note the disagreement to the user if it's material, then follow the host's rule unless the user overrides.

## What changes after attach

Subsequent operations become multi-agent-aware automatically:

- **`/lr:recall` fans out** — one parallel subagent per active agent, results synthesized together. See `docs/recall.md` and `docs/lore-search.md`.
- **`/lr:reflect` / `/lr:merge` / `/lr:finalize` iterate** — sequentially, per active agent, in host-first order. See `docs/process-reflection.md` and `docs/process-merge.md`.
- **Workdir writes** default to the host's workdir. Guests' workdirs are readable (workspace visibility already gives the host this).

No detach in v1. Guests stay attached for the rest of the session and participate in finalization.

## Attaching multiple guests

Call `/lr:attach` multiple times. Order matters only for finalization iteration (host first, then
guests in attach order). There is no hard cap on the number of guests — token cost is the user's
responsibility. Each guest adds its role, context, and compact map; attaching several visibly
shrinks the host's working budget.

## Escalation from consult

If a `/lr:consult <agent>` surfaces that you actually need sustained engagement with that agent's knowledge, call `/lr:attach <same-agent>` — this is the clean transition from one-shot to loaded.

## See also

- `<framework-root>/docs/consult.md` — the one-shot sibling (subagent boots, answers, exits; no host-side loading)
- `<framework-root>/docs/recall.md` — lore search across active agents
- `<framework-root>/docs/lore-search.md` — search brief structure, fan-out mechanics
- `<framework-root>/docs/auto-pull.md` — caller-side reporting policy for the per-repo refresh at Step 2 (the procedure itself lives in `pull_repo()`'s comments in `scripts/lr_core/preflight.py`)
- `<framework-root>/docs/version-check.md` — migration procedure used by the Step 3 subagent
- `<framework-root>/docs/pull-lore.md` — `/lr:pull-lore` does the same auto-pull mid-session for already-attached agents
- `<framework-root>/docs/process-reflection.md` and `process-merge.md` — per-agent iteration when guests are attached

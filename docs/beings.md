# Lore Beings — Autonomous Agents & the Being Keeper (`lrb`)

> **Audience note.** Reference doc for the Lore Beings module. There is no `/lr:` skill for this
> yet — MVP is CLI-only (`lrb`). Read this when the user asks about autonomous/scheduled agents,
> "beings," or the Being Keeper, or when authoring/debugging a `being.md`.

A **being** is an ordinary lore agent plus a `being.md` descriptor (`agents/<name>/being.md`)
declaring a lifecycle of scheduled sessions. Being-ness is additive: the agent stays fully usable
interactively. The **Being Keeper** is the deterministic, machine-level daemon that spawns those
sessions on schedule and enforces budget — it never reasons, never judges. The governing split:
a being's *consciousness* (planning, judgment) is the LLM; its *substrate* (scheduling, spawning,
budget, kill switch) is deterministic code, never a model.

## The being descriptor

```markdown
---
description: Being definition for chronicler
engine: claude                # must be configured (`lrb engines add`)
model: haiku                  # concrete model name for that engine
daily-usd: 1                  # hard daily spend cap — the spawn gate
existential-tasks:
  - name: morning-wakeup
    schedule: "30 8 * * *"    # cron, machine-local time
    prompt: being/morning-wakeup.md   # path inside this agent's directory
    timeout-minutes: 15       # wall-clock hard kill
---

# Being — chronicler

Standing guidance read at the start of every scheduled session (identity,
escalation rules, what it commits/pushes). The Keeper never reads this body —
only the frontmatter above is its contract.
```

Five frontmatter keys, no more; unexpected top-level or task keys are config errors.
`engine:`/`model:` are plain values — no tiers, no fallback; an unconfigured engine is a
config error, surfaced in `lrb status`, never silently substituted. Task `name` values are safe
slugs (letters, digits, dot, underscore, hyphen; max 64) because they become log filename
components. Task `prompt` paths are relative to the agent directory and may not escape it.
Schedules are plain 5-field cron (`minute hour day month weekday`) in **machine-local time**; day
and weekday restrictions are AND'ed (not cron's OR-when-both-restricted nuance) — fine for the
common "daily at HH:MM" shape. `daily-usd` must be finite and nonnegative; `timeout-minutes` must
be between 1 and 1440.

## Prompt layering (what a woken being reads)

1. **Keeper spawn prompt** — assembled by the Keeper: which agent, which task, headless/no-user
   facts, spend-so-far vs cap, this session's timeout, how to self-schedule (`lrb schedule`).
2. **Normal boot** — `agent-boot.md`: role.md + lore-context.md.
3. **`being.md` body** — the generic being prompt, same every wakeup.
4. **The task prompt** — `agents/<name>/<prompt-path>` for an existential task, or the text passed
   to `lrb schedule` for a self-scheduled one-shot.

No framework-canonical task content — what "morning" means is entirely agent-level.

## The Keeper

One Keeper per machine, serving a registry of workspaces. `~/.lore-beings/` (override `$LRB_HOME`)
holds the installed script, `config.json` (workspaces + configured engines/permission modes), and
launchd's plist. `<workspace>/.lr-beings/` (gitignored — `lrb workspaces add` appends it to the
workspace's own `.gitignore` automatically when the workspace is itself a git repo) holds
`state.json`, `outbox/` (`accepted/`/`rejected/`/`done/`), and per-being `logs/<being>/` (session
logs + sibling `.stderr.log`s + `ledger.jsonl`). `lrb status` shows the *running daemon's* recorded
pid/version (from `$LRB_HOME/daemon.info`, written at daemon start) alongside the CLI's own
version, so drift between an old running daemon and a newer installed copy is visible — plus each
being's last ledger outcome and log directory, not just spend and last-run times.

A tick (~30s): reload config + `being.md` files → fire due existential tasks (same-day catch-up if
missed — a laptop asleep at wakeup time fires once on the next tick, ledger-marked
`spawned-late`; past midnight, dropped and ledger-marked `missed`) → validate new outbox requests → spawn accepted
one-shots whose time has come → poll running sessions (timeout → SIGTERM, then SIGKILL after a
grace period; finished → read the engine's result JSON, record cost) → persist state.

**Budget: exactly two enforced mechanisms**, both Keeper-side: the daily `daily-usd` cap as a
**spawn gate** (refuses new spawns once reached, until machine-local midnight), and per-task
`timeout-minutes` as a **hard kill**. The cap can overshoot by at most (concurrency cap × worst
single-session cost) since cost is only known at session end — documented as designed, not a bug.

**Engines are explicit configuration, never auto-detected** (`lrb engines add <name> --command
<path> [--kind claude|codex|cursor] [--plugin-dir PATH] [--session-cost-usd N]
[--permission-mode default|full]` — probes `<path> --version` as validation). Permission mode
defaults to the engine's own default; `full` only by explicit config (`--dangerously-skip-permissions`
on claude-kind, `--dangerously-bypass-approvals-and-sandbox` on codex-kind, `--force --sandbox
disabled` on cursor-kind) — a being never chooses its own permission level.

**Engine kinds.** Each engine has a `kind` — its invocation + result contract. Kind defaults to
the engine *name* when the name is itself a known kind, else `claude`:

- **`claude`** — spawns `CMD -p PROMPT --output-format json --model M`; the single JSON object on
  stdout carries `total_cost_usd`/`is_error`/`result`, and the *reported* cost is charged against
  `daily-usd`.
- **`codex`** — spawns `CMD exec --json --skip-git-repo-check -m M PROMPT`; stdout is JSONL events
  ending in `turn.completed` (token usage — recorded in the ledger — but **no USD**) or
  `turn.failed`. Because Codex reports no cost, `--session-cost-usd` is **required** at `engines
  add`: that flat USD amount is charged per finished session, whatever its outcome (over-charging
  only trips the cap earlier — the safe direction; without it the `daily-usd` spawn gate would
  silently never trip for codex beings).
- **`cursor`** — spawns `CMD -p PROMPT --output-format json --model M --plugin-dir D --workspace W
  --trust` (plus `--force --sandbox disabled` when `permission_mode: full`). Lore skills require
  `--plugin-dir` pointing at a `lore-framework` checkout — **required** at `engines add` via
  `--plugin-dir`. Result JSON is claude-shaped (`total_cost_usd`/`is_error`/`result`/`usage`), but
  real `cursor-agent` responses have been observed to omit `total_cost_usd` entirely (token `usage`
  only) — so, like codex, `--session-cost-usd` is **required** at `engines add`: that flat USD
  amount is charged whenever `total_cost_usd` is absent (and would still be used if a future
  cursor-agent version reports `total_cost_usd`, in which case the reported figure wins instead).
  Without this, the `daily-usd` spawn gate silently never trips for cursor beings.

Example:

```bash
lrb engines add cursor --command cursor-agent --kind cursor \
  --plugin-dir /path/to/lore-framework --session-cost-usd 0.05
# optional: --permission-mode full
```

**Result-capture contract:** the Keeper redirects the engine's stdout to a log file (stderr goes to
a *sibling* `<log>.stderr.log`, never merged in — any stderr noise merged into the JSON stream
would break the whole-content parse and silently zero out the cost, defeating the budget cap;
observed for real: `codex` writes spurious ERROR lines to stderr on perfectly successful runs).
For claude-kind and cursor-kind, the final JSON object *is* the result (`total_cost_usd`,
`is_error`, `result`; cursor may also carry `usage`); for codex-kind, the last JSONL event decides
the outcome (`turn.completed` → ok, with `usage` tokens copied into the ledger; `turn.failed`/
`error` → error). No separate result-file protocol.

**Only one Keeper runs at a time, machine-wide.** `lrb daemon` takes an exclusive lock
(`$LRB_HOME/daemon.lock`); a second concurrent daemon refuses to start rather than double-spawning
due tasks and racing on `state.json`. The concurrency cap itself is also machine-wide, not
per-workspace, for the same fork-bomb-guard reason. A kill (timeout or `lrb stop`) signals the
spawned session's whole process group, not just the direct child, so a session's own Bash/MCP
grandchildren don't survive a "hard kill." For a session re-adopted from `state.json` after a
Keeper restart, the Keeper first verifies the PID still belongs to the recorded engine command. If
the OS or sandbox blocks that `ps` identity check, the Keeper keeps the session visible but refuses
to signal the unverified PID.

## The outbox — self-scheduling

A running session requests a future one-shot session for itself. **`lrb` is never actually on
PATH** — `lrb install` only copies the script into `$LRB_HOME`, it doesn't symlink anywhere on
PATH — so the Keeper's spawn prompt gives every session the concrete invocation to use (derived
from its own running script path, e.g. `python3 /Users/you/.lore-beings/lrb.py`), and the being is
told explicitly not to type bare `lrb`. The shape:

```bash
<the invocation from your spawn prompt> schedule --agent lore-chronicler/chronicler \
  --at "2026-07-19T15:00:00" --timeout-minutes 30 "Observe today's workspace activity and note it"
```

Validated next tick against: known being, `at` within the next 24h, daily budget not already
exhausted, local ISO datetime with no timezone suffix, bounded timeout → `accepted/` or `rejected/`
(with a reason). A stale accepted request whose `at` has
already passed *its own day* is dropped (`missed`) rather than fired late against the wrong day's
budget/context — same "drop past midnight" policy as existential tasks. One-shots only — recurring
schedules belong in `being.md`, which only a reviewed change edits.

**Permissions are the real blocker to end-to-end autonomy right now.** Self-scheduling (and
writing the diary, and committing) is a Bash/Write call — under a `default` permission-mode engine
in headless mode, there's no user to approve it, so it's denied and the being must (per its own
`being.md` guidance) record that in its summary rather than hang. Observed live in testing: this is
expected, not a bug, but it means a being needs either `permission_mode: full` (blast radius = the
whole workspace, since `cwd` is the workspace root) or a future scoped-`--allowedTools` mechanism
before it can actually complete its designed lifecycle unattended. This is an explicit per-engine
user configuration decision (§7) — the framework does not choose it for you.

## CLI

```
lrb install [--launchd]        copy self to $LRB_HOME, write the launchd plist
                                (only bootstraps the real daemon with --launchd)
lrb daemon [--once]            run the tick loop (what launchd invokes; --once for one tick)
lrb status [--json]
lrb pause / lrb resume         all-beings scheduling switch (dead-man file)
lrb stop                       SIGTERM running sessions + pause
lrb engines add|remove|list
lrb workspaces add|remove|list
lrb schedule --agent A --at ISO [--timeout-minutes N] "prompt"
```

**`lrb install` never bootstraps a persistent daemon by itself** — it writes `~/.lore-beings/` and
the plist, but only loads it into launchd when you pass `--launchd`. This is a deliberate,
framework-added safety gate beyond the original design: installing a background daemon that spends
real money on a schedule is a machine-level, hard-to-reverse action, so it needs an explicit flag,
not just running the installer. `$LRB_HOME` and `$LRB_LAUNCHAGENTS_DIR` make the whole CLI
sandboxable for dev/test — set both to point away from the real machine state.

## Concurrency & failure policy (MVP)

No per-being locks — parallel sessions of the same being are allowed; existing push-conflict
resolution is the backstop. One machine-wide concurrency cap (default 3) guards against a
scheduling bug fork-bombing the API. No retries, no alerting — a crashed/timed-out/over-budget
session is a visible red line in `lrb status` and the ledger; failure policy is designed after
real evidence.

## Autonomy (MVP: reflect-only, fixed)

No `autonomy:` field yet. MVP behavior, stated in the being's own `being.md` body: sessions write
`reflections/` and session summaries, and commit/push only those paths; merge stays user-triggered.
A graduated ladder (`observe` → `reflect-only` → `finalize-branch` → `full`) is designed but
deferred until a real being needs a second behavior.

## Non-goals (MVP)

Teams/hierarchy, delegation, retries/alerting, dashboards, full unattended autonomy, worktree-per-
session, systemd/Windows, `lrb-*` skills (namespace reserved).

## See Also
- `scripts/lrb.py` — the implementation (single stdlib file, floor Python 3.9).
- `agent-being-consciousness-substrate-split.md`, `lore-beings-design.md`,
  `unenforceable-caps-are-prompt-theater.md` — the governing lore (lore-architect, lore-framework-dev).
- `wait.md` — `lr-wait`, the in-session synchronous counterpart; the Keeper owns between-session
  existence, the outbox is symmetric to `lr-emit`.

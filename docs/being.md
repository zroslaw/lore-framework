# Lore Beings Command

`/lr:being` is the single user-facing entry point for Lore Beings. It wraps the deterministic
Being Keeper CLI (`scripts/lrb.py`) and owns the guided workflows for creating `being.md`
descriptors. Users should not need to remember raw `lrb` commands for normal operation.

## Step 0 — Announce

Print this to the user before doing anything else, filling in any `<placeholder>`:

> Managing **Lore Beings** — agents that run on their own in the background and pick up work
> without you starting a session. This is the front door: see what's running, create a being, pause
> or resume one. **Their schedule, budget, and stop rules are enforced by plain code, not by the
> agent's own judgement** — an agent can't be trusted as its own off switch.

## Command parsing

Parse the first argument as the subcommand. If there is no argument, run **Status**. If the first
argument is `help`, run **Help**. Unknown subcommands should show Help plus one short line naming
the unknown command.

Always resolve the Keeper invocation from the framework checkout you are currently using:

```bash
python3 <framework-root>/scripts/lrb.py
```

Do not assume `lrb` is on `PATH`.

> **If the Keeper fails to run**, apply the **Script Fallback Contract**
> (`<framework-root>/docs/conventions.md`). `lrb.py` is the strictest *implementation* script in the
> framework: **never** stand in for it. It enforces budget caps, wall-clock kills, and scheduling —
> a model imitating any of that is prompt-theater, not enforcement. Report the failure with the
> command and the error, state plainly that the Keeper is down and beings are not running, and stop
> that operation. Never report a being as spawned, scheduled, paused, or killed on the Keeper's behalf.

## Status

Subcommands: none, `status`, `list`.

Run:

```bash
python3 <framework-root>/scripts/lrb.py status --json
```

Report a compact status, not the full JSON:

- Keeper: running/stopped, version drift if present, paused/resumed.
- Totals: registered workspaces, configured engines, beings, running sessions, config errors.
- Spend: today's total spend and total daily cap across discovered beings.
- Recent health: count of beings whose last outcome is not `ok`, and name the first few.
- For each workspace with beings: one line per being with `spent/cap`, running count, last outcome,
  and log directory.

If the command fails because the Keeper has not been installed, say that and suggest
`/lr:being keeper install`.

## Help

Subcommand: `help`.

Print this short command list:

```text
/lr:being                         short machine status
/lr:being help                    command list
/lr:being init [agent]            guided setup for an existing agent
/lr:being create [agent]          create a lore agent, then make it a being
/lr:being validate                check being descriptors, engines, and workspaces
/lr:being logs <being>            show ledger/log pointers for one being
/lr:being keeper install          install Keeper files and plist, no daemon start
/lr:being keeper start            install and start the launchd Keeper daemon
/lr:being keeper once             run one Keeper tick for smoke testing
/lr:being keeper stop             stop running sessions and pause scheduling
/lr:being pause | resume          pause/resume all being scheduling
/lr:being engine list|add|remove  manage Keeper engines
/lr:being workspace list|add|remove manage registered workspaces
```

Keep explanations to one sentence each. Point to `docs/beings.md` only for deep reference.

## Init existing agent

Subcommand: `init [agent-name]`.

Goal: create `agents/<agent-name>/being.md` and the first task prompt
`agents/<agent-name>/being/<task-name>.md` for an existing lore agent.

Procedure:

1. Discover lore agent repos with `python3 "<framework-root>/scripts/lr-core" discover --workspace "<cwd>"`,
   reading `data.repos` / `data.agents` from its JSON. If it fails to complete, apply the Script
   Fallback Contract: read `cmd_discover`'s docstring in `<framework-root>/scripts/lr_core/preflight.py` — it
   carries the numbered steps — and execute them by hand.
2. Resolve the target agent. If the user supplied `agent-name`, use the matching existing agent.
   If omitted and there is one obvious existing agent, use it. Otherwise ask the user which agent.
3. If `being.md` already exists, do not overwrite it. Offer to add a task instead; if the user
   wants that, edit only the `existential-tasks` list and create the new prompt file.
4. Gather missing choices in one compact questionnaire:
   - engine name (default: `codex` if configured, else first configured engine, else `codex`)
   - model (default from engine kind: `gpt-5.4-mini` for codex, `haiku` for claude,
     `composer-2.5` for cursor)
   - daily USD cap (default: `0.10`)
   - first task name (default: `morning`)
   - schedule as 5-field cron in machine-local time (default: `30 8 * * *`)
   - timeout minutes (default: `10`)
   - what the task should do, in the user's words
5. Create `being.md` with the strict five-key frontmatter from `docs/beings.md` and a short
   reflect-only body. Keep it conservative:

   ```markdown
   ---
   description: Being definition for <agent-name>
   engine: <engine>
   model: <model>
   daily-usd: <daily-usd>
   existential-tasks:
     - name: <task-name>
       schedule: "<cron>"
       prompt: being/<task-name>.md
       timeout-minutes: <minutes>
   ---

   # Being — <agent-name>

   You run unattended. Keep scope narrow and prefer reflection over action.
   Write summaries or reflections only unless the user explicitly grants more authority.
   If blocked by permissions, missing context, or uncertainty, record that clearly and stop.
   Do not make irreversible changes without explicit user involvement.
   ```

6. Create the task prompt. Include the user's task text, plus these guardrails:
   - keep the session bounded to this task
   - record what happened and stop when blocked
   - do not broaden autonomy or edit `being.md`
7. Run `/lr:being validate`. If validation passes, suggest `/lr:being keeper once` as the next
   smoke test. Do not start the persistent daemon automatically.

## Create agent and being

Subcommand: `create [agent-name]`.

Goal: create a new lore agent and immediately run the `init` workflow for it.

Procedure:

1. Follow `docs/create-agent.md` to create the agent. If required information is missing, ask for
   the agent name and role description first.
2. After verifying `role.md`, `lore-context.md`, `lore/`, and `workdir/`, continue directly with
   **Init existing agent** for the new agent.
3. Do not register a shortcut unless the user asks. Mention the registration command in the final
   summary.

## Validate

Subcommand: `validate`.

Run:

```bash
python3 <framework-root>/scripts/lrb.py validate
```

Report whether validation passed. If it fails, group issues by workspace and being, and give the
shortest next fix. Validation is static and does not spend API money.

## Logs

Subcommand: `logs <being-id>`.

Run:

```bash
python3 <framework-root>/scripts/lrb.py logs <being-id>
```

Report the ledger path, log directory, and last few ledger entries. Do not paste full session logs
unless the user explicitly asks.

## Keeper

Subcommands: `keeper install`, `keeper start`, `keeper daemon`, `keeper once`, `keeper stop`,
`keeper pause`, `keeper resume`.

- `install`: run `python3 <framework-root>/scripts/lrb.py install`.
- `start`: run `python3 <framework-root>/scripts/lrb.py install --launchd`.
- `daemon`: run `python3 <framework-root>/scripts/lrb.py daemon` only if the user clearly wants a
  foreground long-running process.
- `once`: run `python3 <framework-root>/scripts/lrb.py daemon --once`.
- `stop`: run `python3 <framework-root>/scripts/lrb.py stop`.
- `pause` / `resume`: same as the top-level pause/resume commands.

Warn before `start` that it creates or restarts a persistent background daemon that can spend real
API money according to configured beings. Continue if the user already asked directly for `start`.

## Pause and resume

Subcommands: `pause`, `resume`.

Run the matching Keeper command:

```bash
python3 <framework-root>/scripts/lrb.py pause
python3 <framework-root>/scripts/lrb.py resume
```

## Engines

Subcommands: `engine list`, `engine add`, `engine remove`.

- `list`: run `python3 <framework-root>/scripts/lrb.py engines list`.
- `remove <name>`: run `python3 <framework-root>/scripts/lrb.py engines remove <name>`.
- `add`: gather missing values, then run `python3 <framework-root>/scripts/lrb.py engines add`.

For `engine add`, default to a safe Codex config when the user gives no details:

```bash
python3 <framework-root>/scripts/lrb.py engines add codex --command codex --kind codex --session-cost-usd 0.05
```

For `cursor`, require `--plugin-dir <framework-root>` and `--session-cost-usd`. For `claude`, use
the configured command as-is; if the user needs Lore skills in claude-kind beings, explain that the
command currently must be a wrapper that supplies `--plugin-dir`.

Do not choose `--permission-mode full` by default. If the user asks for full unattended writes,
include it explicitly and name the workspace-wide blast radius.

## Workspaces

Subcommands: `workspace list`, `workspace add`, `workspace remove`.

- `list`: run `python3 <framework-root>/scripts/lrb.py workspaces list`.
- `add [path]`: default to the current working directory; run `python3 <framework-root>/scripts/lrb.py workspaces add <path>`.
- `remove <path>`: run `python3 <framework-root>/scripts/lrb.py workspaces remove <path>`.

## Design constraints

- This skill is the product UX. `lrb.py` remains deterministic substrate.
- `init` and `create` should be guided and concise, not a wall of docs.
- Never start the persistent daemon as a side effect of `init`, `create`, `engine add`, or
  `workspace add`.
- Prefer low defaults: `daily-usd: 0.10`, `timeout-minutes: 10`, reflect-only body.
- Keep `being.md` schema strict; do not add fields that the Keeper cannot enforce.

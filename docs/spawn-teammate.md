# Spawn Teammate (BETA)

`/lr:spawn-teammate` spawns one or more lore agents as Claude Code Agent Teams teammates. The current session becomes the team lead. Each teammate is a separate, independent Claude Code instance booted as the named lore agent via `agent-boot.md`.

This is the framework's first integration with Agent Teams. It is intentionally **minimal**: a thin name-resolution and spawn-prompt-composition layer over Agent Teams' natural-language interface. It does not introduce any new state, file format, or per-agent metadata.

## Status — BETA

- The skill name and high-level behavior (resolve names → spawn teammates booted as the named agents) are stable for the duration of the beta.
- Internal procedure and presentation may evolve based on real-world usage.
- Open design questions — lore-write serialization across teammates, automated finalization across teammates, hook integration, subagent-definition mode — are explicitly out of scope for v1 and tracked as open questions to be resolved before graduation.

## Usage

```
/lr:spawn-teammate <agent-name>            # spawn one teammate
/lr:spawn-teammate <name-1> <name-2> ...   # spawn multiple at once
/lr:spawn-teammate                         # infer agent set from session context (asks if ambiguous)
```

Agent names are matched case-insensitively with fuzzy-tolerance — typos resolve when the closest match is unambiguous; ambiguity prompts the user.

Examples:

- `/lr:spawn-teammate tax-advisor`
- `/lr:spawn-teammate tax-advisor masschallenge-judge`
- `/lr:spawn-teammate tax-advsr` — resolved to `tax-advisor`

## Procedure

### Step 1 — Preconditions

1. **Verify Agent Teams is enabled.** Either:
   - The environment variable `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` is set to `1` (check via `echo $CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`), **or**
   - `~/.claude/settings.json` contains `"env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" }`.

   If neither is set, print the following and stop:

   > Agent Teams is not enabled. To enable, add to `~/.claude/settings.json`:
   > ```json
   > {
   >   "env": {
   >     "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
   >   }
   > }
   > ```
   > or set `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in your shell. Requires Claude Code v2.1.32 or later.

2. **Locate the domain.** The current working directory is the domain. If no direct subdirectory of the cwd contains a `lore-repo.md`, stop with: `No lore agent repos found in <cwd>. Run /lr:spawn-teammate from a lore framework domain directory.`

   The skill does not check the running Claude Code version — Agent Teams' own error will surface if the version is older than v2.1.32.

### Step 2 — Enumerate available agents

Walk the domain. For each subdirectory containing `lore-repo.md` at its root, scan `agents/*/role.md` to enumerate `(repo, agent-name, role-description)` tuples. Build a flat list of available agents.

If two repos contain agents with the same name, retain the repo qualifier internally (used in Step 4 for cross-repo collision handling).

### Step 3 — Determine the input set

`$ARGUMENTS` is the user input — zero or more space-separated tokens.

**3a. `$ARGUMENTS` non-empty:** tokenize on whitespace. Each token is an input agent name.

**3b. `$ARGUMENTS` empty (context inference):** build the input set from the session conversation:

- Look at recent user and assistant messages, decisions made in the session, and explicit references to lore agents.
- Identify lore agents named directly or strongly implied by the topic of conversation.
- Confidence-gate the result:
  - **Clear** (1–3 agents named directly or unambiguously implied): proceed with that set. Print the resolved set with one-line reasoning, e.g. `Inferred from context: tax-advisor, masschallenge-judge — discussion centered on tax-advice/judging tasks for the X project.`
  - **Ambiguous** (multiple plausible interpretations, or thin signal): present a numbered list of likely candidates and ask the user to pick. Do not guess.
  - **No signal**: print `No agent specified or inferred from context. Available agents: <list>` and stop.

### Step 4 — Match each input name to an available agent

For each input name `n`:

1. **Exact case-insensitive match** against an available agent name — if exactly one match, take it.
2. **Fuzzy match** otherwise: compute Levenshtein distance and substring/prefix bonus against each available agent name. Take the best candidate when:
   - Levenshtein distance ≤ 2, **and**
   - the best candidate's score is meaningfully better than any runner-up (no near-tie).

   When fuzzy-matched, **always tell the user the resolution**: `Resolved '<input>' → '<resolved>'`.
3. **Cross-repo collision** (multiple repos contain agents with the matched name and the input is unqualified): ask the user to disambiguate by repo path.
4. **Ambiguous fuzzy match** (multiple candidates score similarly): ask the user to pick from the candidates.
5. **No plausible match**: print `No match for '<input>'. Available agents: <list>` and stop.

### Step 5 — De-duplicate and check self-spawn

- Collapse duplicates in the resolved set (same agent named twice). Warn if the user input had duplicates.
- If a teammate with the same name already exists in the current Agent Teams team, drop it from the spawn set and warn — Agent Teams uses names as identifiers; spawning a duplicate is undefined.
- If the host session is currently booted as a lore agent and the user is asking to spawn that same agent: allow it but warn. Two parallel sessions of the same agent are out of band but not pathological.

If after de-duplication the spawn set is empty, stop with: `No new teammates to spawn.`

### Step 6 — Compose teammate specs

For each `(agent-name, repo-path)` in the spawn set:

- **Teammate name**: the kebab-case agent name (matches the agent's directory name under `<lore-agent-repo>/agents/`).
- **Spawn prompt** (verbatim, including the closing instruction):

  ```
  Read ${CLAUDE_PLUGIN_ROOT}/docs/agent-boot.md and boot as agent <agent-name> from <abs-path-to-agent-dir>. After boot, await further instructions from the team lead via SendMessage.
  ```

  Substitute:
  - `<agent-name>` — the resolved kebab-case name
  - `<abs-path-to-agent-dir>` — the absolute path to the agent's directory (`<lore-agent-repo>/agents/<agent-name>/`)

  `${CLAUDE_PLUGIN_ROOT}` is left **literal** in the spawn prompt — the teammate's session resolves it via Claude Code (teammates load skills from project and user settings, per the Agent Teams documentation).

  The "After boot, await further instructions from the team lead via SendMessage" line tells the teammate to stop after the boot procedure's "Confirm" step rather than invent a task on its own.

### Step 7 — Invoke Agent Teams

Compose a single natural-language directive to the lead instructing it to create or extend the Agent Teams team with the composed teammate specs. The directive must:

- State whether to create a new team or add to the existing team. Agent Teams allows only one team per session — if a team is already active, add to it.
- For each teammate, provide the **exact name** and the **verbatim spawn prompt** with no paraphrasing.
- Instruct the lead to spawn the teammates immediately rather than just plan.

Template (substitute `<N>` and the per-teammate fields):

```
Create an agent team in this session (or add teammates to the existing team if one is already active in this session) with the following <N> teammates. Use these exact names and spawn prompts verbatim — do not summarize, paraphrase, or wrap them.

Teammate 1:
  - Name: <agent-name-1>
  - Spawn prompt: "<verbatim spawn prompt 1>"

Teammate 2:
  - Name: <agent-name-2>
  - Spawn prompt: "<verbatim spawn prompt 2>"

(... additional teammates as needed ...)

Spawn the teammates now.
```

Once the directive is sent, **Agent Teams owns the spawn lifecycle**. The skill does not poll, monitor, or interact with the team further.

### Step 8 — Report

Print a compact summary:

- **Resolved agents**: the resolved agent set; call out fuzzy-match resolutions and any de-duplications.
- **Team status**: `created` (new team) or `extended` (added to existing team).
- **Teammates spawned**: name + repo path for each.
- **Usage hint** (one line): `Use Shift+Down (in-process) or click into a pane (split-pane) to interact with a teammate. Run /lr:spawn-teammate again to add more. Ask the team lead to clean up when done.`

If this is the first invocation of the skill in the session, also surface beta caveats:

> **BETA notes:**
> - Lore writes by multiple teammates are not serialized — last-write-wins. Defer lore-changing work to finalization.
> - Finalization across teammates is not yet automated. Each teammate runs its own `/lr:finalize` before disbanding; the lead's own session is finalized separately.
> - Agent Teams' own limitations apply: one team per session, no session resumption with in-process teammates, no nested teams, lead is fixed.

## What this skill does NOT do

- Does not modify any framework or repo files. The skill is read-only on the filesystem.
- Does not poll or monitor Agent Teams state after the spawn directive is sent.
- Does not register lore agents as Claude Code subagent definitions. Spawning uses raw natural-language directives with explicit spawn prompts. Subagent-definition mode is intentionally out of scope for v1 — per Agent Teams docs, the `skills` and `mcpServers` fields of a subagent definition are NOT applied to teammates, which would break lore agents that depend on the `/lr:*` skills.
- Does not handle finalization across teammates. (Open design question.)
- Does not check the Claude Code version directly.

## Edge cases

- **Cwd not a domain.** Stop in Step 1 with the message above.
- **Single repo, single agent, host session is the only candidate.** With no args and no contextual signal, the skill asks rather than guessing.
- **Teammate boot fails inside Agent Teams.** Boot output appears in the teammate's pane (split-pane mode) or via Shift+Down (in-process). The skill has no visibility once the directive is sent — investigation and recovery happen through Agent Teams' own UI.
- **Agent Teams not installed / version too old.** The activation check passes (env var present) but the natural-language spawn fails. The lead's response surfaces Agent Teams' own error to the user.
- **Multi-repo domain.** Names from different repos appear in the unified pick list; cross-repo collisions are disambiguated explicitly by repo path.
- **CWD safety.** Use absolute paths when reading agent files across repos. Never `cd` into a repo for inspection — see the CWD safety section of `${CLAUDE_PLUGIN_ROOT}/docs/conventions.md`.

## See Also

- `${CLAUDE_PLUGIN_ROOT}/docs/agent-boot.md` — the boot procedure each teammate follows on spawn.
- `${CLAUDE_PLUGIN_ROOT}/docs/consult.md` — lightweight one-shot question to an unloaded agent (in-session).
- `${CLAUDE_PLUGIN_ROOT}/docs/attach.md` — sustained guest loading within one session.
- `${CLAUDE_PLUGIN_ROOT}/docs/recall.md` — search lore of agents already loaded.
- Official Agent Teams documentation: https://code.claude.com/docs/en/agent-teams

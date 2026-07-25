# Spawn Teammate (BETA)

`/lr:spawn-teammate` spawns one or more lore agents as Claude Code Agent Teams teammates. The current session becomes the team lead. Each teammate is a separate, independent Claude Code instance booted as the named lore agent via `agent-boot.md`.

This is the framework's first integration with Agent Teams. It is intentionally **minimal**: a thin name-resolution and spawn-prompt-composition layer over Agent Teams' `Agent`-tool interface. It does not introduce any new state, file format, or per-agent metadata.

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

2. **Locate the workspace.** The current working directory is the workspace. If no direct subdirectory of the cwd contains a `lore-repo.md`, stop with: `No lore agent repos found in <cwd>. Run /lr:spawn-teammate from a lore framework workspace.`

   The skill does not check the running Claude Code version — Agent Teams' own error will surface if the version is older than v2.1.32.

### Step 2 — Enumerate available agents

Walk the workspace. For each subdirectory containing `lore-repo.md` at its root, scan `agents/*/role.md` to enumerate `(repo, agent-name, role-description)` tuples. Build a flat list of available agents. If a repo has `lore-repo.md` but no `agents/` directory or no agent subdirs with `role.md`, skip it silently (it contributes zero agents to the list).

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
- **Spawn prompt** (verbatim — the teammate boots with this as its first input):

  ```
  Read <framework-root>/docs/agent-boot.md and boot as agent <agent-name> from <abs-path-to-agent-dir>.

  Step 2 of the boot procedure will detect that you were spawned as a teammate and load <framework-root>/docs/teammate-conventions.md — the four RULES declared there are standing rules for this entire session. Recap, in case the boot-time load fails: the user in YOUR own pane is your interlocutor. Talk to them there; SendMessage to the team lead is reserved for explicit user-requested coordination only.

  After boot's Confirm step, stop and wait for the user's instructions in YOUR pane.
  ```

  Substitute:
  - `<agent-name>` — the resolved kebab-case name
  - `<abs-path-to-agent-dir>` — the absolute path to the agent's directory (`<lore-agent-repo>/agents/<agent-name>/`)

  `<framework-root>` is left **literal** in the spawn prompt — the teammate's session resolves it via Claude Code (teammates load skills from project and user settings, per the Agent Teams documentation).

  **Single source of truth.** The four RULES live in `teammate-conventions.md`. The spawn prompt above intentionally does NOT restate them in full — that would create three-way drift between the spawn prompt, the conventions doc, and the conventions.md summary. Instead, the prompt points the teammate at the boot-time load (which is the durable mechanism) and includes only a one-sentence recap as a fallback for the case where the boot-time load fails (e.g. `<framework-root>` doesn't resolve in the spawned environment). The boot-time load via `agent-boot.md` Step 2 is what actually anchors the rules; the spawn-prompt recap is a safety net, not a parallel statement.

### Lead behavior — teammate-to-lead messages

If a spawned teammate sends the lead a message asking for user input, instructions, clarifications, or approvals, the lead **must** respond immediately via SendMessage to redirect them: tell the teammate the user is in their own pane, that they should ask the user there, and that they should only message the lead when the user explicitly asks for cross-agent coordination. Do not paraphrase the user, do not act as a relay, and do not let the request sit unanswered while the teammate idles.

Idle notifications (`{"type":"idle_notification",...}`) are status pings — no response is required and no action is needed.

### Step 7 — Spawn the teammates via the Agent tool

**The current session IS the team lead.** This skill runs in-process — the user invoked `/lr:spawn-teammate` directly in the lead's pane, so the lead has the `Agent` tool in scope right here. There is no separate "lead session" to message; the operative call is a direct `Agent` invocation from this session.

#### 7a. Resolve a stable team name

Pick a team name once and reuse it. Recommended scheme: `lr-<host-agent-name>-team` if the host session is booted as a lore agent, otherwise `lr-spawn-team`. A stable, predictable name makes the failure-recovery instructions in § Common Pitfalls actionable.

Check `~/.claude/teams/<team-name>/`:

- **Exists with `config.json` and the host's session is already part of an active team** → reuse it (Agent Teams allows only one team per session). Skip the `TeamCreate` call.
- **Exists but is empty / missing `config.json` / no team is active in this session** → it's leftover state from a prior failed spawn. Remove it: `rm -rf ~/.claude/teams/<team-name>/`. Then proceed to create a fresh team.
- **Does not exist** → create the team explicitly with `TeamCreate({name: "<team-name>"})` so behavior is deterministic. (Letting Agent Teams auto-create on the first `Agent` call also works, but the team's name is then implementation-defined and recovery is harder.)

#### 7b. Call the `Agent` tool, once per teammate

**Pre-call snapshot.** Before issuing any `Agent` call, read `~/.claude/teams/<team-name>/config.json` once and remember the count of `members[]` entries with `backendType == "iterm2"` AND `agentType != "team-lead"`. **If the file does not exist** (fresh team where `TeamCreate` has just run but Agent Teams hasn't flushed `config.json` yet), the snapshot count is **0**. This snapshot is consumed by Step 8's first-iTerm2-spawn caveat — capture it now because Agent Teams mutates the file the moment any `Agent` call returns.

For each `(agent-name, spawn-prompt)` from Step 6, call:

```
Agent({
  team_name:     "<team-name>",                  // the stable name from 7a
  name:          "<agent-name>",                 // resolved kebab-case agent name
  subagent_type: "claude",                       // or "general-purpose" — must be a full-capability type, NOT a read-only/research-only agent
  prompt:        "<verbatim spawn prompt from Step 6>"
})
```

Important:

- **`prompt` is the verbatim spawn prompt from Step 6** — the one starting `Read <framework-root>/docs/agent-boot.md and boot as agent <agent-name> from <abs-path-to-agent-dir>...`. **Do not** pass the natural-language "Create an agent team..." directive that earlier versions of this doc described — that directive was a relic intended for a separate lead session and never made sense as an `Agent`-tool prompt.
- **Do not delegate this call to a subagent** (e.g. via a wrapping `Agent` call whose prompt says "now spawn a teammate"). Subagents do not have the `Agent` tool in scope; they cannot create teammates. The whole point of being in the lead's pane is to make the call directly.
- Multiple teammates: send the `Agent` calls in a single message in parallel — they are independent.

#### 7c. Post-spawn verification

The `Agent` call returning is **not** sufficient evidence the teammate actually booted. Two known failure modes leave the team registered as if spawn succeeded while no live teammate process exists:

1. **iTerm2 keystroke-corruption race** (see § Common Pitfalls — *Input-slip corruption of the launch command*): Agent Teams' iTerm2 backend opens a new pane and emits the `cd ... && env ... claude --agent-id ...` shell command. The new pane auto-focuses immediately, and any keystrokes the user types in their previous pane during the focus shift leak into the new pane and prefix-corrupt the command. The shell typically rejects with `command not found`, the `&&` short-circuits, and the `claude` binary never starts — but `~/.claude/teams/<team>/config.json` already lists the teammate as `isActive: true`.
2. **Boot failure inside the teammate session.** The `claude` process did start, but `agent-boot.md` failed (e.g. agent path wrong, version-check defer, auto-pull error). The teammate is alive but not ready to interact.

**Important — verification is necessary but not sufficient.** The check below catches the *boot-failure* class (the `claude` process started but didn't bootstrap cleanly). It does **not** reliably catch the *iTerm2 keystroke-corruption race* — Agent Teams writes `isActive: true` and `tmuxPaneId` *before* the launch shell line is executed in the new pane, so a corrupted launch passes the JSON check unchanged. See § Common Pitfalls — *Input-slip corruption of the launch command*. The only authoritative signal for that failure is the teammate's pane contents (a fresh shell prompt + `command not found` indicates corruption); always tell the user in Step 8 to glance at the pane.

After all `Agent` calls return, for each teammate whose `Agent` call returned successfully (skip any whose call errored — those are reported separately in Step 8 with the upstream error):

1. **Read with a brief retry** to absorb the config-write race. Agent Teams may flush `~/.claude/teams/<team-name>/config.json` slightly after the `Agent` call returns. Read up to **5 times with ~50 ms between attempts** before declaring failure. On each attempt:
   - Parse `members[]`.
   - **Skip the lead entry** — entries with `agentType: "team-lead"` are not the spawn target. Match teammates by `name == "<agent-name>"` (or `agentId` ending in `@<team-name>`) AND `agentType != "team-lead"`.
   - For the matched teammate entry, check `isActive: true`. Then apply the per-backend rule:
     - **`backendType == "iterm2"`** (currently the only shipping backend that surfaces a pane id): require `tmuxPaneId` non-empty. Pass = `isActive && tmuxPaneId`.
     - **Any other / unknown `backendType`**: pass condition is `isActive: true` alone. `tmuxPaneId` semantics differ per backend, so its absence here means **inconclusive**, not failed — record this teammate as `verified-inconclusive` (distinct from `verified-live` and `unverified`) so Step 8 can surface the weakened check to the user.
   - If the check passes (live or inconclusive), break the retry loop.
   - If the entry is missing or fails the check, sleep ~50 ms and retry.
2. **Best-effort liveness ping** (don't block on this): the most reliable signal is the teammate's own pane contents, surfaced through Agent Teams' UI. Do **not** auto-`SendMessage` a clarification-style ping — that would itself violate the no-unsolicited-SendMessage discipline `teammate-conventions.md` is teaching the teammate, *and* the teammate's response would also be a SendMessage, polluting the channel. Just tell the user in Step 8 to look at the pane.

If verification fails for a teammate after the retries, surface the failure loudly with the action ladder first, hedging context after:

```
<agent-name>: spawn registered but verification failed.

DO THIS:
  1. Open the teammate's pane (Shift+Down for in-process; click into the split pane otherwise).
  2. Look at the pane:
     - Fresh shell prompt with `command not found` → launch was corrupted. Copy the launch command
       from ~/.claude/teams/<team-name>/config.json (the member's `prompt` and surrounding env)
       and paste it into the pane manually. No config.json edit needed.
     - Partial boot output with an error → boot failure. Fix the cause (e.g. agent-dir path),
       then re-run /lr:spawn-teammate <agent>.
  3. (Last resort, only if step 2 cannot recover AND no other teammates in this team are live):
       rm -rf ~/.claude/teams/<team-name>/
     then re-run /lr:spawn-teammate. **DO NOT** do this if other teammates are live — it destroys
     their state too. To clean a single dead member without touching the rest, edit config.json
     and remove just that member's entry (or leave it; Agent Teams tolerates stale entries).

CONTEXT (for the curious):
  - Most likely cause: iTerm2 keystroke-corruption race during pane focus shift (see Pitfall —
    Input-slip corruption of the launch command). The JSON check cannot detect this case, so
    "verification failed" might also mean "verification was inconclusive"; the pane is the truth.
  - Other cause: boot failure inside the teammate session (agent-dir path wrong, version-check
    defer with dirty files in the booting repo, auto-pull failure).
```

Verification failure does **not** automatically clean up `config.json` — that risks racing with a slow-to-start teammate, and a `rm -rf` of the team dir would blow away every other live teammate. The user inspects, then chooses recovery; the skill never deletes team state on its own.

Once the `Agent` calls return and verification has run, **Agent Teams owns the rest of the spawn lifecycle**. The skill does not poll or monitor further.

### Step 8 — Report

Print a compact summary:

- **Resolved agents**: the resolved agent set; call out fuzzy-match resolutions and any de-duplications.
- **Team status**: `created` (new team) or `extended` (added to existing team).
- **Teammates spawned**, distinguishing four states:
  - **verified-live**: `Agent` returned successfully AND Step 7c verification passed with full strength (`isActive && tmuxPaneId` for iTerm2 backend). Format: name + repo path.
  - **verified-inconclusive**: `Agent` returned successfully AND `isActive: true` but `tmuxPaneId` semantics don't apply for this backend — the teammate is registered as live but the framework cannot positively confirm it booted. Format: name + repo path + one-line nudge: `verification weakened for backendType=<N> — open the pane to confirm boot succeeded (you should see the agent's confirm-loaded message; a bare shell prompt or partial boot output means boot failed — see the recovery block above).`
  - **unverified** (Step 7c's `unverified` state — `Agent` returned successfully but Step 7c verification failed after retries): emit the recovery block from Step 7c.
  - **spawn errored**: the `Agent` call itself returned an error — surface the upstream error verbatim. No verification is run for these (the spawn never happened); no team-state cleanup is suggested (Agent Teams handles its own rollback for failed `Agent` calls).
- **iTerm2 caveat** — emit when both: (a) at least one spawned teammate has `backendType == "iterm2"`, AND (b) this is a **first-time iTerm2 spawn for this lead session**, derived from a concrete observable: BEFORE the `Agent` calls in Step 7b, `members[]` in `~/.claude/teams/<team-name>/config.json` contained zero entries with `backendType: "iterm2"` AND `agentType != "team-lead"` (i.e. no prior iTerm2 teammate has ever joined). When both conditions hold, emit: `Glance at the new pane briefly — Step 7c cannot detect iTerm2 keystroke-corruption (see Pitfall — Input-slip corruption). A fresh shell prompt with no boot output means the launch was corrupted; paste the launch command from config.json to recover.` Subsequent iTerm2 spawns in the same team skip this line; on a verification failure the recovery block already mentions the keystroke race, so no separate caveat is needed.

  *Why this gating?* The caveat is most useful on the first iTerm2 spawn (the user may not yet know the failure mode); on later spawns it becomes ignored boilerplate. Anchoring to `members[]` content before the Agent calls is concrete (no in-LLM state needed) and degrades gracefully — first invocation in a fresh team always emits, repeated invocations in the same team don't.
- **Usage hint** (one line): `Use Shift+Down (in-process) or click into a pane (split-pane) to interact with a teammate. Run /lr:spawn-teammate again to add more. Ask the team lead to clean up when done.`

If this is the first invocation of the skill in the session, also surface beta caveats:

> **BETA notes:**
> - Lore writes by multiple teammates are not serialized — last-write-wins. Defer lore-changing work to finalization.
> - Finalization across teammates is not yet automated. Each teammate runs its own `/lr:finalize` before disbanding; the lead's own session is finalized separately.
> - Agent Teams' own limitations apply: one team per session, no session resumption with in-process teammates, no nested teams, lead is fixed.

## What this skill does NOT do

- Does not modify any framework or repo files. The skill is read-only on the filesystem (it does call `TeamCreate` and `Agent` in Step 7, both of which mutate Agent Teams' own state under `~/.claude/teams/`, not the workspace).
- Does not poll or monitor Agent Teams state after the spawn calls return.
- Does not register lore agents as Claude Code subagent definitions. Spawning uses direct `Agent`-tool calls with explicit spawn prompts. Subagent-definition mode is intentionally out of scope for v1 — per Agent Teams docs, the `skills` and `mcpServers` fields of a subagent definition are NOT applied to teammates, which would break lore agents that depend on the `/lr:*` skills.
- Does not handle finalization across teammates. (Open design question.)
- Does not check the Claude Code version directly.

## Common Pitfalls

### Delegating Step 7 to a subagent

The classic failure: the model running this skill reads "compose a directive to the lead" or similar phrasing and decides to call `Agent` with that directive as the *prompt*. The freshly-spawned subagent receives the directive, looks for the `Agent` tool to act on it, doesn't find it (subagents cannot spawn teammates — only the top-level lead session can), and reports back that nothing happened. The team often ends up half-created (an empty `~/.claude/teams/<name>/` directory) and the user is stuck.

**Why it happens:** the natural reading of "directive to the lead" is "send a message" — but the skill is *already running in the lead's session*. The lead is the caller, not a separate addressee. There is no lead to message; the lead executes.

**How to avoid it:** Step 7 is now explicit — call `Agent` directly from this session with `team_name` / `name` / `subagent_type` / `prompt`, where `prompt` is the verbatim Step 6 spawn prompt. Do not wrap it, do not delegate it, do not paraphrase it.

### Stale team directory from a failed prior spawn

If a prior `/lr:spawn-teammate` invocation failed in Step 7 (often via the pitfall above), it may have created `~/.claude/teams/<name>/` without populating `config.json` or with a `config.json` that no longer corresponds to any active team. A second invocation reusing the same name then misbehaves.

Step 7a's pre-flight handles this: detect-and-clean the empty/stale directory before creating the team. If the user reports that spawn behaves oddly and you suspect a prior partial spawn, manually `rm -rf ~/.claude/teams/<team-name>/` and retry.

### Input-slip corruption of the launch command

**Symptom.** The user runs `/lr:spawn-teammate <agent>`. Agent Teams' iTerm2 backend opens a new pane and starts emitting the launch command (`cd /path && env ... claude --agent-id <agent>@<team> ...`). The new pane auto-focuses **immediately**. If the user happens to be typing in the original pane at that exact moment, the next handful of keystrokes land in the new pane *before* the shell command arrives, prefix-corrupting it. Concrete example seen in real use:

```
Intended:  cd /Users/.../Activities && env ... claude --agent-id <agent>@<team> ...
Got:       pt acd /Users/.../Activities && env ... claude --agent-id ...
           zsh: command not found: pt
```

The user's `pt a` keystrokes prefixed `cd`, the shell rejected `pt`, the `&&` short-circuited, and the actual `claude` invocation never ran. Meanwhile `~/.claude/teams/<team-name>/config.json` already listed the teammate as `isActive: true` because Agent Teams writes that record before — or independently of — the launch command actually executing.

**Why the framework can't fix it directly.** The keystroke-emission path is owned by Agent Teams (the iTerm2 send-text API), not by `/lr:spawn-teammate`. Our skill only composes the boot prompt that's passed to `Agent` as an argument; the outer shell line that opens the pane and starts `claude` is constructed by Agent Teams. Defenses applied in *our* prompt (Ctrl-U, bracketed-paste markers, etc.) don't help — they're inside the `claude -p <prompt>` payload, not on the shell line where the corruption happens.

**What we do.** Step 7c's post-spawn verification reads `config.json` and checks for live `isActive` + non-empty `tmuxPaneId`. **It does not catch this failure** — Agent Teams writes the active record before the launch shell line executes, so a corrupted launch passes the JSON check unchanged. Step 7c is honest about this in its preamble and its failure-recovery message: "Most likely cause: iTerm2 keystroke-corruption race during pane focus shift … the JSON check CANNOT detect this, so even a 'passed' verification doesn't guarantee a live teammate." Step 8's report tells the user to glance at the spawn pane regardless of whether verification passed. The framework cannot do better than that without changes upstream in Agent Teams.

**Mitigations.** Two practices reduce the symptom rate:

- **Stop typing when invoking `/lr:spawn-teammate`.** A literal "hands off the keyboard for ~1 second after submission" works.
- **Use split-pane mode rather than in-process if possible** — focus shifts are less disruptive than tab cycles in busy panes.

**Upstream fix.** The framework-level fix lives in Agent Teams: prepend a buffer-clearing sequence (`\x03\x15` — Ctrl-C then Ctrl-U) to the launch command, or wrap the launch in a temp script (`bash /tmp/lr-spawn-<ts>.sh`) so a small prefix corruption produces a single clean failure. If you hit this enough to be painful, file the issue with the Anthropic Agent Teams team referencing this Pitfall section.

### Wrong `subagent_type`

`subagent_type` must be a full-capability agent (`claude` or `general-purpose`). Read-only / research-only agent types do not have the tools a lore-agent boot procedure needs (Read, Edit, Write, Bash for git status, etc.) — boot will fail partway through Step 1 or Step 2 of `agent-boot.md`. When in doubt, pass `claude`.

## Edge cases

- **Cwd not a workspace.** Stop in Step 1 with the message above.
- **Single repo, single agent, host session is the only candidate.** With no args and no contextual signal, the skill asks rather than guessing.
- **Teammate boot fails inside Agent Teams.** Boot output appears in the teammate's pane (split-pane mode) or via Shift+Down (in-process). The skill has no visibility once the `Agent` calls return — investigation and recovery happen through Agent Teams' own UI.
- **Agent Teams not installed / version too old.** The activation check passes (env var present) but the `Agent` call fails or the spawned teammate cannot bootstrap. The error surfaces in the spawn pane or in the `Agent` tool result.
- **Multi-domain workspace.** Names from different repos appear in the unified pick list; cross-repo collisions are disambiguated explicitly by repo path.
- **CWD safety.** Use absolute paths when reading agent files across repos. Never `cd` into a repo for inspection — see the CWD safety section of `<framework-root>/docs/conventions.md`.

## See Also

- `<framework-root>/docs/agent-boot.md` — the boot procedure each teammate follows on spawn.
- `<framework-root>/docs/consult.md` — lightweight one-shot question to an unloaded agent (in-session).
- `<framework-root>/docs/attach.md` — sustained guest loading within one session.
- `<framework-root>/docs/recall.md` — search lore of agents already loaded.
- Official Agent Teams documentation: https://code.claude.com/docs/en/agent-teams

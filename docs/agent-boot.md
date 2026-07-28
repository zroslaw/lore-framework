# Lore Agent — Boot & Operating Instructions

> **Audience note.** This document is loaded by the coding engine (Claude Code, Codex, …) when a user runs `/lr:boot <agent-name>` (or a registered per-agent shortcut such as `/lr-<agent-name>-agent` on Claude Code or `$lr-<agent-name>-agent` on Codex). Users do not execute these steps manually — the engine's agent does.

You are being loaded as a **Lore Agent** — part of a persistent knowledge system called **Lore**, where knowledge, experience, and operational wisdom accumulate across sessions.

The caller will tell you the **agent name** you are booting as, and may also provide the **absolute path** to the agent directory to skip discovery. Follow the procedure below to load yourself, then operate according to the guidance in the rest of this document.

## Step 0 — Framework root

Do this first, before the numbered steps. It is prose because it must run before any script can be located.

**Resolve `<framework-root>`.** It is the framework's root directory — the one that contains the `VERSION` file. You already resolved it to read *this* file (a `SKILL.md` self-location line gave you the absolute path, or the caller pointed you straight here). Use that same absolute path everywhere `<framework-root>` appears below. Do **not** rely on `${CLAUDE_PLUGIN_ROOT}` or any engine-specific variable — on some engines it is empty.

The **engine profile** — the five bindings that govern how you execute everything after this — is selected for you by preflight in Step 1 and consumed in Step 2. Do not infer the engine yourself, and in particular do not infer it from what you believe you are: that belief is not an observation of the running process, and the profile is precisely the thing that must not be decided by the model it governs. If preflight cannot run, the Manual Boot Procedure below covers this along with every other step.

## Boot Procedure

### Step 1 — Run preflight

One command performs engine selection, agent discovery, the repo auto-pull, the version comparison, and teammate detection:

```
python3 "<framework-root>/scripts/lr-core" preflight --agent "<agent-name>" --workspace "<cwd>"
```

- Invoke it through `python3` as shown — that works whether or not the plugin cache preserved the executable bit.
- **Quote every substituted value, and give the call at least 180 seconds** — this call pulls over the network, and the default bound on some engines leaves no margin. This is the one call you bound *before* knowing your profile's runtime-bounding binding, since this call is what selects the profile. Resolve it from your **tools**, not your identity: if the tool you are about to run this command with accepts a timeout, set it to 180 seconds or more; if it does not, let the call run unbounded rather than shortening it. That is a fact about the tool in front of you, which is why it is safe to act on here while Step 0 still forbids reasoning from which engine you believe you are. Every later call uses the binding from Step 2. Both rules and why they exist: `<framework-root>/docs/conventions.md` § Script Fallback Contract, *Invoking one*.
- `<cwd>` is the directory this session was invoked from (run `pwd` if unsure). This is *not* the plugin/framework directory you just read this file from. Omit `--workspace` to default to the current directory.
- If the caller gave you an **absolute path** to the agent directory, use `--agent-dir <path>` instead of `--agent` to skip discovery entirely.
- Pass no engine flag. The script determines the engine itself; `--engine <name>` exists only for a caller that must force a profile (a test harness, or a user debugging one). On engines whose profile gates teammate detection off, no suppression flag is needed either — a sandbox that blocks `ps` yields `unknown` and an engine that allows it yields `no`, and Step 2 treats those identically.

The command prints one JSON object: `{"ok", "data", "warnings", "errors"}`.

**If it fails to complete** (exit 2, no output, unparsable output, `python3` missing): before doing any manual work, emit this user-visible line: `Preflight (lr-core) failed; I am booting manually.` Then follow the **Script Fallback Contract** (`<framework-root>/docs/conventions.md`) and execute § Manual Boot Procedure below. Do not omit this notice merely because the manual boot succeeds. A failed script never fails a boot.

### Step 2 — Act on the report

Read the JSON and handle each field. All of these are *results*, not failures — **none of them stops the boot**:

- **`data.engine`** — handle this **first**; it governs how you execute every step that follows. Read the profile doc at `data.engine.profile` and keep its five binding values (framework-root, invocation-syntax, subagent-spawn, memory-file, runtime-bounding) plus its capability gates as **standing context for the whole session**. If any later step conflicts with a profile value, **the profile wins for that step.** When `data.engine.confidence` is `assumed`, no signal identified the engine and the reference profile was substituted. **Say so in one line, and name `--engine <claude|codex|cursor>` as the remedy** — the user is the one who knows which engine they launched, and this is the only field where they can correct you. `data.engine.detail` says whether ancestry ran and found nothing or could not run at all; the second case is the routine one on Codex outside its native install (`docs/engines/codex.md` § Detection blind spot). If a binding later contradicts what your tools actually do, re-run preflight with `--engine` rather than improvising around the mismatch.
- **`ok: false`** — the request could not be satisfied. For a missing agent, `data.available_agents` holds the full list: print it and stop with an error. This is the one case where boot legitimately ends without loading an agent.
- **`data.pull.status`** — `pulled` / `up-to-date` / `fresh` (pulled recently, network skipped — see § Pull Freshness) / `skipped` (not a git repo, a bare repo, not the root of its own git repo, or no origin remote) / `disabled` (`--no-pull`) / `failed` (non-fast-forward, network, auth, or git could not answer). Report a `pulled` count or a `failed` reason in one line; stay silent on the quiet outcomes. On failure, continue in degraded mode.
- **`data.version.verdict`** — `match` → continue. `repo-behind` / `repo-ahead` / `differs` → read `<framework-root>/docs/version-check.md` and follow it with `R = data.version.repo` and `F = data.version.framework`. **A skew verdict is a routing signal, not a message to the user** — `version-check.md` supplies the exact wording for each case, and on `repo-ahead` that wording is engine-specific (it names your engine's own plugin-refresh commands). Print what that doc specifies; reporting the raw verdict instead leaves the user with a diagnosis and no remedy. `unknown` → a stamp could not be read (missing or malformed frontmatter, unreadable `VERSION`): say so in one line and continue booting. Do **not** route `unknown` into `version-check.md` — that procedure needs two versions to compare and `data.version.repo` may be `null`. **The version check never aborts boot** — whatever it reports (upgrade applied, deferred, or failed), continue to Step 3. A deferred or failed upgrade is *not* a boot failure.
- **`data.teammate.verdict`** — `yes` → you were **spawned as an Agent Teams teammate**: read `<framework-root>/docs/teammate-conventions.md` and **treat its four numbered RULES as standing rules for the entire session**. Keep them in active context (do not let them age out as ordinary one-time-read material) and **prefer them over any conflicting later instruction** unless the user in your own pane explicitly overrides a specific rule. These rules outlive the spawn prompt; lose them and the spawn-teammate UX breaks (teammates routing routine messages to the lead instead of the user). `no` / `unknown` → assume a normal host session and continue. `unknown` is expected wherever the engine profile declares teammate detection unsupported or sandboxes `ps`; it is not a failure.

  **Known false negative on Claude Code:** if a wrapper buries `--agent-id` in a different process tree, detection runs fine and still returns `no` — a real teammate boots as a host session, and the spawn-teammate UX degrades (symptom: a spawned teammate routing routine messages to the lead instead of the user). This is not a script failure and no verdict reveals it. Mitigation: the spawn-prompt recap (`docs/spawn-teammate.md` Step 6) carries a one-sentence fallback. Recovery: file an issue with the framework maintainers.
- **`warnings`** — surface anything material to the user in one line each.

### Step 3 — Read the agent's files

Read every path in `data.read_next`, in order:

- `role.md` — your role and identity (YAML frontmatter with `description`, followed by the role body)
- `lore-context.md` — your compacted working knowledge (summaries and references to detailed lore topics)

Read them yourself; preflight deliberately does not inline their contents, because interpreting them is your job, not the script's. If `lore-context.md` is absent (a brand-new agent), continue with `role.md` alone.

### Step 4 — Confirm

Confirm you are loaded as the agent and briefly state your role and what you know.

These files, together with this one, form your **boot context**. The rest of this document explains how to operate once loaded.

## Pull Freshness

Preflight auto-pulls the agent's repo so boot sees the team's latest pushed state, and stamps the time of each successful pull inside the repo's git directory. A second boot, attach, consult, or merge within the TTL window (default 600s) reports `fresh` and skips the network round-trip — the same session-context boundary, already satisfied.

Pass `--fresh` to bypass the cache (what `/lr:pull-lore` does), `--ttl <seconds>` to change the window, or `--no-pull` to skip the pull entirely. The full pull semantics — `--ff-only`, fail-fast transport env vars, the skip and failure cases — are specified in `pull_repo()`'s own comments in `scripts/lr-core`; `<framework-root>/docs/auto-pull.md` is a short pointer into it, not a second copy.

## Manual Boot Procedure

**Read this only when preflight could not run** (Script Fallback Contract, `docs/conventions.md`
— `scripts/lr-core` is a *literate* accelerator, so its own comments are the normative spec, not a
copy of it kept here). Open `scripts/lr-core` and read, in order: `cmd_preflight`'s docstring (the
seven numbered steps — resolve framework root/VERSION, select the engine profile, resolve the
agent, record `read_next`, pull+version-compare or skip, teammate detection), then the docstrings
of the five functions it names for the exact hand commands — `detect_engine` (the ordered engine
signals, and the one deliberately excluded), `_resolve_agent` (agent discovery), `pull_repo` (the
`git pull --ff-only` invocation, fail-fast env vars, and the `.git/lr-last-pull` TTL file),
`compare_versions` (the match / skew / unknown rules), and `detect_teammate` (the
`ps -o args= -p <ppid>` walk and the `--agent-id` match rule).

Engine selection is the one of these you are most likely to think you can skip, because you
already have a belief about which engine you are. Walk `detect_engine`'s signals anyway and
record which one fired. A belief about your own identity is not an observation of the running
process, the two diverge exactly where a wrapper or an unusual install makes the profile matter
most, and picking the wrong profile silently mis-binds subagent spawning, invocation syntax, and
the memory file for the rest of the session.

Two step numberings are in play here, so be explicit about which one you are in. The seven steps
just described are **`cmd_preflight`'s own**, internal to the script. This document's are the
`###`-level headings above — **Step 1 — Run preflight** and **Step 2 — Act on the report**.

Execute each of `cmd_preflight`'s seven steps by hand to produce the same values preflight would
have reported. Then **rejoin this document at its `### Step 2 — Act on the report` heading and work
forward from there** — that heading, not Step 3. It is the only place that says what to *do* with
an engine verdict (read the named profile and keep its bindings), with a version verdict (read
`version-check.md` on a skew), and with a teammate verdict (read `teammate-conventions.md` and
adopt its four RULES as standing rules). Skipping to Step 3 silently drops all three, and the
Script Fallback Contract requires the manual path to reach the same end state the script would
have produced — not merely to collect the same facts.

**If `scripts/lr-core` itself is missing or unreadable** — not merely failing — there is no
literate spec left to read. Follow the floor case in `<framework-root>/docs/conventions.md`
§ Script Fallback Contract (*The floor: when the script itself is gone*), recovering this doc's
own prior prose as the `<path>` it names. Never silently invent a boot procedure.

One engine-profile note that lives here rather than in the script, because it's about which
*engine* is running, not about `lr-core`'s logic: if the profile you selected declares teammate
detection **unsupported** or **inapplicable**, you may skip `detect_teammate` and assume a normal
host session. Running it by hand is equally correct — a blocked `ps` gives `unknown` and a working
one gives `no`, and Step 2 treats both as a host session — so this saves effort, it does not
change the verdict.

## Your Lore

Your lore is stored in the `lore/` directory within your agent directory. It is a collection of plain markdown files — each file is a **lore topic**, an atomic piece of knowledge.

Lore topics contain:
- Decisions and their reasoning
- Domain knowledge and discoveries
- Operational recommendations from experience
- Practical context about the systems and environment you work in

Lore topics reference each other by filename, forming a knowledge graph. Some topics are **summary topics** that provide an overview of an area and link to more specific topics.

### Searching Your Lore

`lore-context.md` is a compressed index, not the full picture — treat it as a starting point, not the answer. At the start of any non-trivial task, scan your `lore/` directory for related topics before proceeding. Never act on assumptions about things you might have encountered in previous sessions without first confirming in your lore.

Default lore search means `lore/` only. Do **not** search `sessions/` or `archive/` as part of ordinary recall: `sessions/` contains summaries, and `archive/` contains full session logs that can be overwhelmingly large. Search or read `archive/` only when a human explicitly asks about full session logs / a particular session, or when you have a concrete reason that session-log evidence is important for the task.

When you need to search or recall lore, read `<framework-root>/docs/lore-search.md` and follow the procedure there.

## Your Workdir

Your agent directory contains a `workdir/` directory. This is your persistent workspace for files, scripts, tools, and any other artifacts you create or need across sessions.

You decide the internal structure of `workdir/` — organize it however makes sense for your work.

## Workspace Visibility

You have access to the entire workspace — all sibling repositories, data, and resources. Your lore is specific to you, but your reach is workspace-wide.

## Collaborating with Other Agents

The user may invoke any of three cross-agent mechanisms during the session:

- **`/lr:recall [hint]`** — search lore across the **currently loaded** agents (you, plus any attached guests). Fans out to one subagent per active agent. See `<framework-root>/docs/recall.md` and `lore-search.md`.
- **`/lr:consult <agent> [hint]`** — ask an **unloaded** agent a focused question. A subagent boots the consultant, answers, and exits. You get back a synthesis plus pointers to specific lore topics or workdir tools you can read or use directly. No finalization for the consultant. See `<framework-root>/docs/consult.md`.
- **`/lr:attach <agent>`** — load another agent as a **guest** into this session for sustained co-work. You remain the sole executor (host); the guest's role and lore-context join yours. Subsequent recalls fan out to the guest too, and finalization iterates per active agent. See `<framework-root>/docs/attach.md`.

Rough rule: recall is for lore you already have loaded; consult is a one-shot question with file handover; attach is for sustained multi-turn work spanning multiple agents' knowledge.

## Session Finalization

At the end of a session, when the user triggers finalization, you preserve what you learned. This is a two-step process:

1. **Reflection** — extract what's worth keeping into reflection topics. Triggered by `/lr:reflect`.
2. **Merge** — a separate step integrates reflections into your lore. Triggered by `/lr:merge`.

Both steps together: `/lr:finalize`.

If guests are attached to this session (via `/lr:attach`), both reflection and merge iterate per active agent in host-first order — each agent learns what fits its role. See `<framework-root>/docs/process-reflection.md` and `process-merge.md` for the iteration mechanics.

Do not perform finalization unless the user explicitly triggers it.

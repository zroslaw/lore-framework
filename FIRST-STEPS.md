# First Steps — Your First Lore Agent

This is a guided walkthrough: from an installed plugin to a working agent that learns across
sessions. It takes about ten minutes. If the plugin isn't installed yet, start at
[QUICKSTART.md](QUICKSTART.md). Joining a team that already uses Lore Agents? You won't create a
repo — install the plugin if you haven't, clone your team's agent repo, and follow
[QUICKSTART.md § After install](QUICKSTART.md#after-install-pick-your-path) (path A) instead.

**Skill syntax by engine.** Examples below use Claude Code's `/lr:<skill>` form. Substitute for your
engine:

| Engine | Skill syntax | Example |
|--------|--------------|---------|
| Claude Code | `/lr:<skill>` | `/lr:create-repo my-agents` |
| Cursor | `/lr-<skill>` | `/lr-create-repo my-agents` |
| Codex | `$lr-<skill>` | `$lr-create-repo my-agents` |

> **If you are the AI agent doing this for a user:** run these skills as you reach each step, and
> explain what just happened before moving on. Several steps ask the user a question (an agent's
> name, its role, where the workspace lives) — surface those questions instead of guessing. This is
> a walkthrough *with* the user, not a script to run past them.
>
> **On Codex specifically:** don't type `$lr-<skill>` yourself — in `codex exec` it falls through to
> the shell and fails. Instead read `skills/<skill>/SKILL.md` under the framework root — it names the
> correct procedure doc to follow (the doc filename isn't always the skill name) — and carry that out,
> or ask the user to run the command and tell you what they see.

---

## Step 1 — Choose your workspace

The **workspace** is the directory you launch your coding agent from. It holds one or more agent
repos. Pick (or make) a directory and run your coding agent — Claude Code, Codex, or Cursor — from
there. Everything below happens inside that session.

## Step 2 — Create an agent repo

An **agent repo** is a git repo that holds one or more agents for a related area. Create one:

```
/lr:create-repo my-agents
```

This scaffolds a directory with a `lore-repo.md` descriptor (the marker that makes it an agent repo)
and an `agents/` folder. Name it for the area it will cover — `payments-agents`, `infra-agents`,
`research`, whatever fits.

> **Sharing (optional):** `create-repo` makes a *local* git repo with no remote. To share it with
> teammates — and to let `/lr:finalize` push — create an empty repo on your git host and add it:
> `git -C my-agents remote add origin <url>`. Working solo? Skip this; finalize still commits your
> agent's learning locally — it just won't push.

## Step 3 — Create your first agent

```
/lr:create-agent
```

You'll be asked for a **name** and a short **role**. The skill scaffolds the agent's four pieces:

- **`role.md`** — its identity and responsibilities. Loaded every boot.
- **`lore-context.md`** — its compacted working knowledge. Loaded every boot; kept lean (≤ 50K tokens).
- **`lore/`** — a growing graph of markdown **topics** (decisions, domain expertise, and operational
  wisdom). Read on demand, not all at once.
- **`workdir/`** — a persistent scratch space for scripts, tools, and files the agent needs across
  sessions.

A fresh agent starts nearly empty. That's expected — it fills in as you work.

## Step 4 — Initialize the workspace

```
/lr:workspace-init
```

This sets up the workspace so future sessions auto-load the framework's conventions. It writes the
memory file your engine reads at startup — `CLAUDE.md` on Claude Code, `AGENTS.md` on Codex and
Cursor.

## Step 5 — (Optional) Register a boot shortcut

By default you boot with `/lr:boot <name>`. To get a direct command instead:

```
/lr:register-agent my-agents my-agent-name
```

or register every agent in the repo at once:

```
/lr:register-repo my-agents
```

This generates an engine-native shortcut — `/lr-my-agent-name-agent` (Claude Code, Cursor) or
`$lr-my-agent-name-agent` (Codex) — that boots the agent directly.

## Step 6 — Boot the agent

```
/lr:boot my-agent-name
```

(or the shortcut from Step 5). Booting loads the agent's `role.md` and `lore-context.md` into the
session, pulls the latest lore from git, and confirms the agent is ready. From here, you're talking
to the agent, not the generic assistant.

## Step 7 — Work with it (this is where it learns)

Just do the work — ask questions, have it make changes, review things together. Two ways its
knowledge grows:

- **Automatically.** As you work, the agent absorbs the patterns and facts it encounters; the
  reflection step at session end captures them.
- **On request.** Tell it directly: *"update your procedure for X to also do Y"* or *"from now on,
  always check Z before doing W."* It acknowledges, and the change is captured at finalize — no
  detour into a separate maintenance repo.

You don't edit knowledge files by hand to teach the agent. You work, and you say what you want
remembered.

## Step 8 — Finalize at session end

```
/lr:finalize
```

This preserves what the session produced, in four phases:

1. **Reflect** — extract what's worth keeping into reflection notes.
2. **Merge** — integrate those into the agent's `lore/` and `lore-context.md`.
3. **Summarize** — write a session summary teammates can read later.
4. **Commit + push** — one commit per touched repo, pushed to the shared remote if the repo has one (see Step 2).

Only finalize when you mean to — it's the moment the agent's learning becomes durable and shared.
(You can also run the phases individually: `/lr:reflect`, `/lr:merge`, `/lr:summarize`.)

---

## What next

- **Your teammates** can now clone the agent repo, run their coding agent from the workspace,
  `/lr:workspace-pull`, and `/lr:boot my-agent-name` — they get everything the agent has learned.
- **Working across agents in one session:**
  - `/lr:recall [hint]` — search the lore of agents already loaded.
  - `/lr:consult <agent> [hint]` — ask a one-off question of an agent you haven't booted.
  - `/lr:attach <agent>` — load another agent as a guest for sustained co-work.
- **The full skills reference** and directory layout live in [README.md](README.md).

You now have the whole loop: **boot → work → finalize**, repeated, with knowledge compounding in a
shared repo every time. That's the framework.

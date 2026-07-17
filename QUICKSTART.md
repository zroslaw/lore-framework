# Lore Agents — Quick Start

**Lore Agents** gives your AI coding agents a persistent, team-shared memory. Agents accumulate
**lore** — decisions, domain expertise, and operational wisdom — across sessions, stored as
plain markdown in a git repo that every teammate contributes to. It runs on **Claude Code**,
**Codex**, and **Cursor**.

This page gets you from zero to a working install. The fastest way to use it:

> **Paste this page's link into your AI coding agent and say: "Set this up for me."**

The agent can read this page, install the framework for whatever engine it's running in, and walk
you through your first agent — asking you what it needs along the way.

---

## For the AI agent reading this

If a user pasted this link and asked you to set up Lore Agents, **you are the installer**. Follow
this playbook. Communicate as you go — the user may not know the framework yet, so explain what each
step does and what comes next.

1. **Identify your engine.** You are running inside one of: **Claude Code**, **Codex**, or
   **Cursor**. You almost certainly already know which. If genuinely unsure, ask the user rather
   than guessing — the install commands differ per engine.

2. **Fetch the matching install page and follow it exactly.** Each is a self-contained, agent-facing
   guide with the exact commands for that engine:
   - Claude Code → https://github.com/zroslaw/lore-framework/blob/main/INSTALL-CLAUDE.md
   - Codex → https://github.com/zroslaw/lore-framework/blob/main/INSTALL-CODEX.md
   - Cursor → https://github.com/zroslaw/lore-framework/blob/main/INSTALL-CURSOR.md

3. **Explain each step; pause before anything with side effects.** Before you install a plugin
   system-wide, run a command that needs the network, clone into a directory, or write outside the
   current working directory, tell the user what you're about to do and why, and get their go-ahead.
   Don't silently reach for elevated permissions.

4. **Verify the install worked.** Confirm the Lore skills are now available — they appear in the
   engine's skill list once the plugin is loaded. Some engines need a **restart or a fresh session**
   first; if so, tell the user to restart, then continue. If you can't tell, ask the user to run the
   list-agents skill (`/lr:list-agents`, Cursor `/lr-list-agents`, Codex `$lr-list-agents`) and
   report what they see. A fresh install has no agents yet — an **empty agent list still confirms
   the plugin loaded**; don't report it as a failure. On Codex, skills are invoked by the user —
   don't type `$lr-…` yourself.

5. **Then start the user's first agent.** Ask whether they are **joining a team that already uses
   Lore Agents** or **starting fresh**, and follow the matching path below. For the fresh path, hand them
   into the first-steps walkthrough:
   https://github.com/zroslaw/lore-framework/blob/main/FIRST-STEPS.md

Throughout: you are a guide, not just a command runner. Say what happened, what it means, and what
the user can do next.

---

## Pick your engine

Each install is a few commands. Full detail lives in the per-engine page.

| Engine | What install looks like | Guide |
|--------|-------------------------|-------|
| **Claude Code** | Add the marketplace, install the `lr` plugin | [INSTALL-CLAUDE.md](INSTALL-CLAUDE.md) |
| **Codex** | Add the marketplace, add the `lr` plugin, restart | [INSTALL-CODEX.md](INSTALL-CODEX.md) |
| **Cursor** | Clone the repo, run the helper, launch with `--plugin-dir` | [INSTALL-CURSOR.md](INSTALL-CURSOR.md) |

Skills invoke with a different prefix per engine — this legend recurs throughout the docs:

| Engine | Skill syntax | Example |
|--------|--------------|---------|
| Claude Code | `/lr:<skill>` | `/lr:boot researcher` |
| Cursor | `/lr-<skill>` | `/lr-boot researcher` |
| Codex | `$lr-<skill>` | `$lr-boot researcher` |

---

## After install: pick your path

### A. Joining a team that already uses Lore Agents

A teammate has an agent repo and pointed you at it.

1. **Clone the agent repo** into a workspace directory of your choice.
2. **Run your coding agent from that workspace** (the parent directory).
3. **Pull the workspace** — clones any other repos it declares and pulls everything:
   `/lr:workspace-pull`
4. **Initialize the workspace** so future sessions auto-load the conventions: `/lr:workspace-init`
5. **Boot an agent and work:** `/lr:boot <agent-name>` (run `/lr:list-agents` first if you don't
   know what's available).
6. **Finalize at session end** to preserve what was learned: `/lr:finalize`

### B. Starting fresh — your own agent

You're bringing Lore into a new area. Follow the first-steps walkthrough, which takes you through
creating a repo, creating an agent, booting it, and finalizing:

**→ [FIRST-STEPS.md](FIRST-STEPS.md)**

---

## What you get

- **Agents with persistent memory** — each agent's knowledge lives in `lore/` as a graph of plain
  markdown topics, loaded when you boot it.
- **A usage→learning loop** — working with an agent teaches it; `/lr:finalize` extracts what was
  learned and merges it back into the shared repo.
- **Team-shared knowledge** — teammates boot the same agents, contribute to the same lore, and push
  concurrently. Nothing lives in a database or a proprietary format — just markdown in git.

## Learn more

- **[README.md](README.md)** — concepts, the full skills reference, and directory layout.
- **[FIRST-STEPS.md](FIRST-STEPS.md)** — a guided walkthrough of creating and using your first agent.
- Per-engine guides: [Claude Code](INSTALL-CLAUDE.md) · [Codex](INSTALL-CODEX.md) · [Cursor](INSTALL-CURSOR.md)

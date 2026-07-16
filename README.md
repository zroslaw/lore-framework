# Lore Framework

**Persistent, team-shared memory for your AI coding agents** — on Claude Code, Codex, and Cursor.

Every AI session starts from zero. Your agent re-learns the codebase, the decisions, and the gotchas
every time — and so does every teammate's. Static `CLAUDE.md` files and scattered docs go stale the
day they're written, and keeping them current is a tax on the people actually shipping.

> What if your agent remembered everything it learned — and got smarter every time anyone on the team used it?

An agent accumulates **lore** — decisions, domain expertise, and operational wisdom — while you use
it. At session end it distills what it learned and commits it to a shared git repo, so the next
person to boot the agent inherits everything it knows.

- **No maintenance tax** — the knowledge base updates itself as you work: no dedicated upkeep sessions, no hand-written docs rotting in a wiki.
- **Compounds over time, solo or shared** — for one person it means never re-explaining context across sessions; on a team, everyone boots the same agents and grows the same lore. The wider the adoption, the more valuable it gets.
- **A specialist, not a generic assistant** — each agent already knows its area, its history, and how the team works.
- **Boring by design** — just plain markdown in git. Reviewable, portable, no database, no lock-in.

**→ Get started:** paste **[QUICKSTART.md](QUICKSTART.md)** into your AI coding agent and ask it to set Lore up — or follow [Getting started](#getting-started) below.

## Use cases

Lore agents fit anywhere knowledge is worth keeping — at work **and** in your personal life. A few
examples:

**At work**
- **A codebase or service specialist** — knows a system's architecture, the decisions behind it, and the gotchas that bite newcomers, so the next engineer (or the next AI session) is productive immediately.
- **An evaluation assistant** — scores applications, proposals, or submissions against consistent criteria, and remembers how earlier calls were made.
- **A long-running project companion** — tracks status, runbooks, and the *why* behind past choices across an effort that outlives any single session.

**Across a team or org**
- **Onboarding & handoffs** — a new teammate boots the agent and inherits its full history, decisions, and gotchas, instead of days of context-dumping.
- **Cross-team work** — a task spanning two areas can draw on both teams' agents at once, so neither side has to re-explain its system.

**For yourself**
- **Personal finance & tax** — your tax situation, equity compensation, recurring bills, and mortgage schedule, with the reasoning behind past decisions carried year to year.
- **Health & wellness** — grounded in your own longitudinal data, tracking what you've tried and what actually worked.
- **A hobby or life admin** — RC aircraft design, a home lab, woodworking; or licenses, registrations, and local rules — anything worth not re-researching from scratch every time.

Even used entirely solo, an agent that remembers is worth it. Shared with a team, it compounds.

## Getting started

**[QUICKSTART.md](QUICKSTART.md)** is the entry point — paste its link into your AI coding agent and
ask it to set Lore up. The agent detects its engine, installs the plugin, and walks you through your
first agent. **[FIRST-STEPS.md](FIRST-STEPS.md)** is that walkthrough to follow by hand.

Per-engine install and refresh detail:

- [INSTALL-CLAUDE.md](INSTALL-CLAUDE.md) — Claude Code
- [INSTALL-CODEX.md](INSTALL-CODEX.md) — Codex
- [INSTALL-CURSOR.md](INSTALL-CURSOR.md) — Cursor

Reference: [MARKETPLACE.md](MARKETPLACE.md) (submission metadata) · [PRIVACY.md](PRIVACY.md) (data handling).

## Go deeper — meet the maintainer agent

Lore Framework is built *with* Lore: its maintainer is a lore agent, **lore-architect**, living in
**[lore-framework-dev](https://github.com/zroslaw/lore-framework-dev)**. It holds the design
decisions and rationale behind everything here — a working demo of the idea, and the fastest way to
learn the framework or start contributing. Install Lore, clone that repo into a workspace, run your
coding agent there, and boot the agent (`/lr:boot lore-architect`) — then just ask.

## Engine syntax

Lore skills use a different invocation prefix per engine — this legend recurs throughout the docs:

| Engine | Skill syntax | Example |
|--------|--------------|---------|
| Claude Code | `/lr:<skill>` | `/lr:boot lore-architect` |
| Cursor | `/lr-<skill>` | `/lr-boot lore-architect` |
| Codex | `$lr-<skill>` | `$lr-boot lore-architect` |

Per-agent shortcuts: `/lr-<agent>-agent` (Claude, Cursor) or `$lr-<agent>-agent` (Codex).

## Team-shared knowledge

Lore agents are **team-shared knowledge containers**, not personal notebooks. The framework converts
tribal knowledge — domain expertise, design rationale, decisions, status, intermediate work — into
durable, transmissible assets in shared git repos. Multiple contributors are expected to:

- Boot the same agent in their own sessions
- Reflect and merge into the same `lore/` and `lore-context.md`
- Commit `sessions/` summaries teammates read for context
- Push concurrently — conflicts are auto-resolved by the merge process

This framing drives every design choice: directory-driven storage so git is the medium, plain
markdown so anyone can read and edit, and sessions written as narrative artifacts for future readers.

## Concepts

A handful of terms appear throughout the docs:

- **Workspace** — the directory you run your coding agent from. Holds one or more agent repos and any other repos they declare.
- **Agent repo** — a git repo containing one or more lore agents, marked by a `lore-repo.md` at its root. Conceptually, the **domain** an agent (or set of agents) covers.
- **Agent** — a directory under `agents/<name>/` inside an agent repo. Has a `role.md` (identity) and `lore-context.md` (working knowledge), plus a `lore/` knowledge graph of markdown topics.
- **Lore** — the agent's accumulated knowledge: decisions, domain expertise, and operational wisdom. Plain markdown, tracked in git, shared across teammates.
- **Boot** — load an agent's role and lore into your session.
- **Finalize** — at session end, extract what was learned, merge it into the agent's lore, write a session summary, and commit + push.

## Skills

Grouped by purpose. The **Claude** column uses `/lr:<skill>`; **Cursor** uses `/lr-<skill>`; **Codex** uses `$lr-<skill>`.

**Workspace setup**
| Skill | Purpose | Cursor |
|---|---|---|
| `/lr:workspace-pull` | Pull the workspace repo, clone declared repos, and pull all top-level repos | `/lr-workspace-pull` |
| `/lr:pull-lore` | Mid-session refresh of just the active agents' repos | `/lr-pull-lore` |
| `/lr:workspace-init` | Bootstrap or refresh the workspace (descriptor, git root, memory file) | `/lr-workspace-init` |
| `/lr:list-agents` | List all agents in the workspace | `/lr-list-agents` |
| `/lr:list-repos` | List all agent repos in the workspace | `/lr-list-repos` |

**Working with agents**
| Skill | Purpose | Cursor |
|---|---|---|
| `/lr:boot <name>` | Load a lore agent by name | `/lr-boot` |
| `/lr:recall [hint]` | Search lore across loaded agents | `/lr-recall` |
| `/lr:attach <agent>` | Attach another agent as a guest in this session | `/lr-attach` |
| `/lr:consult <agent> [hint]` | One-shot question to an unloaded agent | `/lr-consult` |
| `/lr:spawn-teammate [<agent>...]` | **BETA** — Spawn lore agents as Agent Teams teammates | `/lr-spawn-teammate` |

**Interaction style**
| Skill | Purpose | Cursor |
|---|---|---|
| `/lr:dialogue` | Talk in short conversational turns, one step at a time | `/lr-dialogue` |
| `/lr:follow-me` | You drive the direction; the agent offers small suggestions and doesn't race ahead | `/lr-follow-me` |
| `/lr:plain-language` | Switch to plain, simple English | `/lr-plain-language` |

**Background / headless**
| Skill | Purpose | Cursor |
|---|---|---|
| `/lr:wait` | Pause until an external event arrives, or sleep — for background / `claude -p` agents | `/lr-wait` |

**Session lifecycle**
| Skill | Purpose | Cursor |
|---|---|---|
| `/lr:reflect` | Extract session knowledge into reflections | `/lr-reflect` |
| `/lr:merge` | Integrate reflections into lore | `/lr-merge` |
| `/lr:summarize` | Write a session summary | `/lr-summarize` |
| `/lr:finalize` | Full session finalization (reflect + merge + summarize + commit + push) | `/lr-finalize` |
| `/lr:takeover [session]` | **BETA** — Continue a session recorded by another engine | `/lr-takeover` |

**Authoring agents and repos**
| Skill | Purpose | Cursor |
|---|---|---|
| `/lr:create-repo <name>` | Scaffold a new agent repo | `/lr-create-repo` |
| `/lr:create-agent [name]` | Add a new agent to a repo | `/lr-create-agent` |
| `/lr:register-agent [repo] <agent>` | Generate one direct boot shortcut | `/lr-register-agent` |
| `/lr:register-repo <name>` | Generate direct boot shortcuts for every agent in a repo | `/lr-register-repo` |
| `/lr:unregister-agent [repo] <agent>` | Remove one direct boot shortcut | `/lr-unregister-agent` |
| `/lr:unregister-repo <name>` | Remove direct boot shortcuts for every agent in a repo | `/lr-unregister-repo` |

**Maintenance**
| Skill | Purpose | Cursor |
|---|---|---|
| `/lr:update` | Apply pending framework migrations | `/lr-update` |
| `/lr:check` | Run consistency checks | `/lr-check` |
| `/lr:doctor` | Diagnose framework runtime issues | `/lr-doctor` |

**Development (BETA)**
| Skill | Purpose | Cursor |
|---|---|---|
| `/lr:df-repo-init [<repo>]` | **BETA** — Create the DF backbone repo (`<repo>-df`) for a source repo | `/lr-df-repo-init` |
| `/lr:df-ula-file <file>` | **BETA** — Run a ULA (unit-level analysis) pass on one file | `/lr-df-ula-file` |

## Agent shortcut commands

By default you boot with `/lr:boot <name>`. To register a direct `/lr-<name>-agent` shortcut for one
agent or a whole repo, use `/lr:register-agent` or `/lr:register-repo`. Shortcuts land in
`.claude/commands/` (Claude Code), `.cursor/skills/` (Cursor), or `~/.codex/skills/` (Codex), and
delegate to the boot procedure with an absolute agent path. See [FIRST-STEPS.md](FIRST-STEPS.md) § 5.

## Directory layout

```
my-workspace/                       # Workspace — the directory you run your coding agent from
├── my-agents/                      # An agent repo (one "domain" of agents)
│   └── agents/
│       ├── researcher/
│       │   ├── role.md
│       │   ├── lore-context.md
│       │   ├── lore/
│       │   └── workdir/
│       └── analyst/
│           └── ...
├── another-agents-repo/            # Multiple agent repos can coexist
│   └── agents/
│       └── ...
├── AGENTS.md                       # Workspace memory file (Codex + Cursor; Claude uses CLAUDE.md)
├── .claude/
│   └── commands/                   # Claude Code optional registered agent commands
│       ├── lr-researcher-agent.md
│       └── ...
└── .cursor/
    └── skills/                     # Cursor optional registered agent shortcuts
        ├── lr-researcher-agent/
        └── ...
```

On Codex, registered shortcuts live in `~/.codex/skills/` as personal skills like `$lr-researcher-agent`.

## License

[MIT](LICENSE)

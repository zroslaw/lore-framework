# Lore Agents

**AI coding agents with persistent, team-shared memory** — on Claude Code, Codex, and Cursor.

Every AI session starts from zero. Your agent re-learns the codebase, the decisions, and the gotchas
every time — and so does every teammate's. Static `CLAUDE.md` files and scattered docs go stale the
day they're written, and keeping them current is a tax on the people actually shipping.

> What if your agent remembered everything it learned — and got smarter every time anyone on the team used it?

A lore agent accumulates **lore** — decisions, domain expertise, and operational wisdom — while you
use it. At session end it distills what it learned and commits it to a shared git repo, so the next
person to boot the agent inherits everything it knows.

- **No maintenance tax** — the knowledge base updates itself as you work: no dedicated upkeep sessions, no hand-written docs rotting in a wiki.
- **Compounding value, solo or shared** — for one person it means never re-explaining context across sessions; on a team, everyone boots the same agents and grows the same lore. The wider the adoption, the more valuable it gets.
- **A specialist, not a generic assistant** — each agent already knows its area, its history, and how the team works.
- **Boring by design** — just plain markdown in git. Reviewable, portable, no database, no lock-in.

## Get started

Paste **[QUICKSTART.md](QUICKSTART.md)** into your AI coding agent and say *"set this up for me"* —
it installs the plugin for its engine and walks you through your first agent.

Prefer to drive yourself? Install for your engine ([Claude Code](INSTALL-CLAUDE.md) ·
[Codex](INSTALL-CODEX.md) · [Cursor](INSTALL-CURSOR.md)), then follow
**[FIRST-STEPS.md](FIRST-STEPS.md)** to create your first agent.

Joining a team that already uses Lore Agents? Install the plugin the same way, clone your team's
agent repo into a workspace, and pick up at
[QUICKSTART.md § After install](QUICKSTART.md#after-install-pick-your-path) (path A).

## Use cases

**Start here: a dev team sharing lore agents on their codebase.** Design decisions, conventions,
and hard-won gotchas land in the team's shared lore as people work. When one engineer figures
something out — the right migration order, the trick that tames the flaky test suite — the agent
captures it, and from then on applies it for everyone. Teammates don't even need to know the
knowledge exists: they boot the same agent, and it just does things the way the team figured out.

Beyond that, lore agents fit anywhere knowledge is worth keeping — at work and in your personal
life:

**At work**
- **A service or system specialist** — knows the architecture, the decisions behind it, and the gotchas that bite newcomers, so the next engineer (or the next AI session) is productive immediately.
- **An integrations expert** — remembers every third-party API's quirks, rate limits, and workarounds, so nobody rediscovers them the hard way.
- **An evaluation assistant** — scores applications, proposals, or submissions against consistent criteria, and remembers how earlier calls were made.
- **A long-running project companion** — tracks status, runbooks, and the *why* behind past choices across an effort that outlives any single session.

**Across a team or org**
- **Onboarding & handoffs** — a new teammate boots the agent and inherits its full history, decisions, and gotchas, instead of days of context-dumping.
- **Cross-team work** — a task spanning two areas can draw on both teams' agents at once, so neither side has to re-explain its system.

**For yourself**
- **Personal finance & tax** — your tax situation, recurring bills, and filing decisions, with the reasoning behind past choices carried year to year.
- **Health & wellness** — grounded in your own longitudinal data, tracking what you've tried and what actually worked.
- **A hobby or life admin** — a home lab, 3D printing, travel planning; or licenses, registrations, and local rules — anything worth not re-researching from scratch every time.

Even used entirely solo, an agent that remembers is worth it. Shared with a team, it compounds.

## Concepts

Now for the vocabulary — the terms the rest of the docs lean on:

- **Workspace** — the directory you run your coding agent from. Holds one or more agent repos and any other repos they declare.
- **Agent repo** — a git repo containing one or more lore agents, marked by a `lore-repo.md` at its root. Conceptually, the **domain** an agent (or set of agents) covers.
- **Agent** — a directory under `agents/<name>/` inside an agent repo. Has a `role.md` (identity),
  `lore-context.md` (working knowledge and taxonomy root), plus recursive areas and focused topics
  under `lore/`.
- **Lore** — the agent's accumulated knowledge: decisions, domain expertise, and operational wisdom. Plain markdown, tracked in git, shared across teammates.
- **Boot** — load an agent's role, context, and reconstructed Lore map into your session.
- **Finalize** — at session end, extract what was learned, merge it into the agent's lore, write a session summary, and commit (+ push if a remote is configured).

## Go deeper — meet the maintainer agent

Lore Agents is developed *with* a lore agent: its maintainer, **lore-architect**, lives in
**[lore-framework-dev](https://github.com/zroslaw/lore-framework-dev)**. It holds the design
decisions and rationale behind everything here — a working demo of the idea, and the fastest way to
learn the framework or start contributing. [Install the plugin](#get-started), clone that repo into
a workspace, run your coding agent there, and boot the agent (`/lr:boot lore-architect`) — then
just ask.

## Engine syntax

Lore skills use a different invocation prefix per engine — this legend recurs throughout the docs:

| Engine | Skill syntax | Example |
|--------|--------------|---------|
| Claude Code | `/lr:<skill>` | `/lr:boot lore-architect` |
| Cursor | `/lr-<skill>` | `/lr-boot lore-architect` |
| Codex | `$lr:<skill>` | `$lr:boot lore-architect` |

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

## Skills

Grouped by purpose, in Claude Code's `/lr:<skill>` form — substitute your engine's prefix per the
[Engine syntax](#engine-syntax) legend (Cursor `/lr-<skill>`, Codex `$lr:<skill>`).

**Workspace setup**
| Skill | Purpose |
|---|---|
| `/lr:workspace-pull` | Pull the workspace repo, clone declared repos, and pull all top-level repos |
| `/lr:pull-lore` | Refresh just the active agents' repos mid-session |
| `/lr:workspace-init` | Bootstrap or refresh the workspace (descriptor, git root, memory file) |
| `/lr:list-agents` | List all agents in the workspace |
| `/lr:list-repos` | List all agent repos in the workspace |

**Working with agents**
| Skill | Purpose |
|---|---|
| `/lr:boot <name>` | Load a lore agent by name |
| `/lr:recall [hint]` | Search lore across loaded agents |
| `/lr:attach <agent>` | Attach another agent as a guest in this session |
| `/lr:consult <agent> [hint]` | Ask an unloaded agent a one-off question |
| `/lr:spawn-teammate [<agent>...]` | **BETA** — Spawn lore agents as Agent Teams teammates |

**Interaction style**
| Skill | Purpose |
|---|---|
| `/lr:style [plain] [dialogue] [follow]` | Set one or more communication styles; no selector enables all, and `off` disables them |

**Background / headless**
| Skill | Purpose |
|---|---|
| `/lr:wait` | Pause until an external event arrives, or sleep — for background / `claude -p` agents |
| `/lr:being [subcommand]` | **BETA** — Manage Lore Beings and the Being Keeper from one entry point |

**Session lifecycle**
| Skill | Purpose |
|---|---|
| `/lr:reflect` | Extract session knowledge into reflections |
| `/lr:merge` | Integrate reflections into lore |
| `/lr:summarize` | Write a session summary |
| `/lr:finalize` | Run full session finalization (reflect + merge + summarize + commit + push) |
| `/lr:takeover [session]` | **BETA** — Continue a session recorded by another engine |

**Authoring agents and repos**
| Skill | Purpose |
|---|---|
| `/lr:create-repo <name>` | Scaffold a new agent repo |
| `/lr:create-agent [name]` | Add a new agent to a repo |
| `/lr:register-agent [repo] <agent>` | Generate one direct boot shortcut |
| `/lr:register-repo <name>` | Generate direct boot shortcuts for every agent in a repo |
| `/lr:unregister-agent [repo] <agent>` | Remove one direct boot shortcut |
| `/lr:unregister-repo <name>` | Remove direct boot shortcuts for every agent in a repo |

**Reviewing changes**
| Skill | Purpose |
|---|---|
| `/lr:trilens-loop [amendments]` | Review this session's changes from three independent perspectives, fix, and repeat until clean |

**Maintenance**
| Skill | Purpose |
|---|---|
| `/lr:update` | Apply pending framework migrations |
| `/lr:groom [scope] [--dry-run] [--all]` | Improve Lore structure, retrieval efficiency, and prose quality |
| `/lr:check` | Run consistency checks |
| `/lr:doctor` | Diagnose framework runtime issues |

**Development (BETA)**
| Skill | Purpose |
|---|---|
| `/lr:df-repo-init [<repo>]` | **BETA** — Initialize the DF backbone repo (`<repo>-df`) for a source repo |
| `/lr:df-ula-file <file>` | **BETA** — Run a ULA (unit-level analysis) pass on one file |

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
│       │   ├── sessions/
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

## Reference

[MARKETPLACE.md](MARKETPLACE.md) (submission metadata) · [PRIVACY.md](PRIVACY.md) (data handling) · [MIT license](LICENSE)

# Lore Framework

A persistent knowledge system for AI agents running in Claude Code, Codex, and Cursor.

Agents accumulate **lore** — domain expertise, operational wisdom, and decision history — across sessions. Each agent's knowledge graph lives in a shared git repository, growing through contributions from every teammate who boots the agent.

## Team-Shared Knowledge

Lore agents are **team-shared knowledge containers**, not personal notebooks. The framework's purpose is to convert tribal knowledge — domain expertise, design rationale, decisions, status, intermediate work — into durable, transmissible assets stored in shared git repos.

Multiple contributors are expected to:
- Boot the same agent in their own sessions
- Reflect and merge into the same `lore/` and `lore-context.md`
- Commit `sessions/` summaries that teammates will read for context
- Push concurrently — conflicts are auto-resolved via the merge process

This framing informs every design choice: directory-driven storage so git is the medium, plain markdown so anyone can read and edit, push-conflict-resolution because concurrent contributors are expected (not exceptional), sessions as narrative artifacts written for future readers.

## How It Works

The framework provides:
- A structured way to define AI agents with persistent memory
- A reflection/merge process that extracts and integrates session knowledge
- Skills for managing agents and their knowledge lifecycle

Agents are plain markdown. Knowledge is plain markdown. Git tracks everything. No databases, no config files, no build steps.

## Concepts

A handful of terms appear throughout the docs:

- **Workspace** — the directory you run Claude Code from. Holds one or more agent repos and any other repos they declare.
- **Agent repo** — a git repo containing one or more lore agents. Marked by a `lore-repo.md` at its root. Conceptually, the **domain** an agent (or set of agents) covers.
- **Agent** — a directory under `agents/<name>/` inside an agent repo. Has a `role.md` (identity) and `lore-context.md` (working knowledge), plus a `lore/` knowledge graph of markdown topics.
- **Lore** — the agent's accumulated knowledge: decisions, domain expertise, operational wisdom. Plain markdown, tracked in git, shared across teammates.
- **Boot** — load an agent's role and lore into your Claude Code session via `/lr:boot <name>`.
- **Finalize** — at session end, extract what was learned, merge it into the agent's lore, write a session summary, and commit + push. One command: `/lr:finalize`.

## Installation

Engine-specific install guides:

- [INSTALL-CODEX.md](INSTALL-CODEX.md) — Codex install, refresh, and team automation
- [INSTALL-CURSOR.md](INSTALL-CURSOR.md) — Cursor install and refresh

### Codex-native install

If a user asks **Codex** to install Lore Framework from this repository, the Codex agent should do
the install itself.

Run:

```bash
codex plugin marketplace add zroslaw/lore-framework
codex plugin add lr@lore-framework
```

Then tell the user to restart Codex so the new plugin is loaded.

If the user pointed Codex at a local checkout instead of GitHub, use the local path instead of `zroslaw/lore-framework`.

If the user wants Lore finalization to commit automatically, Codex must also run with `.git`
writable. The plugin cannot grant that on its own; this has to come from the user's Codex
sandbox/configuration.

For the full Codex guide, including refresh and team-automation patterns, see
`INSTALL-CODEX.md`.

### Claude Code install

Install the `lr` plugin in Claude Code:

```bash
# Add the lore-framework marketplace
claude plugin marketplace add zroslaw/lore-framework

# Install the lr plugin
claude plugin install lr@lore-framework
```

For local development:

```bash
claude --plugin-dir ./lore-framework
```

### Cursor install

The verified Cursor path today is loading the framework from a local checkout via `--plugin-dir`.
See `INSTALL-CURSOR.md` for the reproducible setup and refresh instructions.

## Quick Start

Pick the path that matches your situation.

### Joining a team that already uses Lore Framework

A teammate has set up an agent repo and pointed you at it.

1. **Clone any one of the agent repos** into a workspace directory of your choice.
2. **Run Claude Code from the workspace** (the parent directory).
3. **Sync the workspace** — clones any other repos the agent repo declares; pulls everything:
   ```
   /lr:workspace-sync
   ```
4. **Initialize the workspace** so future Claude Code sessions auto-load the framework's conventions:
   ```
   /lr:init
   ```
5. **Boot an agent and start working:**
   ```
   /lr:boot <agent-name>
   ```
   (Run `/lr:list-agents` if you don't yet know what's available.)
6. **Finalize at session end** to preserve what was learned:
   ```
   /lr:finalize
   ```

### Starting fresh — creating your own agent repo

You're introducing the framework into a new area.

1. **Run Claude Code from a workspace directory.**
2. **Create an agent repo:**
   ```
   /lr:create-repo my-agents
   ```
3. **Create an agent:**
   ```
   /lr:create-agent
   ```
4. **Initialize the workspace:**
   ```
   /lr:init
   ```
5. **Boot and work with the agent:**
   ```
   /lr:boot my-agent-name
   ```
6. **Finalize at session end:**
   ```
   /lr:finalize
   ```

## Skills

Grouped by purpose:

**Workspace setup**
| Skill | Purpose |
|---|---|
| `/lr:workspace-sync` | Clone declared repos and pull all top-level repos in the workspace |
| `/lr:init` | Write the framework-managed section into the workspace's `CLAUDE.md` |
| `/lr:list-agents` | List all agents in the workspace |
| `/lr:list-repos` | List all agent repos in the workspace |

**Working with agents**
| Skill | Purpose |
|---|---|
| `/lr:boot <name>` | Load a lore agent by name |
| `/lr:recall [hint]` | Search lore across loaded agents |
| `/lr:attach <agent>` | Attach another agent as a guest in this session |
| `/lr:consult <agent> [hint]` | One-shot question to an unloaded agent |
| `/lr:spawn-teammate [<agent>...]` | **BETA** — Spawn lore agents as Agent Teams teammates |

**Background / headless**
| Skill | Purpose |
|---|---|
| `/lr:wait` | Pause until an external event arrives, or sleep — for background / `claude -p` agents |

**Session lifecycle**
| Skill | Purpose |
|---|---|
| `/lr:reflect` | Extract session knowledge into reflections |
| `/lr:merge` | Integrate reflections into lore |
| `/lr:summarize` | Write a session summary |
| `/lr:finalize` | Full session finalization (reflect + merge + summarize + commit + push) |

**Authoring agents and repos**
| Skill | Purpose |
|---|---|
| `/lr:create-repo <name>` | Scaffold a new agent repo |
| `/lr:create-agent [name]` | Add a new agent to a repo |
| `/lr:register-repo <name>` | Generate per-agent boot shortcuts |
| `/lr:unregister-repo <name>` | Remove per-agent boot shortcuts |

**Maintenance**
| Skill | Purpose |
|---|---|
| `/lr:update` | Apply pending framework migrations |
| `/lr:check` | Run consistency checks |

**Development (BETA)**
| Skill | Purpose |
|---|---|
| `/lr:df-repo-init [<repo>]` | **BETA** — Create the DF backbone repo (`<repo>-df`) for a source repo |
| `/lr:df-ula-file <file>` | **BETA** — Run a ULA (unit-level analysis) pass on one file |

## Optional: Agent Shortcut Commands

By default, agents are loaded via `/lr:boot <agent-name>`. For convenience, you can register per-agent shortcuts:

```
/lr:register-repo my-agents
```

This generates engine-native per-agent shortcuts:

- **Claude Code:** `/lr-<agent-name>-agent` in `.claude/commands/`
- **Codex:** `$lr-<agent-name>-agent` as personal skills in `~/.codex/skills/`

Both are one-line delegations to `agent-boot.md` with absolute paths to the agent directory for faster boot.

## Directory Layout

```
my-workspace/                       # Workspace — the directory you run Claude from
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
└── .claude/
    └── commands/                   # Claude Code optional registered agent commands
        ├── lr-researcher-agent.md
        └── ...
```

On Codex, the equivalent registered shortcuts live in `~/.codex/skills/` as personal skills like `$lr-researcher-agent`.

## License

[MIT](LICENSE)

# Lore Framework

A persistent knowledge system for AI agents running in Claude Code, Codex, and Cursor.

Agents accumulate **lore** — domain expertise, operational wisdom, and decision history — across sessions. Each agent's knowledge graph lives in a shared git repository, growing through contributions from every teammate who boots the agent.

## Engine syntax

Lore skills use different invocation prefixes per engine:

| Engine | Skill syntax | Example boot |
|--------|--------------|--------------|
| Claude Code | `/lr:<skill>` | `/lr:boot lore-architect` |
| Cursor | `/lr-<skill>` | `/lr-boot lore-architect` |
| Codex | `$lr-<skill>` | `$lr-boot lore-architect` |

Per-agent shortcuts: `/lr-<agent>-agent` (Claude, Cursor) or `$lr-<agent>-agent` (Codex).

If Cursor plugin skills are unavailable, see [INSTALL-CURSOR.md](INSTALL-CURSOR.md) and `docs/engines/cursor.md` § Mid-session fallback.

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

- **Workspace** — the directory you run your coding agent from (Claude Code, Codex, or Cursor). Holds one or more agent repos and any other repos they declare.
- **Agent repo** — a git repo containing one or more lore agents. Marked by a `lore-repo.md` at its root. Conceptually, the **domain** an agent (or set of agents) covers.
- **Agent** — a directory under `agents/<name>/` inside an agent repo. Has a `role.md` (identity) and `lore-context.md` (working knowledge), plus a `lore/` knowledge graph of markdown topics.
- **Lore** — the agent's accumulated knowledge: decisions, domain expertise, operational wisdom. Plain markdown, tracked in git, shared across teammates.
- **Boot** — load an agent's role and lore into your session (see engine syntax above).
- **Finalize** — at session end, extract what was learned, merge it into the agent's lore, write a session summary, and commit + push (one command per engine syntax table).

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

Two-step install (clone, then helper), then launch with `--plugin-dir`:

```bash
git clone https://github.com/zroslaw/lore-framework.git "${LORE_FRAMEWORK_DIR:-$HOME/src/lore-framework}"
bash "${LORE_FRAMEWORK_DIR:-$HOME/src/lore-framework}/scripts/install-cursor-plugin" "${LORE_FRAMEWORK_DIR:-$HOME/src/lore-framework}"
cursor-agent --plugin-dir "${LORE_FRAMEWORK_DIR:-$HOME/src/lore-framework}"
```

Refresh after updates:

```bash
bash "${LORE_FRAMEWORK_DIR:-$HOME/src/lore-framework}/scripts/cursor-refresh-plugin"
cursor-agent --plugin-dir "${LORE_FRAMEWORK_DIR:-$HOME/src/lore-framework}"
```

Full guide: [INSTALL-CURSOR.md](INSTALL-CURSOR.md).

## Quick Start

Pick the path that matches your situation.

### Joining a team that already uses Lore Framework

A teammate has set up an agent repo and pointed you at it.

1. **Clone any one of the agent repos** into a workspace directory of your choice.
2. **Run your coding agent from the workspace** (the parent directory) — Claude Code, Codex, or Cursor.
3. **Pull the workspace** — clones any other repos the workspace and agent repos declare; pulls everything:
   ```
   /lr:workspace-pull
   ```
   (Cursor: `/lr-workspace-pull`; Codex: `$lr-workspace-pull`.)
4. **Initialize the workspace** so future sessions auto-load the framework's conventions:
   ```
   /lr:workspace-init
   ```
   On Codex and Cursor this writes `AGENTS.md` (not `CLAUDE.md`).
5. **Boot an agent and start working:**
   ```
   /lr:boot <agent-name>
   ```
   (Cursor: `/lr-boot <agent-name>`; Codex: `$lr-boot <agent-name>`. Run list-agents if you don't yet know what's available.)
6. **Finalize at session end** to preserve what was learned:
   ```
   /lr:finalize
   ```

### Starting fresh — creating your own agent repo

You're introducing the framework into a new area.

1. **Run your coding agent from a workspace directory.**
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
   /lr:workspace-init
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

Grouped by purpose. **Claude** column uses `/lr:<skill>`; **Cursor** uses `/lr-<skill>`; **Codex** uses `$lr-<skill>`.

**Workspace setup**
| Skill | Purpose | Cursor |
|---|---|---|
| `/lr:workspace-pull` | Pull the workspace repo, clone declared repos, and pull all top-level repos | `/lr-workspace-pull` |
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

## Optional: Agent Shortcut Commands

By default, agents are loaded via `/lr:boot <agent-name>`. For convenience, you can register either
one agent or a whole repo:

```
/lr:register-agent my-agents researcher
/lr:register-repo my-agents
```

This generates engine-native per-agent shortcuts:

- **Claude Code:** `/lr-<agent-name>-agent` in `.claude/commands/`
- **Cursor:** `/lr-<agent-name>-agent` in `.cursor/skills/`
- **Codex:** `$lr-<agent-name>-agent` as personal skills in `~/.codex/skills/`

All of them delegate to `agent-boot.md` with an absolute agent path for faster boot. Cursor and
Codex shortcut skills also carry intent-oriented descriptions so engine skill pickers can tell the
agents apart more reliably.

## Directory Layout

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

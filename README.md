# Lore Framework

A persistent knowledge system for AI agents running in [Claude Code](https://claude.com/claude-code).

Agents accumulate **lore** — domain expertise, operational wisdom, and decision history — across sessions. Each agent maintains a personal knowledge graph that grows and evolves through use.

## How It Works

The framework provides:
- A structured way to define AI agents with persistent memory
- A reflection/merge process that extracts and integrates session knowledge
- Skills for managing agents and their knowledge lifecycle

Agents are plain markdown. Knowledge is plain markdown. Git tracks everything. No databases, no config files, no build steps.

## Installation

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

## Quick Start

1. **Create an agent repo:**
   ```
   /lr:create-repo my-agents
   ```

2. **Create an agent:**
   ```
   /lr:create-agent
   ```

3. **Load and work with an agent:**
   ```
   /lr:boot my-agent-name
   ```

4. **Finalize at session end** to preserve what was learned:
   ```
   /lr:finalize
   ```

## Skills

| Skill | Purpose |
|---|---|
| `/lr:boot <name>` | Load a lore agent by name |
| `/lr:reflect` | Extract session knowledge into reflections |
| `/lr:merge` | Integrate reflections into lore |
| `/lr:finalize` | Reflect + merge in one step |
| `/lr:create-repo <name>` | Scaffold a new agent repo |
| `/lr:create-agent [name]` | Add a new agent to a repo |
| `/lr:register-repo <name>` | Generate per-agent boot commands |
| `/lr:unregister-repo <name>` | Remove per-agent boot commands |
| `/lr:list-agents` | List all agents in the domain |
| `/lr:list-repos` | List all agent repos in the domain |
| `/lr:check` | Run consistency checks |

## Optional: Per-Agent Boot Commands

By default, agents are loaded via `/lr:boot <agent-name>`. For convenience, you can register per-agent commands:

```
/lr:register-repo my-agents
```

This generates `/lr-<agent-name>-agent` commands in `.claude/commands/` that work even without the plugin installed.

## Directory Layout

```
my-domain/                          # Domain directory
├── my-agents/                      # An agent repo
│   └── agents/
│       ├── researcher/
│       │   ├── role.md
│       │   ├── lore-context.md
│       │   ├── lore/
│       │   └── workdir/
│       └── analyst/
│           └── ...
├── another-agents-repo/            # Multiple agent repos supported
│   └── agents/
│       └── ...
└── .claude/
    └── commands/                   # Optional registered agent commands
        ├── lr-researcher-agent.md
        └── ...
```

## License

MIT

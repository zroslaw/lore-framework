# Lore Framework

A persistent knowledge system for AI agents running in [Claude Code](https://claude.com/claude-code).

Agents accumulate **lore** — domain expertise, operational wisdom, and decision history — across sessions. Each agent maintains a personal knowledge graph that grows and evolves through use.

## How It Works

The framework provides:
- A structured way to define AI agents with persistent memory
- A reflection/merge process that extracts and integrates session knowledge
- Slash commands for managing agents and their knowledge lifecycle

Agents are plain markdown. Knowledge is plain markdown. Git tracks everything. No databases, no config files, no build steps.

## Quick Start

1. **Clone this repo** into your working directory (the "domain directory"):
   ```bash
   cd my-domain/
   git clone <this-repo> lore-framework
   ```

2. **Start Claude Code** in the domain directory and ask it to set up the framework:
   ```
   Set up the lore framework
   ```
   Claude will create the necessary command files in `.claude/commands/`.

3. **Create an agent repo** or register an existing one:
   ```
   /lr-create-repo my-agents
   ```
   or
   ```
   /lr-register-repo my-existing-agents
   ```

4. **Create an agent:**
   ```
   /lr-create-agent
   ```

5. **Load and work with an agent:**
   ```
   /lr-my-agent-name-agent
   ```

6. **Finalize at session end** to preserve what was learned:
   ```
   /lr-finalize
   ```

## Directory Layout

```
my-domain/                          # Domain directory
├── lore-framework/                 # This repo
│   ├── CLAUDE.md                   # Framework overview (for Claude)
│   ├── docs/                       # Detailed instructions
│   └── commands/                   # Command templates
├── my-agents/                      # An agent repo (yours)
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
    └── commands/                   # Installed by framework setup
        ├── lr-register-repo.md
        ├── lr-create-agent.md
        ├── lr-researcher-agent.md  # Generated per agent
        └── ...
```

## License

MIT

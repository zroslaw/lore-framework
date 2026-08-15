# Lore Agents

> Named AI specialists that learn and grow with you.

AI agents are powerful, but keeping them effective is tedious: you repeatedly provide context,
manually refine instructions, and carry important lessons between sessions.

Lore Agents are named specialists that take responsibility for maintaining the context and
instructions they need. Guided by their roles and your feedback, they capture and curate an
evolving body of context and knowledge—**Lore**—and reuse it in future work. You provide direction;
they manage the context they need to learn and grow.

## How it works

1. **Give every domain its own expert**

   For each project or area of expertise, create a named Lore Agent responsible for it.

   ```text
   /lr:create-agent domain-expert
   ```

2. **Summon the right expert**

   Whenever you work in that domain, use its registered shortcut to bring the agent's accumulated
   context and knowledge into the session.

   ```text
   /lr-domain-expert-agent
   ```

   You can also use `/lr:boot domain-expert` if no shortcut is registered.

3. **Work together**

   Delegate real tasks as you normally would. Share additional data, guidance, and feedback when
   needed.

4. **Finalize the session**

   At the end of the session, ask the agent to finalize it.

   ```text
   /lr:finalize
   ```

   For learning, finalization does two key things:

   - **Reflects on the session** — reviews what happened, identifies what matters, captures new
     knowledge, and considers how to improve.
   - **Updates its Lore** — merges durable lessons and findings into the agent's accumulated
     knowledge.

5. **Repeat—with an agent that remembers**

   The next time you summon it, its accumulated knowledge is already available. Continue from
   experience instead of starting over.

## Get started

Choose the path that fits:

1. **Let your agent set it up** — Give **[QUICKSTART.md](QUICKSTART.md)** to your AI coding agent
   and say *"set this up for me"*. It will install Lore Agents for its engine and guide you through
   creating or joining an agent repo.
2. **Install it yourself** — Follow the guide for
   [Claude Code](INSTALL-CLAUDE.md), [Codex](INSTALL-CODEX.md), or
   [Cursor](INSTALL-CURSOR.md), then use **[FIRST-STEPS.md](FIRST-STEPS.md)** to create your first
   specialist.
3. **Join an existing team** — Install Lore Agents, clone the team's agent repo into your
   workspace, and continue at
   **[QUICKSTART.md § After install](QUICKSTART.md#after-install-pick-your-path)** (path A).

## Use cases

Lore Agents fit wherever expertise should deepen through repeated work instead of resetting with
each session. Build one for yourself, share one with a team, or bring several specialists together.

- **A long-running project companion** — carries status, decisions, rationale, what has already
  been tried, and next steps across the life of a project.
- **A personal domain specialist** — retains your history and constraints across finance, health,
  hobbies, travel, or life administration without rebuilding the background every time.
- **A research or evaluation partner** — preserves sources, criteria, intermediate findings, and
  the reasoning behind earlier judgments.
- **A shared software expert** — learns a codebase's architecture, conventions, migration paths,
  and debugging lessons. When one engineer teaches it something, the whole team can benefit.
- **An integrations and operations expert** — remembers third-party API quirks, rate limits,
  procedures, and hard-won workarounds.
- **A team of specialists** — combines expertise from several domains in one task, without making
  you re-explain each domain from scratch.

The common thread is continuity: work produces knowledge, and that knowledge makes the next session
more useful. Even solo, the value accumulates. Shared with a team, it compounds.

## Concepts

These terms appear throughout the documentation:

| Concept | Meaning |
|---|---|
| **Workspace** | The directory where you run your coding agent. It contains one or more agent repos and the other repos or resources they use. |
| **Agent repo** | A Git repo containing one or more Lore Agents, identified by `lore-repo.md`. It usually represents a domain, project, or team. |
| **Lore Agent** | A named specialist under `agents/<name>/`, with a role, working context, Lore, session history, and a persistent `workdir/` for artifacts. |
| **Lore** | Curated knowledge accumulated through work: decisions, feedback, domain expertise, and operational wisdom. Stored as Markdown and tracked in Git. |
| **Boot** | Load an agent's role, working context, and compact Lore map into the current session. |
| **Finalize** | Reflect on the session, merge useful learning into Lore, write a summary, then commit and push the result. |

## Meet Lore Architect

The Lore Agents framework is itself developed with a Lore Agent. **Lore Architect** lives in
**[lore-framework-dev](https://github.com/zroslaw/lore-framework-dev)** and holds the framework's
design decisions, rationale, and operating knowledge. It is a working demonstration of the idea
and the fastest way to understand the framework or begin contributing.

[Install Lore Agents](#get-started), clone that repo into a workspace, boot `lore-architect`, and
start asking questions.

## Engine syntax

Lore skills use engine-specific invocation syntax:

| Engine | Skill syntax | Example |
|--------|--------------|---------|
| Claude Code | `/lr:<skill>` | `/lr:boot lore-architect` |
| Cursor | `/lr-<skill>` | `/lr-boot lore-architect` |
| Codex | `$lr:<skill>` | `$lr:boot lore-architect` |

The skills below use Claude Code syntax. Translate them for Cursor or Codex using the table above.
Direct agent shortcuts use `/lr-<agent>-agent` in Claude Code and Cursor, or
`$lr-<agent>-agent` in Codex.

## Personal or team-shared knowledge

Lore Agents work for an individual, a team, or both. A personal agent carries your own context
across sessions. Share its Git repo, and its expertise becomes a durable, reviewable asset for
everyone who works with it.

In a shared repo, contributors can:

- Boot the same specialist in their own sessions
- Contribute to the same shared Lore
- Read session summaries and review Lore changes in Git
- Work concurrently; finalization reconciles concurrent Lore changes when possible

The storage model stays the same in both cases: directories provide structure, Git provides
history and sharing, Markdown keeps the knowledge readable, and session summaries preserve a
narrative record for future readers.

## Skills

The framework provides skills for the complete agent lifecycle. Unless noted otherwise, commands
below use Claude Code's `/lr:<skill>` syntax; substitute your engine's prefix from
[Engine syntax](#engine-syntax).

### Workspace setup

| Skill | Purpose |
|---|---|
| `/lr:workspace-pull` | Refresh the entire workspace: pull its repo, clone declared repos, and pull every top-level repo |
| `/lr:pull-lore` | Refresh only the repos of active agents, then reload their roles and contexts |
| `/lr:workspace-init` | Initialize a workspace or reconcile its framework-managed configuration with disk reality |
| `/lr:workspace-push` | Commit and push the framework-managed workspace files |
| `/lr:workspace-status` | Diagnose workspace health; every finding includes the command that fixes it |
| `/lr:list-agents` | Show available agents, their scope, and shortcut status |
| `/lr:list-repos` | Show available agent repos, their scope, and shortcut status |

### Working with agents

| Skill | Purpose |
|---|---|
| `/lr:boot <agent-name>` | Load a named Lore Agent into the session |
| `/lr:recall [hint]` | Find relevant Lore across loaded agents |
| `/lr:attach [agent-name]` | Load another agent as a guest for sustained co-work, or list attached guests with no argument |
| `/lr:consult <agent-name> [hint]` | Ask an unloaded agent a focused, one-off question |
| `/lr:spawn-teammate [<agent-name>...]` | **BETA, Claude Code only** — Spawn Lore Agents as Agent Teams teammates |

### Interaction style

| Skill | Purpose |
|---|---|
| `/lr:style [plain] [dialogue] [follow]`, `/lr:style all`, `/lr:style off` | Set the session's Lore communication styles; no argument enables all styles |

### Background and headless operation

| Skill | Purpose |
|---|---|
| `/lr:wait` | **Claude Code only** — Wait for an external event or sleep during background operation |
| `/lr:being [subcommand]` | **BETA** — Manage Lore Beings and the Being Keeper |

### Session lifecycle

| Skill | Purpose |
|---|---|
| `/lr:reflect` | Extract knowledge worth preserving into reflection topics |
| `/lr:merge` | Integrate reflection topics into Lore |
| `/lr:summarize` | Write a committable session summary |
| `/lr:finalize` | Reflect, merge, summarize, then commit and push |
| `/lr:takeover [session]` | **BETA** — Continue a session recorded by another engine |

### Authoring agents and repos

| Skill | Purpose |
|---|---|
| `/lr:create-repo <lore-agent-repo>` | Scaffold a new agent repo |
| `/lr:create-agent [agent-name]` | Create a Lore Agent with an initial role and Lore structure |
| `/lr:register-agent [repo] <agent-name>` | Create or refresh one direct boot shortcut |
| `/lr:register-repo <repo>` | Create or refresh shortcuts for every agent in a repo |
| `/lr:unregister-agent [repo] <agent-name>` | Remove one direct boot shortcut |
| `/lr:unregister-repo <repo>` | Remove all direct boot shortcuts for a repo |

### Reviewing changes

| Skill | Purpose |
|---|---|
| `/lr:trilens-loop [amendments]` | Review this session's changes from three independent perspectives, fix what matters, and repeat until clean |

### Maintenance

| Skill | Purpose |
|---|---|
| `/lr:update [--dry-run]` | Update domain artifacts to match the installed framework version |
| `/lr:groom [scope] [--dry-run] [--all]` | Improve Lore structure, retrieval efficiency, and prose quality |
| `/lr:check` | Check consistency across the domain and all its agents |
| `/lr:doctor` | Diagnose and repair known framework runtime issues |

### Development tools

| Skill | Purpose |
|---|---|
| `/lr:df-repo-init [<repo>]` | **BETA** — Initialize a Dark Factory backbone repo (`<repo>-df`) for a source repo |
| `/lr:df-ula-file <file>` | **BETA** — Analyze one file for potential bugs, test scenarios, and test gaps |

## Direct boot shortcuts

You can always boot an agent with `/lr:boot <agent-name>`. For agents you use often, create a direct
shortcut with `/lr:register-agent`, or register every agent in a repo with `/lr:register-repo`.

Shortcuts are stored inside the workspace under `.claude/commands/`, `.cursor/skills/`, or
`.codex/skills/`, depending on the engine. Publish them with `/lr:workspace-push`, and teammates
receive them through `/lr:workspace-pull`. See [FIRST-STEPS.md](FIRST-STEPS.md), Step 5.

## Directory layout

```text
my-workspace/                       # Run your coding agent here
├── my-agents/                      # Agent repo for one domain
│   ├── lore-repo.md                # Declares the repo and its domain
│   └── agents/
│       ├── researcher/
│       │   ├── role.md
│       │   ├── lore-context.md
│       │   ├── lore/
│       │   ├── sessions/           # Created when sessions are summarized
│       │   └── workdir/
│       └── analyst/
│           └── ...
├── another-agent-repo/            # Multiple domains can share a workspace
│   ├── lore-repo.md
│   └── agents/
│       └── ...
├── AGENTS.md                       # Shared workspace guidance
├── CLAUDE.md                       # AGENTS.md import for Claude Code
├── .claude/
│   └── commands/                   # Registered Claude Code agent shortcuts
│       ├── lr-researcher-agent.md
│       └── ...
├── .codex/
│   └── skills/                     # Registered Codex agent shortcuts
│       ├── lr-researcher-agent/
│       └── ...
└── .cursor/
    └── skills/                     # Registered Cursor agent shortcuts
        ├── lr-researcher-agent/
        └── ...
```

Codex discovers `.codex/skills/` from the Git root of the working directory, so start it at the
workspace root. Shortcuts created before v37 may still live under `~/.codex/skills/`;
`/lr:update` moves them into the workspace.

## Reference

[Marketplace metadata](MARKETPLACE.md) · [Privacy and data handling](PRIVACY.md) ·
[MIT License](LICENSE)

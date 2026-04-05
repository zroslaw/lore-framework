# Lore Framework

A persistent knowledge system for AI agents. Agents accumulate knowledge — called **lore** — across sessions, building up domain expertise, operational wisdom, and decision history.

## Core Concepts

- **Domain directory** — a working directory containing multiple repositories and data. The framework is installed into a domain directory and operates across all its contents.
- **Framework** (`lore-framework/`) — this repo. Defines how agents work, how knowledge is stored, and provides commands for managing everything.
- **Agent repo** — a sibling repository containing one or more agent definitions. A domain can have multiple agent repos.
- **Agent** — a role with persistent knowledge. Defined by `role.md` (identity), `lore-context.md` (working knowledge), and a `lore/` directory (knowledge graph of detailed topics).

## Lifecycle

1. **Setup** — install the framework into a domain directory. See `docs/setup.md`.
2. **Create or register agent repos** — either scaffold a new repo (`docs/create-repo.md`) or register an existing one (`docs/register-repo.md`).
3. **Create agents** — add agents to a repo. See `docs/create-agent.md`.
4. **Work** — load an agent via its `/lr-<name>-agent` command and work. The agent has access to all repos in the domain.
5. **Finalize** — at session end, preserve knowledge via reflection and merge. See `docs/process-reflection.md` and `docs/process-merge.md`.

## Commands

Framework commands are installed into the domain directory's `.claude/commands/` during setup.

| Command | Docs | Purpose |
|---|---|---|
| `/lr-register-repo` | `docs/register-repo.md` | Register an agent repo, generate agent commands |
| `/lr-unregister-repo` | `docs/register-repo.md` | Remove agent commands for a repo |
| `/lr-create-repo` | `docs/create-repo.md` | Scaffold a new agent repo |
| `/lr-create-agent` | `docs/create-agent.md` | Add a new agent to a repo |
| `/lr-reflect` | `docs/process-reflection.md` | Extract session knowledge into reflections |
| `/lr-merge` | `docs/process-merge.md` | Integrate reflections into lore |
| `/lr-finalize` | `docs/process-reflection.md`, `docs/process-merge.md` | Reflect + merge in sequence |

Per-agent commands (`/lr-<name>-agent`) are generated during repo registration. They load an agent's boot context. See `docs/agent-boot.md`.

## Key Constraints

- `lore-context.md` budget: 10K tokens max
- Lore topics: atomic, under 1K tokens preferred, plain markdown, no frontmatter
- Git tracks all metadata — no timestamps or status fields in files
- Obsolete topics are deleted, not marked — git preserves history

See `docs/conventions.md` for the full set of conventions.

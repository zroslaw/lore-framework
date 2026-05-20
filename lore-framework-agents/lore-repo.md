---
description: Lore agents dedicated to lore framework development
version: "9"
---

# Lore Framework Agents

Agents that work on the lore-framework itself. Currently houses the **lore-architect** — the architect and maintainer of the lore system.

This is a dedicated agent repo, separate from the framework plugin (`lore-framework/`). It exists so that framework design decisions, history, reasoning, and intermediate work accumulate as team-shared knowledge accessible to anyone contributing to the framework.

The intent is to extract this directory into its own GitHub repository — it lives here temporarily as a sibling-of-convenience while the eventual repo location is being set up.

## Why a Separate Repo

- Keeps the framework plugin (`lore-framework/`) slim and focused on what gets distributed via the Claude Code marketplace.
- Plugin-repo and agent-repo concerns are separate: `.claude-plugin/`, `skills/`, `docs/`, `migrations/` belong in the plugin; `lore-repo.md`, `agents/`, `sessions/`, `workdir/` belong in an agent repo.
- Contributors who want to converse with the framework's accumulated design knowledge clone this repo as a sibling in their domain and boot `lore-architect`.

See the lore-framework's README for the team-shared-knowledge framing that underlies all lore agents.

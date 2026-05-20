The lore system is split across a plugin and one or more agent repos within a domain directory.

**Plugin** (`lore-framework` — installed as `lr`):
- `.claude-plugin/plugin.json` — plugin manifest
- `.claude-plugin/marketplace.json` — self-hosted marketplace manifest
- `skills/<name>/SKILL.md` — 13 skill definitions (boot, reflect, merge, finalize, register-repo, unregister-repo, create-repo, create-agent, list-agents, list-repos, check, pull-domain, update)
- `docs/` — detailed instructions referenced by skills via `${CLAUDE_PLUGIN_ROOT}/docs/`
- `migrations/<N>.md` — per-version migration instructions consumed by `/lr:update`
- `VERSION` — single source of truth for the current framework version (currently `2`)

**Agent repo** (e.g., `lore-agents/`):
- `lore-repo.md` — repo descriptor at the root; marks the directory as a lore agent repo. YAML frontmatter: `description` and `version` (framework version string). This is the **only** place a framework version is stamped.
- `agents/<name>/role.md` — agent identity. YAML frontmatter: `description` only. Body: role definition.
- `agents/<name>/lore-context.md` — compacted working knowledge (≤50K tokens)
- `agents/<name>/lore/` — knowledge graph of atomic topics
- `agents/<name>/reflections/` — temporary, finalization step 1 output
- `agents/<name>/workdir/` — persistent workspace for artifacts

**Boot flow:** the caller reads `${CLAUDE_PLUGIN_ROOT}/docs/agent-boot.md` (or `lore-framework/docs/agent-boot.md` for per-agent commands) and passes the agent name. `agent-boot.md` contains both the boot procedure (discover agent → read `role.md` + `lore-context.md` → confirm) and the operating instructions. Single source of truth — both `/lr:boot` and the registered `/lr-<name>-agent` commands are one-line delegations to this file. See `slash-command-system.md`.

**Repo discovery:** skills scan for `lore-repo.md` at the directory root — not for `agents/` subdirectories. This prevents false positives from other repos that happen to have an `agents/` directory.

**Version chain (v2+):** `VERSION` → `lore-repo.md` frontmatter `version`. One identifier per repo, no per-agent stamping. `/lr:check` validates this at check 3. `/lr:update` migrates repos forward by applying `migrations/<N>.md` docs sequentially, then stamping the new version on success. See `consistency-checks.md`, `update-process.md`.

The domain directory contains only agent repos — `lore-framework/` no longer needs to be a sibling. The plugin is installed via `/plugin marketplace add zroslaw/lore-framework` + `/plugin install lr@lore-framework`, or loaded locally via `claude --plugin-dir ./lore-framework`. See `plugin-distribution.md`.

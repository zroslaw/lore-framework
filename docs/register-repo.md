# Register / Unregister Agent Shortcuts

Manage direct per-agent boot shortcuts for the current engine.

These shortcuts are **optional** — agents can always be loaded via `/lr:boot <agent-name>` (or
the engine-native equivalent). Registration adds a faster direct entry point with an absolute agent
path and, on skill-based engines, richer routing metadata.

The four user-facing operations share one procedure doc:

- **Register Agent** — create or refresh a shortcut for one specific agent
- **Register Repo** — create or refresh shortcuts for every agent in a repo
- **Unregister Agent** — remove one agent's shortcut
- **Unregister Repo** — remove every shortcut associated with a repo

Use the current engine profile (`<framework-root>/docs/engines/<engine>.md`, selected at boot) to
decide which native artifact to generate.

## Engine-native shortcut locations

- **Claude Code** — workspace-local command file:
  `.claude/commands/lr-<agent-name>-agent.md`
- **Cursor** — workspace-local skill:
  `.cursor/skills/lr-<agent-name>-agent/SKILL.md`
- **Codex** — personal skill:
  `~/.codex/skills/lr-<agent-name>-agent/SKILL.md`

All generated shortcuts must remain thin pointers to `agent-boot.md`. Never inline boot logic or
operating instructions into the generated artifact.

## Shared helper steps

### Resolve the target repo

When an operation targets a repo explicitly:

1. Treat the repo argument as a directory name relative to the current working directory.
2. Verify `<workspace>/<repo-name>/lore-repo.md` exists.
3. Call that path `<lore-agent-repo>`.

When an operation targets a single agent and no repo argument was provided:

1. Scan all directories in the current working directory for lore agent repos (directories
   containing `lore-repo.md` at the root).
2. Look for `agents/<agent-name>/role.md` inside each repo.
3. If exactly one match exists, use that repo.
4. If no match exists, report the available agents and stop with an error.
5. If multiple matches exist, ask the user which repo they want.

### Resolve agent metadata

For every target agent:

1. Verify `<lore-agent-repo>/agents/<agent-name>/role.md` exists.
2. Resolve:
   - **`<agent-dir>`** — absolute path to `<lore-agent-repo>/agents/<agent-name>/`
   - **`<agent-boot-path>`** — absolute path to `<framework-root>/docs/agent-boot.md`
   - **`<repo-name>`** — basename of `<lore-agent-repo>`
3. Read the `description` field from `role.md` YAML frontmatter. Use it as
   **`<agent-purpose>`**. If missing, fall back to `Lore agent in <repo-name>`.

### Current shortcut templates

Generate exactly these engine-native forms.

#### Claude Code

Write exactly this single line plus a trailing newline:

```markdown
Read `<agent-boot-path>` and boot as agent `<agent-name>` from `<agent-dir>`.
```

#### Cursor

Write this `SKILL.md`:

```markdown
---
name: lr-<agent-name>-agent
description: "Boot the <agent-name> lore agent from <repo-name> — <agent-purpose>"
paths:
  - "<repo-name>/**"
disable-model-invocation: true
---

Read `<agent-boot-path>` and boot as agent `<agent-name>` from `<agent-dir>`.
```

The `paths:` scoping keeps the shortcut visible only when the matching repo is relevant in the
workspace, and `disable-model-invocation: true` keeps it explicit-only.

#### Codex

Write this `SKILL.md`:

```markdown
---
name: lr-<agent-name>-agent
description: "Boot the <agent-name> lore agent from <repo-name> — <agent-purpose>"
---

Read `<agent-boot-path>` and boot as agent `<agent-name>` from `<agent-dir>`.
```

## Register Agent

**Inputs:** `[<lore-agent-repo>] <agent-name>`

1. Resolve `<lore-agent-repo>` and the agent metadata using the shared helper steps above.
2. Compute the engine-native target path for that agent.
3. If the target artifact already exists:
   - If it already points at the same `<agent-dir>`, overwrite it with the current template
     (refresh behavior).
   - If it points at a different repo/agent path, warn about the collision and stop without
     overwriting.
4. Create the parent directory if needed and write the current template.
5. Report the created shortcut in the engine-native form:
   - **Claude Code / Cursor:** `/lr-<agent-name>-agent`
   - **Codex:** `$lr-<agent-name>-agent`

## Register Repo

**Input:** `<lore-agent-repo>`

1. Resolve `<lore-agent-repo>`.
2. Scan `<lore-agent-repo>/agents/` for directories containing `role.md`.
3. For each agent found, run the **Register Agent** procedure above.
4. Report the created or refreshed shortcuts.

## Unregister Agent

**Inputs:** `[<lore-agent-repo>] <agent-name>`

1. Resolve `<lore-agent-repo>` and `<agent-name>`.
2. Compute the engine-native shortcut path for that agent.
3. If the artifact does not exist, report `not registered` and stop successfully.
4. Delete the artifact:
   - **Claude Code:** delete the `.md` file.
   - **Cursor / Codex:** delete the `lr-<agent-name>-agent/` directory.
5. Report the removed shortcut in the engine-native form.

## Unregister Repo

**Input:** `<lore-agent-repo>`

1. Resolve `<lore-agent-repo>`.
2. Scan the repo's `agents/` directory for valid agents.
3. For each agent found, run the **Unregister Agent** procedure above.
4. Report the removed shortcuts.

## Collision rule

Shortcuts are keyed by agent name, so collisions are possible if two repos both define
`agents/researcher/`.

- If a shortcut already exists and points at a different `<agent-dir>`, do **not** overwrite it.
- Tell the user which existing path owns the shortcut today and which repo they attempted to
  register.
- The user resolves the naming collision by renaming an agent or unregistering the old shortcut
  first.

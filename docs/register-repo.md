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
- **Codex** — workspace-local skill:
  `.codex/skills/lr-<agent-name>-agent/SKILL.md`

All three are workspace-local, so all three are published by `/lr:workspace-push` and arrive for a
teammate by git. Codex also loads personal skills from `~/.codex/skills/`, which is where the
framework wrote its shortcuts before v37; never write there now — that copy reaches nobody else, and
`workspace-status` finding S15 asks for any leftover to be relocated (`migrations/37.md` does it in
bulk). Codex resolves the workspace-local root from the git root of the session's working directory:
see `docs/engines/codex.md` § Where per-agent shortcuts live.

All generated shortcuts must remain thin delegations to the active framework boot entry point.
They pin only the agent identity and absolute agent directory; they must never bake a plugin-cache
path, scan for a framework checkout, select an installed version, or inline boot logic.

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
   - **`<repo-name>`** — basename of `<lore-agent-repo>`
3. Read the `description` field from `role.md` YAML frontmatter. Use it as
   **`<agent-purpose>`**. If missing, fall back to `Lore agent in <repo-name>`.

### Resolve the shortcut bootstrap

Read the current engine profile's **Registered shortcut bootstrap** section. Copy its exact
engine-specific bootstrap sentence into every generated shortcut, substituting `<agent-name>` and
`<agent-dir>`. The active boot skill self-locates the framework root, so the emitted shortcut must
not contain an `<agent-boot-path>` or any other plugin-install path.

**Emit the bootstrap as one unwrapped line, on every engine**, however the profile's fenced block
happens to be wrapped for reading. Two things depend on it: `migrations/33.md` classifies an
existing shortcut as `current` only on a **byte-for-byte** match with the freshly generated
artifact, so an executor that re-wraps differently makes every upgrade rewrite a shortcut that was
already correct; and Claude Code renders a command's description from the file's **first line**, so
a wrapped bootstrap shows up in the command list as a sentence fragment.

### Current shortcut templates

Generate exactly these engine-native forms.

#### Claude Code

Write exactly this single line plus a trailing newline:

```markdown
<shortcut-bootstrap>
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

<shortcut-bootstrap>
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

<shortcut-bootstrap>
```

### Maintain the workspace Agents section

A shortcut is the membership record: the workspace memory file's `## Agents` section lists
**registered** agents — it is the "what can I boot here" answer. So every operation below writes the
shortcut and updates that section **in the same operation**. A shortcut without an entry is an agent
nobody reading the memory file knows exists.

For every register/unregister operation, after the artifact is written or deleted:

1. **Ensure `<workspace>/AGENTS.md` exists** with the canonical payload. If it does not, or carries
   no `## Agents` heading, do not synthesize one here — report that the workspace memory file needs
   `/lr:workspace-init` and continue; registration itself has succeeded.
2. **Rewrite the `## Agents` section body** from the shortcuts now on disk, across all three engine
   locations (§ Engine-native shortcut locations) plus any legacy `~/.codex/skills/` shortcut for an
   agent in this workspace — an agent bootable only from the legacy location is still registered, and
   dropping it from the list would make the membership record disagree with what Codex offers. The section runs from its exact `## Agents`
   heading to the line before the next `^## ` heading, or EOF, **ignoring any such line inside a
   ``` or `~~~` fence** — a fenced example in the user's own prose is not a heading. Keep the
   provenance comment as the first line of the body.

   Each shortcut supplies *membership* and, in its boot line, the agent's absolute `<agent-dir>`.
   Take the **role description from `<agent-dir>/role.md`'s frontmatter `description`** and the repo
   dirname from that path — not from the shortcut, which on Claude Code is a single bootstrap line
   carrying neither. Fall back to `Lore agent in <repo-dirname>` when `role.md` has no description,
   matching § Resolve agent metadata. One line per agent:

   ```markdown
   - `<agent-name>` (`<repo-dirname>`) — <role description>. Boot: `lr-<agent-name>-agent`.
   ```

   With none left, emit the single line:
   `_(No agents registered yet — run `register-agent` to add one.)_`

   Render from disk rather than editing the one line you just changed: it is idempotent, it repairs
   drift from a hand-edited file for free, and it cannot leave a stale entry behind when an
   unregister and a register happen in the same run.
3. **Ensure the `CLAUDE.md` import stub.** If `<workspace>/CLAUDE.md` has no line whose trimmed
   content is exactly `@AGENTS.md`, append the two-line stub, preserving all existing content:

   ```markdown
   <!-- Lore Framework: this workspace's memory lives in AGENTS.md, shared across engines. -->

   @AGENTS.md
   ```

   Claude Code does not read `AGENTS.md`. Without that line, a Claude Code session in this workspace
   sees no workspace memory at all — including the Agents list just written — and nothing reports it.
   Never regenerate or truncate `CLAUDE.md`; that one line is the only framework-managed content in
   it.

Full contract, including the parsing rules and the marker migration: `docs/workspace-init.md` §
The memory-file contract. `workspace-init`'s convergence pass re-renders the same section from the
same source, so the two writers agree by construction — **registration remains the single membership
authority; init is only the renderer.**

These writes leave the workspace dirty. `/lr:workspace-push` publishes them.

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
5. Maintain the workspace Agents section and the `CLAUDE.md` import stub (shared helper step above).
6. Report the created shortcut in the engine-native form:
   - **Claude Code / Cursor:** `/lr-<agent-name>-agent`
   - **Codex:** `$lr-<agent-name>-agent`

## Register Repo

**Input:** `<lore-agent-repo>`

1. Resolve `<lore-agent-repo>`.
2. Scan `<lore-agent-repo>/agents/` for directories containing `role.md`.
3. For each agent found, run the **Register Agent** procedure above, deferring its § Maintain the
   workspace Agents section step to step 4. A collision on one agent stops **that agent only** —
   record it and carry on with the rest; a repo-wide registration must not be abandoned halfway
   because one name is taken.
4. Run § Maintain the workspace Agents section once at the end rather than per agent — **all** of it,
   the `CLAUDE.md` import stub included. The section is rendered from disk, so one pass after the
   last write is both correct and cheaper; skipping the helper's other items is not part of the
   saving.
5. Report the created or refreshed shortcuts.

## Unregister Agent

**Inputs:** `[<lore-agent-repo>] <agent-name>`

1. Resolve `<lore-agent-repo>` and `<agent-name>`.
2. Compute the engine-native shortcut path for that agent.
3. If the artifact does not exist, report `not registered` and stop successfully.
4. Delete the artifact:
   - **Claude Code:** delete the `.md` file.
   - **Cursor / Codex:** delete the `lr-<agent-name>-agent/` directory.

   On Codex, also check `~/.codex/skills/lr-<agent-name>-agent/SKILL.md`. Delete it too **when its
   boot line names an `<agent-dir>` under this workspace** — leaving it behind means the agent the
   user just unregistered still appears in every Codex session. When it names a different path, it
   belongs to another workspace: report it and leave it alone.
5. Maintain the workspace Agents section and the `CLAUDE.md` import stub (shared helper step above) —
   the removed agent's line goes with it.
6. Report the removed shortcut in the engine-native form.

## Unregister Repo

**Input:** `<lore-agent-repo>`

1. Resolve `<lore-agent-repo>`.
2. Scan the repo's `agents/` directory for valid agents.
3. For each agent found, run the **Unregister Agent** procedure above, deferring its § Maintain the
   workspace Agents section step to step 4.
4. Run § Maintain the workspace Agents section once at the end — all of it, the `CLAUDE.md` import
   stub included.
5. Report the removed shortcuts.

## Collision rule

Shortcuts are keyed by agent name, so collisions are possible if two repos both define
`agents/researcher/`.

- If a shortcut already exists and points at a different `<agent-dir>`, do **not** overwrite it.
- Tell the user which existing path owns the shortcut today and which repo they attempted to
  register.
- The user resolves the naming collision by renaming an agent or unregistering the old shortcut
  first.

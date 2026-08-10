# Create Agent

Add a new agent to an existing agent repo.

## Steps

1. **Determine the target repo.** If the user specified one, use it. If there's only one lore agent repo in the workspace (identified by `lore-repo.md` at the root), use that. Otherwise, ask.

2. **Get the agent name.** Kebab-case, descriptive (e.g., `code-reviewer`, `data-analyst`).

3. **Get a role description.** Ask the user what this agent does — its responsibilities, how it works, what are its job responsibilities and work area to cover.

4. **Create the agent directory structure:**
   ```
   <lore-agent-repo>/agents/<agent-name>/
   ├── role.md              # Agent identity and responsibilities
   ├── lore-context.md      # Initial working knowledge (starts minimal)
   ├── lore/                # Knowledge topics (starts empty)
   └── workdir/             # Workspace for artifacts
   ```

5. **Write `role.md`** with YAML frontmatter and body. The frontmatter contains:
   - `description` — a one-line summary of the agent's purpose

   The body includes:
   - Agent name as heading
   - Responsibilities section
   - How You Work section

   Example:
   ```markdown
   ---
   description: Reviews pull requests for code quality and security
   ---

   # Code Reviewer

   ...
   ```

   Keep it concise — this is a living document that evolves.

   Note: the framework version is tracked **only** at the repo level (`lore-repo.md` frontmatter). Agents do not carry their own version stamp — they migrate together with the repo via `/lr:update`.

6. **Write `lore-context.md`** as a minimal Lore v1 root (schema:
   `<framework-root>/docs/lore-structure.md`):
   ```markdown
   ---
   lore: 1
   type: context
   summary: "Initial working knowledge and navigation for this agent."
   ---

   # Lore Context

   Initial session. No accumulated lore yet.
   ```

7. **Verify before reporting success.** Check that `<lore-agent-repo>/agents/<agent-name>/role.md`,
   `<lore-agent-repo>/agents/<agent-name>/lore-context.md`,
   `<lore-agent-repo>/agents/<agent-name>/lore/`, and
   `<lore-agent-repo>/agents/<agent-name>/workdir/` exist. If any are missing, create
   the missing item before continuing. Do not print "done" for a no-op.

8. **Report** what was created. The agent is now loadable via `/lr:boot <agent-name>`.

   Shortcut options:
   - Register just this agent: `/lr:register-agent <lore-agent-repo> <agent-name>`
   - Register every agent in the repo: `/lr:register-repo <lore-agent-repo>`

   Registering is also what adds the agent to the workspace memory file's `## Agents` section — the
   "what can I boot here" list a teammate reads on arrival. An unregistered agent is bootable but
   invisible there (`/lr:workspace-status` finding S11).

   Engine-native shortcut forms:
   - **Claude Code:** `/lr-<agent-name>-agent`
   - **Cursor:** `/lr-<agent-name>-agent`
   - **Codex:** `$lr-<agent-name>-agent`

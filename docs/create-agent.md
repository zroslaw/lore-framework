# Create Agent

Add a new agent to an existing agent repo.

## Steps

1. **Determine the target repo.** If the user specified one, use it. If there's only one lore agent repo in the domain (identified by `lore-repo.md` at the root), use that. Otherwise, ask.

2. **Read the framework version** from `${CLAUDE_PLUGIN_ROOT}/VERSION`. This will be stamped into the agent's `role.md`.

3. **Get the agent name.** Kebab-case, descriptive (e.g., `code-reviewer`, `data-analyst`).

4. **Get a role description.** Ask the user what this agent does — its responsibilities, how it works, what are its job responsibilities and work area to cover.

5. **Create the agent directory structure:**
   ```
   <repo>/agents/<agent-name>/
   ├── role.md              # Agent identity and responsibilities
   ├── lore-context.md      # Initial working knowledge (starts minimal)
   ├── lore/                # Knowledge topics (starts empty)
   └── workdir/             # Workspace for artifacts
   ```

6. **Write `role.md`** with YAML frontmatter and body. The frontmatter contains:
   - `description` — a one-line summary of the agent's purpose
   - `version` — the framework version (read from `VERSION` file)

   The body includes:
   - Agent name as heading
   - Responsibilities section
   - How You Work section

   Example:
   ```markdown
   ---
   description: Reviews pull requests for code quality and security
   version: "1"
   ---

   # Code Reviewer

   ...
   ```

   Keep it concise — this is a living document that evolves.

7. **Write `lore-context.md`** with a minimal starting structure:
   ```markdown
   # Lore Context

   Initial session. No accumulated lore yet.
   ```

8. **Report** what was created. The agent is now loadable via `/lr:boot <agent-name>` and also via `/lr-<agent-name>-agent`.

# Create Agent

Add a new agent to an existing agent repo.

## Steps

1. **Determine the target repo.** If the user specified one, use it. If there's only one agent repo in the domain, use that. Otherwise, ask.

2. **Get the agent name.** Kebab-case, descriptive (e.g., `code-reviewer`, `data-analyst`).

3. **Get a role description.** Ask the user what this agent does — its responsibilities, how it works, what domain it covers.

4. **Create the agent directory structure:**
   ```
   <repo>/agents/<agent-name>/
   ├── role.md              # Agent identity and responsibilities
   ├── lore-context.md      # Initial working knowledge (starts minimal)
   ├── lore/                # Knowledge topics (starts empty)
   └── workdir/             # Workspace for artifacts
   ```

5. **Write `role.md`** based on the user's description. Include:
   - Agent name as heading
   - Responsibilities section
   - How You Work section
   Keep it concise — this is a living document that evolves.

6. **Write `lore-context.md`** with a minimal starting structure:
   ```markdown
   # Lore Context

   Initial session. No accumulated lore yet.
   ```

7. **Create the slash command** at `.claude/commands/lr-<agent-name>-agent.md` following the template described in `register-repo.md`.

8. **Report** what was created. The agent is now loadable via `/lr-<agent-name>-agent`.

# Create Agent Repo

Scaffold a new agent repository in the domain directory.

**Input:** repo name (e.g., `my-agents`)

## Steps

1. **Verify** the name doesn't collide with an existing directory in the domain dir.

2. **Read the framework version** from `${CLAUDE_PLUGIN_ROOT}/VERSION`. This will be stamped into the repo descriptor.

3. **Create the directory structure:**
   ```
   <lore-agent-repo>/
   ├── agents/           # Agent definitions go here
   ├── lore-repo.md      # Repo descriptor (marks this as a lore agent repo)
   ├── .gitignore
   └── README.md
   ```

4. **Write `lore-repo.md`** with YAML frontmatter. Ask the user for a short description of the repo's purpose. Stamp the framework version:
   ```markdown
   ---
   description: <user-provided description>
   version: "<framework version>"
   ---

   # <Repo Name>

   <brief description of the repo>
   ```

5. **Write `.gitignore`:**
   ```
   # Agent reflections are temporary
   **/reflections/
   ```

6. **Write `README.md`** with a brief description explaining this is a lore agents repository. Mention that agents are managed via the `lr` plugin.

7. **Initialize git** — run `git init` and create an initial commit.

8. **Report** what was created. Remind the user they can now add agents with `/lr:create-agent`.

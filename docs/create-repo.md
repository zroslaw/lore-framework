# Create Agent Repo

Scaffold a new agent repository in the domain directory.

**Input:** repo name (e.g., `my-agents`)

## Steps

1. **Verify** the name doesn't collide with an existing directory in the domain dir.

2. **Create the directory structure:**
   ```
   <repo-name>/
   ├── agents/           # Agent definitions go here
   ├── .gitignore
   └── README.md
   ```

3. **Write `.gitignore`:**
   ```
   # Agent reflections are temporary
   **/reflections/
   ```

4. **Write `README.md`** with a brief description explaining this is a lore agents repository and pointing to the framework for documentation.

5. **Initialize git** — run `git init` and create an initial commit.

6. **Report** what was created. Remind the user they can now add agents with `/lr-create-agent`.

# Create Agent Repo

Scaffold a new agent repository in the workspace.

**Input:** repo name (e.g., `my-agents`), or a disposable path under `.tmp/` (e.g.,
`.tmp/new-fixture-repo`) for throwaway / test scaffolds that must not look like a workspace child.

## Steps

1. **Verify** the target doesn't collide with an existing path in the workspace. A normal agent
   repo is a single top-level directory name. Disposable scaffolds go under `.tmp/<name>/` (that
   tree is gitignored by default — see `docs/workspace-init.md` Step 6).

2. **Read the framework version** from `<framework-root>/VERSION`. This will be stamped into the repo descriptor.

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

8. **Verify before reporting success.** Check that `<lore-agent-repo>/lore-repo.md`,
   `<lore-agent-repo>/agents/`, `<lore-agent-repo>/.gitignore`,
   `<lore-agent-repo>/README.md`, and `<lore-agent-repo>/.git/` exist. If any are
   missing, create the missing item before continuing. Do not print "done" for a
   no-op.

9. **Report** what was created. Remind the user they can now add agents with `/lr:create-agent`, and
   that registering them (`/lr:register-repo <lore-agent-repo>`) is what lists them in the workspace
   memory file's `## Agents` section.
10. If this workspace declares its repos in `lore-workspace.md`, note that the new repo is not in it
    yet — `/lr:workspace-init` offers to declare it, and until then a teammate's `/lr:workspace-pull`
    will not clone it (`/lr:workspace-status` finding S5).

# Create Agent Repo

Scaffold a new agent repository in the workspace.

**Input:** repo name (e.g., `my-agents`), or a disposable path under `.tmp/` (e.g.,
`.tmp/new-fixture-repo`) for throwaway / test scaffolds that must not look like a workspace child.

## Step 0 — Announce

**Skip this announcement when another procedure reached this doc** rather than the user
invoking the skill directly — that caller has already announced, and `conventions.md`
§ Skill Purpose Announcement allows one announcement per user invocation.

Print this to the user before doing anything else, filling in any `<placeholder>`:

> Creating a new **lore agent repo** — a git repo that holds lore agents rather than source code.
> **Your workspace can hold both kinds side by side**, and this is the agent kind. It's the
> shareable unit: one or more agents live in it, and pushing it is how your whole team gets the same
> agents with the same accumulated knowledge. I'll scaffold the structure, mark it as a lore agent
> repo, and stamp the current framework version into it. **It starts as a local git repo with no
> remote** — add one when you're ready to share it.

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

4. **Write `lore-repo.md`** with YAML frontmatter. Ask for a concise **routing description**, not
   merely a category label: what the repo owns, what useful material it contains, and when an
   unfamiliar agent should inspect it. If sibling repos already exist, make the distinction clear.
   Stamp the framework version:
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

9. **Report** what was created. Remind the user they can now add agents with `/lr:create-agent`,
   which registers each agent as it creates it — that registration is what lists an agent in the
   workspace memory file's `## Agents` section. `/lr:register-repo <lore-agent-repo>` is the bulk
   path for agents that arrived some other way, or to refresh existing shortcuts.
10. If this workspace declares its repos in `lore-workspace.md`, note that the new repo is not in it
    yet — `/lr:workspace-init` offers to declare it, and until then a teammate's `/lr:workspace-pull`
    will not clone it (`/lr:workspace-status` finding S5).

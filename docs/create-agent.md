# Create Agent

Add a new agent to an existing agent repo.

## Step 0 — Announce

Print this to the user before doing anything else, filling in any `<placeholder>`. Skip it entirely
when another procedure reached this doc rather than the user invoking `/lr:create-agent` — that
caller has already announced (`conventions.md` § Skill Purpose Announcement). Since registration is
suppressed only by such a caller (step 8), a direct invocation always attempts it. Registration can
still stop without writing — a shortcut collision, or a workspace with no `AGENTS.md` to list the
agent in — so step 9 reports what actually happened; the announcement states the intent:

> Creating a new agent inside one of your lore agent repos. An agent is four things: a role (who it
> is and what it owns), a lore context (its working knowledge in short), a `lore/` folder where
> knowledge accumulates topic by topic, and a `workdir/` for files it makes. I'll ask what this
> agent owns before writing anything — that description is also how other agents decide when to call
> on it. **Then I'll register the agent, which writes its boot shortcut and adds it to this
> workspace's shared agent list** — the list is what tells anyone else here that the agent exists.
> Those two files land in your workspace uncommitted; `/lr:workspace-push` is what carries them to
> your teammates.

## Steps

1. **Determine the target repo.** If the user specified one, use it. If there's only one lore agent
   repo in the workspace (identified by `lore-repo.md` at the root), use that. If there are several,
   ask which one.

   **If there are none, stop and offer to create one.** An agent exists only inside an agent repo:
   with no `lore-repo.md` above it, discovery cannot find it and `/lr:boot` cannot load it, so an
   agent scaffolded anywhere else is invisible from the moment it is written. Say the workspace has
   no agent repo yet, and on the user's go-ahead run `<framework-root>/docs/create-repo.md`, then
   continue here with the repo it creates. Never scaffold the agent directory outside a repo.

2. **Get the agent name.** Kebab-case, descriptive (e.g., `code-reviewer`, `data-analyst`).

3. **Get a role description.** Ask what this agent owns or knows and when another agent should boot
   or attach it. The one-line frontmatter description is a routing aid for an unfamiliar agent, not
   merely a title. If sibling agents overlap, make the boundary clear. Use the role body for the
   fuller responsibilities and working method.

4. **Create the agent directory structure:**
   ```
   <lore-agent-repo>/agents/<agent-name>/
   ├── role.md              # Agent identity and responsibilities
   ├── lore-context.md      # Initial working knowledge (starts minimal)
   ├── lore/                # Knowledge topics (starts empty)
   └── workdir/             # Workspace for artifacts
   ```

5. **Write `role.md`** with YAML frontmatter and body. The frontmatter contains:
   - `description` — a one-line routing summary: scope/knowledge + when to boot or attach

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

8. **Register the agent.** Run the **Register Agent** procedure in
   `<framework-root>/docs/register-repo.md` with `<lore-agent-repo>` and `<agent-name>`. That
   procedure writes the engine-native shortcut *and* adds the agent to the workspace memory file's
   `## Agents` section — the "what can I boot here" list a teammate reads on arrival. Creating an
   agent and leaving it out of that list is the gap this step closes: it is bootable via
   `/lr:boot <agent-name>` but invisible to everyone who does not already know its name, and
   `/lr:workspace-status` reports it as finding S11.

   Skip this step only when the procedure that called this one says to — `docs/being.md` § Create
   agent and being does. Do not skip it on your own judgement, and do not ask the user whether to
   register: registration is how a created agent becomes visible, not an extra feature.

   Registration is the publishing step, not part of building the agent. If it stops without writing
   (a shortcut collision — see that doc's § Collision rule), the agent is still created: report it
   as created with its shortcut unwritten, never as a failed creation.

9. **Report** what was created, naming the shortcut from the Register Agent procedure's own report
   step, and note that the agent is also loadable via `/lr:boot <agent-name>`. If registration was
   skipped or stopped, say so plainly and name `/lr:register-agent <lore-agent-repo> <agent-name>`
   as the way to finish it.

   Registration leaves the shortcut and the memory-file edit uncommitted in the **workspace** repo,
   which is a different repo from the one holding the agent. Name `/lr:workspace-push` in the report
   whenever a shortcut was written, or the agent stays visible only on this machine — the failure
   this step exists to prevent.

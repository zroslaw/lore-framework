# Merge Process

Integrate reflection topics into the agent's existing lore.

## Execution model

Merge always runs in a subagent, one per active agent, with all subagents launched in parallel. This is uniform for single- and multi-agent sessions — a single-agent session just spawns one subagent. Running merge in a subagent keeps session noise out of merge decisions and gives a clean, focused context.

**Each subagent boots as the agent it is merging for**, using the standard boot procedure. Booting gives the subagent the agent's role, identity, and lore context naturally — the same pattern `/lr:consult` uses. After booting, the subagent runs the process below scoped to its own agent and returns a short summary to the host.

Host responsibilities when merge is invoked:

1. Collect active agents (host + any attached guests).
2. For each, spawn a **`general-purpose`** subagent (merge needs `Write`/`Edit`/`Bash`; `Explore` does not) with a brief such as: _"Boot as agent `<name>` (repo: `<path>`) per `${CLAUDE_PLUGIN_ROOT}/docs/agent-boot.md`, then run the merge procedure in `${CLAUDE_PLUGIN_ROOT}/docs/process-merge.md` scoped to yourself. Return a short summary of topics touched, role changes, and any anomalies. Do not commit — finalize handles that."_
3. In a multi-agent session, spawn all subagents in parallel (single message with multiple Agent tool calls).
4. Collect summaries and report per-agent success/failure to the user. **Retain each subagent's return** — phase 3 (summarize) uses it to compose guest summaries.

Each subagent's work is independent: separate `reflections/` directory, separate lore subtree. Merge does not commit — all changes are left uncommitted on disk. Committing is handled once, at the end of `/lr:finalize`, or by the user themselves if merge is invoked standalone.

If any subagent fails, the others still proceed.

## Inputs (per subagent)

- The agent's `lore-context.md` — current compacted knowledge
- The agent's `lore/` directory — existing lore topics
- The agent's `reflections/` directory — new reflection topics to integrate
- The agent's `role.md` — current role description

## Process

The steps below are what **each subagent** runs once booted as its target agent. The host does not run these steps inline — it orchestrates subagents per the Execution model above and aggregates their summaries.

### Step 1: Read Everything

Read all reflection topics, the current `lore-context.md`, and scan the existing `lore/` directory to understand what's already there.

### Step 2: Integrate Lore Topics

For each reflection topic, decide:

1. **Update an existing topic** — if the reflection adds to, refines, or corrects an existing lore topic, update that topic in place. This is the preferred approach.

2. **Create a new topic** — if the reflection covers something no existing topic addresses, create a new file in `lore/`. Lowercase kebab-case filename.

3. **Remove an obsolete topic** — if a reflection makes an existing topic fundamentally wrong (not just partially outdated), delete it. Git preserves history.

When updating or creating topics:
- Keep topics under 5000 tokens when possible. Split if too large.
- Topics can reference other topics by filename.
- Summary topics can link to clusters of related topics.
- Include operational recommendations where relevant.
- Only essential information — no filler.

### Step 3: Handle Role Updates

If any reflection topic has a `role-update-` prefix:
- Read the current `role.md`
- Integrate the role update into the body
- Keep `role.md` focused and concise
- Preserve the YAML frontmatter. Update the `description` field if the role change warrants a different one-line summary.

### Step 4: Update Lore Context

Update `lore-context.md` to reflect the new state of the agent's knowledge.

`lore-context.md` should contain:
- **Inline summarized knowledge** — general context, key facts the agent needs readily available
- **Topic summaries with references** — brief summary of a topic area + reference to the lore file by name

Prioritize recent and frequently relevant knowledge. Older or less critical knowledge should be more summarized or referenced only.

**Size budget**: keep `lore-context.md` under 50,000 tokens. If it exceeds this, compact by:
- Summarizing older entries more aggressively
- Replacing inline details with references to lore topics
- Removing information well-covered by lore topics

### Step 5: Cleanup

Delete the current agent's `reflections/` directory and all its contents.

Merge does not commit — leave all changes uncommitted on disk. In a multi-agent session, return a short summary of what was integrated (topics touched, role changes, any anomalies) to the host. Committing is handled at the end of `/lr:finalize`, or by the user directly if merge is invoked standalone.

## Guidelines

- **Preserve knowledge** — don't lose information during merging. If removing content from `lore-context.md`, make sure it exists in a lore topic.
- **Maintain the graph** — when creating new topics that relate to existing ones, add cross-references.
- **Be conservative with deletions** — only delete topics that are fundamentally wrong. Updating is almost always better.
- **Respect the agent's voice** — lore should read naturally as the agent's own knowledge, not as third-party documentation.
- **Shared topics** — the same topic may legitimately appear in multiple agents' lore if it matters to each of them. Don't try to consolidate into one agent's lore during merge; each agent owns its own copy for its own scope.

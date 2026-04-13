# Merge Process

Integrate reflection topics into the agent's existing lore.

## Single-agent and multi-agent sessions

If the session has only a host (no guests attached via `/lr:attach`), run this process once for the host. That is the default case.

If one or more guests are attached, **run this process once per active agent, sequentially, in host-first order** (host, then each guest in the order they were attached). Each iteration uses that agent's own `reflections/`, `lore/`, `lore-context.md`, and `role.md` only. Commit each agent's merge before moving to the next — scope each commit to that agent's subdirectory so history stays clean per agent.

Host goes first deliberately: the host's merge may capture decisions that guest iterations then reference. Each iteration is independent of the others in its inputs (each agent has its own `reflections/`) but sequential in execution.

## Inputs (per agent iteration)

- The agent's `lore-context.md` — current compacted knowledge
- The agent's `lore/` directory — existing lore topics
- The agent's `reflections/` directory — new reflection topics to integrate
- The agent's `role.md` — current role description

## Process

For a single-agent session, run the steps below once. For a multi-agent session, run the steps below once per active agent in host-first order, then announce overall completion.

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

### Step 6: Commit

Commit the changes with a descriptive message summarizing what was integrated. In a multi-agent session, scope the commit to the current agent's subdirectory (e.g., `agents/<agent-name>/`) so history remains clean per agent. Then, if there are more active agents to merge, move to the next one. When all active agents have merged, announce that the full merge step is complete.

## Guidelines

- **Preserve knowledge** — don't lose information during merging. If removing content from `lore-context.md`, make sure it exists in a lore topic.
- **Maintain the graph** — when creating new topics that relate to existing ones, add cross-references.
- **Be conservative with deletions** — only delete topics that are fundamentally wrong. Updating is almost always better.
- **Respect the agent's voice** — lore should read naturally as the agent's own knowledge, not as third-party documentation.
- **Shared topics** — the same topic may legitimately appear in multiple agents' lore if it matters to each of them. Don't try to consolidate into one agent's lore during merge; each agent owns its own copy for its own scope.

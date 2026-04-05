List all agents registered in this domain with their description and repo.

To produce this list:

1. Look at all files in `.claude/commands/` matching the pattern `lr-*-agent.md` — each file is a registered agent boot command. The filename encodes the agent name (e.g., `lr-lore-architect-agent.md` → agent `lore-architect`).
2. For each agent, read its boot command file to find which agent repo it belongs to (look for the path to `role.md`).
3. Read the agent's `role.md` to extract a one-line description of its purpose (first paragraph or the sentence immediately after the heading).
4. Output a table with columns: **Agent**, **Repo**, **Purpose**.

List all agent repos registered in this domain with their description and purpose.

To produce this list:

1. Look at all files in `.claude/commands/` matching the pattern `lr-*-agent.md` — each file belongs to a registered agent. The boot command file contains the path to the agent's `role.md`, which reveals the repo it lives in.
2. Collect the unique set of agent repos referenced across all boot commands.
3. For each repo, read its `README.md` (if present) or the first agent's `role.md` to extract a short description of the repo's purpose.
4. Output a table with columns: **Repo**, **Path**, **Purpose**.

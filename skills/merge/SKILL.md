---
description: "Integrate reflection topics into the agent's lore. Run after /lr:reflect."
---

Begin the merge process to integrate reflection topics into lore.

Read `${CLAUDE_PLUGIN_ROOT}/docs/process-merge.md` for detailed instructions. The doc explains single-agent and multi-agent (attached-guests) iteration — if guests are attached via `/lr:attach`, merge runs per active agent in host-first order, each scoped to its own directory and commit.

Integrate all reflection topics from each active agent's `reflections/` directory into that agent's `lore/`, `lore-context.md`, and `role.md` as appropriate.

When done, confirm what was integrated for each active agent and commit the changes.

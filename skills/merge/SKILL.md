---
description: "Integrate reflection topics into the agent's lore. Run after /lr:reflect."
---

Begin the merge process to integrate reflection topics into lore.

Read `${CLAUDE_PLUGIN_ROOT}/docs/process-merge.md` for detailed instructions. The doc explains the execution model — merge always runs in a subagent, one per active agent, in parallel. Each subagent boots as its target agent before running the merge procedure, giving it that agent's role and lore context naturally. Merge does not commit; committing happens at the end of `/lr:finalize`, or by the user directly if merge is invoked standalone.

Collect active agents (host + any guests attached via `/lr:attach`), spawn a subagent per agent with a brief to boot as that agent and then run the merge procedure, then aggregate the returned summaries.

When done, confirm what was integrated for each active agent.

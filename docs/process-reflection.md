# Reflection Process

This process is triggered by the user at the end of a session. You reflect on the current session and extract knowledge worth preserving.

## Single-agent and multi-agent sessions

If the session has only a host (no guests attached via `/lr:attach`), run this process once for the host. That is the default case.

If one or more guests are attached, **run this process once per active agent, sequentially, in host-first order** (host, then each guest in the order they were attached). Each iteration is scoped to one agent:

- Review the session through the lens of **that agent's** `role.md` + `lore-context.md` — these describe the agent's identity, responsibilities, and areas of concern, and define what "relevant to this agent" means.
- Extract only what matches that scope. Some session noise leaking into an iteration is acceptable — the role lens is a guide, not a strict filter.
- Shared topics are allowed: if something is genuinely relevant to multiple agents (a common workflow, a shared constraint), write it into each agent's `reflections/`. Duplication for legitimately shared knowledge beats each agent re-learning it separately.
- Write to that agent's `reflections/` directory only.
- Confirm completion for that agent and list the topics written, then move on to the next active agent.

The per-agent scope is what prevents a guest from accumulating lore that belongs to the host (or vice versa). Let each agent's role definition guide what it keeps.

## What to Extract

For each agent iteration, review the session and identify:

- **New knowledge** — things you learned about the domain, systems, codebase, or environment that are relevant to this agent's role
- **Operational lessons** — approaches that worked or didn't work within this agent's scope. If you tried something that failed and then found a better approach, capture that lesson
- **Decisions made** — choices and their reasoning, so you don't revisit settled questions
- **Recommendations** — practical guidance for future sessions (e.g., "when doing X, use Y approach because Z")
- **Role insights** — if the session revealed something about how this agent's role should be understood differently, capture that as a separate role-update topic

## How to Write Reflection Topics

Write each reflection topic as a plain markdown file in the current agent's `reflections/` directory (the agent whose iteration is running).

Rules:
- **One topic per file** — atomic, focused on a single concept or lesson
- **Filename**: lowercase kebab-case, descriptive (e.g., `api-retry-behavior.md`, `role-update-scope-change.md`)
- **Keep it compact** — only essential information, no filler or general knowledge
- **Be specific** — include concrete details, not vague observations
- **Include operational guidance** — if the knowledge implies a way of working, state it explicitly

Role update topics should be named with a `role-update-` prefix so the merge process can identify them.

## What NOT to Extract

- Things that are obvious from the code or documentation
- General knowledge that anyone could look up
- Temporary state that won't matter next session
- Verbatim conversation excerpts — distill the insight, don't copy the chat

## Example Reflection Topics

**`api-timeout-handling.md`**:
```
The billing API has a 30-second timeout but does not return a timeout
error — it returns a generic 500. When retrying billing calls, treat
any 500 after 25+ seconds as a likely timeout rather than a server error.
Retry with the same idempotency key.
```

**`role-update-deployment-ownership.md`**:
```
The team has decided that this agent should also handle deployment
verification after releases, not just the release process itself.
This includes checking health endpoints and monitoring error rates
for 15 minutes post-deploy.
```

## After Reflection

Once you have written all reflection topics for the current agent iteration, inform the user that reflection is complete for that agent and list the topics created. Then, if there are more active agents to reflect, move to the next one. When all active agents have reflected, announce that the full reflection step is complete.

The next step — merging reflections into lore — is a separate step triggered by `/lr:merge`. Merge also iterates per active agent in the same host-first order.

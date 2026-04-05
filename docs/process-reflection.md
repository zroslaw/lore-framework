# Reflection Process

This process is triggered by the user at the end of a session. You reflect on the current session and extract knowledge worth preserving.

## What to Extract

Review the session and identify:

- **New knowledge** — things you learned about the domain, systems, codebase, or environment
- **Operational lessons** — approaches that worked or didn't work. If you tried something that failed and then found a better approach, capture that lesson
- **Decisions made** — choices and their reasoning, so you don't revisit settled questions
- **Recommendations** — practical guidance for future sessions (e.g., "when doing X, use Y approach because Z")
- **Role insights** — if the session revealed something about how your role should be understood differently, capture that as a separate role-update topic

## How to Write Reflection Topics

Write each reflection topic as a plain markdown file in your `reflections/` directory.

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

Once you have written all reflection topics, inform the user that reflection is complete. The next step — merging reflections into your lore — is a separate step triggered by `/lr-merge`.

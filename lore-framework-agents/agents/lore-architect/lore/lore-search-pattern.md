Starting with v3, the preferred way to search lore is a subagent scan, not direct grep/read. Full instructions and a worked example in framework doc `docs/lore-search.md`.

## Why subagent scan, not vector search

At small lore sizes (< ~100 topics), LLM-driven reading produces stronger semantic matches than embedding similarity — with no infrastructure. Chroma-backed search is parked in `vector-db-search-parked.md` for when this changes.

## Search brief structure (4 parts)

When dispatching the Explore subagent:
1. **Task** — 1-2 sentences on what you're actively working on
2. **Session context** — 2-5 bullets (decisions made, paths/files involved, open questions)
3. **Angle** — what kind of lore would help (prior decisions, lessons, pitfalls, domain facts). Include any user hint from `/lr:recall`.
4. **Output shape** — compact synthesis ≤400 words, topic filenames, explicit call-outs for topics worth reading in full; "nothing relevant" if true

Keep the brief ≤300 words.

## When to use direct tools instead

Use Glob/Grep/Read when searching by name or exact term. Use `git log --diff-filter=A -- lore/<topic>.md` to find when a topic was created. Deleted topics remain in git history.

## User-triggered entry point

`/lr:recall [hint]` is the user-invocable version of the same mechanism. Show the synthesis to the user (transparency), then carry it as working context for the session.

## Fan-out with attached guests (v4+)

When guests are attached via `/lr:attach`, recall and agent-initiated lore search run across **all active agents** (host + guests). Dispatch one `Explore` subagent per active agent **in parallel** (single message, multiple Agent calls — no dependencies between them). Each subagent scans one agent's `lore/` directory with the same brief, plus a line identifying which agent it is.

Present the synthesis grouped by agent so the user can see whose lore each finding came from.

With no guests, this reduces to a single subagent — identical to the v3 single-agent case. See `attach-pattern.md`.

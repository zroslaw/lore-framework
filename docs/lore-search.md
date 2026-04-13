# Searching Your Lore

Read this when you need to find or recall topics from your lore. Covers both the agent-initiated case (you decide you need lore) and the user-triggered case (`/lr:recall`). Also covers the multi-agent case when guests are attached to the host session.

## Preferred Mechanism: Subagent Scan

For any non-trivial search, **dispatch an `Explore` subagent** with a structured search brief. The subagent reads relevant lore topics directly, synthesizes findings, and returns a compact result. This keeps your main context clean and uses the LLM's own semantic understanding — stronger than keyword matching for finding topics by *meaning* rather than by *exact term*.

Why a subagent:
- Reading 10–100 topic files in your main context wastes tokens you need for the user's task
- The synthesis can be inlined cheaply (a few hundred words)
- `Explore` is fast and tool-restricted (Read/Grep/Glob, no edit/agent tools) — exactly what's needed for a search

## Active Agents: Fan Out When Guests Are Attached

If guests are attached to the host session (via `/lr:attach`), the search runs across **all active agents' lore directories** — host + every attached guest. Execute this by dispatching **one `Explore` subagent per active agent in parallel** (all subagent calls in a single message), each scoped to one agent's `lore/` directory.

Each subagent receives the same brief but is told which agent's lore to scan. Each returns its own compact synthesis. The host merges the results for the user, grouped by agent so it's clear whose lore each finding came from.

When there are no guests, the fan-out reduces to a single subagent — behavior is identical to the single-agent case. You don't need to branch your procedure; just enumerate the active agents (host plus any attached guests) and dispatch N subagents.

**Why parallel, not serial:** each subagent runs independently and there are no dependencies between them. Single-message parallel dispatch is both faster and the standard pattern for independent subagent work.

## How to Prepare a Search Brief

The quality of what comes back depends entirely on the brief. A good brief has four parts:

### 1. The Task — One or Two Sentences

What you're actively working on. Be concrete:

- Good: *"Refactoring the framework update process to support a release-notes track alongside migrations."*
- Bad: *"Working on framework stuff."*

### 2. Session Context That Shapes Relevance

Two to five bullets covering decisions made, constraints surfaced, paths or filenames being touched, open questions. This is what lets the subagent distinguish *relevant* from *generally related*.

### 3. The Angle — If You Have One

If the user provided a hint (`/lr:recall anything about versioning`), center the brief on it.

If not, describe the *kind* of lore that would help — prior decisions, operational lessons, domain facts, known pitfalls, past trade-offs. This anchors the subagent's reading.

### 4. The Output Shape You Want Back

Ask explicitly for:
- A compact synthesis (under ~400 words) grouped by theme
- Each finding tagged with its source topic filename
- Explicit call-outs for topics worth reading in full yourself
- *"Nothing relevant found"* if that's the honest answer — don't invent relevance

Keep the whole brief under ~300 words. The subagent has access to your full `lore/` directory; you don't need to summarize what's *in* lore, only what's in *this session*.

## Worked Example

**Brief sent to the subagent:**

> Search the lore at `agents/lore-architect/lore/` for topics relevant to my current task.
>
> **Task:** Designing a `/lr:recall` skill that lets the user explicitly trigger a lore search mid-session. The synthesis is inlined into the main agent's working context.
>
> **Session context:**
> - Decided against introducing a vector DB at current scale — using LLM-driven subagent scan instead
> - Framework bumping to v3 with new search guidance and a recall skill
> - Keeping `agent-boot.md` compact — detailed search guidance lives in a separate doc
> - Following the existing skill/doc separation pattern
>
> **Looking for:** prior decisions on user-invocable skills, transparency patterns (showing intermediate results to the user), past discussion of subagent usage in the framework.
>
> **Output:** compact synthesis grouped by theme, ≤400 words, with topic filenames. Flag anything I should read in full. Say "nothing relevant" if true.

**Expected response shape:**

> **User-invocable skill conventions** (`slash-command-system.md`): all user-invocable skills use the `/lr:` prefix; generated artifacts use `/lr-`. Skill files are thin pointers; logic lives in `docs/`.
>
> **Skill/doc separation** (`skill-doc-pattern.md`): every skill is one line pointing at `${CLAUDE_PLUGIN_ROOT}/docs/<name>.md`. Recall should follow this exactly.
>
> **No prior recall pattern** — no existing topic discusses user-triggered context enrichment. New ground.
>
> **Read in full:** `slash-command-system.md` for the conventions you'll be following.

## What to Do With the Result

1. **Show the synthesis to the user.** Transparency — they should see what got pulled in and judge whether the recall was useful. If multiple active agents were scanned (fan-out), group results by agent so it's clear whose lore each finding came from.
2. **Carry it as working context** for the rest of the session.
3. **Read flagged topics in full yourself** — don't trust synthesis alone for load-bearing details.

## Direct-Tool Fallback

When you know exactly what you're looking for or just need a quick check, the standard tools are fine — no subagent needed:

- **Glob / list** — see what topics exist
- **Grep** — search for a specific keyword across topics
- **Read** — read a specific topic in full
- **`git log`** — when a topic was created (`git log --diff-filter=A -- lore/<topic>.md`), last updated (`git log -1 -- lore/<topic>.md`), or full history (`git log --follow -- lore/<topic>.md`)
- **Deleted topics** remain in git history — searchable if you need past knowledge that was later removed

Rule of thumb: use the subagent when you're searching by **meaning**; use direct tools when you're searching by **name** or **exact term**.

# Autonomous Lore Agents — Vision

Active design exploration (parked, not decided). User-articulated vision (2026-04-26): lore agents should evolve into **autonomous background agents**. The shape:

- Agents run continuously in the background, not only when the user is interacting with them.
- The user kicks off an agent with a task; the agent works on it independently across time.
- Agents only **raise for user input** when they hit a decision they cannot make alone, encounter a question worth clarifying, or need confirmation. The act of raising is also a learning event — the answer feeds back into lore.
- The user sees a **status surface**: which agents are running, which are waiting on input, which are idle, which are done.

This re-frames lore agents from "session-bound knowledge workers the user converses with" to "always-on collaborators with persistent state, asking for help when needed."

## Why this matters for the framework

This is a **major architectural direction**, not a minor feature. It implies:

- **Process model:** agents need a daemonization story — currently each lore agent is just a Claude Code session the user boots interactively. Autonomous agents need to keep running across user disconnects.
- **State model:** lore already gives persistent knowledge across sessions; autonomous mode needs persistent **task state** across long-running work, not just knowledge.
- **Communication model:** the framework needs structured "agent → user" channels (notifications, statuses, request-for-input prompts) that don't exist today. Today the only channel is the user reading the chat.
- **Reflection model:** when an agent learns something *from* a clarification it requested, that learning needs to flow back into lore without a human-driven `/lr:finalize`. Either reflection needs to be triggerable autonomously, or finalize semantics need to broaden.
- **Multi-agent surface:** with N agents running in parallel, the user needs a switchboard — the cross-agent collaboration mechanisms (`/lr:recall`, `/lr:consult`, `/lr:attach`) were designed for one-host-at-a-time. Autonomous mode breaks that assumption.

## Status

Parked exploration. Substrate findings (tools, APIs, protocols) captured separately in `autonomous-agents-substrate.md`. No design doc yet.

**Concrete first step taken (v10):** `/lr:spawn-teammate` uses Claude Code's Agent Teams feature as the initial multi-agent substrate. The user framing: "I'll use that command for some time and check how it fits our needs." The custom tmux/iTerm2 substrate is parked but remains valid if Agent Teams proves insufficient. See `spawn-teammate-feature.md` and `autonomous-agents-substrate.md`.

Likely to compose well with:
- **Workdir-as-reference-library** (parked) — autonomous agents will accumulate workdir artifacts heavily. See `workdir-as-reference-library.md`.
- **Attach pattern** (v4+) — sustained co-work across agents is even more valuable when agents are long-lived. See `attach-pattern.md`.

## Open questions

- Where does an autonomous agent live? Inside an iTerm2 session backed by tmux? A headless `claude` invocation under `launchd`? A cloud runner?
- How does the framework express "this agent is autonomous" vs "this agent is interactive only"? Per-agent flag in `role.md` frontmatter? Per-invocation?
- How does a user **adopt** a running autonomous agent into their interactive session — is that just `/lr:attach` extended, or a new `/lr:resume`?
- Concurrency: can two user sessions interact with the same autonomous agent simultaneously? How do lore writes serialize?
- Cost / loop safety: an autonomous agent that loops can burn through API budget silently. Need budget caps and a kill switch.
- Does this require Anthropic's hosted "Managed Agents" / Claude Agent SDK as the runtime, or is local Claude Code the substrate?

## See Also

- `autonomous-agents-substrate.md` — concrete substrate findings (tmux, iTerm2 Python API, Claude Code hooks, escape sequences, switchboard daemon, security boundaries)
- `workdir-as-reference-library.md` — another parked exploration; composes with this direction
- `attach-pattern.md` — current cross-agent collaboration mechanism that autonomous mode will need to extend
- `framework-improvements-backlog.md` — running backlog where this direction is tracked

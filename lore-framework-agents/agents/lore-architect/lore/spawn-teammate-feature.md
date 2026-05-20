# `/lr:spawn-teammate` — Feature (v10, BETA)

Added in v10. Spawns one or more lore agents as Claude Code Agent Teams teammates. The current session becomes the team lead.

## Implementation files

- `skills/spawn-teammate/SKILL.md` — thin one-line pointer (standard skill pattern)
- `docs/spawn-teammate.md` — 8-step procedure
- `release-notes/10.md` — release notes (release-notes-only bump, no migration)
- `VERSION` bumped 9 → 10
- `README.md` — skills table row added with **BETA** marking

## Design decisions

**Spawn prompt format** — always uses `agent-boot.md` directly with absolute agent-dir path. No fallback to `/lr-<name>-agent` shortcut commands (user specified this). Format (post-v10 in-band BETA refinement):
```
Read ${CLAUDE_PLUGIN_ROOT}/docs/agent-boot.md and boot as agent <name> from <abs-path>.

You were spawned primarily as a parallel session for the user to work with you directly. After boot, wait for the user's instructions in this session and respond to them here — not via SendMessage. Use SendMessage to the team lead or other teammates only when the user explicitly asks you to share or coordinate something.
```
`${CLAUDE_PLUGIN_ROOT}` is left literal — the teammate's session resolves it at boot time (teammates load skills from project/user settings per Agent Teams docs).

The post-boot paragraph does two things: it stops the teammate after the boot procedure's "Confirm" step (rather than letting it invent a task), and it frames **the user — in the teammate's own session — as the primary interlocutor**. SendMessage is reserved for explicit user-requested coordination. This is a design **invariant** of spawn-teammate, not a procedural detail.

**Why the reframe** — the v10 initial release used "After boot, await further instructions from the team lead via SendMessage." Real-world usage report: when the user worked directly with a spawned teammate (Shift+Down into its pane in in-process mode, or click into its pane in split-pane mode), the teammate kept defaulting to *reporting progress back to the team lead via SendMessage* instead of responding in its own session. The dominant usage pattern is the inverse — users spawn a teammate to drive it directly from its pane as a parallel session; cross-agent messaging is the exception. The reframe aligns the teammate's default with that dominant pattern. Boot-time stop behavior was preserved unchanged.

**Refinement workflow** — this change was made in-band on the BETA feature: edit `docs/spawn-teammate.md`, leave `release-notes/10.md` historical (it documents the v10 initial release), no `VERSION` bump. The BETA caveat in the release notes ("internal procedure and presentation may evolve based on real-world usage") is the contract that licenses post-release evolution without ceremony. See `versioning-release-types.md` for the general pattern.

**Operational lesson** — for BETA features, the spawn prompt / first-message framing is a high-leverage place to fix default-behavior divergence. A small wording change there reshapes every future session of that feature. When real-usage reports surface unexpected default behavior, look at the prompt before considering procedural changes.

**Why no subagent-definition mode** — Agent Teams docs confirm `skills` and `mcpServers` fields of a subagent definition are NOT applied to teammates. Using natural-language spawn directives (verbatim name+prompt) is the correct path for now. If this changes in a future Agent Teams version, subagent-definition mode would be preferable (more explicit, type-checked) — track.

**Invocation layer** — the skill composes a single natural-language directive to Agent Teams asking it to create-or-extend the team with exact names and verbatim spawn prompts. Agent Teams owns the spawn lifecycle; the skill does not poll afterward.

**Context inference for zero-arg case** — three branches: clear signal (1–3 agents directly named/implied → proceed with explanation), ambiguous (multiple plausible readings → ask user), no signal (list available + stop).

**Fuzzy matching** — Levenshtein ≤2 with no near-tie, plus prefix/substring bonus. Always report resolutions to user.

## Beta rationale

- Agent Teams itself is experimental; its contract may evolve.
- Lore writes by concurrent teammates are last-write-wins (no serialization). Mitigation: defer lore-changing work to finalization.
- Finalization across teammates is not automated — each teammate runs its own `/lr:finalize`.

## Open questions for beta graduation

1. **Lore-write serialization** — last-write-wins is the current state. Is a serialization mechanism (file locks, queued merges) needed, or is deferring lore-changing work to finalization sufficient?
2. **Automated finalization across teammates** — currently each teammate finalizes manually. Could the lead trigger finalization on all teammates before disbanding via Agent Teams SendMessage?
3. **Hook integration** — `Stop` and `Notification` hooks might automate teammate finalization. Explore whether hooks fire in teammate sessions the same way as regular sessions.
4. **Subagent-definition mode** — track whether Agent Teams adds skills/mcpServers support for subagent-definition mode in a future version.
5. **`/lr:check` validators** — add checks for spawn-teammate-related state (Agent Teams enabled, teammate boot paths valid). Deferred until usage shows what to check.
6. **Consistency review of `/lr:finalize` multi-teammate behavior** — finalize and summarize docs were designed for host+attached-guest model. Do they compose correctly with Agent Teams' separate teammate sessions, or need adjustments?
7. **User-primary-interlocutor framing** — should this be locked as a graduation invariant in stable releases, or remain tunable? Currently treated as an invariant in BETA based on observed dominant usage pattern.

## See Also

- `autonomous-agents-vision.md` — wider vision this feature advances
- `autonomous-agents-substrate.md` — original custom substrate (tmux/iTerm2) this is replacing experimentally
- `attach-pattern.md` — in-session guest model; different from Agent Teams teammates
- `slash-command-system.md` — skill listing context
- `framework-improvements-backlog.md` — beta graduation questions tracked there

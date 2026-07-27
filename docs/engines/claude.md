# Engine Profile — Claude Code (reference)

Selected by boot (`agent-boot.md` Step 0) when `<framework-root>` lives under a Claude plugin
dir (`~/.claude/plugins/…`) or the session was started with `--plugin-dir`. This is the
**reference profile**: every other engine profile fills the same five bindings; only the values
differ.

## Binding values

| Binding | Value on Claude Code |
|---|---|
| **framework-root** | Self-locate (Step 0). `${CLAUDE_PLUGIN_ROOT}` also expands to it and may be used as a literal-path fallback. |
| **invocation-syntax** | Skills are user-invoked as slash commands `/lr:<skill>`; the engine expands them. Canonical skill folders live under `skills/<skill>/`. Per-agent boot shortcuts `/lr-<agent>-agent`. |
| **subagent-spawn** | The `Agent` tool. Fan-out = **N parallel `Agent` calls in a single message**. Sub-agent types: `general-purpose` (write), `Explore` (read-only, but excerpt-based — it locates material rather than reviewing it in depth), and `fork` (**inherits the caller's full conversation context**). Each subagent boots as its target agent and reads the procedure doc itself. Two traps: (1) `fork` is unsuitable wherever a subagent must be *independent* of the caller's reasoning — it carries the caller's context by design; (2) passing a **`name`** makes the call an Agent-Teams teammate, and **a teammate does not auto-return its final report to the caller** — only an unnamed call does. Spawn unnamed when you need the result back, or instruct a named teammate to `SendMessage` its report before going idle. |
| **memory-file** | `CLAUDE.md`. |
| **runtime-bounding** | The Bash-tool `timeout` parameter bounds a command's runtime. |

## Capability gates

- **teammate-detection** — supported. `lr-core preflight` walks up to six process ancestors,
  reading each one's args with a single-field `ps -o args= -p <pid>` call and matching `--agent-id`
  on a flag boundary (so `--agent-idle-timeout` does not false-positive); the engine is often the
  grandparent rather than the immediate parent. Agent-Teams / `spawn-teammate` features are
  available.

## Notes

- This profile documents the historical default. The framework was authored on Claude Code, so
  the shared procedure docs describe the Claude mechanism directly; other profiles state where
  they diverge and win on conflict (`agent-boot.md` Step 0).

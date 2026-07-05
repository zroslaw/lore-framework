# Engine Profile — Claude Code (reference)

Selected by boot (`agent-boot.md` Step 0) when `<framework-root>` lives under a Claude plugin
dir (`~/.claude/plugins/…`) or the session was started with `--plugin-dir`. This is the
**reference profile**: every other engine profile fills the same five bindings; only the values
differ.

## Binding values

| Binding | Value on Claude Code |
|---|---|
| **framework-root** | Self-locate (Step 0). `${CLAUDE_PLUGIN_ROOT}` also expands to it and may be used as a literal-path fallback. |
| **invocation-syntax** | Skills are user-invoked as slash commands `/lr:<skill>`; the engine expands them. Per-agent boot shortcuts `/lr-<agent>-agent`. |
| **subagent-spawn** | The `Agent` tool. Fan-out = **N parallel `Agent` calls in a single message**. Sub-agent types: `general-purpose` (write), `Explore` (read-only). Each subagent boots as its target agent and reads the procedure doc itself. |
| **memory-file** | `CLAUDE.md`. |
| **runtime-bounding** | The Bash-tool `timeout` parameter bounds a command's runtime. |

## Capability gates

- **teammate-detection** — supported. `ps -o args= -p $PPID` reads the parent args for
  `--agent-id`; Agent-Teams / `spawn-teammate` features are available.

## Notes

- This profile documents the historical default. The framework was authored on Claude Code, so
  the shared procedure docs describe the Claude mechanism directly; other profiles state where
  they diverge and win on conflict (`agent-boot.md` Step 0).

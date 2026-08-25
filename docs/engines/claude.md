# Engine Profile — Claude Code (reference)

Selected by `lr-core`'s `detect_engine` (reported as `data.engine` by preflight, consumed at
`agent-boot.md` Step 2) when `CLAUDE_PLUGIN_ROOT` is set, when a `claude` process appears in this
session's ancestry, or when `<framework-root>` lives under `~/.claude/plugins/…`. Also the
**fallback** when no signal identifies the engine, in which case `data.engine.confidence` is
`assumed` rather than `confident`. This is the **reference profile**: every other engine profile
fills the same five bindings; only the values differ.

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

## Project-scope plugin settings

A workspace's committed `.claude/settings.json` can carry `extraKnownMarketplaces` plus
`enabledPlugins`, which makes `lr` available to anyone who clones it — written by `workspace-init`
(v43), reported as finding S18 when absent.

**The trap: `extraKnownMarketplaces` applies only after the teammate trusts the folder.** Until
they do, Claude Code does not load plugins from a marketplace the project file declares, and the
symptom is indistinguishable from the file being absent. Check trust before diagnosing anything
else. Nothing here hot-reloads either: the plugin appears in the next session, not this one.

## Registered shortcut bootstrap

When `/lr:register-agent` or `/lr:register-repo` emits a Claude per-agent shortcut, use this
exact body after substituting the agent values — **as a single unwrapped line** (see
`register-repo.md` § Resolve the shortcut bootstrap for why):

```markdown
Read the `SKILL.md` for the installed `/lr:boot` skill available in this session. Follow its self-location instruction to resolve `<framework-root>`, then read its `docs/agent-boot.md` and boot as agent `<agent-name>` from `<agent-dir>`.
```

Do not substitute `${CLAUDE_PLUGIN_ROOT}`, an absolute plugin path, or a workspace checkout into
the shortcut. If the active boot skill is unavailable, follow this profile's normal fallback at the
point of use; generated shortcuts do not implement a second resolver.

## Notes

- This profile documents the historical default. The framework was authored on Claude Code, so
  the shared procedure docs describe the Claude mechanism directly; other profiles state where
  they diverge and win on conflict (`agent-boot.md` Step 2).

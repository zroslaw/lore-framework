# Stale Shortcut Bootstrap

## Symptoms

- A registered per-agent shortcut cannot read `agent-boot.md` after a framework or plugin upgrade.
- The shortcut contains `plugins/cache/` or an absolute path ending in `docs/agent-boot.md`.
- Booting the same agent through the normal boot skill works, but the direct shortcut does not.

## Diagnosis

Inspect the engine-native shortcut artifact:

- Claude Code: `<workspace>/.claude/commands/lr-<agent-name>-agent.md`
- Cursor: `<workspace>/.cursor/skills/lr-<agent-name>-agent/SKILL.md`
- Codex: `~/.codex/skills/lr-<agent-name>-agent/SKILL.md`

The current format names the session's installed boot skill and keeps only the agent name and
absolute agent directory. A versioned cache path or absolute `agent-boot.md` path identifies this
ailment.

## Remedy

Regenerate the shortcut using the currently installed framework:

```text
/lr:register-agent <lore-agent-repo> <agent-name>
```

Or regenerate every shortcut in the repo:

```text
/lr:register-repo <lore-agent-repo>
```

On Codex, use the equivalent native skill invocation. Registration rewrites only a shortcut that
already belongs to the same agent directory; it preserves the collision protection for another
repo's agent with the same name.

## Prevention

Generated shortcuts delegate to the active boot skill and must never contain a plugin-cache path
or absolute `agent-boot.md` path. `/lr:check` detects the obsolete forms.

## See Also

- `docs/register-repo.md` — canonical registration templates.
- `docs/check.md` — static shortcut-format check.
- `docs/doctor-stale-plugin-cache.md` — different issue: stale plugin content rather than a stale
  shortcut path.

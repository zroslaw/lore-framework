# Stale Shortcut Bootstrap

## Symptoms

- A registered per-agent shortcut cannot read `agent-boot.md` after a framework or plugin upgrade.
- The shortcut contains `plugins/cache/` or an absolute path ending in `docs/agent-boot.md`.
- Booting the same agent through the normal boot skill works, but the direct shortcut does not.

## Diagnosis

Inspect the engine-native shortcut artifact:

- Claude Code: `<workspace>/.claude/commands/lr-<agent-name>-agent.md`
- Cursor: `<workspace>/.cursor/skills/lr-<agent-name>-agent/SKILL.md`
- Codex: `<workspace>/.codex/skills/lr-<agent-name>-agent/SKILL.md`, and
  `~/.codex/skills/lr-<agent-name>-agent/SKILL.md` for a shortcut registered before v37 (Codex loads
  both, so inspect both — a stale home copy keeps failing while a fresh workspace copy exists)

The current format names the session's installed boot skill and keeps only the agent name and
absolute agent directory. A versioned cache path or absolute `agent-boot.md` path identifies this
ailment.

## Remedy

On framework v33 or later, use the normal engine-specific boot or update entry once: Claude Code
`/lr:boot` or `/lr:update`; Cursor `/lr-boot` or `/lr-update`; Codex's installed `$lr:boot` or
`$lr:update` skill through its native skill mechanism. Migration 33 refreshes a clean legacy
shortcut automatically when its agent path proves it belongs to the repo being upgraded. Registered
shortcuts are framework-owned artifacts, so customization is replaced. A broken direct shortcut
cannot repair itself, so use the normal entry point for that first upgrade.

To repair it immediately, regenerate it using the currently installed framework:

Use the equivalent native registration skill for your engine: Claude Code
`/lr:register-agent`, Cursor `/lr-register-agent`, or Codex's installed `$lr:register-agent` skill.

Or regenerate every shortcut in the repo:

For every shortcut in a repo, use the equivalent `register-repo` skill instead.

On Codex, use the equivalent native skill invocation. Registration rewrites only a shortcut that
already belongs to the same agent directory; it preserves the collision protection for another
repo's agent with the same name.

## Prevention

Generated shortcuts delegate to the active boot skill and must never contain a plugin-cache path
or absolute `agent-boot.md` path. `/lr:check` detects the obsolete forms; migration 33 regenerates
owned shortcuts and preserves only collisions or unrecognised artifacts.

## See Also

- `docs/register-repo.md` — canonical registration templates.
- `docs/check.md` — static shortcut-format check.
- `docs/doctor-stale-plugin-cache.md` — different issue: stale plugin content rather than a stale
  shortcut path.

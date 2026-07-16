# Install Lore Framework on Claude Code

This is the canonical Claude Code install and refresh guide for Lore Framework.

If a Claude Code agent is asked to install Lore from GitHub, point it at this file and have it follow
the commands here directly.

## For the AI agent reading this

If a user asked you to set up Lore Framework and you are running in **Claude Code**, you are the
installer. Run the install yourself, explaining each step. Before you add a marketplace, install a
plugin, or delete a cache directory, tell the user what you're about to do and get their go-ahead —
these change global Claude Code state, not just this workspace. After install, some skills only
appear in a **fresh session**; if a skill you expect is missing, that's usually the cache, not a
failed install (see § Refresh and § Version mismatch below). When the plugin is loaded, hand the
user into [FIRST-STEPS.md](FIRST-STEPS.md).

## Normal team install (Git marketplace)

Use this for teammates and customers who should track the published `lore-framework` repo:

```bash
claude plugin marketplace add zroslaw/lore-framework
claude plugin install lr@lore-framework
```

The `lr` skills (`/lr:boot`, `/lr:workspace-init`, `/lr:finalize`, …) become available. If they
don't appear immediately, start a fresh Claude Code session.

If you want direct per-agent boot shortcuts, use `/lr:register-agent` or `/lr:register-repo` after
the plugin is loaded. Those shortcuts are workspace-local commands under `.claude/commands/`.

## Local development install (local checkout)

Use this when the plugin source is a local checkout on disk — the fastest loop for working on the
framework itself:

```bash
claude --plugin-dir ./lore-framework
```

Run this from the workspace root (the directory that contains your `lore-framework/` checkout). The
plugin loads directly from disk with no marketplace or cache involved, so edits to the checkout take
effect in the next session.

## Refresh after the framework updates

The marketplace install caches the plugin tree under `~/.claude/plugins/`. After the upstream repo
moves forward, re-resolve it:

```bash
claude plugin marketplace add zroslaw/lore-framework
claude plugin install lr@lore-framework
```

Then start a fresh session. A refresh done mid-session affects future sessions, not the one already
running.

If skills still reflect the old version after that — a new skill is missing, or a renamed skill
still shows its old name — the running session is loading a **stale plugin cache**. Run `/lr:doctor`
(it diagnoses and heals this), or clear the cache directly:

```bash
rm -rf ~/.claude/plugins/cache/lore-framework/
```

This is destructive — confirm with the user first — and only removes the locally cached copy, which
Claude Code repopulates from the marketplace on the next session. Then **exit and start a fresh
session**; the old skill list is held in memory until you do. See
`docs/doctor-stale-plugin-cache.md` for the full diagnosis and remedy.

## Optional Claude Code configuration

Lore's normal git-backed lifecycle (boot auto-pull, `/lr:finalize` commit + push) needs the same
things any git workflow does: network access to reach your remotes, and normal filesystem
permissions in the workspace. Claude Code grants these through its usual permission model — there is
no Lore-specific configuration to set.

## Per-agent boot shortcuts

After the plugin is loaded, register workspace-local shortcuts:

```
/lr:register-agent my-agents researcher
/lr:register-repo my-agents
```

These create `.claude/commands/lr-<agent>-agent.md` files that boot the agent directly (e.g.
`/lr-researcher-agent`). They delegate to the framework's boot procedure with an absolute agent path.

## Version mismatch symptom

If boot says your agent repo is stamped at a version newer than the installed framework, the usual
cause is that the repo moved forward but the installed Claude Code plugin did not — or the running
session holds a stale cache. Refresh the plugin using the commands above, clear the cache if needed,
start a fresh session, then boot again. See `docs/version-check.md` and
`docs/doctor-stale-plugin-cache.md`.

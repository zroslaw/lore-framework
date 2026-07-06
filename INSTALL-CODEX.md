# Install Lore Framework on Codex

This is the canonical Codex install and refresh guide for Lore Framework.

If a Codex agent is asked to install Lore from GitHub, point it at this file and have it follow the
commands here directly.

## Normal Team Install (Git marketplace)

Use this for teammates and customers who should track the published `lore-framework` repo:

```bash
codex plugin marketplace add zroslaw/lore-framework
codex plugin add lr@lore-framework
```

Then restart Codex so new sessions load the plugin.

## Local Development Install (local checkout)

Use this when the plugin source is a local checkout on disk:

```bash
codex plugin marketplace add /absolute/path/to/lore-framework
codex plugin add lr@lore-framework
```

Then restart Codex so new sessions load the plugin.

## Refresh After the Framework Updates

Codex installs plugins persistently under `~/.codex/plugins/cache/...`. Refreshing the plugin is a
separate step from updating the repo or marketplace source.

On the verified Codex builds used for this port, the refresh path is `codex plugin add
lr@lore-framework`; there is no separate `codex plugin update` subcommand.

### If the marketplace is Git-backed

```bash
codex plugin marketplace upgrade lore-framework
codex plugin add lr@lore-framework
```

### If the marketplace is a local source

```bash
codex plugin add lr@lore-framework
```

If the installed version still does not move forward, use the fallback reinstall:

```bash
codex plugin remove lr@lore-framework
codex plugin add lr@lore-framework
```

Then restart Codex. A refresh done mid-session affects future sessions, not the one that is already
running.

## Team Automation

For a near-zero-headache team setup, run the refresh path before launching Codex:

```bash
codex plugin marketplace upgrade lore-framework || true
codex plugin add lr@lore-framework
codex
```

For a local-source marketplace, the middle line is enough:

```bash
codex plugin add lr@lore-framework
codex
```

The helper script [`scripts/codex-refresh-plugin`](scripts/codex-refresh-plugin) wraps this refresh
sequence.

## Optional Codex Configuration

If you want Lore's normal git-backed lifecycle on Codex:

- Enable network so boot auto-pull and push can reach remotes.
- Make repo `.git` directories writable if you want `/lr:finalize` to commit automatically.

The plugin cannot widen Codex's sandbox on its own; those settings come from how Codex is launched
or configured.

## Version Mismatch Symptom

If boot says your agent repo is stamped at a version newer than the installed framework, the usual
cause is that the repo or marketplace moved forward but the installed Codex plugin did not. Refresh
the plugin using the commands above, restart Codex, then boot again.

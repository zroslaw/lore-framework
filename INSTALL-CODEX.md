# Install Lore Agents on Codex

This is the canonical Codex install and refresh guide for Lore Agents.

If a Codex agent is asked to install Lore from GitHub, point it at this file and have it follow the
commands here directly.

## For the AI agent reading this

If a user asked you to set up Lore Agents and you are running in **Codex**, you are the installer.
Run the install yourself, explaining each step. Before you add a marketplace or add a plugin, tell
the user what you're about to do and get their go-ahead — and warn them that **Codex must be
restarted** before new sessions load the plugin. You can't restart Codex yourself, so ask the user to
exit and start a new session, then resume. Also note: **you can't invoke `$lr-<skill>` yourself** — in
`codex exec` it falls through to the shell and fails; when you need a skill's behavior, read
`skills/<skill>/SKILL.md` under the framework root (it names the correct procedure doc — don't guess
the doc filename from the skill name) and follow that, or have the user run the command. If the
user wants automatic commits at `/lr:finalize`, that needs a writable `.git` and network, which come
from how Codex is launched, not from the plugin (see § Optional Codex configuration). When the plugin
is loaded, ask whether the user is joining a team that already uses Lore Agents or starting fresh —
for joining, point them to
[QUICKSTART.md § After install](QUICKSTART.md#after-install-pick-your-path); for starting fresh,
hand them into [FIRST-STEPS.md](FIRST-STEPS.md).

Lore ships **native Codex packaging** — a `.codex-plugin/plugin.json` manifest and a
`.agents/plugins/marketplace.json` marketplace file — so Codex loads it through its own supported
manifest path and presents it (display name, logo, category) in the `/plugins` browser. The install
commands below are unchanged; a repo checkout without these files still installs via the legacy
`.claude-plugin/marketplace.json` fallback, but the native packaging is preferred when present.

## Normal team install (git marketplace)

Use this for teammates and customers who should track the published `lore-framework` repo:

```bash
codex plugin marketplace add zroslaw/lore-framework
codex plugin add lr@lore-framework
```

Then restart Codex so new sessions load the plugin.

If you want direct per-agent boot shortcuts, ask the user to run `$lr-register-agent` or
`$lr-register-repo` after the plugin is loaded — as an agent you cannot invoke these yourself (see
above). Those shortcuts are personal skills under `~/.codex/skills/`.

## Local development install (local checkout)

Use this when the plugin source is a local checkout on disk:

```bash
codex plugin marketplace add /absolute/path/to/lore-framework
codex plugin add lr@lore-framework
```

Then restart Codex so new sessions load the plugin.

## Refresh after the framework updates

Codex installs plugins persistently under `~/.codex/plugins/cache/...`. Refreshing the plugin is a
separate step from updating the repo or marketplace source.

On the verified Codex builds used for this port, the refresh path is `codex plugin add
lr@lore-framework`; there is no separate `codex plugin update` subcommand.

### If the marketplace is git-backed

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

## Team automation

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

## Optional Codex configuration

If you want Lore's normal git-backed lifecycle on Codex:

- Enable network so boot auto-pull and push can reach remotes.
- Make repo `.git` directories writable if you want `/lr:finalize` to commit automatically.

The plugin cannot widen Codex's sandbox on its own; those settings come from how Codex is launched
or configured.

## Version mismatch symptom

If boot says your agent repo is stamped at a version newer than the installed framework, the usual
cause is that the repo or marketplace moved forward but the installed Codex plugin did not. Refresh
the plugin using the commands above, restart Codex, then boot again.

## After install

Plugin installed? Continue with [FIRST-STEPS.md](FIRST-STEPS.md) to create your first agent — or,
if you're joining a team that already uses Lore Agents, pick up at
[QUICKSTART.md § After install](QUICKSTART.md#after-install-pick-your-path) (path A).

# Install Lore Framework on Cursor

This is the canonical Cursor install and refresh guide for Lore Framework.

If a Cursor agent is asked to install Lore from GitHub, point it at this file and have it follow the
commands here directly.

## For the AI agent reading this

If a user asked you to set up Lore Framework and you are running in **Cursor**, you are the
installer. Cursor's verified path is a **local checkout launched with `--plugin-dir`** — not a
one-command marketplace install — so this involves cloning the repo, running a helper script, and
relaunching. Before you clone into a directory, run the helper, or create a symlink, tell the user
what you're about to do and where, and get their go-ahead. Cursor does **not** hot-reload skills, so
new skills appear only after you relaunch with `--plugin-dir`; tell the user to expect that restart.
When the plugin is loaded, hand the user into [FIRST-STEPS.md](FIRST-STEPS.md).

## Engine syntax

On Cursor, Lore skills invoke as **`/lr-<skill>`** (hyphen, no colon) — e.g. `/lr-boot`,
`/lr-recall`, `/lr-finalize`. Per-agent shortcuts are `/lr-<agent-name>-agent` under
`.cursor/skills/` after registration.

Claude Code uses `/lr:<skill>`; Codex uses `$lr-<skill>`. See the README engine legend.

## Install sequence (two-step bootstrap)

There is no single self-contained one-command install for a user with no prior checkout. Use this
documented sequence:

### Step 1 — Bootstrap checkout (user or agent)

```bash
git clone https://github.com/zroslaw/lore-framework.git "${LORE_FRAMEWORK_DIR:-$HOME/src/lore-framework}"
```

Or update an existing checkout:

```bash
git -C "${LORE_FRAMEWORK_DIR:-$HOME/src/lore-framework}" pull --ff-only
```

### Step 2 — Post-clone helper

```bash
bash "${LORE_FRAMEWORK_DIR:-$HOME/src/lore-framework}/scripts/install-cursor-plugin" "${LORE_FRAMEWORK_DIR:-$HOME/src/lore-framework}"
```

The helper validates that `VERSION` exists (i.e. you cloned first). It optionally runs
`git pull --ff-only` and can create a local-plugins symlink with `--symlink` — see § Local plugins
symlink below.

### Step 3 — Launch (the user must do this)

> **Agents: you cannot perform this step.** Relaunching Cursor is the user's action — you're running
> inside the current, plugin-less session and can't restart it with a new flag. Tell the user to run
> this (or add `--plugin-dir` to their launch config), then continue once they're in the new session.
> While you wait, you can still help via the mid-session fallback in `docs/engines/cursor.md`.

```bash
cursor-agent --plugin-dir "${LORE_FRAMEWORK_DIR:-$HOME/src/lore-framework}"
```

Some installs expose `agent` as an alias for `cursor-agent`; all examples here use `cursor-agent`.

After launch, Lore skills appear as `/lr-boot`, `/lr-workspace-init`, `/lr-finalize`, etc.

## Verified install path today

The reliable, reproducible path is **local checkout + `--plugin-dir`**. The framework ships
`.cursor-plugin/plugin.json` and `.cursor-skills/` wrappers, but treat `--plugin-dir` as the
deterministic way to load Lore until a Cursor-native marketplace install has been verified on your
build.

## Local plugins symlink (optional)

`install-cursor-plugin --symlink` can create:

```
~/.cursor/plugins/local/lore-framework → /your/checkout
```

**Only use `--symlink` after confirming** your Cursor build loads Lore skills from
`~/.cursor/plugins/local/` *without* `--plugin-dir`. If you haven't confirmed that, skip `--symlink`
and use `--plugin-dir` every time. The install helper **defaults to no symlink** (`--symlink` is
opt-in).

## Refresh after the framework updates

Cursor does not hot-reload plugin skills mid-session. After updating the checkout on disk, start a
**fresh** session.

### Manual refresh

```bash
git -C /absolute/path/to/lore-framework pull --ff-only
cursor-agent --plugin-dir /absolute/path/to/lore-framework
```

### Helper script

```bash
bash /absolute/path/to/lore-framework/scripts/cursor-refresh-plugin /absolute/path/to/lore-framework
cursor-agent --plugin-dir /absolute/path/to/lore-framework
```

`cursor-refresh-plugin` exits non-zero if `git pull --ff-only` fails — fix the git state before
continuing.

If you are on an unpushed local branch, use whatever action brings the checkout to the desired
commit; the important part is a **new session** with `--plugin-dir` pointing at that tree.

If skills are listed but show **stale or wrong content** after upgrading, the checkout may be
current but the session still holds an old plugin tree — run `cursor-refresh-plugin`, start a fresh
`cursor-agent --plugin-dir` session, and see the troubleshooting table below. On Claude Code, see
`docs/doctor-stale-plugin-cache.md`.

## Team automation

Wrap refresh before launch so teammates always pick up the latest framework:

```bash
LORE_FRAMEWORK_DIR="${LORE_FRAMEWORK_DIR:-$HOME/src/lore-framework}"
bash "$LORE_FRAMEWORK_DIR/scripts/cursor-refresh-plugin" "$LORE_FRAMEWORK_DIR"
cursor-agent --plugin-dir "$LORE_FRAMEWORK_DIR"
```

Set `LORE_FRAMEWORK_DIR` in your shell profile or team dotfiles when the checkout lives elsewhere.

## Mid-session fallback (plugin not loaded)

If Lore slash commands are missing but you have a checkout path, use the canonical procedure in
`docs/engines/cursor.md` § Mid-session fallback (file-driven via `.cursor-skills/lr-<skill>/SKILL.md`).

## Per-agent boot shortcuts

After the plugin is loaded, register workspace-local shortcuts:

```
/lr-register-agent my-agents researcher
/lr-register-repo my-agents
```

These create `.cursor/skills/lr-<agent>-agent/` wrappers scoped to the matching repo.

## Cursor-native plugin installs (not yet verified)

Marketplace / IDE-native install flows are **not** documented as verified here. Don't assume a
marketplace install works until you've checked it on your own CLI build
(`cursor-agent --help | grep -i plugin`); until then, use the `--plugin-dir` path above.

## Optional Cursor configuration

If you want Lore's full git-backed lifecycle on Cursor:

- Allow network so boot auto-pull and push can reach remotes.
- Allow git writes if you want `/lr-finalize` to commit automatically.

Cursor's sandbox and approval model is controlled by how the host is launched, not by the Lore
plugin itself.

## Version mismatch symptom

If boot says your agent repo is stamped at a version newer than the installed framework, the usual
cause is that the repo moved forward but the Cursor session still holds an older plugin tree.
Refresh the checkout, start a fresh `cursor-agent --plugin-dir` session, then boot again. See
`docs/version-check.md`.

## Troubleshooting

| Symptom | See |
|---------|-----|
| No `/lr-*` skills at all | `docs/doctor-cursor-session-without-plugin.md` |
| Skills present but old content | Refresh + new session; `doctor-stale-plugin-cache.md` (Claude) |
| Need Lore mid-session without plugin | `docs/engines/cursor.md` § Mid-session fallback |

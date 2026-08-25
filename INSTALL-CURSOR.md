# Install Lore Agents on Cursor

This is the canonical Cursor install and refresh guide for Lore Agents.

If a Cursor agent is asked to install Lore from GitHub, point it at this file and have it follow the
commands here directly.

## For the AI agent reading this

If a user asked you to set up Lore Agents and you are running in **Cursor**, you are the installer.

The install has **two steps, and you can only do the first one.**

1. **You** add the Lore Agents marketplace to the user's Cursor account. This is one command.
2. **The user** enables the plugin in Cursor's UI. You cannot do this — there is no non-interactive
   install command in Cursor today. Do not try to fake it, and do not edit any file under
   `~/.cursor/plugins/` to simulate it (see § Do not hand-edit the plugin manifest).

So: run Step 1, then **show the user the highlighted block in Step 2 and stop**. Wait for them to
confirm they clicked Add before you continue.

Before you run a command that changes their account or their disk, say what you are about to do and
get their go-ahead.

Cursor does **not** hot-reload plugins. After the user enables it, they need a **fresh session**
before `/lr-*` skills appear. Tell them to expect that.

When the plugin is loaded, ask whether the user is joining a team that already uses Lore Agents or
starting fresh — for joining, point them to
[QUICKSTART.md § After install](QUICKSTART.md#after-install-pick-your-path); for starting fresh,
hand them into [FIRST-STEPS.md](FIRST-STEPS.md).

## Engine syntax

On Cursor, Lore skills invoke as **`/lr-<skill>`** (hyphen, no colon) — e.g. `/lr-boot`,
`/lr-recall`, `/lr-finalize`. Per-agent shortcuts are `/lr-<agent-name>-agent` under
`.cursor/skills/` after registration.

Claude Code uses `/lr:<skill>`; Codex uses `$lr:<skill>`. See the README engine legend.

## Install

### Step 1 — Add the marketplace (the agent can do this)

```bash
cursor-agent plugin marketplace add https://github.com/zroslaw/lore-framework
```

Expected output:

```
✓ Added marketplace lore-framework (1 plugin)
  lr - Lore Agents — named AI specialists that learn and grow with you
```

Verify it landed before moving on:

```bash
cursor-agent plugin marketplace list --format json
```

The list must contain an entry whose `gitUrl` is `https://github.com/zroslaw/lore-framework`. If it
does not, Step 1 failed — fix that before showing the user Step 2.

This registers the marketplace on the user's **Cursor account**, not just this machine.

### Step 2 — Enable the plugin (only the user can do this)

> ## ⚠️ ACTION REQUIRED — the install is not finished
>
> **Adding the marketplace does not install the plugin.** You must enable it yourself in Cursor.
> Nothing else in this guide will work until you do.
>
> **In the Cursor app:**
>
> 1. Open **Customize** in the sidebar, then the **Plugins** tab.
> 2. Click **+ Add**, then **From Marketplace**.
>    (The Plugins tab looks empty until you do this — that is expected.)
> 3. Scroll to the **Lore Framework** section.
> 4. On the **Lore Agents** row, click **Add**.
> 5. If Cursor asks for a scope, choose **user** — it then follows you to every project and machine.
>
> **Or do it in the terminal instead:**
>
> 1. Run `cursor-agent`.
> 2. Type **`/plugin`**.
> 3. Press **Tab** (or →) to switch to the **Marketplace** tab.
> 4. Type `Lore` to search, and select **Lore Agents (lore-framework)**. Press Enter.
> 5. Choose the scope. Press Enter.
>    - **Install for you (user scope)** — follows you to every project and machine.
>    - **Install for all collaborators on this repository (project scope)** — scoped to this repo.
>
> **Then start a fresh Cursor session.** Cursor does not hot-reload plugins.
>
> **Don't see a "Lore Framework" section?** Add the marketplace by hand: in that same browse view,
> click the **+ Add Marketplace** chip and paste
> `https://github.com/zroslaw/lore-framework`. Then repeat steps 3–4.

You only do this **once per Cursor account**. The install syncs to your other machines and to your
CLI sessions — you do not repeat it per laptop.

### Step 3 — Confirm it worked

In a new session, type `/lr-` and check that Lore skills appear (`/lr-boot`, `/lr-workspace-init`,
`/lr-finalize`, …).

If nothing appears, see § Troubleshooting.

## Keeping it up to date

Once installed from the marketplace, Cursor owns the update. Re-index after the framework ships a
new version:

```bash
cursor-agent plugin marketplace update lore-framework
```

Then start a fresh session.

To have pushes flow through without running that command, enable **Auto Refresh** and install the
**Cursor GitHub App** on the repo. Cursor then re-indexes at most once every 10 minutes. A fresh
session is still required — no hot reload, on any path.

### Pinning to a specific ref

`marketplace add` tracks the repo's default branch unless told otherwise:

```bash
cursor-agent plugin marketplace add https://github.com/zroslaw/lore-framework --git-ref <branch-or-tag>
```

A tag pins permanently — you will not receive later versions until you re-add. A branch tracks
whatever that branch points at.

## Do not hand-edit the plugin manifest

`~/.cursor/plugins/cache/.cloud-plugin-manifest.json` looks like an install record. It lists plugin
names, ids and resolved commits, so it is tempting to write an install into it.

**It is a downloaded cache of server-side state.** Cursor overwrites it on the next sync, and your
edit disappears. Installs live on the Cursor account, not on disk. There is no supported file you
can write to install a plugin.

## Development path — local checkout with `--plugin-dir`

Use this **only when working on the framework itself**, against a tree that is not pushed yet. It is
not managed by Cursor: no update checks, no account sync, no marketplace.

```bash
git clone https://github.com/zroslaw/lore-framework.git "${LORE_FRAMEWORK_DIR:-$HOME/src/lore-framework}"
bash "${LORE_FRAMEWORK_DIR:-$HOME/src/lore-framework}/scripts/install-cursor-plugin" "${LORE_FRAMEWORK_DIR:-$HOME/src/lore-framework}"
cursor-agent --plugin-dir "${LORE_FRAMEWORK_DIR:-$HOME/src/lore-framework}"
```

> **Agents: you cannot perform the launch step.** Relaunching Cursor is the user's action — you are
> running inside the current session and cannot restart it with a new flag. Tell the user to run it,
> then continue once they are in the new session. While you wait, you can still help via the
> mid-session fallback in `docs/engines/cursor.md`.

Some installs expose `agent` as an alias for `cursor-agent`; all examples here use `cursor-agent`.

To refresh this path after changing the checkout:

```bash
bash /absolute/path/to/lore-framework/scripts/cursor-refresh-plugin /absolute/path/to/lore-framework
cursor-agent --plugin-dir /absolute/path/to/lore-framework
```

`cursor-refresh-plugin` exits non-zero if `git pull --ff-only` fails — fix the git state before
continuing.

### Local plugins symlink (optional, same development path)

`install-cursor-plugin --symlink` can create:

```
~/.cursor/plugins/local/lore-framework → /your/checkout
```

This is the same unmanaged class as `--plugin-dir`, not a lighter-weight install. **Only use
`--symlink` after confirming** your Cursor build loads Lore skills from `~/.cursor/plugins/local/`
*without* `--plugin-dir`. The helper **defaults to no symlink** (`--symlink` is opt-in).

If you have installed from the marketplace, remove this symlink so the two copies cannot shadow each
other.

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

## Optional Cursor configuration

If you want Lore's full git-backed lifecycle on Cursor:

- Allow network so boot auto-pull and push can reach remotes.
- Allow git writes if you want `/lr-finalize` to commit automatically.

Cursor's sandbox and approval model is controlled by how the host is launched, not by the Lore
plugin itself.

## Version mismatch symptom

If boot says your agent repo is stamped at a version newer than the installed framework, the plugin
tree is behind. Re-index the marketplace (or refresh the checkout), start a fresh session, then boot
again. See `docs/version-check.md`.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Marketplace added, but no `/lr-*` skills | The plugin was never enabled — Step 1 is not Step 2 | Do § Step 2, then start a fresh session |
| Plugins tab looks completely empty | That is the empty state, not an error | Click **+ Add** → **From Marketplace** |
| No **Lore Framework** section in the browse view | Marketplace not registered on this account | Re-run Step 1, or use the **+ Add Marketplace** chip |
| Enabled, but still no `/lr-*` skills | Session predates the install | Start a fresh session — Cursor has no hot reload |
| Skills present but old content | Plugin tree is stale | `cursor-agent plugin marketplace update lore-framework`, fresh session |
| Two marketplaces for the same repo | Added once by CLI and once by the UI | Keep one: `cursor-agent plugin marketplace remove <name>` |
| No `/lr-*` skills at all | — | `docs/doctor-cursor-session-without-plugin.md` |
| Need Lore mid-session without plugin | — | `docs/engines/cursor.md` § Mid-session fallback |

## After install

Plugin installed? Continue with [FIRST-STEPS.md](FIRST-STEPS.md) to create your first agent — or,
if you're joining a team that already uses Lore Agents, pick up at
[QUICKSTART.md § After install](QUICKSTART.md#after-install-pick-your-path) (path A).

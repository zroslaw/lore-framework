# Install Lore Framework on Cursor

This is the canonical Cursor install and refresh guide for Lore Framework.

## Verified Install Path Today

The verified reproducible Cursor path today is loading the framework from a local checkout with
`--plugin-dir`.

1. Clone or update a local checkout of `lore-framework`.
2. Launch Cursor Agent CLI with that checkout as the plugin directory:

```bash
cursor-agent --plugin-dir /absolute/path/to/lore-framework
```

The framework's Cursor skill wrappers live under `skills/cursor/`, so the user-facing commands are
slash commands such as `/lr-boot`, `/lr-recall`, and `/lr-finalize`.

## Refresh After the Framework Updates

Update the checkout that Cursor points at, then start a fresh Cursor session with the same
`--plugin-dir` path:

```bash
git -C /absolute/path/to/lore-framework pull --ff-only
cursor-agent --plugin-dir /absolute/path/to/lore-framework
```

If you are working from an unpushed local branch, replace the `git pull` with whatever action
brings that checkout to the desired commit. The important part is that Cursor must be restarted;
the current session will keep using the plugin tree it already loaded.

## Cursor-Native Plugin Installs

The framework ships a `.cursor-plugin/plugin.json`, but the documented and empirically verified path
today is still `--plugin-dir` against a local checkout. If your team adopts a Cursor-native install
flow later, keep the same rule: update the plugin source, then start a fresh session so Cursor
reloads it.

## Optional Cursor Configuration

If you want Lore's full git-backed lifecycle on Cursor:

- Allow network so boot auto-pull and push can reach remotes.
- Allow git writes if you want `/lr-finalize` to commit automatically.

Like Codex, Cursor's sandbox and approval model is controlled by how the host is launched, not by
the Lore plugin itself.

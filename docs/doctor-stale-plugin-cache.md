# Stale Plugin Cache

> **Bootstrap note.** This ailment can mask its own diagnostic tool: if a plugin upgrade adds or renames `/lr:doctor` itself, `/lr:doctor` may be missing from your available-skills list right when you'd want to use it. The Remedy below still applies — clear the cache directly, restart Claude Code, then re-attempt `/lr:doctor` to verify.

## Symptoms

- A skill known to exist in the current framework `VERSION` does not appear in the session's available-skills list (e.g. `/lr:workspace-sync` is missing on a v11+ install).
- An **old** skill name still appears after a hard rename (e.g. `/lr:pull-domain` is still listed after the v11 rename to `/lr:workspace-sync`).
- A SKILL.md or doc edit made in the marketplace install at `~/.claude/plugins/marketplaces/lore-framework/`, or via a normal plugin update, doesn't seem to have taken effect — the prior content keeps loading.
- A registered per-agent shortcut (`/lr-<agent-name>-agent` on Claude Code, `$lr-<agent-name>-agent` on Codex) points at a path or behavior that no longer matches the framework — typically right after upgrading.
- A `/plugin update` or marketplace refresh appears to succeed but Claude Code's behavior reflects the prior version.
- An expected **MCP server's tools do not appear** after an upgrade (e.g. `lr-wait`'s `wait_for_event` / `sleep` are missing) — the cache holds the prior plugin tree without the new `.mcp.json` / server. (If instead the server is present but failing to launch, that is not a cache issue — check its runtime is installed, e.g. `python3` on `PATH` for `lr-wait`.)

## Diagnosis

1. **Confirm the framework `VERSION`.**

   ```bash
   cat ~/.claude/plugins/marketplaces/lore-framework/VERSION
   ```

   If the source-of-truth `VERSION` reflects what's expected, the framework files on disk are current — the issue is then almost certainly cached state in the running Claude Code session.

2. **Inspect the cache structure.** Plugin caches live under `~/.claude/plugins/cache/`. The top-level entries are marketplace names; one or two levels deeper you find per-plugin version directories. List the structure:

   ```bash
   find ~/.claude/plugins/cache -maxdepth 3 -type d
   ```

3. **Cross-check the cached version against the marketplace install.** The marketplace files (the upstream "truth") live under `~/.claude/plugins/marketplaces/lore-framework/`. Compare cached `VERSION` to marketplace `VERSION`:

   ```bash
   ls ~/.claude/plugins/cache/lore-framework/lr/
   for v in ~/.claude/plugins/cache/lore-framework/lr/*/; do
     echo "cache: $(basename "$v") -> VERSION=$(cat "$v/VERSION" 2>/dev/null)"
   done
   echo "marketplace: VERSION=$(cat ~/.claude/plugins/marketplaces/lore-framework/VERSION)"
   ```

   Then diff the skill catalogs. If `lr/` contains exactly one version directory, the simpler form works; if multiple version directories coexist, pick the one Claude Code is actually loading from `installed_plugins.json`:

   ```bash
   # Single-version case:
   LR_CACHE_VER=$(ls ~/.claude/plugins/cache/lore-framework/lr/ | sort -V | tail -1)
   diff -r ~/.claude/plugins/cache/lore-framework/lr/$LR_CACHE_VER/skills/ \
           ~/.claude/plugins/marketplaces/lore-framework/skills/ | head
   ```

4. **The deciding signal:** the symptom (e.g. a v11-only skill missing from the available-skills list) does not go away across new sessions until the cache is refreshed. Editing the marketplace files does not propagate; the cache is what Claude Code appears to load at session start.

## Remedy

Clear the plugin cache so Claude Code repopulates it from the marketplace on the next session.

**Targeted (recommended):**

```bash
rm -rf ~/.claude/plugins/cache/lore-framework/
```

Clears only the lore-framework cache; other plugins' caches (e.g. agoda-marketplace) remain intact and don't need to be re-resolved on next session.

**Broader (fallback, if you suspect cross-plugin corruption):**

```bash
rm -rf ~/.claude/plugins/cache/
```

Wipes every plugin's cache — Claude Code repopulates them all on the next session start. No permanent state is lost; only the locally cached copies of installed plugins are removed.

**Workspace-local helper.** Some agent-repo workspaces ship a `./clear_plugin_cache.sh` script (e.g. the Activities workspace). It runs `rm -rf ~/.claude/plugins/cache/*`, which wipes the cache contents but preserves the `cache/` directory itself — a near-equivalent of the broader manual command above.

This is a destructive operation. Confirm with the user before running.

**After clearing:**

1. **Exit the current Claude Code session.** The cached state is held in memory for the duration of the session — even after wiping the cache, this session continues to see the old skill list.
2. **Start a fresh session.** Claude Code re-resolves plugins from the marketplace, repopulates the cache, and the new skill list takes effect.
3. **Verify.** Confirm the previously-missing skill now appears (e.g. type `/lr:workspace-sync` and check that the slash-command picker resolves it). Re-boot the agent and confirm any version-dependent boot output reflects the current `VERSION`.

## Why It Happens

Claude Code appears to resolve plugin content through `~/.claude/plugins/cache/` rather than reading the marketplace files on every session start: the cache directory holds the resolved plugin tree, and `installed_plugins.json` points its `installPath` at the cache, not the marketplace. In some upgrade scenarios the cache is not invalidated when the marketplace updates, leaving the whole prior-version plugin tree resident. This is most user-visible when the new version contains hard renames (a deleted directory plus a freshly named one) or removed skills, since those changes make the divergence concrete.

A few common triggers:

- A `/plugin update` ran but the cache wasn't invalidated for the affected plugin (race / partial-update case).
- The user is developing the framework locally (`claude --plugin-dir ./lore-framework`) and switched between branches that have different skill catalogs without restarting.
- A version bump that included **deletions** (e.g. v11's removal of `skills/pull-domain/`) — the cache still has the old directory.
- Manual edits to cache contents (rare; for debugging) that get overwritten by a refresh in inconsistent ways.

In practice, the session also appears to load the available skill list once at start: even after wiping the cache mid-session, the running session continues to see the prior skill list — a fresh session is required for changes to take effect.

## Prevention

Whenever a framework migration or release note **adds, removes, or renames** a skill or `/lr-*` command — or **edits SKILL.md content** in a way that changes runtime behavior — the migration / release-notes doc must instruct the user to clear the plugin cache and restart Claude Code after applying the upgrade. See `docs/conventions.md` § Migration / Release-Note Authoring (the v12 cache-clear footer convention).

## See Also

- `docs/doctor.md` — orchestrator and ailment catalog.
- `docs/doctor-cursor-session-without-plugin.md` — Cursor session with no plugin loaded (missing skills entirely, not stale content).
- `docs/conventions.md` — the cache-clear footer convention authors must apply when shipping cache-affecting versions.
- `docs/update.md` — `/lr:update` flow; cache-clear is a follow-up step after a version bump that changes skills.
- `release-notes/12.md` — first release note that codifies the cache-clear convention.

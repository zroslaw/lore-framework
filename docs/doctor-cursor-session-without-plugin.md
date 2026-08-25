# Cursor Session Without Plugin Loaded

## Symptoms

- `/lr-boot`, `/lr-doctor`, `/lr-check`, and other Lore slash commands are **not** in the
  session's available-skills list.
- The user expected Lore commands after opening an IDE chat or starting `cursor-agent` **without**
  `--plugin-dir` (and without a verified local-plugin load path).
- Boot or framework operations fail because the host has no registered `/lr-*` skills.

## Diagnosis

1. **Confirm the skill is missing.** Check whether `/lr-boot` (or any known Lore skill) appears in
   the session skill list. If skills are listed but show **old or wrong content** after an upgrade,
   this is a different ailment — see the differential table below.

2. **Identify the session surface.**
   - **CLI:** was `cursor-agent` launched with `--plugin-dir /path/to/lore-framework`?
   - **IDE chat:** was a verified local-plugin path active (see `docs/engines/cursor.md` § Load
     surfaces)?
   - **Cloned a Lore workspace and expected `lr` to be there already?** Since v43 a workspace can
     carry `.cursor/settings.json` with a `plugins."lore-framework/lr"` entry, which loads the
     plugin with no per-person install. Check that path first:

     ```bash
     python3 "<framework-root>/scripts/lr-core" workspace-scan --workspace "<workspace>"
     ```

     Read `data.plugin_config`. `missing` means the workspace never had the file — the fix is
     `workspace-init`, not anything in this ailment. `unresolvable` means the file exists but
     cannot be parsed or safely merged, so Cursor may be ignoring it too: fix the JSON by hand.
     An entry present with `"enabled": false` is a deliberate opt-out, and the missing skills are
     the intended outcome rather than a fault. Only when `data.plugin_config` is clean does the
     rest of this ailment apply.

3. **Verify the checkout on disk** (if the user has one):

   ```bash
   cat /path/to/lore-framework/VERSION
   ```

   Compare with the version the team expects. A stamp mismatch without missing skills is usually
   `docs/version-check.md`, not this ailment.

**Do not use `${CLAUDE_PLUGIN_ROOT}` on Cursor** — it is always empty, even when the plugin loaded
correctly. Missing skills in the picker is the right signal.

### Not this ailment (differential routing)

| Symptom | Route to |
|---------|----------|
| Skills listed but wrong/old content after upgrade | `doctor-stale-plugin-cache` (Claude-specific cache remedy); on Cursor → `scripts/cursor-refresh-plugin` + fresh session |
| `R > F` version stamp mismatch at boot | `docs/version-check.md` / `INSTALL-CURSOR.md` refresh |
| Invalid or missing checkout path | `INSTALL-CURSOR.md` § Step 1 (clone) |
| Mid-session need with checkout path available | `docs/engines/cursor.md` § Mid-session fallback |

## Remedy

**Preferred — load the plugin for the next session:**

```bash
bash /path/to/lore-framework/scripts/cursor-refresh-plugin /path/to/lore-framework
cursor-agent --plugin-dir /path/to/lore-framework
```

Replace `/path/to/lore-framework` with your checkout (or set `LORE_FRAMEWORK_DIR`).

**Same-session workaround (no plugin loaded):** follow `docs/engines/cursor.md` § Mid-session
fallback — file-driven execution via `.cursor-skills/lr-<skill>/SKILL.md` when the user provides
the checkout path.

**Note:** `/lr-doctor` itself is unavailable in this state. Read this topic directly (or use the
mid-session fallback to boot an agent that can guide you).

## Why It Happens

Cursor loads plugin skills at **session start** only. A session started without
`cursor-agent --plugin-dir <checkout>` (and without a verified IDE local-plugin path) has no
registered `/lr-*` skills. Updating files on disk mid-session does not hot-reload the skill catalog;
a fresh session (or the file-driven fallback) is required.

## See Also

- `docs/doctor.md` — orchestrator and ailment catalog.
- `docs/engines/cursor.md` — load surfaces, refresh contract, mid-session fallback.
- `INSTALL-CURSOR.md` — canonical install and refresh guide.
- `doctor-stale-plugin-cache.md` — stale content after upgrade (different root cause).

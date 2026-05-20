Migrations that touch user-side artifacts must distinguish between files the framework still owns and files that are no longer framework-generated. Different handling for each category — the filename-based "looks like one of ours" heuristic is necessary but not sufficient.

See also `update-process.md` for the general migration pattern.

## Two categories in `.claude/commands/`

1. **Owned, potentially stale** — `lr-<agent-name>-agent.md` files whose content matches a known framework template (current or historical). The framework still produces these; the migration's job is to regenerate them to the current template.

2. **Orphaned** — files that were once part of the framework but no longer are. Example: pre-plugin installs put `lr-boot.md`, `lr-reflect.md`, etc. directly in `.claude/commands/` as local duplicates of what are now plugin skills. The framework no longer emits them; they persist on user machines purely as drift.

## Handling

**Owned, stale:**
- Detect: content matches a known-clean template (current or pre-current version).
- Action: overwrite with new template. Silent.
- If content matches no known template → user edited it. Three-way merge, present to user.

**Orphaned:**
- Detect: filename matches a pattern the framework once emitted, AND collides with a current framework skill (so the local copy is now redundant with the installed plugin, which takes precedence at command resolution time).
- Action: **prompt the user**. Options: Delete / Keep / Keep all remaining. Never auto-delete.

Migration 5 implements both: Step 1 for owned-stale, Step 2 for orphans.

## Why prompt for orphans

A file the framework no longer owns may have diverged significantly from its original content. The user may have adapted it for their own workflow that happens to share a filename with a current skill. Auto-deleting would destroy non-framework work. Prompting is the correct default.

Contrast with owned-stale: when content matches a known template byte-for-byte, the user provably hasn't touched it, so overwriting is safe.

## Check complement

`/lr:check` catches drift between migration runs:
- **Check 17** — reports orphans (informational; action is a user decision).
- **Check 18** — reports owned-but-stale (legacy sibling-path per-agent boot commands).

Both checks can run any time. Migrations clean up both categories on version walk; the checks surface anything that slips through.

## Design rule for future migrations

When designing a migration that touches user-side generated files, for each touched file ask: **does the framework still emit this?**
- Yes → regenerate with template-match + three-way-merge on divergence.
- No → prompt. Don't auto-delete.

The ownership question — not the filename — determines handling.

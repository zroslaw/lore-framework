`/lr:update` reconciles user-side artifacts with the currently-installed framework version. Defined in `${CLAUDE_PLUGIN_ROOT}/docs/update.md`. Two types of per-version artifacts:
- **Migrations** (`migrations/<N>.md`) — physical file changes, executed and applied
- **Release notes** (`release-notes/<N>.md`) — informational, displayed to user only

At least one must exist per version bump; both may coexist for large releases. See `versioning-release-types.md`.

## What it does

- Compares `${CLAUDE_PLUGIN_ROOT}/VERSION` (framework version `F`) against each repo's `lore-repo.md` frontmatter `version` (`R`)
- For repos where `R < F`, walks versions `R+1` through `F`: applies `migrations/<v>.md` if present, displays `release-notes/<v>.md` if present
- After all upgrade steps succeed for a repo, stamps `F` into `lore-repo.md`
- If any migration step fails, stops for that repo and leaves the version un-stamped — re-running retries

## What it does NOT do

- Does not update the plugin itself (that's `/plugin update lr`)
- Does not touch lore topics, `lore-context.md`, or `workdir/` contents (agent-owned, not templated)
- Does not commit changes — leaves everything uncommitted for user review
- Does not skip versions
- Does not overwrite hand-edited generated files without user confirmation

## Key design choices

- **Repo-level version only** — no per-agent stamps. Agents within a repo always migrate together. One identifier per repo is the single source of truth for migration state.
- **Idempotent migrations** — every migration step must be safe to re-run. Because the version is stamped only after success, a partial failure leaves the repo on the old version and re-running resumes correctly.
- **Atomic commit of version** — the version field is the migration high-water mark. It advances only after all steps verify.
- **Dry-run support** — `/lr:update --dry-run` previews all changes (planned file creates, modifies, deletes, and frontmatter updates) without writing anything. Essential safety net for multi-repo migrations.
- **Manual-edit detection** — generated files (like `.claude/commands/lr-*-agent.md`) are regenerated only if the on-disk content matches a known previous-version template. If the file diverges, the process does a three-way merge (old template → new template, applied to current content), presents the merged result to the user, and asks: accept / edit / skip.
- **Freeform migration docs** — each `migrations/<N>.md` is a plain markdown doc describing what changed and how to migrate. Claude reads and executes the instructions. No rigid schema, matching the "agent-driven operations" design principle.

## Migration authoring rules

1. Scope each migration to a single repo. The update process iterates repos independently.
2. Steps must be idempotent. Safe to re-run any number of times.
3. Do not stamp `lore-repo.md` version inside the migration — the update process does that after success.
4. If the migration regenerates templated files, include the known previous-version templates so divergence detection can distinguish clean vs. hand-edited files.
5. Keep the migration focused on a single framework version bump. If multiple concerns ship in the same version, list them as separate steps within the single migration doc.

## Boot-time auto-upgrade

Since v3, `agent-boot.md` also performs a version check on every boot. If the agent's repo is behind, the same migration/release-notes walk runs automatically — no user prompt, uncommitted-changes safety gate, degraded-mode boot on failure. See `docs/version-check.md` in the framework.

## Current state

Framework is at version 5.
- `migrations/2.md` — removes `version` from `role.md`, regenerates boot commands (exercised 2026-04-11 on `lore-agents/`). Its Step 2 template was patched in v5 to emit the plugin-safe form.
- `release-notes/3.md` — first release-notes-only bump; introduces /lr:recall, subagent-scan search, auto boot version check, two-track update flow
- `release-notes/4.md` — /lr:attach, /lr:consult; host/guest model; per-agent finalization iteration
- `migrations/5.md` — regenerates `lr-*-agent.md` to plugin-safe form; prompts delete for orphaned pre-plugin skill duplicates. Dry-run supported. Idempotent.
- `release-notes/5.md` — plugin-compat summary; placeholder vocabulary; CWD safety conventions; checks 17/18.

`lore-agents/` is stamped at v4; will auto-upgrade to v5 on next agent boot when migration 5 runs.

**Dry-run reporting note:** Summary counters (upgraded / skipped / warned / failed) must reflect *would-be* outcomes, not literal writes (which are always zero in dry-run). The `[DRY RUN]` prefix distinguishes the mode; the counts still carry signal.

**Ownership-aware migrations (v5+):** migrations that touch user-side generated files must distinguish framework-owned-stale from orphaned. Owned-stale regenerates (three-way-merge on user edits); orphans prompt the user. See `migration-ownership.md`.

**Template-emission audit:** when the framework changes its file-reference form (e.g., sibling-path → plugin form), every template that emits content — not just runtime code — must be audited. Missed emission sites produce broken artifacts on user machines indefinitely. See `plugin-compat-template-audit.md`.

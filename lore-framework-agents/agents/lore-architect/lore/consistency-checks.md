`/lr:check` runs 18 consistency checks. Defined in `${CLAUDE_PLUGIN_ROOT}/docs/check.md`.

**Descriptor validation (1–5):**
1. Agent repo discovery — scan for `lore-repo.md` at root; flag if no lore agent repos found
2. lore-repo.md validation — verify YAML frontmatter has non-empty `description` and `version`
3. Framework version consistency (repo) — compare `lore-repo.md` version against `VERSION`; warn on mismatch (triggers `/lr:update`)
4. Agent discovery — scan `agents/` within discovered repos; flag repos with no agents (informational)
5. role.md frontmatter validation — verify YAML frontmatter has non-empty `description`. Legacy `version` field (if present) is flagged as informational — the repo predates migration 2.

**Structural (6–8):**
6. Agent discovery vs registration — bidirectional: every agent dir has a boot command (informational, not error — registration optional); every boot command points to a real agent dir (error if broken)
7. Boot command link validity — all file paths in `lr-*-agent.md` resolve on disk
8. Agent directory structure — each agent has `role.md`, `lore-context.md`, `lore/`, `workdir/`

**Reference integrity (9–10):**
9. lore-context.md topic references — filenames linked in lore-context exist in `lore/`
10. Lore topic cross-references — filenames referenced inside topics exist in the same `lore/`

**Size and state (11–13):**
11. lore-context.md size — warn at 40K tokens, flag at 50K
12. Pending reflections — non-empty `reflections/` dir means merge not yet run
13. Uncommitted lore changes — git status detects modified lore files not yet committed

**Temporal/semantic (14–16):**
14. lore-context.md staleness — topics committed more recently than lore-context may not be reflected in summary
15. lore-context.md semantic consistency — topic headings/opening sentences compared against lore-context summaries
16. Boot command vs role.md — timestamps + agent name match between boot command and role.md heading

**Drift / orphans (17–18, added v5):**
17. Orphaned pre-plugin skill commands — flags `.claude/commands/lr-<name>.md` files where `<name>` collides with a current framework skill (e.g., `lr-boot.md`, `lr-reflect.md`). These are pre-plugin local duplicates that shadow or duplicate the installed plugin skill; framework no longer emits them. Informational — user decides to keep or delete. See `migration-ownership.md`.
18. Legacy sibling-path per-agent boot commands — scans `lr-*-agent.md` for `lore-framework/docs/agent-boot.md` pattern (pre-v5 emission form). These break on plugin installs. Triggers `/lr:update` (migration 5 regenerates them). See `plugin-compat-template-audit.md`.

**History:** originally 17 checks. Migration 2 dropped the agent-level version check (old check 6) because `role.md` no longer carries a `version` field — subsequent checks renumbered down by one, leaving 16. Migration 5 added checks 17 and 18 for drift detection.

Key principle: git history is the metadata layer for temporal checks — no embedded timestamps in files.

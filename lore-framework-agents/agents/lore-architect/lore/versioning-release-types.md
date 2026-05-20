Starting with v3, framework version bumps can carry two kinds of artifacts:

**Migration** (`migrations/<N>.md`) — physical instructions to modify user-side repo files (frontmatter updates, file regenerations, directory restructures). Executed by `/lr:update` and the auto-upgrade-at-boot. Must be idempotent.

**Release notes** (`release-notes/<N>.md`) — informational only; describes what's new in version N. Displayed to the user, not executed. No user-side file edits required.

## Rules for authoring a new version bump

- User-side file changes required → create `migrations/<N>.md`
- Feature/doc additions only → create only `release-notes/<N>.md`
- Large release with both → create both
- **At least one must exist** — the update process treats a gap as a framework packaging bug

## History

- v1, v2 — migration-only (both required user-side schema changes)
- v3 — first release-notes-only bump (added /lr:recall, subagent-scan, auto boot version check; no user-side file changes needed)
- v4 — release-notes-only (added /lr:attach, /lr:consult; additive)
- v5 — both (migration regenerating legacy sibling-path boot commands, plus release notes)
- v6 — both (migration, plus release notes)
- v7 — release-notes-only (session summaries feature; `sessions/` dirs created on demand, no schema change)
- v8 — **release-notes-only** (v8 is purely behavioral: merge moves to uniform subagents, guest summaries in phase 3, commit+push centralized into phase 4, conflict-resolution subagent procedure. None of this touches user-side files — only framework docs/skills change.)
- v9 — release-notes-only (worktree convention, `/lr:init`, fully automated finalization).
- v10 — release-notes-only (`/lr:spawn-teammate` BETA — Agent Teams integration).

## In-band BETA refinement (post-v10 observation)

When a BETA feature needs refinement after its initial release, the version-bump ceremony is **not** required. Pattern:

1. **Edit the procedure doc** (`docs/<feature>.md`) — source of truth for current behavior.
2. **Leave the release notes alone** (`release-notes/<N>.md`) — they're a historical record, frozen at the version they describe. A verbatim citation that goes stale post-refinement is acceptable.
3. **No `VERSION` bump** — the BETA caveat ("internal procedure may evolve based on real-world usage") in the release notes is the contract that licenses this.
4. **Update lore at finalization** — design-decisions topics for the feature reflect the *current* state, not the originally-shipped state.

When the feature graduates from BETA, the graduation release notes describe the cumulative final state, not each iteration. Stable (non-BETA) features need a different cadence — refinements there are full release-notes events with version bumps.

**When to break this pattern** (not yet observed; anticipated):

- **Breaking change within BETA** — if existing usage will fail in a non-obvious way, mark explicitly with release notes + bump.
- **New state, file format, or per-agent metadata** — needs migration tracking regardless of stability label.
- **Refinement large enough to be a new feature** — graduate the BETA or treat as v(N+1).

First observed instance: spawn-teammate post-v10 boot-prompt reframe (see `spawn-teammate-feature.md`). If more BETA refinements accumulate and the playbook stays stable, this section should be promoted to a standalone topic (`beta-refinement-workflow.md`).

See `update-process.md` for how the update flow applies both types.

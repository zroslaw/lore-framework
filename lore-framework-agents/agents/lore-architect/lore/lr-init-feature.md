Framework command (v9+) that writes or refreshes a framework-managed section in the domain-level `CLAUDE.md`, distributing the worktree convention (and future framework-wide conventions) into any Claude Code session starting in the domain.

## Why `/lr:init` Exists

`CLAUDE.md` at a working directory is loaded automatically by every Claude Code session starting there. Parking framework conventions inside it is the simplest way to make them visible without relying on agent memory or manual context-setting. The framework cannot ship the domain's `CLAUDE.md` directly (that file belongs to the user's domain, not the plugin), so it ships a command that writes conventions into a delimited section, leaving the rest of the file untouched.

## Mechanism

- **Target**: `<cwd>/CLAUDE.md` — the user runs `/lr:init` from the domain directory.
- **Marker protocol**: framework-managed content lives between `<!-- lr:init:start -->` and `<!-- lr:init:end -->` (HTML comments, each on its own line). Content outside the markers is never touched.
- **Behavior table**:
  - No `CLAUDE.md` → create with canonical payload at top.
  - Exists, no markers → prepend canonical payload.
  - Markers present, content matches → no-op.
  - Markers present, content differs → show diff of the managed section, confirm, replace.
  - Malformed markers (missing pair, duplicates) → error, stop.
- **No three-way merge**. Show-diff-and-confirm is the entire user-edit protocol — simpler than full merge machinery and matches the "show before persist" discipline where it matters.

## Canonical Payload (v1)

Compact worktree convention statement + link to the full doc at the public GitHub URL (`github.com/zroslaw/lore-framework/blob/main/docs/worktrees.md`, not `${CLAUDE_PLUGIN_ROOT}` — a user-facing file should reference paths that resolve whether the plugin is loaded or not).

## Design Decisions

- **Markers over separate file or frontmatter block**: HTML comments render invisibly, are standard for managed-section patterns (all-contributors, CI tools, prettier-ignore), and avoid polluting the visible rendered markdown. If a renderer strips them, switch to visible sentinels — not a v9 concern.
- **Top placement on first write**: managed convention is essential context; agents see it first.
- **No args in v1**: simplicity. Later additions (`--dry-run`, `--force`) only if real need emerges.
- **No framework commit**: `/lr:init` does not run git — user reviews and commits themselves.
- **No auto-invocation at agent boot**: considered but explicitly dropped — "too complicated; will do work later to force people to be synchronized." Discovery gap is intentional, to be solved by a future domain-creation automation.

## Future Extensions

Designed to grow. More content may be added inside the same marker block in later framework versions (domain intro, agent registry pointers, invocation tips, etc.). The mechanism stays the same; only the payload grows. Tracked in `framework-improvements-backlog.md`.

## Design History

Emerged from the worktree-convention design conversation. Initial thought was "instructions to whoever runs native `/init`" — rejected because native `/init` doesn't read plugin docs; there's no hook. `/lr:init` owns the job as the reliable automated path. A complementary static doc for human-or-Claude-consulted manual setup was folded into `docs/init.md` itself rather than splitting into a separate `docs/domain-claude-md.md`.

## See Also

- `worktrees-convention.md` — v1 payload content
- `framework-improvements-backlog.md` — deferred extensions (domain creation automation, richer payloads, sync-on-version-bump)
- `skill-doc-pattern.md` — why `skills/init/SKILL.md` is a thin pointer
- `migration-ownership.md` — related three-way-merge pattern we deliberately did *not* adopt here

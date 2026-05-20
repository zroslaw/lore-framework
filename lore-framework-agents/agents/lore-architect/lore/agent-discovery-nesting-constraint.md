**Agent discovery scans direct subdirectories of cwd for `lore-repo.md` — it does not walk nested directories.**

Domain discovery (the procedure in `agent-boot.md` and the various skills below) only sees agent repos that sit as direct subdirectories of where Claude is invoked from. Nested agent repos are functional but invisible.

## Confirmed This Session

`lore-framework-agents/` was placed inside `lore-framework/` (path: `lore-framework/lore-framework-agents/lore-repo.md`). Running domain discovery from `~/Documents/git/` saw only `lore-agents/`. The nested repo was invisible.

## Consequence — Which Operations Skip Nested Repos

- `/lr:list-agents`, `/lr:list-repos`
- `/lr:check` (descriptor validation, structural checks)
- `/lr:recall` fan-out across active agents
- `/lr:pull-domain`
- `/lr:spawn-teammate` agent enumeration
- `/lr:boot <name>` discovery path

Only the registered `/lr-<agent>-agent` shortcut commands work — they hardcode absolute paths and bypass discovery entirely. So a nested agent is reachable only by users who have the absolute path or the registered command.

## Operational Rule

When recommending a placement for a new agent repo, it must be at the **domain root** (a direct subdirectory of where Claude is invoked from). Nested placements are functional but lose discoverability — they are effectively private to whoever has the absolute path.

Make this trade-off explicit when discussing placement options. Don't silently accept a nested placement without surfacing what the user gives up.

## When a Nested Placement Is Acceptable

A nested placement is acceptable as a **known temporary state** when:

- The user understands the discovery gap.
- There's a concrete plan to move the repo (e.g., extracting to its own GitHub remote later).
- The registered `/lr-<name>-agent` shortcut command is available as the bridge.

In this session, `lore-framework-agents/` was accepted as nested because the user plans to extract it to its own GitHub repository on a different account. The discovery gap is tolerated as a transition cost.

## Related Backlog

If nested-but-discoverable agent repos become a recurring pattern, consider whether discovery should walk one level deeper or accept a config-file hint. Not currently a priority — see `framework-improvements-backlog.md`.

## See Also

- `architecture-overview.md` — domain directory concept
- `domain-directory-concept.md` — what counts as "the domain"
- `plugin-vs-agent-repo-separation.md` — why `lore-framework-agents/` exists at all
- `consistency-checks.md` — current discovery-related checks

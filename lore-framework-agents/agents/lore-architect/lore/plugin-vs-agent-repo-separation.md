Plugin repos and agent repos serve different purposes and remain separate, even when an agent's lore is *about* the plugin's design.

## The Rule

- **Plugin repos** host `.claude-plugin/`, `skills/`, `docs/`, `migrations/`, `release-notes/`, `VERSION` — content distributed via the Claude Code marketplace to anyone installing `lr@lore-framework`.
- **Agent repos** host `lore-repo.md`, `agents/<name>/role.md`, `lore/`, `sessions/`, `workdir/` — cloned by contributors as siblings in their domain when they want to work with the agent.

Keep them in two different repos. They are two different distribution stories with two different audiences.

## Why Not Merge Them

The technical argument for fusing them was real: `.claude-plugin/` and `lore-repo.md` are orthogonal markers; a repo can be both a plugin and an agent repo simultaneously. The user explicitly rejected this on principle, and the reasons hold up:

- **Marketplace-installed users get unexpected baggage** they didn't ask for — `agents/`, `sessions/`, `workdir/` are noise to anyone consuming the plugin.
- **Plugin repo's surface area grows** — releases conflate plugin code changes with agent lore writes.
- **Reflective writes interleave with framework-code changes** in git history — they happen frequently during sessions and clutter the release-relevant history.
- **Distribution stories blur** — "install the plugin" and "clone the agent repo" are different operations for different audiences.

## Concrete Decision (this session)

`lore-framework/` (plugin) stays slim. `lore-framework-agents/` (a separate agent repo) was carved out to host `lore-architect` — and any future agents whose work is *about* the framework. Currently nested at `lore-framework/lore-framework-agents/` as a temporary placement; intent is to extract to a domain-root sibling on its own GitHub repository. See `agent-discovery-nesting-constraint.md` for the temporary trade-off.

## Operational Rule

When designing where a new artifact goes, ask: **"is this distributed via the Claude Code marketplace, or cloned into the domain by contributors who want to work with it?"**

- Distributed → plugin (`lore-framework/`).
- Cloned → agent repo (`lore-framework-agents/`, `lore-agents/`, or appropriate agent repo).

The same content question applies to where new agents go:
- Agent is *about* the framework itself → `lore-framework-agents/`.
- Agent is personal/domain-specific → `lore-agents/` or a new domain-specific repo.

## Relationship to `framework-scope-vs-agent-scope.md`

This rule is the **repo-topology** axis of the scope question:

- `framework-scope-vs-agent-scope.md` — what *content* belongs in framework vs agent.
- This topic — what *repo* hosts each kind of content.

Together: universal-and-distributed lives in the plugin repo; universal-but-cloned (like the architect's lore about framework design) lives in a dedicated agent repo; repo/host/workflow-specific lives in personal agent repos.

## See Also

- `framework-scope-vs-agent-scope.md` — content-level scope
- `plugin-distribution.md` — marketplace distribution mechanics
- `architecture-overview.md` — domain topology
- `agent-discovery-nesting-constraint.md` — why repo placement (root vs nested) matters for discoverability
- `team-shared-knowledge-principle.md` — the underlying framing for why the architect's lore is team-shared in the first place

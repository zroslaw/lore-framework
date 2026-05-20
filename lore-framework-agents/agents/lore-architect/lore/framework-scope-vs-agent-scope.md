A crystallized design rule for deciding what belongs in the framework vs in agent knowledge. Emerged sharply during the `contributions-feature.md` brainstorm.

## The Rule

**The framework owns what is universal across all repos, hosts, and workflows. Agents own what is specific to a repo, host, team, or workflow.**

When designing a new feature, the test is: "would this apply identically to every possible user of the framework, or does it depend on which repo / which host / which team conventions?" Universal → framework. Specific → agent knowledge (in that agent's lore, or in a specialist agent reached via `/lr:consult` or `/lr:attach`).

## Why It Matters

- Keeps the framework thin and maintainable. Every piece of machinery the framework adds is a constraint on every user forever.
- Pushes specifics to where they naturally live — agents that encounter them regularly, and whose lore is the right home for durable repo/host knowledge.
- Composes with the existing cross-agent mechanisms. Specialist agents are not new infrastructure; `/lr:consult` and `/lr:attach` already handle "I need knowledge I don't have."

## Diagnostic Signals (overengineering)

These were the red flags during the contributions-feature debate — each a signal that repo/host/workflow specifics were being pulled into the framework:

- Command proliferation — a new skill for every lifecycle verb (`/lr:ship`, `/lr:open-pr`, `/lr:resume`, `/lr:contributions`, ...).
- Schema lock-in — rich frontmatter with status/PR URL/base branch/timestamps.
- Host-mapping docs in the framework repo (`git-hosts/github.md`, `git-hosts/gitlab.md`).
- Hard gates around workflow steps (auto-detecting test commands, enforcing CI green before PR open).

Each of those collapsed back into the agent's domain the moment the rule was applied.

## Operational Guidance

When the user asks for a new framework feature, start by isolating the truly universal core. Everything else gets pushed out. When in doubt, cut — add later only when real usage shows the missing piece is genuinely universal.

This composes with `design-doc-before-implement.md`: first draft what universal core looks like; only then ship.

## See Also

- `system-design-principles.md` — "minimal and essential" principle; this rule sharpens the universality test
- `plugin-vs-agent-repo-separation.md` — the **repo-topology axis** of the same scope question (this topic is the content axis)
- `contributions-feature.md` — the design debate where this rule crystallized *(note: dangling reference — pre-existing draft never landed in `lore/`; tracked in `framework-improvements-backlog.md`)*
- `consult-pattern.md`, `attach-pattern.md` — the mechanisms that make specialist-agent knowledge a first-class alternative to framework machinery
- `design-doc-before-implement.md` — draft the minimal core before shipping

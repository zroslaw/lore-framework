The lore framework exists to make tribal knowledge durable. Lore agents are **team-shared knowledge containers**, not personal notebooks — sessions, lore topics, and workdir artifacts are committed and pushed to a shared repository where the entire team can read, contribute, and build on what was learned.

## The Principle

An agent's `lore/`, `lore-context.md`, `role.md`, `workdir/`, and `sessions/` all live in a shared git repository. Multiple contributors are expected to boot the same agent, finalize into the same files, and push concurrently. The framework's machinery is built around this: push-conflict-resolution, merge in role-booted subagents, sessions as narrative for future readers, repo-level versioning, auto-push at finalization.

This is the value proposition. Not "Claude remembers things for me" — but "the team's tribal knowledge is no longer trapped in individuals."

## Why It Matters

- **Frames every design decision.** Almost every framework mechanism makes sense only under the shared-knowledge lens. Directory-driven storage exists so git can be the medium. Plain markdown exists so any contributor can read and edit. Push-conflict-resolution exists because concurrent contributors are expected, not exceptional.
- **Determines the right framing for new features.** When weighing a design decision, the question "what if multiple people use this agent simultaneously?" should resolve toward "good — make it work," not "we should isolate per-user."
- **Determines the right framing for content.** Sessions are written for future readers, not just the author. Lore reflects accumulated team understanding, with multi-author voice expected. Workdir contains artifacts intended for handoff and asynchronous collaboration.

## Diagnostic Signals (misframing)

Treating lore agents as personal-private notebooks produces wrong instincts. Red flags:

- "Don't commit sessions — they contain personal narrative" → loses the transmission value entirely; sessions are exactly the medium of transmission.
- "Multi-author lore is a coherence problem" → reverses the framework's purpose.
- "Workdir leaks half-formed drafts" → drafts in workdir are intentional artifacts for handoff.
- "Voice drift across contributors is undesirable" → it's an accepted property of collective knowledge; coherence comes from `role.md` and topic structure, not single authorship.
- "Finalized knowledge should stay local until reviewed" → contradicts the auto-push default; finalization publishes by design (see `finalize-autopush.md`).

If a proposed design starts from any of these instincts, the framing is wrong, not the design.

## Operational Guidance

When evaluating a design decision:
1. Ask: does this make team-shared usage better or worse?
2. If a feature only helps single-user workflows, push it down into agent specifics (lore, workdir tools), not framework machinery.
3. If a feature gates publication unnecessarily (extra approval steps, isolation between contributors), it likely contradicts the principle.

When writing content (sessions, lore, workdir):
1. Write for the team, not just yourself.
2. Capture *why*, not just *what* — future readers won't have the session context.
3. Use `See also:` links liberally — the knowledge graph is the navigation aid for newcomers.

## Known Gaps

The principle's guarantees apply to the standard finalization flow (sequential sessions; concurrent finalizations reconciled by push-conflict-resolution at phase 4). The `spawn-teammate` BETA (`/lr:spawn-teammate`, Agent Teams integration) does not yet serialize concurrent lore writes across teammates within a single Agent Teams session — last-write-wins applies. See `spawn-teammate-feature.md` for the BETA caveats and open design questions on this.

## See Also

- `system-design-principles.md` — core principles; this is the foundational one
- `naming-foundational-principles.md` — the meta-lesson that named *this* topic; explains why explicit naming matters
- `push-conflict-resolution.md` — the machinery that makes concurrent contribution safe
- `finalization-process.md` — four-phase flow that publishes per-session knowledge
- `finalize-autopush.md` — auto-push as the default at finalization
- `merge-in-booted-subagents.md` — per-agent merge lens for cross-contributor coherence
- `session-summaries-feature.md` — session summary mechanics; the narrative-for-future-readers artifact this principle relies on
- `framework-scope-vs-agent-scope.md` — universal vs specific boundary (different axis, related concern)
- `plugin-vs-agent-repo-separation.md` — downstream consequence: framework design knowledge gets its own team-shared agent repo, not a personal one

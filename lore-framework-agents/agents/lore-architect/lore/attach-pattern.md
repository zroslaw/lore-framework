`/lr:attach` loads another lore agent into the currently booted host session for sustained multi-domain work. The host remains the sole executor; the guest's role and lore-context join the host's working context. Multi-personality, single executor.

Introduced in framework v4 alongside `/lr:consult`. See `consult-pattern.md` for the one-shot sibling.

## Terminology

- **Host** — the originally booted agent. Exactly one per session.
- **Guest** — an attached agent. Zero or more per session. Knowledge load, not an executor.
- **Active agents** — host + all attached guests. This is what recall fans out over and what finalization iterates over.

## Design decisions

- **Host-wins on conflicts.** When guest lore contradicts host lore, host governs. Guest perspective is visible and informs judgment, but the host's identity and rules stay stable — no silent harmonization.
- **No token-budget cap.** Each guest's `lore-context.md` can be up to 50K. Multiple guests visibly shrink the host's working budget. Cost is the user's responsibility, not a framework check.
- **Version reconcile in a subagent.** If the guest repo's `version` differs from framework `VERSION`, attach dispatches a subagent to execute `docs/version-check.md` scoped to the guest repo. Subagent absorbs migration tool output and returns only a compact report + release notes text. Host relays release notes to the user. Reuses existing version-check machinery — no parallel migration pipeline.
- **State in conversation, not disk.** The `/lr:attach` confirmation message is the record. No session-state file. Host enumerates active agents from conversation history on every operation (recall, reflect, merge).
- **No detach in v1.** Once attached, stays attached through the session and participates in finalization. Avoids edge cases around partial-session participation. Can be revisited later if needed.
- **Workdir writes default to host's.** Guest workdirs are readable via domain visibility; writes during the session go to host's workdir unless clearly guest material. Ownership resolves at reflection time.

## What changes after attach

- `/lr:recall` fans out — one `Explore` subagent per active agent in parallel, results grouped by agent. See `lore-search-pattern.md`.
- `/lr:reflect` iterates inline per active agent in host-first order (needs session context). `/lr:merge` spawns parallel subagents per active agent, each booted as its target (v8+). `/lr:summarize` runs once, session-wide, from the host's perspective; in v8+ it also writes a short guest summary into each attached guest's own repo when that guest had lore updates. `/lr:finalize` chains these into four phases ending with commit+push. See `finalization-process.md`, `merge-in-booted-subagents.md`.
- Topics relevant to multiple agents may duplicate across their lore — shared knowledge is a feature, efficiency over mutual exclusivity.

## Why introduce it

Narrow utility/functional domains (external API clients, per-repo commit conventions, specialized tooling) show up across many agents without being any single agent's primary role. Without a shared-knowledge mechanism, each agent re-learns the same domain independently — duplication, divergence, no compounding. Attach lets a specialist agent be the single source of truth for its domain, with other agents loading it when they genuinely need sustained fluency in it.

## Boundary vs. consult

- **Consult** — one-shot Q&A in a subagent. Consultant not loaded. Specific file pointers handed back. No finalization for the consultant.
- **Attach** — sustained loading into host context. Recall fans out. Finalization iterates. Use when the task genuinely spans multiple domains over many turns.

Escalation path: if a consult reveals deeper engagement is needed, `/lr:attach <same-agent>`.

## Implementation

- Skill: `skills/attach/SKILL.md` (thin pointer)
- Doc: `docs/attach.md` (full procedure, including list-guests-with-no-args behavior)
- Cross-references: `recall.md`, `lore-search.md`, `consult.md`, `version-check.md`, `process-reflection.md`, `process-merge.md`

## Related topics

- `consult-pattern.md` — the one-shot sibling
- `lore-search-pattern.md` — search brief structure and fan-out mechanics
- `finalization-process.md` — per-agent iteration in reflect/merge
- `skill-doc-pattern.md` — thin-skill + detailed-doc convention followed here
- `versioning-release-types.md` — why v4 is release-notes-only (additive feature, no migration needed)

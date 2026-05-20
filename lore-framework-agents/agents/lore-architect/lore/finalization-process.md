Session finalization is user-triggered. As of v8 it is a four-phase process orchestrated by `docs/finalize.md`:

**Phase 1 — Reflect** (`/lr:reflect`): runs **inline**, host-first, per active agent. The agent reviews the session and writes reflection topics to each active agent's `reflections/`. Each topic is one atomic insight, lesson, or decision. Topics named `role-update-*.md` signal that `role.md` needs updating. Stays inline because reflection needs the current session context — a fresh-booted subagent wouldn't have it. Detailed instructions in `lore-framework/docs/process-reflection.md`.

**Phase 2 — Merge** (`/lr:merge`): runs in **parallel subagents, one per active agent**. Each `general-purpose` subagent boots as its target agent and integrates that agent's reflections into its `lore/`, `lore-context.md`, and `role.md`. Cleans up `reflections/`. Does **not** commit — phase 4 handles that. Detailed instructions in `lore-framework/docs/process-merge.md`. See `merge-in-booted-subagents.md` and `reflect-merge-execution-asymmetry.md`.

**Phase 3 — Summarize** (`/lr:summarize`, v7+, expanded v8): composed inline by the host. Writes the canonical session-wide narrative summary to the host agent's `sessions/YYYY/MM/` directory with a UUIDv4 in frontmatter. **As of v8**, also writes a short guest summary into each attached guest's repo when that guest had lore updates in phase 2 — same session UUID, slim frontmatter pointing back to the host summary. Consultants get no summary. Detailed instructions in `lore-framework/docs/summarize.md`. See `session-summaries-feature.md`.

**Phase 4 — Commit and Push** (v8+, only from `/lr:finalize`): one commit per touched repo with a mandatory review gate, then push. Commit message default: `Finalize session <short-uuid>`. Only `/lr:finalize` touches git at the end; standalone `/lr:reflect`, `/lr:merge`, and `/lr:summarize` leave all changes uncommitted for the user to review and commit themselves.

All four phases combined: `/lr:finalize`.

## Why merge moved from inline to subagents (v8)

Prior to v8, merge ran inline in a single-agent session and only dispatched subagents when guests were attached. v8 makes subagent execution uniform — a single-agent session just spawns one subagent. Rationale: booting gives each subagent the agent's role perspective as the natural lens for merge decisions (same pattern as `/lr:consult`); subagent context isolation keeps session noise out of merge reasoning; parallel execution speeds up multi-agent finalizes. The asymmetry with reflect (which stays inline) is deliberate — see `reflect-merge-execution-asymmetry.md`.

**The host must retain each merge subagent's return value through to phase 3.** Summarize composes each guest summary from (a) the host summary, (b) session memory of what the guest contributed, and (c) the merge subagent's return for that guest — so dropping those returns after phase 2 loses the lore-changes list for guest summaries.

## Per-agent iteration when guests are attached (v4+)

If one or more guests are attached to the host session via `/lr:attach`, phases 1 and 2 iterate per active agent (host-first). Phase 3 runs **once, session-wide**, from the host's perspective (v7+), and in v8+ adds a short guest summary to each attached guest's repo that had lore updates.

- Each agent writes to its own `reflections/` directory.
- Each merge subagent writes to that agent's subtree (e.g., `agents/<name>/`) so history stays clean per agent.
- Topics that legitimately matter to multiple agents may appear in multiple agents' lore — shared knowledge is allowed and preferred over each agent re-learning it separately.
- Some session noise leaking into an iteration is acceptable; role-based filtering is a guide, not a strict gate.

Single-agent sessions reduce phases 1 and 2 to a single pass (one inline reflect iteration, one merge subagent).

## Commit centralization rationale (v8)

In v7, each merge committed its own changes per agent, and summarize stayed uncommitted. v8 centralizes commit+push into phase 4: one commit per touched repo, one push. Reasons:

- **Simpler mental model.** A session produces one commit per repo titled `Finalize session <short-uuid>`. History reads as one session = one commit.
- **Single review gate per repo** instead of multiple gates per phase.
- **Failure handling moved, not weakened.** If summarize fails, commit reflect+merge output alone. If a merge subagent failed in a repo, don't commit in that repo. The v7 "summarize is non-blocking" property is preserved.
- The v7 robustness argument (merge output safe on disk if summarize fails or user aborts) was weaker than it looked — merge writes survive in the working tree anyway; they just need committing. Phase 4 with fallback-on-summarize-failure covers the same ground with one commit instead of two.

Trade-off acknowledged: if the user interrupts mid-finalize (ctrl-C between phases), nothing is committed. Both v7 partial-commit and v8 nothing-committed are recoverable — v8 just fails cleaner.

## Push conflict resolution (v8)

When phase 4 push is rejected due to concurrent writes inside an agent subtree (e.g., two users finalized the same agent), `docs/resolve-conflicts.md` runs one `general-purpose` subagent per conflicted agent, each booted as its target, capped at 3 total attempts. Scope is agent subtree content only (lore, lore-context, role); conflicts outside agent subtrees hand back to the user. See `push-conflict-resolution.md`.

## Related topics

- `session-summaries-feature.md` — summary feature specifics, including v8 guest summaries
- `merge-in-booted-subagents.md` — merge execution model in detail
- `reflect-merge-execution-asymmetry.md` — why reflect is inline and merge is in subagents
- `push-conflict-resolution.md` — what happens when phase 4 push is rejected
- `attach-pattern.md` — host/guest model and what changes on attach
- `lore-search-pattern.md` — recall fan-out (the read-side counterpart to per-agent finalization)
- `skill-doc-pattern.md` — `docs/finalize.md` as the orchestration home; the skill file is a thin pointer

# Session Summaries (v7, expanded v8)

Introduced in v7 as the third phase of finalization — capturing session narrative alongside lore's capture of session learnings. Expanded in v8 with short guest summaries.

## What it is

A model-composed markdown file written at finalization, committed to the host agent's repo. Complements lore: lore records *what was learned*; summaries record *what happened*.

**Host summary file layout:** `<lore-agent-repo>/agents/<host-agent>/sessions/<YYYY>/<MM>/<YYYY-MM-DD>-<short-uuid>.md`. Year/month nesting prevents single-directory bloat. Short UUID (8 hex chars) in filename; full UUIDv4 in frontmatter.

**Host frontmatter:** `uuid`, `start`, `end`, `host_agent`, `host_repo`, `participants`, `username`, `full_name`, `topics` (free-form kebab-case tags for later analysis), `artifacts` (list of `{path, kind}` entries), `consulted`.

**Body:** a 3–7 paragraph narrative in past tense, third person, covering context → what happened → plot twists → where it landed → next steps. The process doc contains the exact narrative prompt.

## Guest summaries (v8)

When one or more guests are attached via `/lr:attach` and a guest has **lore updates in phase 2**, v8 writes a short record into that guest's own repo at `agents/<guest>/sessions/YYYY/MM/<date>-<short-uuid>.md`. Guests attached but with no lore updates get nothing. Consultants (`/lr:consult`) never get a summary — they remain ephemeral, recorded only in the host summary's `consulted` frontmatter.

**Guest summary shape:**

- **Same session UUID as the host summary.** One grep finds host summary + every guest summary + the private Claude Code JSONL.
- **Slim frontmatter:** `uuid`, `date`, `role: guest`, `host_agent`, `host_summary_repo`, `host_summary_path`, `lore_changes`. The `host_summary_repo` / `host_summary_path` split (review outcome) keeps the path robust across checkout layouts — path is repo-relative, not domain-relative.
- **Short body:** one participation sentence, one contribution sentence, bulleted lore updates with one-line reasons, back-reference to the host summary. No plot-twists, no next-steps — those live in the canonical host narrative.
- **Composed by the host inline in phase 3**, from (a) the host summary just composed, (b) session memory of what the guest contributed, and (c) the merge subagent's return for that guest. No additional subagents are spawned for summarization.

**Privacy:** guest repos may have different visibility than the host's. The review gate (phase 3) shows every summary for approval; the approver must consider each guest summary against its destination repo specifically, not uniformly. Individual guest summaries can be dropped at review without blocking the host or other guests.

The design chose pointer-preferring minimalism over full narrative duplication across repos — consistent with the `/lr:consult` precedent where handover is by pointers, not content copies.

## Key design decisions

**Session-wide narrative, per-repo pointer records.** Host summary is the one canonical narrative of the session. Guest summaries are thin pointers back to it, existing so each guest's own repo carries evidence that the guest participated.

**Host summary lives in the host's repo.** The host agent "owns" the session narrative. v8's guest-summary addition resolves the previous v7 limitation where cross-repo guests left no trace in their own repos.

**UUID correlation across host + guests + private JSONL.** The summary's UUIDv4 is echoed in the agent's user-visible output during summarize. That echo lands in the Claude Code session JSONL naturally. A single UUID now correlates (a) the host summary, (b) every guest summary in each guest's own repo, and (c) the private JSONL on the user's machine. See `jsonl-session-files-investigation.md`.

**Mandatory review gate.** The composed summary(ies) are shown to the user before any file is written. Consistent with the show-before-persist principle. No automated privacy scrubbing — judgment + review is the defence.

**Additive and non-blocking.** Summarize runs after reflect + merge. Its failure never rolls back reflect or merge. Disk errors, model errors, user aborts → report and continue. In v8, if summarize fails, phase 4 still commits reflect+merge output alone.

**No migration required for the feature.** `sessions/` directories are created on demand. Both v7 and v8 extensions of this feature are additive — no schema changes to existing repos.

## Why we didn't parse the JSONL

The initial proposal was to parse Claude Code's internal session JSONL files, filter technical noise, and use the result for both reflection and archive. Investigation (captured in `jsonl-session-files-investigation.md`) showed real obstacles: format is proprietary, `~/.claude/sessions/<pid>.json` goes stale after `/clear`, cwd encoding is lossy, filtering decisions are non-obvious, and any archive becomes a long-lived copy of sensitive material.

The pivot to model-composed markdown sidesteps all of these. The cost is that summaries reflect the model's in-context memory of the session (lossy on long sessions due to compaction), tracked as improvement rather than blocker.

## Integration with finalize (v8)

`/lr:finalize` now runs reflect → merge → summarize → commit+push. `/lr:summarize` standalone still works for mid-session checkpoints or for sessions without lore changes worth recording. Standalone summarize does not commit — the user commits what they want to keep. See `finalization-process.md`.

## Known limitations (tracked in workdir/framework-improvements.md)

1. **Compaction-aware narrative quality.** Long sessions may have earlier turns compressed out of the model's context. The prompt instructs the model to say so plainly rather than confabulate.
2. **Reliable start-time capture.** Start time is best-effort from the model's session memory, rounded to nearest 5 minutes. End time is exact.

(The former "cross-repo guest participation" limitation is **resolved in v8** by guest summaries.)

## Files

- `skills/summarize/SKILL.md` — thin skill pointer (skill-doc-pattern)
- `docs/summarize.md` — authoritative process, frontmatter schemas (host + guest), narrative prompt, failure modes
- `docs/finalize.md` — phase 3 reference point; v8 orchestration home
- `docs/conventions.md` — `sessions/` directory in the agent-repo tree
- `release-notes/7.md` — v7 user-facing description (introduction)
- `release-notes/8.md` — v8 user-facing description (guest summaries, four-phase finalize)

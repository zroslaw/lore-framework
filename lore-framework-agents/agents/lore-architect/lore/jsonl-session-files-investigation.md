# Claude Code Session JSONL Files — Investigation Notes

Notes on Claude Code's internal session files, gathered while exploring whether to parse them for session summaries. The framework ultimately chose not to depend on this format, but the findings remain useful for any future revisit.

## File location

**Path pattern:** `~/.claude/projects/<encoded-cwd>/<sessionId>.jsonl`

Where `<encoded-cwd>` is the absolute working-directory path with every `/` replaced by `-` (including the leading `/`). Example: `/Users/yaroslav/Documents/git-repos` becomes `-Users-yaroslav-Documents-git-repos`.

**Encoding is lossy.** Existing `-` characters in path names are preserved, so `/a-b/c` and `/a/b/c` both encode to `-a-b-c`. Rare in practice but possible; the `cwd` field inside each JSONL line is the canonical disambiguator.

## Format

JSON Lines. Each line is a self-contained JSON object with a `type` field. Observed types:

- `user` — user messages (incl. tool results)
- `assistant` — assistant messages (with `requestId`, message content blocks)
- `system` — system reminders / hook outputs / internal telemetry (categorized by `subtype`: `local_command`, `turn_duration`, `away_summary`, etc.)
- `attachment` — file attachments from the user
- `file-history-snapshot` — file-state bookkeeping
- `last-prompt` — marks the most recent prompt

Common fields across message types: `parentUuid`, `isSidechain`, `type`, `uuid`, `timestamp` (ISO 8601 UTC), `userType`, `entrypoint`, `cwd`, `sessionId`, `version`, `gitBranch`. `isMeta: true` marks system-injected synthetic user messages.

## Resolving the current sessionId

Three mechanisms exist, all with gaps:

1. **`~/.claude/sessions/<pid>.json`** — runtime registry keyed by CC process PID. Contains `pid`, `sessionId`, `cwd`, `startedAt`, `version`, `kind`, `entrypoint`. **But it goes stale on `/clear`** — the PID file continues to reference the pre-clear sessionId while the active session writes to a new file.
2. **Environment variables** — `CLAUDE_CODE_ENTRYPOINT`, `CLAUDE_CODE_SSE_PORT`, `CLAUDECODE` exist, but no `CLAUDE_SESSION_ID`.
3. **Most-recently-modified `.jsonl` in `projects/<encoded-cwd>/`** — pragmatic but ambiguous if multiple CC instances share a cwd. Cross-check by opening the candidate file, reading its `sessionId` field and `cwd` field from any line.

None of these three is fully reliable on its own.

## Why we chose not to parse it

- **No public stability contract.** Internal fields (`promptId`, `requestId`, `parentUuid`, `isSidechain`, `isMeta`) suggest the schema can change without notice.
- **Privacy surface.** The file contains complete tool results, including any file content read, any environment variables that leaked into a bash result, etc. Any long-lived archive would be a copy of all of that.
- **Filtering is a real design problem.** Tool calls and results are simultaneously the richest signal (what was done) and the noisiest content (gigantic bash dumps, file contents). Drawing the line is nontrivial.
- **Session boundary ambiguity.** `/clear` rotates to a new JSONL. Whether "the session" means since boot or since last clear is a product decision, not a tech one.

## UUID correlation (our alternative)

Instead of parsing the JSONL, framework v7+ uses a UUIDv4 echoed in the agent's user-visible output during summarize. That echo lands in the JSONL naturally as part of the assistant turn. Users can later `grep` their own `~/.claude/projects/` for the UUID to find the raw session — correlation works entirely on the user's machine, no copy of the JSONL is ever shared.

**v8 update:** the same UUID now spans multiple summary files — the host summary plus one short guest summary per attached guest that had lore updates. A single grep still finds all related records: host summary + every guest summary + the private JSONL. This is intentional — one session UUID, one narrative thread, any number of per-repo pointer records, and the private transcript all share the same identifier.

## Minimal safe uses (not taken)

If the framework ever needs a single piece of information from the JSONL, the safest targets are `timestamp` on the first line (session start time) and the set of unique `sessionId` values (for session grouping). Everything else is risk-weighted against the privacy and stability concerns.

## See also

- `session-summaries-feature.md` — the feature that was built instead, and why; now including v8 guest summaries
- `workdir/framework-improvements.md` — backlog item for reliable start-time capture references this investigation

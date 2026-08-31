# Takeover (BETA)

> **Audience note.** This doc backs the `/lr:takeover` skill. It is executed by the engine's agent when the user invokes the skill.

Take over a session recorded by another coding engine (or an earlier session on this one) and continue it here with its context restored. A session that died mid-task — rate limit, crash, engine switch — is not lost: its log is converted into a **takeover digest** the current session loads as prior context.

The mechanical work lives in `<framework-root>/scripts/session-takeover` (python3, stdlib-only — same dependency footprint as `lr-wait`). It parses an engine-native session log into a unified message list and renders the digest. The skill's job is orchestration: discover sessions, ask the user, load the digest, and resume the work faithfully.

> **If the script fails to run**, apply the **Script Fallback Contract** (`<framework-root>/docs/conventions.md`): this is an *implementation* script, so report the failure with the command and error rather than improvising a manual substitute, and never report the operation as done.

## Step 0 — Announce

Print this to the user before doing anything else, filling in any `<placeholder>`:

> Picking up a session that ended somewhere else. A session that died mid-task — a crash, a rate
> limit, or you simply switched tools — still left a log behind; I read it and rebuild it into a
> digest this session continues from. **It works across Claude Code, Codex, and Cursor, so the tool
> you started in doesn't have to be the one you finish in.** I'll show you the candidates and let
> you pick.

## Engine support

| Engine | Discover | Convert |
|---|---|---|
| Codex (`~/.codex/sessions/`) | yes | yes |
| Claude Code (`~/.claude/projects/`) | yes | yes |
| Cursor (`~/.cursor/chats/` + `~/.cursor/projects/.../agent-transcripts/`) | yes | yes — ordered JSONL transcript; tool results paired from `store.db` when present |

Cursor conversion reads `agent-transcripts/<session-uuid>/<session-uuid>.jsonl` for message order and user/assistant/tool-call content. Tool **results** are loaded from the matching `store.db` under `~/.cursor/chats/` and paired by batch-window name matching (parallel tool calls may complete out of JSONL order; same-name parallel batches set `pairing_uncertain` in the digest). Some assistant text is stored as `[REDACTED]` at rest and is omitted from the digest. Listing timestamps are shown in the **local timezone**. Trust on-disk state over the digest when they disagree.

## Inputs

- Optional: `<session-id | log-path>` — a session id (prefix is enough), an absolute path to a Cursor agent-transcript `.jsonl`, or a Cursor `store.db` path (redirects to the sibling JSONL by session uuid).

## Procedure

### With no argument — explore and ask

1. Run `<framework-root>/scripts/session-takeover --list` (Bash-tool timeout ~30s; add `--all` only if the user asks about test-fixture sessions).
2. Show the user a compact table of what was found — per engine: last-updated time, short id, title, model/status when known, and cwd when it differs from the current workspace.
3. Ask which session to take over. Do not pick one yourself — recency is not intent.
4. Continue with the chosen id below.

### With a session id or path — take over directly

1. Run the script with the token and write the digest to a temp file:
   `<framework-root>/scripts/session-takeover <token> -o "${TMPDIR:-/tmp}/lr-takeover-<token>.md"`
   On an ambiguous prefix the script lists the candidates — relay them and ask the user.
2. **Read the digest file fully into context.** This is the point of the skill: the digest *is* the restored session. Do not summarize it from the file listing alone.
3. **Boot the right identity first, if any.** If the digest shows the recorded session booted a lore agent (a boot skill invocation near the top, or the assistant confirming "Loaded as `<agent>`"), and that agent is not already active here, boot it via the standard boot flow (`agent-boot.md`) **before** acting on the digest — the takeover continues that agent's work, so its role and lore must be loaded. If the digest shows no lore agent, skip this.
4. **Verify on-disk state before continuing.** The digest's footer marks where the recording stopped; the last turns say what was in flight. Check the files/repos the session was touching — the tail of a dying session may claim work it never finished (e.g. a script rewritten but never run).
5. Confirm the takeover to the user in a few sentences: what the session was about, where it stopped, what appears unfinished, and what you propose to do next. Then continue the work as if the digest's conversation were your own history — the user's instructions recorded there still stand unless they say otherwise.

## Boundaries

- **Read-only on the source.** Never modify or delete the engine-native session logs. The digest is a derived artifact; the temp file may be discarded after loading.
- **A takeover is a continuation, not a finalization trigger.** If the taken-over session was a lore agent session, its unfinalized knowledge is preserved the normal way — by the user triggering `/lr:reflect` / `/lr:finalize` at the end of *this* session.
- Tool calls in the digest are one-line summaries — enough to follow the work, not enough to replay it. Trust the on-disk state over the digest when they disagree.

## See Also

- `agent-boot.md` — boot flow used when the digest names a lore agent.
- `wait.md` — the other session-continuity primitive (waiting for external events vs restoring lost context).
- `finalize.md` — how session knowledge is durably preserved; takeover is the recovery path for sessions that never got there.
- Cursor pairing details and per-engine log layouts live in the lore-architect dev repo: `lore/cursor-takeover-batch-pairing.md`, `lore/engine-session-log-formats.md`, `lore/takeover-feature.md`.

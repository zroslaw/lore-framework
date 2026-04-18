# Session Summarization Process

This process is triggered at the end of a session, as the final phase of finalization (after reflect + merge) or directly via `/lr:summarize`. It writes short, committable markdown records of what happened during the session.

The host agent always receives a **full summary** in its own `sessions/` directory. Each attached guest that had lore updates during merge additionally receives a **short guest summary** in its own repo, linking back to the host's canonical record. All summaries for a session share the same UUID. Consulted agents receive nothing — their involvement is recorded in the host summary only.

Summaries are **public artifacts** (committed to each respective agent repo). They complement lore — lore captures *what was learned*, summaries capture *what happened*.

## Relationship to reflect and merge

- **Reflect and merge** iterate per active agent (host + each attached guest) and update each agent's lore.
- **Summarize** runs **once, session-wide**, composed by the host from its perspective. The host summary is the canonical narrative; short guest summaries link back to it.
- Summarize is **additive and non-blocking**: if it fails (disk, model, user aborts), reflect and merge stay committed.
- Summarize runs **after** merge so the host narrative can reference the lore changes just made, and so guest summaries can enumerate those changes.

## File layout

**Host summary:**
```
<lore-agent-repo>/agents/<host-agent>/sessions/<YYYY>/<MM>/<YYYY-MM-DD>-<short-uuid>.md
```

**Guest summary (per attached guest with lore updates):**
```
<guest-repo>/agents/<guest-agent>/sessions/<YYYY>/<MM>/<YYYY-MM-DD>-<short-uuid>.md
```

- `<lore-agent-repo>` / `<guest-repo>` — the respective agent's repo (may be the same repo if host and guest share one)
- `<host-agent>` / `<guest-agent>` — the respective agent's directory name
- `<YYYY>/<MM>/` — year and zero-padded month, avoids single-directory bloat over time
- `<short-uuid>` — first 8 hex characters of the session UUIDv4; the full UUID lives in frontmatter and is shared across host and guest summaries for the same session

Directories are created on demand by this process. No pre-existing `sessions/` directory or migration is required.

## Frontmatter schema

```yaml
---
uuid: 550e8400-e29b-41d4-a716-446655440000
start: 2026-04-18T07:40:00Z
end: 2026-04-18T09:30:00Z
host_agent: lore-architect
host_repo: lore-agents
participants:
  - agent: lore-architect
    repo: lore-agents
    role: host
  - agent: masschallenge-judge
    repo: lore-agents
    role: guest
username: yaroslav
full_name: Yaroslav Roslaw
topics: [session-summaries, finalization]
artifacts:
  - { path: lore-framework/docs/summarize.md, kind: created }
  - { path: lore-framework/skills/summarize/SKILL.md, kind: created }
consulted: []
---
```

Field notes:
- **`uuid`** — UUIDv4 generated this session. Required.
- **`start`** / **`end`** — ISO 8601 UTC. `end` is the time summarize runs. `start` is best-effort from the agent's memory of when the session began — acceptable to round to nearest 5 minutes. See framework improvements backlog for planned reliable capture.
- **`host_agent`** / **`host_repo`** — the agent that hosted this session (the originally booted agent).
- **`participants`** — host + guests. `role` is `host` or `guest`. `repo` may differ across participants when guests come from a different lore agent repo.
- **`username`** / **`full_name`** — identity of the user running the session. Optional; omit fields that can't be determined.
- **`topics`** — free-form kebab-case tags for later analysis. Reuse tags already seen in prior summaries rather than inventing synonyms.
- **`artifacts`** — files created, modified, or deleted during the session. `kind` is `created`, `modified`, or `deleted`. Paths relative to the domain root.
- **`consulted`** — agents queried via `/lr:consult` during this session. List of `{ agent, repo }` entries. Empty array if no consults.

Unknown fields are tolerated by design — the schema is additive.

## Guest frontmatter schema

Guests use a slimmer schema that references the host summary:

```yaml
---
uuid: 550e8400-e29b-41d4-a716-446655440000
date: 2026-04-18
role: guest
host_agent: lore-architect
host_summary_repo: lore-agents
host_summary_path: agents/lore-architect/sessions/2026/04/2026-04-18-550e8400.md
lore_changes:
  - { path: lore/api-retry-behavior.md, kind: created }
  - { path: lore-context.md, kind: modified }
---
```

Field notes (guest schema):
- **`uuid`** — same UUIDv4 as the host summary. This is the correlation key across host summary, guest summaries, and the private JSONL.
- **`date`** — session date (same `YYYY-MM-DD` as the host summary).
- **`role`** — always `guest` in guest summaries.
- **`host_agent`** — directory name of the agent that hosted this session.
- **`host_summary_repo`** — repo directory name that owns the host summary (e.g., `lore-agents`). Separate from path so consumers can resolve the repo root in their own checkout.
- **`host_summary_path`** — path to the host summary **relative to the `host_summary_repo` root**, not domain root. Robust across different checkout layouts.
- **`lore_changes`** — files the guest's merge subagent touched during this session. Paths are relative to the guest's `agents/<guest-name>/` directory. `kind` is `created`, `modified`, or `deleted`.

Guest summaries deliberately omit `start`/`end`/`artifacts`/`consulted`/`topics`/`username`/`full_name` — those belong to the host's canonical record and are one `host_summary_path` hop away.

## Body structure

```markdown
# <one-line descriptive title>

<narrative — 3–7 paragraphs, past tense, third person>

## Consultations
<only if any /lr:consult calls occurred during the session>
- **<agent-name>** — brief summary of what was asked and what came back,
  if the exchange materially shaped the session.
```

Title style: verb-led or noun-phrase, under ~10 words, specific (e.g., "Designed session summary feature for lore framework", not "Session work").

## Guest body structure

```markdown
# <title — typically the same as the host summary title>

Participated as a guest in a session hosted by **<host-agent>** (`<host_summary_repo>`).
Helped with <one-line summary of contribution>.

## Lore updates

- `<path>` — <one-line why this was added/updated>
- `<path>` — <one-line why this was added/updated>

Full session narrative: `<host_summary_repo>/<host_summary_path>` (same UUID).
```

Keep guest bodies short: one participation sentence, one contribution sentence, a bulleted list of lore updates with one-line reasons, and the back-reference to the host summary. No plot-twists section, no next-steps section — those belong in the host's canonical record. If a reader wants the full story, the back-reference takes them there.

## Narrative prompt

When composing the narrative paragraphs, use this exact structure:

```
Write the session summary in 3–7 paragraphs, past tense, third person
("The session opened with…", "The user pushed back when…"). Cover, in order:

1. Context — what the user came in with: the problem, idea, question,
   or task. What was the starting state and motivation?

2. What happened — the substantive work and decisions. Files touched,
   approaches tried, things decided or built. Focus on outcomes, not every
   keystroke.

3. Plot twists — surprises, corrections, dead ends, assumptions that got
   overturned mid-session. If the direction changed, say why.

4. Where it landed — end state. What was committed, what's deferred, what's
   unresolved. Be honest about incomplete pieces.

5. Next steps — open threads, pending decisions, follow-ups.

Guidance:
- Specific over abstract: name files, decisions, components.
- Public-audience aware: no secrets, credentials, internal client names,
  or details the user wouldn't want shared. If unsure, ask before writing.
- Avoid listicles — flowing prose reads better across many summaries.
- If earlier parts of the session are hazy (context compaction), say so
  plainly rather than inventing detail.
```

## Process

### Step 1: Generate the session UUID

```bash
python3 -c "import uuid; print(uuid.uuid4())"
```

Record the full UUID. Derive `<short-uuid>` = first 8 hex chars (before the first `-`).

### Step 2: Resolve host, participants, and timestamps

- **Host agent and repo** — from the booted agent context. If running inside finalize after attach, the host is the originally-booted agent, not a guest.
- **Participants** — host + any agents currently attached via `/lr:attach`. For each, record `agent`, `repo`, `role`.
- **`end`** — now, ISO 8601 UTC: `date -u +%Y-%m-%dT%H:%M:%SZ`.
- **`start`** — best-effort from session memory, rounded to nearest 5 minutes. If memory is unclear, estimate from observable artifacts (e.g., the earliest timestamp on a file you created this session).

### Step 3: Identify the user

Run, in order, until you have a username:

```bash
id -un 2>/dev/null
```

For full name, try in order, stopping at first non-empty result:

```bash
id -F 2>/dev/null                       # macOS real name
git config user.name 2>/dev/null        # fallback
```

If the username is empty, omit `username`. If full name is empty, omit `full_name`. Do not prompt the user for missing identity fields.

### Step 4: Collect the artifacts list

From the session's in-context memory, list files created, modified, or deleted during the session. For each: `path` (relative to domain root) and `kind` (`created` / `modified` / `deleted`).

When uncertain, cross-check with `git -C <lore-agent-repo> status` and `git -C <lore-agent-repo> diff --name-status <base>..HEAD` in the relevant repos. The artifacts list is a curated record, not an exhaustive git diff — include files that matter to the session's story, skip incidental touch-ups.

### Step 5: Collect consulted agents

List all agents queried via `/lr:consult` during this session, with their repo. Empty list if none.

### Step 6: Compose the host narrative

Use the narrative prompt above. 3–7 paragraphs, past tense, third person. Title under 10 words.

### Step 7: Choose topics tags

Glance at existing frontmatter in prior summaries to reuse established tags:

```bash
ls <lore-agent-repo>/agents/<host-agent>/sessions/**/*.md 2>/dev/null | head -20
```

If any matches exist, read a few to scan their `topics` field. Prefer reuse over invention. Tags are kebab-case lowercase, typically 3–7 per summary.

Fresh repos with no prior summaries naturally introduce their own tag vocabulary — that's expected.

### Step 8: Assemble the host document

Combine frontmatter + title + narrative + optional Consultations section.

### Step 9: Compose guest summaries (if applicable)

For each attached guest whose merge subagent reported lore updates (any topic added/modified, or `lore-context.md`/`role.md` modified), compose a short guest summary. A guest that was attached but had no lore updates gets no summary. If no guests were attached at all, skip this step.

Derive each guest summary from:

- **The host summary** you just composed — title, overarching framing.
- **Your session memory** — what this guest specifically contributed during the session.
- **The merge subagent's return for this guest** — which files changed and why.

Assemble guest frontmatter (see **Guest frontmatter schema** above) and guest body (see **Guest body structure** above). Keep each one short — a participation sentence, a one-line contribution summary, a bulleted list of lore updates with one-line reasons, and the back-reference.

### Step 10: Show to the user and wait for approval

Display the host summary and all guest summaries to the user in one batch. The user may:

- **Approve all** — proceed to write
- **Request edits** — revise specific summaries based on feedback and show again
- **Skip the whole session** — no files are written, no UUID is emitted (nothing to correlate to). Proceed directly to step 13.
- **Skip individual guest summaries** — write the host summary and only the approved guest summaries; drop the rest silently.

This review gate is mandatory. Consistent with the framework's general principle: show before persist.

### Step 11: Write the files

Write the host summary first, then each approved guest summary. Create directories as needed, e.g.:

```bash
mkdir -p <lore-agent-repo>/agents/<host-agent>/sessions/<YYYY>/<MM>
mkdir -p <guest-repo>/agents/<guest-agent>/sessions/<YYYY>/<MM>
```

Use the Write tool for each file on its final path; it overwrites if needed.

### Step 12: Do not commit

Summarize does not commit. When invoked as part of `/lr:finalize`, the final commit+push step covers the host and guest summaries along with reflect/merge output (each repo's changes go into its own commit). When invoked standalone via `/lr:summarize`, leave the new files uncommitted and let the user commit them themselves.

### Step 13: Emit the UUID in user-visible output

If the host summary was written, close the summarize step with a block that prints the UUID and paths in a grep-friendly format:

```
✓ Host summary written: <path-to-host-summary>
✓ Guest summaries written: <count>
  - <path-to-guest-summary-1>
  - <path-to-guest-summary-2>
Session UUID: <full-uuid>
```

Omit the guest summaries block if none were written.

The UUID line is required discipline — it's the only mechanism by which the public summaries can later be correlated to the Claude Code JSONL on the user's machine. The user can later run:

```bash
grep -rl "<full-uuid>" ~/.claude/projects/
```

to find the raw session JSONL if they want to replay or inspect it. The same UUID also finds every host and guest summary for the session in the domain.

If summarize was skipped in step 10, do not emit a UUID line.

## Failure modes

| Failure | Response |
|---|---|
| Model cannot produce the host narrative | Report error, do not write any files, do not roll back reflect or merge |
| Model cannot produce a specific guest summary | Write the host summary and other guest summaries; skip the failing one with a note |
| User rejects / asks to skip the whole session | No files written, no UUID emitted |
| User rejects an individual guest summary | Drop that guest summary silently; write everything else |
| Disk write fails for any file | Report the failure with the composed text so the user can copy it manually; other approved files still get written |
| `id -un` / `id -F` return empty | Omit the affected field, proceed |
| Directory creation fails | Report error for that path, do not write there; other paths proceed |
| Early session hazy due to compaction | Narrative says so plainly; do not fabricate detail |

Summarize failure never rolls back or poisons reflect or merge.

## Privacy

Session summaries are committed to potentially public repos — and with guest summaries, **possibly multiple repos with different visibility settings**. A guest attached from a different repo may land in a repo with broader or narrower visibility than the host's. Two layers of defence:

1. **Narrative guidance** (in the prompt above): public-audience aware, no secrets or sensitive specifics, ask the user if unsure. Guest summaries inherit the same constraint — the one-line contribution summary should be as safe to publish as the host narrative.
2. **Mandatory review gate** (step 10): nothing is written until the user has seen the composed host summary **and** every guest summary and approved the batch. When reviewing guest summaries, consider each one **against its destination repo specifically** — content acceptable in the host's repo may not be acceptable in a differently-visible guest repo. Individual guest summaries can be dropped at review time without blocking the host or other guests.

No automated scrubbing in v1. The framework relies on the agent's judgment plus the user's review.

## Consult handling

`/lr:consult` invocations do not trigger their own finalization — the consultant subagent exits without any state changes. Instead, this session's summary records the consult in:

- `consulted` frontmatter field (agent + repo)
- Optional **Consultations** section in the body, if the exchange materially shaped the session

If no consults happened, omit the section and use `consulted: []`.

## Standalone invocation

`/lr:summarize` can be called on its own without running reflect or merge first. In that case, skip any references to "after merge" — write a summary of the session as it stands now. This is useful as a mid-session checkpoint or for sessions where no lore changes were produced but the work itself is worth recording.

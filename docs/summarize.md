# Session Summarization Process

This process is triggered at the end of a session, as the final phase of finalization (after reflect + merge) or directly via `/lr:summarize`. It writes a short, committable markdown record of what happened during the session into the host agent's `sessions/` directory.

Session summaries are **session-wide** (one file per session, regardless of attached guests) and **public artifacts** (committed to the agent repo). They complement lore — lore captures *what was learned*, summaries capture *what happened*.

## Relationship to reflect and merge

- **Reflect and merge** iterate per active agent (host + each attached guest) and update each agent's lore.
- **Summarize** runs **once, session-wide**, from the host agent's perspective. Participants are recorded in frontmatter.
- Summarize is **additive and non-blocking**: if it fails (disk, model, user aborts), reflect and merge stay committed.
- Summarize runs **after** merge so the narrative can reference the lore changes just made.

## File layout

```
<lore-agent-repo>/agents/<host-agent>/sessions/<YYYY>/<MM>/<YYYY-MM-DD>-<short-uuid>.md
```

- `<lore-agent-repo>` — the host agent's repo
- `<host-agent>` — the host agent's directory name
- `<YYYY>/<MM>/` — year and zero-padded month, avoids single-directory bloat over time
- `<short-uuid>` — first 8 hex characters of the session UUIDv4; full UUID lives in frontmatter

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

### Step 6: Compose the narrative

Use the narrative prompt above. 3–7 paragraphs, past tense, third person. Title under 10 words.

### Step 7: Choose topics tags

Glance at existing frontmatter in prior summaries to reuse established tags:

```bash
ls <lore-agent-repo>/agents/<host-agent>/sessions/**/*.md 2>/dev/null | head -20
```

If any matches exist, read a few to scan their `topics` field. Prefer reuse over invention. Tags are kebab-case lowercase, typically 3–7 per summary.

Fresh repos with no prior summaries naturally introduce their own tag vocabulary — that's expected.

### Step 8: Assemble the full document

Combine frontmatter + title + narrative + optional Consultations section.

### Step 9: Show to the user and wait for approval

Display the complete summary to the user. The user may:

- **Approve** — proceed to write
- **Request edits** — revise based on feedback and show again
- **Skip persistence** — the user decides not to commit a summary for this session; proceed directly to step 12 without writing, and do not emit a UUID line (nothing to correlate to)

This review gate is mandatory. Consistent with the framework's general principle: show before persist.

### Step 10: Write the file

Create directories as needed:

```bash
mkdir -p <lore-agent-repo>/agents/<host-agent>/sessions/<YYYY>/<MM>
```

Write the file atomically. Use the Write tool on the final path; it overwrites if needed.

### Step 11: Do not commit

The user reviews and commits the new summary themselves, typically alongside the merge commit from the same finalization. Stage but do not commit.

### Step 12: Emit the UUID in user-visible output

If a file was written, close the summarize step with a line that prints the UUID in a grep-friendly format:

```
✓ Session summary written: <relative-path-to-summary>
Session UUID: <full-uuid>
```

The UUID line is required discipline — it's the only mechanism by which the public summary can later be correlated to the Claude Code JSONL on the user's machine. The user can later run:

```bash
grep -rl "<full-uuid>" ~/.claude/projects/
```

to find the raw session JSONL if they want to replay or inspect it.

If summarize was skipped in step 9, do not emit a UUID line.

## Failure modes

| Failure | Response |
|---|---|
| Model cannot produce a narrative | Report error, do not write a file, do not roll back reflect or merge |
| User rejects / asks to skip | No file written, no UUID emitted |
| Disk write fails | Report error with the composed summary text so the user can copy it manually |
| `id -un` / `id -F` return empty | Omit the affected field, proceed |
| Directory creation fails | Report error, do not write |
| Early session hazy due to compaction | Narrative says so plainly; do not fabricate detail |

Summarize failure never rolls back or poisons reflect or merge.

## Privacy

Session summaries are committed to potentially public repos. Two layers of defence:

1. **Narrative guidance** (in the prompt above): public-audience aware, no secrets or sensitive specifics, ask the user if unsure.
2. **Mandatory review gate** (step 9): nothing is written until the user has seen the composed summary and approved.

No automated scrubbing in v1. The framework relies on the agent's judgment plus the user's review.

## Consult handling

`/lr:consult` invocations do not trigger their own finalization — the consultant subagent exits without any state changes. Instead, this session's summary records the consult in:

- `consulted` frontmatter field (agent + repo)
- Optional **Consultations** section in the body, if the exchange materially shaped the session

If no consults happened, omit the section and use `consulted: []`.

## Standalone invocation

`/lr:summarize` can be called on its own without running reflect or merge first. In that case, skip any references to "after merge" — write a summary of the session as it stands now. This is useful as a mid-session checkpoint or for sessions where no lore changes were produced but the work itself is worth recording.

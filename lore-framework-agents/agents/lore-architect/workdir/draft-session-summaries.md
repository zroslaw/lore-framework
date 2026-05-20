# Design Doc — Session Summaries at Finalization

**Status:** draft · not yet implemented
**Related:** [framework-improvements.md](framework-improvements.md)

## Motivation

Lore captures *what was learned* from a session (distilled, atomic topics). It doesn't capture *what happened* during the session — the narrative, the decisions, the surprises. That history is currently lost when the conversation ends.

Session summaries fill that gap. At finalization, after reflect + merge, the host agent writes a short markdown summary of the session into a structured directory, committable to the agent repo. Over time this becomes a searchable log of framework evolution and a ground-truth record of who did what and when.

**Explicit non-goal:** this is not a replay mechanism. The private Claude Code JSONL session files remain the only complete record; users who want to restore a session can do so on their own machine by grepping for the summary's UUID.

## File layout

```
<host-repo>/agents/<host-agent>/sessions/<YYYY>/<MM>/<YYYY-MM-DD>-<short-uuid>.md
```

- `<host-repo>` = the repo containing the agent booted as the session's host
- `<host-agent>` = that agent's directory name
- `<YYYY>/<MM>/` = year + zero-padded month, to avoid single-directory bloat
- `<short-uuid>` = first 8 hex chars of the UUIDv4 (filename-friendly; full UUID lives in frontmatter)

Dirs are created on-demand by summarize. No migration needed for existing repos.

## Frontmatter schema

```yaml
---
uuid: 550e8400-e29b-41d4-a716-446655440000
start: 2026-04-18T07:40:00Z            # best-effort in v1 (see backlog)
end: 2026-04-18T09:30:00Z              # exact: finalize invocation time
host_agent: lore-architect
host_repo: lore-agents
participants:
  - agent: lore-architect
    repo: lore-agents
    role: host
  - agent: masschallenge-judge
    repo: lore-agents
    role: guest                         # attached via /lr:attach
username: yaroslav                      # from `id -un`
full_name: Yaroslav Smirnov             # from `id -F`, optional
topics: [session-summaries, finalization]   # free-form tags for later analysis
artifacts:                              # files created/edited/deleted this session
  - { path: lore-framework/docs/summarize.md, kind: created }
  - { path: lore-framework/skills/summarize/SKILL.md, kind: created }
consulted: []                           # list of agents queried via /lr:consult
---
```

Fields are **additive** — missing optional fields are fine. Parsers should tolerate unknown fields.

**Tags discipline.** `topics` is free-form but should use kebab-case lowercase and prefer terms already in use across prior summaries. The agent should briefly scan existing `sessions/*/*/*.md` frontmatter for existing tags before inventing new ones, to keep the tag space from fragmenting. Cheap if it skips on failure.

## Body structure

```markdown
# <one-line descriptive title>

<narrative — 3–7 paragraphs, past tense, third person>

## Consultations  (only if any occurred)
- **<agent-name>** — short summary of what was asked and what came back,
  if the exchange carried information worth preserving in the session log.
```

### Narrative prompt (exact text emitted to the model)

```
Write the session summary in 3–7 paragraphs, past tense, third person
("The session opened with…", "The user pushed back when…"). Cover, in order:

1. **Context** — what the user came in with: the problem, idea, question,
   or task. What was the starting state and motivation?

2. **What happened** — the substantive work and decisions. Files touched,
   approaches tried, things decided or built. Focus on outcomes, not every
   keystroke.

3. **Plot twists** — surprises, corrections, dead ends, assumptions that
   got overturned mid-session. If the direction changed, say why.

4. **Where it landed** — end state. What was committed, what's deferred,
   what's unresolved. Be honest about incomplete pieces.

5. **Next steps** — open threads, pending decisions, follow-ups.

Guidance:
- Specific over abstract: name files, decisions, components.
- Public-audience aware: no secrets, credentials, internal client names,
  or details the user wouldn't want shared. If unsure, ask before writing.
- Avoid listicles — flowing prose reads better across many summaries.
- If earlier parts of the session are hazy (context compaction), say so
  plainly rather than inventing detail.
```

## The summarize step (process)

Triggered as a standalone skill (`/lr:summarize`) and as the third phase of `/lr:finalize` (after reflect + merge).

Order of operations:

1. **Generate UUIDv4.** `python3 -c "import uuid; print(uuid.uuid4())"` or equivalent. Derive `<short-uuid>` = first 8 chars.

2. **Resolve host context.** Host agent name + repo are known from boot context. Participants = host + any attached guests (see `attach-pattern.md`).

3. **Identify the user.** `id -un` → username. `id -F` → full name (macOS). If any command fails or returns empty, omit the field. Do not prompt the user for missing values.

4. **Compute timestamps.** `end` = now (ISO 8601 UTC). `start` = best-effort from the model's memory of when the session began; acceptable to round to nearest 5 minutes. Note "start time is approximate" in the improvements backlog.

5. **Collect artifacts list.** From the model's in-context memory of what was created/edited/deleted during the session. `git status` + `git diff --name-status <base>..HEAD` in relevant repos can help if uncertain.

6. **Collect consulted agents.** Any `/lr:consult` invocations during the session.

7. **Compose narrative** using the prompt above.

8. **Choose topics tags.** Briefly scan existing `sessions/*/*/*.md` frontmatter in the host repo for existing tags; prefer reuse over invention.

9. **Assemble frontmatter + body.**

10. **Show the full summary to the user.** The user can request edits, approve, or skip persistence entirely. No file is written until the user approves (per `show-test-before-push` feedback principle).

11. **Write the file.** Create `sessions/YYYY/MM/` directories as needed. Write atomically (write to tmp, rename).

12. **Emit the UUID prominently** in user-visible output. Required discipline — this is the only mechanism by which users can later correlate the public summary to the private JSONL on their machine. Example closing line:

    ```
    ✓ Session summary written: sessions/2026/04/2026-04-18-550e8400.md
    Session UUID: 550e8400-e29b-41d4-a716-446655440000
    ```

13. **Do not commit.** The user reviews the generated file themselves and commits it with their other finalization changes.

## Integration with `/lr:finalize`

`docs/finalize.md` currently orchestrates reflect → merge. After this change, it orchestrates reflect → merge → **summarize**.

- Reflect + merge iterate per active agent (host-first) as they do today.
- Summarize runs **once, session-wide**, after all agents have merged.
- Summarize failure (disk, model, user abort) does **not** roll back reflect or merge. Summary is additive and non-blocking.

## Failure modes

| Failure | Response |
|---|---|
| Model cannot produce a narrative | Show error, skip file write, do not block finalize completion |
| Disk write fails | Show error with the composed summary text so user can copy/save manually |
| User rejects the summary at review | Skip write, do not emit UUID (nothing to correlate to) |
| `id -F` fails / empty | Omit `full_name` field, proceed |
| Directory creation fails | Show error, skip file write |
| Early session hazy due to compaction | Narrative says so explicitly; do not fabricate |

## Privacy conventions

Summaries are committed to a potentially public repo. Two layers of defence:

1. **Narrative guidance** (already in the prompt): public-audience aware, no secrets, ask if unsure.
2. **Mandatory review gate** (step 10): the user must approve before write. Consistent with `show-test-before-push`.

No automated scrubbing in v1 — we rely on the model's judgment plus user review.

## Consult handling

`/lr:consult` invocations do not themselves finalize. Instead, the host session's summary mentions them under a **Consultations** section:

- Which agent was consulted
- What was asked (brief)
- What came back, if it materially shaped the session

If no consults occurred, omit the section entirely.

## What ships in v1

- New skill: `skills/summarize/SKILL.md` (one-line pointer per `skill-doc-pattern.md`)
- New doc: `docs/summarize.md` (the authoritative description of this process)
- `docs/finalize.md` updated to invoke summarize as the third phase
- `docs/conventions.md` mentions the `sessions/` directory convention
- `/lr:check` may or may not get a new check — likely deferred to v2 (verifying summary integrity isn't high-value yet)

## Open questions (non-blocking for draft)

- **Standalone `/lr:summarize` semantics.** Is summarize useful outside finalize? E.g., mid-session "checkpoint" summaries? v1 assumes no — summarize is a finalization phase that can also be invoked directly if the user wants only the summary without reflect+merge. Worth validating.
- **Title generation.** The H1 title is model-written. Should the doc constrain style (e.g., "verb-led", "<10 words")? Probably yes — consistency helps scanning.
- **Cross-linking.** Should narrative paragraphs link to lore topics created/touched this session? Low cost, raises value of the log. Lean yes.

## What this doc doesn't cover

- Actual implementation of the skill/doc files (that's the next step after design approval).
- Changes to `agent-boot.md` to capture session start time reliably (see backlog).
- Analytics/search tooling over the summary corpus (future work).

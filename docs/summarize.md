# Session Summarization Process

This process is triggered at the end of a session, as the final phase of finalization (after reflect + merge) or directly via `/lr:summarize`. It writes short, committable markdown records of what happened during the session.

Here, `<framework-root>` means the parent directory of the `docs/` directory containing this file. If you read this file from an absolute path, use scripts and `VERSION` from that same checkout; do not substitute a different installed plugin cache path.

The host agent always receives a **full summary** in its own `sessions/` directory. Each attached guest that had lore updates during merge additionally receives a **short guest summary** in its own repo, linking back to the host's canonical record. All summaries for a session share the same UUID. Consulted agents receive nothing — their involvement is recorded in the host summary only.

Summaries are **public artifacts** (committed to each respective agent repo). Lore remains the
durable knowledge; summaries capture *what happened* and include a compact audit of what reflection
selected and how merge changed Lore. The audit is not a second copy of the learned knowledge.

## Relationship to reflect and merge

- **Reflect and merge** iterate per active agent (host + each attached guest) and update each agent's lore.
- **Summarize** runs **once, session-wide**, composed by the host from its perspective. The host summary is the canonical narrative; short guest summaries link back to it.
- The host summary's **Learning** section is composed from each active agent's retained Reflection
  outcome and Merge handoff. It records the reflection-to-merge outcome without reconstructing
  deleted reflections or duplicating Lore.
- Summarize is **additive and non-blocking**: if it fails (disk, model), reflect and merge stay committed.
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
framework_version: "29"
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
full_name: Yaroslav Panasyuk
topics: [session-summaries, finalization]
artifacts:
  - { path: lore-framework/docs/summarize.md, kind: created }
  - { path: lore-framework/skills/summarize/SKILL.md, kind: created }
consulted: []
usage:
  models: [claude-sonnet-5]
  models_source: per-message   # per-message | session-level-last-used | unavailable
  tokens:
    input: 123456
    output: 45678
    cache_read: 90000
    cache_creation: 12000
  cost_usd: 4.32
  cost_source: computed        # reported | computed | unavailable
---
```

Field notes:
- **`uuid`** — UUIDv4 generated this session. Required.
- **`framework_version`** — the framework `VERSION` used to write the summary.
- **`start`** / **`end`** — ISO 8601 UTC. `end` is the time summarize runs. `start` is best-effort from the agent's memory of when the session began — acceptable to round to nearest 5 minutes. See framework improvements backlog for planned reliable capture.
- **`host_agent`** / **`host_repo`** — the agent that hosted this session (the originally booted agent).
- **`participants`** — host + guests. `role` is `host` or `guest`. `repo` may differ across participants when guests come from a different lore agent repo.
- **`username`** / **`full_name`** — identity of the user running the session. Optional; omit fields that can't be determined.
- **`topics`** — free-form kebab-case tags for later analysis. Reuse tags already seen in prior summaries rather than inventing synonyms.
- **`artifacts`** — files created, modified, or deleted during the session. `kind` is `created`, `modified`, or `deleted`. Paths relative to the workspace root.
- **`consulted`** — agents queried via `/lr:consult` during this session. List of `{ agent, repo }` entries. Empty array if no consults.
- **`usage`** — token/cost/model totals for the session, from Step 1.5's stats JSON. Host schema only (guests follow `host_summary_path` to reach it — not duplicated). Sub-fields:
  - **`models`** — ordered-unique list of model ids observed this session.
  - **`models_source`** — how the list was gathered: `per-message` (Claude/Codex, full fidelity), `session-level-last-used` (Cursor, only a single session-level `lastUsedModel` is available — not per-message), or `unavailable`.
  - **`tokens`** — `input` / `output` / `cache_read` / `cache_creation` sums. Omitted for engines with no token data (Cursor).
  - **`cost_usd`** — total USD cost. Present only when `cost_source: computed`; omitted otherwise.
  - **`cost_source`** — provenance of the cost: `reported` (engine reported an authoritative dollar figure), `computed` (derived from token totals × a confirmed, cited per-model price — Claude only in v1, and only for models with a known price), or `unavailable` (Codex/Cursor, or any Claude model whose price couldn't be confirmed — no number is guessed).

Unknown fields are tolerated by design — the schema is additive. The `usage` block is additive and tolerant: it is **omitted entirely** when Step 1.5 was skipped or failed, and a consumer that doesn't know it ignores it.

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
- **`uuid`** — same UUIDv4 as the host summary. This is the correlation key across host and guest summaries.
- **`date`** — session date (same `YYYY-MM-DD` as the host summary).
- **`role`** — always `guest` in guest summaries.
- **`host_agent`** — directory name of the agent that hosted this session.
- **`host_summary_repo`** — repo directory name that owns the host summary (e.g., `lore-agents`). Separate from path so consumers can resolve the repo root in their own checkout.
- **`host_summary_path`** — path to the host summary **relative to the `host_summary_repo` root**, not workspace root. Robust across different checkout layouts.
- **`lore_changes`** — files the guest's merge subagent touched during this session. Paths are relative to the guest's `agents/<guest-name>/` directory. `kind` is `created`, `modified`, or `deleted`.

Guest summaries deliberately omit `start`/`end`/`artifacts`/`consulted`/`topics`/`username`/`full_name` — those belong to the host's canonical record and are one `host_summary_path` hop away.

## Body structure

```markdown
# <one-line descriptive title>

<narrative — 3–7 paragraphs, past tense, third person>

## Learning

### <agent-name>

- **What mattered:** <durable lessons, decisions, or operational insights selected in reflection>
- **Lore changes:** <material paths created, updated, consolidated, simplified, or deleted by merge>
- **Not merged:** <remaining reflection topics and reasons, or None.>
- **Issues:** <confidence-affecting merge anomalies or unavailable evidence, or None.>

## Consultations
<only if any /lr:consult calls occurred during the session>
- **<agent-name>** — brief summary of what was asked and what came back,
  if the exchange materially shaped the session.
```

Title style: verb-led or noun-phrase, under ~10 words, specific (e.g., "Designed session summary feature for lore framework", not "Session work").

The **Learning** section is mandatory in every host summary. It is a concise audit, not part of the
3–7 narrative paragraphs. A finalize summary uses one subsection per active agent, in host-first
order, including agents whose reflection or merge failed. The unavailable-state wording is defined
in Process Step 6.5.

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
- Public-audience aware: before writing, explicitly check the summary for
  private PII, secrets, credentials, internal client names, or details the
  user would not want shared. Do not include them. If unsure, ask before writing.
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

### Step 1.5: Resolve usage metadata from the native session log

This step captures aggregate token, cost, and model usage for the host summary. It is a **required attempt** in every summarize/finalize run, but is additive and non-blocking: every failure is warn-and-continue, and summarize proceeds without the `usage` frontmatter block. This step must never write a transcript or archive to an agent repo.

1. **Resolve this session's native log.** The UUID generated in Step 1 has, by now, already appeared in the engine's transcript (the `python3` command that printed it *is* a recorded tool call). Use that to find which native log on disk is this session's:

   ```bash
   <framework-root>/scripts/session-takeover --find-by-uuid <full-uuid> --engine <engine>
   ```

   where `<framework-root>` is the framework root resolved at boot (the dir holding `VERSION`) and `<engine>` is the current engine (`claude`, `codex`, or `cursor`). This prints the resolved native log path on stdout.

   **How to read the result — this is the one spot models get wrong, so follow it exactly:**
   - **A path was printed on stdout → use it and continue to sub-step 2.** This is the success case. It stays the success case *even if a `warning:` line was also printed on stderr* — the warning only means the tool couldn't confirm the UUID and fell back to the most-recently-modified log for this engine (normal for Cursor, whose printed output isn't grep-able; and for any engine whose transcript hasn't flushed the UUID line yet). A stderr warning is **not** a skip signal.
   - **Only skip the rest of this step (warn and continue to Step 2) if the command printed _no path at all_ on stdout, or exited non-zero** — that means there were genuinely no candidate logs from which to calculate usage.

2. **Capture usage stats.** Run the stats verb before assembling final frontmatter:

   ```bash
   <framework-root>/scripts/session-takeover stats <resolved-log> \
     --stats <scratch>/session-stats.json \
     --engine <engine>
   ```

   The stats JSON carries the models list and `models_source`, token totals (or `tokens: null` when the engine doesn't expose them), cost (`cost_usd` + `cost_source`, the latter one of `reported` / `computed` / `unavailable`), `framework_version`, and `started` — the native log's earliest message timestamp, which also feeds Step 2's `start` (see Step 2). The file remains in `<scratch>` and is never committed.

`session-takeover archive` remains available as a manual, dormant maintenance command. Summarize and finalize must not invoke it; any future use or redesign requires an explicit feature decision.

### Step 2: Resolve host, participants, and timestamps

- **Host agent and repo** — from the booted agent context. If running inside finalize after attach, the host is the originally-booted agent, not a guest.
- **Participants** — host + any agents currently attached via `/lr:attach`. For each, record `agent`, `repo`, `role`.
- **`end`** — now, ISO 8601 UTC: `date -u +%Y-%m-%dT%H:%M:%SZ`.
- **`start`** — if Step 1.5 succeeded, prefer the native log's earliest message timestamp from the stats JSON — it's the true session start, strictly more accurate and free (already computed). Otherwise, best-effort from session memory, rounded to nearest 5 minutes; if memory is unclear, estimate from observable artifacts (e.g., the earliest timestamp on a file you created this session).

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

From the session's in-context memory, list files created, modified, or deleted during the session. For each: `path` (relative to workspace root) and `kind` (`created` / `modified` / `deleted`).

When uncertain, cross-check with `git -C <lore-agent-repo> status` and `git -C <lore-agent-repo> diff --name-status <base>..HEAD` in the relevant repos. The artifacts list is a curated record, not an exhaustive git diff — include files that matter to the session's story, skip incidental touch-ups.

### Step 5: Collect consulted agents

List all agents queried via `/lr:consult` during this session, with their repo. Empty list if none.

### Step 6: Compose the host narrative

Use the narrative prompt above. 3–7 paragraphs, past tense, third person. Title under 10 words.

### Step 6.5: Compose the Learning section

Always add `## Learning` after the narrative and before optional `## Consultations`.

For a finalize run, compose one subsection per active agent, in host-first order, from that agent's
retained **Reflection outcome** and **Merge handoff**. Use the current-session reflection themes,
as retained by the host and distilled in the handoff, for **What mattered**; use the handoff's file
actions for **Lore changes**, its residual reflection list for **Not merged**, and its anomalies for
**Issues**. The Reflection outcome distinguishes a real zero-topic result from a failed or
unavailable reflection. Never put a carried-over reflection theme under **What mattered**; preserve
its origin when summarizing a Lore change or residual.

Keep each field to one compact bullet; name material agent-relative paths. Preserve meaningful
merge actions: if the merge consolidated or simplified Lore, say so rather than flattening the
action to "updated." Keep the concrete learned fact or decision and its useful reason in **What
mattered**; a category-only phrase such as "updated the monitoring-tool knowledge" is not enough for
this audit. Include `lore-context.md` and `role.md` only when they materially changed. Summarize the
handoffs; do not reproduce reflection files or Lore prose.

Render empty and unavailable states honestly:

- Reflection completed and produced no topics → **What mattered:** `No durable learning identified.`
- Reflection failed or its outcome is missing → say the reflection outcome is unavailable under
  **What mattered** and explain the failure or missing evidence under **Issues**.
- Merge completed without changing Lore → **Lore changes:** `None.`
- Nothing remained after a successful merge → **Not merged:** `None.`
- Merge failed or its handoff is missing → say the merge outcome is unavailable and identify any
  known pending reflections under **Not merged**; record the failure or missing handoff under
  **Issues**. Never translate absence into "no learning."
- Merge did not run after reflection → report the retained reflection outcome, say **Lore changes:**
  `Not assessed; merge did not run.`, and name pending topics under **Not merged**.
- Both phase outcomes are available, reflection succeeded, and merge completed without anomalies →
  **Issues:** `None.` Earlier missing or failed phase evidence always takes precedence.

When `/lr:summarize` is invoked directly and neither reflection nor merge ran in the current
workflow, write exactly:

```markdown
## Learning

Learning was not assessed because no completed reflection-and-merge handoff was available.
```

If standalone reflection or merge ran earlier in the same session, branch on their retained phase
states using the rules above; do not use the direct-invocation sentence to make a claim about phases
whose state is unknown. Never infer the learning result from a diff.

### Step 7: Choose topics tags

Glance at existing frontmatter in prior summaries to reuse established tags:

```bash
ls <lore-agent-repo>/agents/<host-agent>/sessions/**/*.md 2>/dev/null | head -20
```

If any matches exist, read a few to scan their `topics` field. Prefer reuse over invention. Tags are kebab-case lowercase, typically 3–7 per summary.

Fresh repos with no prior summaries naturally introduce their own tag vocabulary — that's expected.

### Step 8: Assemble the host document

Combine frontmatter + title + narrative + mandatory Learning section + optional Consultations
section.

Add `framework_version` from `<framework-root>/VERSION`.

If Step 1.5 succeeded, add `usage:` from the stats JSON. Include `cost_usd` only when the stats JSON has a non-null value.

### Step 9: Compose guest summaries (if applicable)

For each attached guest whose merge subagent reported lore updates (any topic added/modified, or `lore-context.md`/`role.md` modified), compose a short guest summary. A guest that was attached but had no lore updates gets no summary. If no guests were attached at all, skip this step.

Derive each guest summary from:

- **The host summary** you just composed — title, overarching framing.
- **Your session memory** — what this guest specifically contributed during the session.
- **The merge subagent's return for this guest** — which files changed and why.

Assemble guest frontmatter (see **Guest frontmatter schema** above) and guest body (see **Guest body structure** above). Keep each one short — a participation sentence, a one-line contribution summary, a bulleted list of lore updates with one-line reasons, and the back-reference.

For guest frontmatter, normalize the Merge handoff's semantic action into the closed `kind` schema:
`created` → `created`; `deleted` → `deleted`; and `updated`, `consolidated`, or `simplified` →
`modified`. Preserve the more precise semantic action in the guest body's human-readable reason.

### Step 10: Write the files

Write the host summary first, then each guest summary. Create directories as needed, e.g.:

```bash
mkdir -p <lore-agent-repo>/agents/<host-agent>/sessions/<YYYY>/<MM>
mkdir -p <guest-repo>/agents/<guest-agent>/sessions/<YYYY>/<MM>
```

Use the Write tool for each file on its final path; it overwrites if needed.

### Step 11: Do not commit

Summarize does not commit. When invoked as part of `/lr:finalize`, the final commit+push step covers the host and guest summaries along with reflect/merge output (each repo's changes go into its own commit). When invoked standalone via `/lr:summarize`, leave the new files uncommitted and let the user commit them themselves.

### Step 12: Emit the UUID and display the host summary

Close the summarize step with a block that prints the paths, the UUID, and the host summary contents inline:

```
✓ Host summary written: <path-to-host-summary>
✓ Guest summaries written: <count>
  - <path-to-guest-summary-1>
  - <path-to-guest-summary-2>
Session UUID: <full-uuid>

--- Host Summary ---
<contents of the host summary file>
```

Omit the guest summaries block if none were written. Always include the inline host summary so the user sees what was recorded without having to open the file.

The UUID line is required discipline — it's the only mechanism by which the public summaries can later be correlated to the Claude Code JSONL on the user's machine. The user can later run:

```bash
grep -rl "<full-uuid>" ~/.claude/projects/
```

to find the raw session JSONL if they want to replay or inspect it. The same UUID also finds every host and guest summary for the session in the workspace.

## Failure modes

| Failure | Response |
|---|---|
| Model cannot produce the host narrative | Report error, do not write any files, do not roll back reflect or merge |
| Model cannot produce a specific guest summary | Write the host summary and other guest summaries; skip the failing one with a note |
| Disk write fails for any file | Report the failure with the composed text so the user can copy it manually; other files still get written |
| `id -un` / `id -F` return empty | Omit the affected field, proceed |
| Directory creation fails | Report error for that path, do not write there; other paths proceed |
| Step 1.5 can't resolve the native log or write stats | Print a one-line warning, omit `usage` frontmatter; write the summary as normal |
| Early session hazy due to compaction | Narrative says so plainly; do not fabricate detail |

Summarize failure never rolls back or poisons reflect or merge.

## Privacy

Session summaries are committed (by `/lr:finalize`) to potentially public repos — and with guest summaries, **possibly multiple repos with different visibility settings**. A guest attached from a different repo may land in a repo with broader or narrower visibility than the host's. Native engine logs remain in their engine-owned locations and are not copied into agent repos by summarize or finalize.

Defence relies on the **composition guidance** baked into the narrative and Learning steps:
public-audience aware, no secrets or sensitive specifics, ask the user mid-compose if unsure. The
Learning section names only publication-safe lessons and paths; it must not quote a sensitive
reflection merely because that reflection was later merged. Guest summaries inherit the same
constraint — the one-line contribution summary should be as safe to publish as the host narrative.
When writing guest summaries, consider each one **against its destination repo specifically** —
content acceptable in the host's repo may not be acceptable in a differently-visible guest repo.

The agent is the sole privacy filter at write time for summaries. Post-hoc review happens via git history — the user sees what was pushed after the fact and can amend or revert if something slipped through.

## Consult handling

`/lr:consult` invocations do not trigger their own finalization — the consultant subagent exits without any state changes. Instead, this session's summary records the consult in:

- `consulted` frontmatter field (agent + repo)
- Optional **Consultations** section in the body, if the exchange materially shaped the session

If no consults happened, omit the section and use `consulted: []`.

## Standalone invocation

`/lr:summarize` can be called on its own without running reflect or merge first. In that case, skip
any narrative references to "after merge" and use Step 6.5's direct-invocation Learning state when
no phase state exists. If reflection or merge did run, report its retained state instead. Do not
present missing evidence as a negative result. This is useful as a mid-session checkpoint or for
sessions where no lore changes were produced but the work itself is worth recording.

Step 1.5 (usage metadata) runs in standalone `/lr:summarize` too, not just under finalize — the mechanism lives in one place in this doc, so it behaves the same regardless of caller. A standalone summarize writes only the summary and its optional `usage` frontmatter.

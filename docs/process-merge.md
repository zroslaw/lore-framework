# Merge Process

Integrate reflection topics into the agent's existing lore.

## Execution model

Merge always runs in a subagent, one per active agent, with all subagents launched in parallel. This is uniform for single- and multi-agent sessions — a single-agent session just spawns one subagent. Running merge in a subagent keeps session noise out of merge decisions and gives a clean, focused context.

> **Engine note.** The spawn mechanics below describe Claude Code. If your engine profile (`<framework-root>/docs/engines/<engine>.md`, selected at boot) defines a **subagent-spawn override**, follow it instead — e.g. on Codex use `spawn_agent`, explicitly authorize the required write scope in its brief, and do not pass a synthetic `role` argument. The **host reads this procedure and passes the steps inline** into each subagent's brief rather than pointing the subagent at this doc. The subagent still boots as its target agent.

**Each subagent boots as the agent it is merging for**, using the standard boot procedure. Booting gives the subagent the agent's role, identity, and lore context naturally — the same pattern `/lr:consult` uses. After booting, the subagent runs the process below scoped to its own agent and returns a short summary to the host.

Host responsibilities when merge is invoked:

1. Collect active agents (host + any attached guests).
2. For each, spawn a **`general-purpose`** subagent (merge needs `Write`/`Edit`/`Bash`; `Explore` does not) with a brief such as: _"Boot as agent `<name>` (repo: `<path>`) per `<framework-root>/docs/agent-boot.md`, then run the merge procedure in `<framework-root>/docs/process-merge.md` scoped to yourself. Current-session reflection topics: `<paths from a completed Reflection outcome; None if it completed with zero topics; Failed plus any known partial paths if reflection failed; or Unavailable if no outcome was retained>`. Return the required Merge handoff from Step 6. Do not commit — finalize handles that."_
3. In a multi-agent session, spawn all subagents in parallel (single message with multiple Agent tool calls).
4. Collect handoffs and report per-agent success/failure to the user. **Retain every subagent's
   return** — summarize uses it for the canonical host Learning section, and for a guest summary
   when applicable.

Each subagent's work is independent: separate `reflections/` directory, separate lore subtree. Merge does not commit — all changes are left uncommitted on disk. Committing is handled once, at the end of `/lr:finalize`, or by the user themselves if merge is invoked standalone.

If any subagent fails, the others still proceed.

## Inputs (per subagent)

- The agent's `lore-context.md` — current compacted knowledge
- The agent's `lore/` directory — existing lore topics
- The agent's `reflections/` directory — new reflection topics to integrate
- The agent's `role.md` — current role description

Lore v1 structure is canonical in `<framework-root>/docs/lore-structure.md`. Read it before
creating or migrating any Lore file.

## Process

The steps below are what **each subagent** runs once booted as its target agent. The host does not run these steps inline — it orchestrates subagents per the Execution model above and aggregates their summaries.

### Step 0: Refresh the Repo

The boot procedure already auto-pulls, so this step is defense-in-depth: the freshness contract belongs at the merge site explicitly — the moment when stale lore is most damaging — and it covers any boot-pull skip (no remote, network blip) that left the repo behind.

Before reading the lore for integration, auto-pull the agent's repo, reading `data.pull` for the outcome:

```
python3 "<framework-root>/scripts/lr-core" preflight --agent-dir "<agent-dir>" --fresh --no-teammate-check
```

`--fresh` because merge is exactly the moment where the TTL shortcut is not worth taking. Quote the substituted values as shown and bound the call at **at least 180 seconds** via your engine profile's runtime-bounding binding — `--fresh` guarantees the network round-trip, so this is the site most likely to need the headroom (`docs/conventions.md` § Script Fallback Contract, *Invoking one*).

If the script fails to complete, apply the **Script Fallback Contract** (`<framework-root>/docs/conventions.md`) and read `pull_repo`'s comments in `<framework-root>/scripts/lr_core/preflight.py` (`docs/auto-pull.md` points to the same place) to run the pull against the agent's repo by hand.

`--ff-only` is safe even though the merge subagent's working tree is dirty (the `reflections/` from phase 1, or any merge-in-progress edits): git refuses to fast-forward if the operation would clobber uncommitted edits, and otherwise advances `HEAD` cleanly leaving the working tree untouched. See `docs/auto-pull.md` § Invariants.

If auto-pull surfaces a non-fast-forward failure, do **not** abort merge — proceed in degraded mode and surface the warning in your return summary so the host can flag it. Concurrent finalize collisions are handled by the push-conflict resolution path in `resolve-conflicts.md`, not here.

### Step 1: Read Everything

Generate the compact baseline before semantic integration:

```
python3 "<framework-root>/scripts/lr-core" lore-map --agent-dir "<agent-dir>" --view boot
```

Record its file and estimated-token coverage. Use the compact map for navigation. Generate scoped
detailed views only for areas or files actually needed by the merge. Never print or read an
unscoped detailed census merely to preserve baseline numbers. If mapping fails, report it and
continue with legacy directory search; merge remains usable, but do not claim a coverage change
without a valid before/after pair.

Read all reflection topics, the current `lore-context.md`, and the relevant existing Lore files.
When coverage is partial or legacy, search uncovered Lore as well as following the map.

### Step 2: Integrate Lore Topics

For each reflection topic, decide:

1. **Update an existing topic** — if the reflection adds to, refines, or corrects an existing lore topic, update that topic in place. This is the preferred approach.

2. **Create a new topic** — if the reflection covers something no existing topic addresses, create a new file in `lore/`. Lowercase kebab-case filename.

3. **Remove an obsolete topic** — if a reflection makes an existing topic fundamentally wrong (not just partially outdated), delete it. Git preserves history.

When updating or creating topics:
- Keep topics under 5000 tokens when possible. Split if too large.
- Every new Lore file uses v1 frontmatter from `docs/lore-structure.md`.
- New area hubs use `type: area`; focused leaves use `type: topic`.
- Use normal Markdown links for wider knowledge-graph relationships.
- Include operational recommendations where relevant.
- Only essential information — no filler.

Before the first v1 child in a legacy agent, add valid v1 metadata to the fixed
`lore-context.md`, whose identity is unambiguous. Migrate the minimum clear existing area chain
needed for the new child. When no narrower parent is defensible, use `lore-context.md` rather than
inventing an area.

If a legacy root already has non-v1 frontmatter, preserve it unchanged; it is not safe for
automatic conversion. New files still use v1 and may temporarily point to that fixed legacy root,
which the map reports as `unreachable_v1`.

An unsupported future-version root is different: it is read-only, and a v1 child cannot validly
attach to it. An invalid-v1 root is also not silently replaced. In either case, integrate a
reflection only when an existing writable file is a safe target and the edit introduces no new
finding. If new structure is required, leave that reflection unmerged and report the exact root
blocker to the host; do not discard the knowledge or invent legacy metadata.

An existing legacy file materially edited by this merge is a lazy-migration candidate. Add v1
metadata only when its type, concise summary, and primary parent are clear. Migrate at most the
minimum existing ancestor chain needed to reach the root. Existing summary hubs may become areas
when that role is clear. Otherwise leave the file legacy without asking the user merely for
migration bookkeeping.

Lazy migration is metadata-only. It never merges, splits, renames, deletes, or broadly rewrites
existing topics. A legacy file with non-v1 frontmatter is not auto-migrated. A future-version file
is read-only and must never be edited or migrated by this procedure.

A genuinely new area is allowed only when the current session established that knowledge area and
the new file contains real scope or area-wide knowledge, not placeholder structure. This is normal
knowledge integration, not migration.

### Step 3: Handle Role Updates

If any reflection topic has a `role-update-` prefix:
- Read the current `role.md`
- Integrate the role update into the body
- Keep `role.md` focused and concise
- Preserve the YAML frontmatter. Update the `description` field if the role change warrants a different one-line summary.

### Step 4: Update Lore Context

Update `lore-context.md` to reflect the new state of the agent's knowledge.

Exception: an unsupported future-version root remains byte-identical. For an invalid-v1 root,
preserve its frontmatter unless the correction is unambiguous and retains every useful existing
field. If this prevents an honest context update, leave the affected reflection unmerged under the
Step 2 blocker rule.

**`lore-context.md` is the agent's every-session working knowledge and the root of the Lore
taxonomy — not an index of all topics.** Carry compacted knowledge needed in essentially every
session plus high-level routing to top-level areas. Let areas carry their own shared knowledge and
route to descendants.

- **Compacted working knowledge** — facts, decisions, and context the agent draws on across most sessions, stated tightly and in the **present tense**.
- **Reference areas; don't enumerate leaves** — point at a theme's area hub and let its generated
  children fan out to detail. Do not list every file in `lore/`. Create a new area only when it has
  real area-wide scope or knowledge.
- **No version-history narrative** — `lore-context.md` is present-tense. Changelog-style "vN did X" annotations and dated step-by-step history belong in git, release notes, or the relevant topic.

**Preserve graph navigability.** When you remove something from `lore-context.md`, ensure it still
lives in a reachable area or topic. Existence somewhere is not enough; the generated parent path
from the root must still lead there.

**V1 size budget:** target at most 10,000 estimated tokens. The validator warns above 10,000 and
errors above 20,000. Demote detail into reachable areas before removing unique knowledge. Legacy
contexts retain the historical 50,000-token ceiling until migrated, but shape remains the primary
discipline.

### Step 5: Validate the merge

Regenerate the boot map for global coverage. Generate a scoped detailed map for every changed Lore
file and link repair. When the changed root would make that scope equal the whole corpus, redirect
the detailed YAML to a temporary file and inspect only its `validation` entries for changed paths;
do not load the taxonomy body into context. Validate every changed file and repair. Fix structural
errors the merge introduced: invalid metadata, missing or wrong-type parents, cycles, children
under topics, unreachable v1 files, and broken links. Delete temporary map files after the check.

Pre-existing legacy files and findings outside the write set do not fail merge. The only allowed
new uncovered case is a valid v1 child temporarily blocked by incompatible frontmatter on the
fixed legacy root. If optional metadata migration is invalid, correct or remove the metadata while
preserving the knowledge edit.

When both baseline and final maps are valid and coverage changed, return one quiet line:

```text
Lore structure coverage: 24% → 27%
```

Use file coverage percentage. Say nothing when it did not change.

### Step 6: Cleanup

Delete each reflection topic only after its knowledge was successfully integrated. If every topic
was integrated, remove the now-empty `reflections/` directory. Leave blocked or failed topics in
place and name them in the return summary so a later merge can retry without knowledge loss.

Merge does not commit — leave all changes uncommitted on disk. Return this compact handoff to the
host, including explicit `None.` values rather than dropping a field:

```text
Merge handoff — <agent-name>
- What mattered: <one to three concrete durable facts, decisions, or lessons from the current-session reflection topics only>
- Lore changes:
  - `<agent-relative-path>` — <created, updated, consolidated, simplified, or deleted> — <why; identify current-session, carried-over, or mixed origin when carried-over reflection contributed>
- Unmerged: <remaining reflection paths, current-session or carried-over origin, and reasons; or None.>
- Anomalies: <warnings or failures that affect confidence in the result, or None.>
```

Name changes to `lore-context.md` and `role.md` in **Lore changes** like any other material change.
When consolidation or simplification was the meaningful operation, say that explicitly instead of
reducing it to "updated." Make **What mattered** understandable without opening Lore: preserve the
specific fact or decision and its useful reason, rather than naming only its category. If no
reflection topics were available, say so under **What mattered**; if Lore did not change, use
`- Lore changes: None.` A failed or missing merge is not the same as no learning; return the failure
or leave the affected reflection under **Unmerged**.

Treat a caller-provided **completed** current-session topic set as authoritative; do not reconstruct
it from the directory. Only with that complete set may an unlisted reflection be classified as
carried over from an earlier run. Do not include a carried-over theme under **What mattered**.
Identify its origin in the affected **Lore changes** and **Unmerged** entries so the summary cannot
attribute old learning to this session. If the caller marked the set `Failed`, use any supplied
partial paths only as known-current evidence and treat every other origin as unknown. If it marked
the set `Unavailable`, treat all origins as unknown. In either case, say session attribution is
incomplete or unavailable under **What mattered** and explain it under **Anomalies**.

This handoff is the authoritative merge-side input to the host summary's Learning section and to
guest-summary lore updates. It is an audit of outcomes, not a copy of the resulting Lore. Committing
is handled at the end of `/lr:finalize`, or by the user directly if merge is invoked standalone.

## Guidelines

- **Preserve knowledge** — don't lose information during merging. If removing content from `lore-context.md`, make sure it exists in a lore topic.
- **Maintain the graph** — when creating new topics that relate to existing ones, add cross-references.
- **Be conservative with deletions** — only delete topics that are fundamentally wrong. Updating is almost always better.
- **Respect the agent's voice** — lore should read naturally as the agent's own knowledge, not as third-party documentation.
- **Shared topics** — the same topic may legitimately appear in multiple agents' lore if it matters to each of them. Don't try to consolidate into one agent's lore during merge; each agent owns its own copy for its own scope.

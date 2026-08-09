# Groom Lore

Keep one agent's Lore useful per token: easy to retrieve, compact, current, and free of low-value
AI prose. Default grooming is iterative and bounded. Whole-Lore mode is explicit and approval-gated.

Usage:

```text
/lr:groom [<area-or-topic>] [--dry-run] [--all]
```

Resolve `<framework-root>` from the invoking skill and `<agent-dir>` from the currently booted
agent. If no agent is booted, ask which agent to groom and resolve it through normal discovery.

## Safety Rules

- Markdown and Git remain canonical; the map supplies facts and the agent supplies judgment.
- Preserve unique claims, reasons, procedures, exceptions, uncertainty, and evidence pointers.
- Never remove a file merely because it is old, small, or weakly linked.
- Unsupported future-version files are read-only.
- Files outside the declared write set remain unchanged, except exact link repairs declared before
  apply.
- Never overwrite an unreviewed destination.
- Never commit or push as part of grooming.
- A dry run changes neither Lore nor the grooming cursor.

## Default or Scoped Run

### 1. Select the workset

Run:

```text
python3 "<framework-root>/scripts/lr-core" lore-workset --agent-dir "<agent-dir>"
```

Add `--scope "<area-or-topic>"` when the user supplied one. Paths are agent-relative, such as
`lore/architecture.md`. The default budget is 30,000 estimated tokens; do not increase it silently.

The command is read-only and emits a compact YAML manifest containing coverage, editable files,
read-only halo records, per-entry estimated costs, omissions, and SHA-256 snapshots. The complete
census stays outside model context. If selection fails, stop grooming; do not reconstruct a
whole-corpus workset with the model.

Files with invalid UTF-8 never enter the workset or halo. The map emits no per-file corruption
list; `coverage.uncovered.invalid_utf8` reports only their count. Safe content cleanup elsewhere
may continue.

Load the complete text of every `editable` file. Use halo summaries as read-only context. A named
halo file may be loaded in full only when the remaining 30,000-token budget permits; record its
estimated cost and SHA-256 before review. Otherwise defer the decision that needs it.

### 2. Declare the write set

The initial write set is the manifest's editable paths. A halo file becomes editable only when it
is explicitly promoted before apply and the budget still holds. A rename, merge, split, or deletion
may add exact inbound link-repair files after the safety scan below; report those additions before
writing.

An explicit scope is the semantic write boundary. Outside it, only declared mechanical link repairs
are allowed.

### 3. Review semantically

For the bounded workset, check:

- taxonomy placement and retrieval summaries;
- area hubs that should own essential shared knowledge and route to children;
- mixed or oversized topics that should split;
- fragmented siblings that should consolidate;
- duplicated, stale, contradictory, or superseded claims;
- broken or context-free links;
- excessive detail in `lore-context.md`;
- AI slop.

AI slop is prose removable without losing a durable claim, decision, reason, procedure, exception,
evidence pointer, or navigation cue. Typical examples are generic advice, ceremonial introductions,
obvious restatement, repeated conclusions, and easily recreated explanation. Keep explanations that
carry applicability conditions, derivation, operational judgment, or non-obvious reasons.

Allowed improvements are concise rewrites, summary and routing improvements, v1 metadata migration,
parent changes, link repair, splits, consolidation, context demotion, and deletion of a fully
superseded or fully incorporated topic. Uncertain changes remain proposals.

### 4. Protect structural changes

Before a rename, merge, or deletion, generate the unscoped detailed map into a temporary file:

```text
python3 "<framework-root>/scripts/lr-core" lore-map --agent-dir "<agent-dir>" --view detailed > "<temporary-map>"
```

Search that file for the exact source and destination paths and inspect only their formal and
legacy inbound records. Do not load the complete census into model context. Include references
from legacy and future files. Defer the operation when any inbound source is an unsupported
future-version file, `coverage.uncovered.invalid_utf8` is nonzero, a legacy basename is ambiguous,
a required repair exceeds the budget, or a new source would expand the write set after apply
starts. A nonzero invalid-UTF-8 count means the inbound scan cannot be complete. Delete the
temporary map after the run.

For every destructive operation, record:

- source paths;
- destination paths;
- exact link-repair paths;
- why no unique claim, procedure, exception, uncertainty, or evidence pointer is lost.

Each destructive source must be tracked and clean relative to Git. Every new destination must be
absent both when proposed and immediately before apply. If a destination exists, either make it an
explicit reviewed source whose content and hash the operation preserves, or abort the operation.
The detailed record's `uncommitted` field supplies the review-time state.

### 5. Recheck the snapshot, then apply

Immediately before the first write, calculate SHA-256 for every editable and loaded halo source and
compare it with the review snapshot. Include any file loaded after initial selection. If any hash
differs, write nothing: rebuild the workset and repeat the review. Ordinary iterative runs do not
need renewed user approval unless the rebuilt proposal changes a user-approved scope or decision.

Recheck destination absence and Git cleanliness of every destructive source at the same boundary.
Apply only the declared write set.

If `--dry-run` was supplied, stop after presenting the proposed operations and projected metrics.

### 6. Verify

Regenerate the boot map for global coverage and scoped detailed maps for every changed file and
link repair. If a required scope expands to the whole corpus, redirect it to a temporary file and
inspect only relevant validation records. Confirm the run introduced no new cycle, orphan, broken
link, topic-with-children relation, or unsupported-version edit. Compare estimated tokens and
file/token coverage before and after. Inspect the final diff for knowledge loss and scope expansion.

Pre-existing findings outside the write set do not fail the run.

Report briefly:

```yaml
grooming:
  reviewed_files: 14
  changed_files: 8
  estimated_tokens: {before: 21400, after: 15700}
  coverage_percent: {before: 42.0, after: 45.5}
  fixed: {structure: 3, links: 4, slop: 6}
  remaining_candidates: 11
```

### 7. Update the optional cursor

Only after a successful applying run, update `<agent-dir>/workdir/lore-grooming-state.yaml`:

```yaml
lore_grooming: 1
last_successful_at: "2026-08-08T12:00:00Z"
last_successful_commit: abc123
reviewed:
  - {file: lore/example.md, at: "2026-08-08T12:00:00Z"}
```

Use UTC, path-sort reviewed entries, and use `null` when no commit exists. This is disposable derived
state, not Lore. Preserve existing reviewed timestamps for files outside this run.

## Whole-Lore Mode

`--all` is an explicit bulk conversion and grooming mode. It is single-session and non-resumable in
v1. Do not write while reviewing partitions.

If `coverage.uncovered.invalid_utf8` is nonzero, stop Whole-Lore mode before partitioning. It cannot
claim exhaustive ownership while a discovered file is unreadable and has no review record.

### 1. Partition exhaustively

Generate the complete detailed map into a temporary file; never load it wholesale. Read its records
in bounded slices while assigning every discovered file to exactly one review partition. Mark each
member `editable` or `read_only`; every unsupported future-version file is read-only.

- A mapped top-level area subtree at or below 30,000 tokens is one partition.
- For an oversized area, put the area node in its own hub partition and partition each child subtree
  recursively. The area may repeat elsewhere only as read-only halo.
- Put the root and direct-root topics into path-ordered budget batches.
- Partition legacy link components, then catch-all invalid, unreachable, unlinked legacy, and future
  files into path-ordered budget batches.
- A file over budget is one `over_budget: true` singleton. Split oversized multi-file components
  into path-ordered batches.

Every discovered file must have exactly one owning partition. Ancestors repeated as halo do not own
the file. If any file has zero or multiple owners, stop and repair the partition plan.

### 2. Review every partition

Review partitions one at a time under the same budget and safety rules as an iterative run. Capture
the hash of every reviewed input and potential write source. A future-version member may inform the
review but never enter the write candidates.

### 3. Produce one proposal

Before any write, show one global YAML proposal containing:

- partition count and exhaustive ownership coverage;
- current and projected structure coverage;
- unresolved files and reasons;
- snapshot hashes;
- operations with stable IDs, reasons, sources, destinations, link repairs, and exact write sets;
- destination-absence preconditions;
- whether every partition was reviewed.

If a partition was not reviewed, label the proposal partial; never claim a complete redesign.

### 4. Obtain approval and apply once

Ask the user to approve the exact global proposal. Approval applies only to that proposal and
snapshot. Immediately before apply, recheck every source hash and destination precondition. Any
mismatch aborts the entire apply: rebuild, show the revised proposal, and obtain fresh approval.

The approved write set cannot expand. One writer applies area hubs before leaves, then repairs
links. Regenerate the complete map into a temporary file, inspect its validation and coverage in
bounded slices, inspect the complete Git diff after apply, then delete the map file.

Durable proposal bundles, resumable runs, multiple writers, scheduled apply, and autonomous deletion
are outside v1.

## Migration Behavior

Intentional v1 conversion is part of grooming. Convert a legacy file only when its type, summary,
and parent are clear. A legacy file with existing non-v1 frontmatter may be converted only after
every old field is preserved as useful Markdown knowledge or consciously proven redundant in the
review. Ambiguous files remain legacy. Whole-Lore mode may legitimately finish with partial coverage.

Routine, metadata-only migration during merge is defined in `docs/process-merge.md`. Boot never
migrates Lore.

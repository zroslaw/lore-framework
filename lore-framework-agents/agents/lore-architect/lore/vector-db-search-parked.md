Design exploration (parked, not decided): introducing Chroma DB as a derived semantic-search index over lore topics.

## When to Revisit

Revisit only when there is concrete evidence the subagent-scan pattern (framework `docs/lore-search.md`) is failing:
- Lore size makes subagent scan slow or expensive
- Real recall failures observed (topics existed but weren't surfaced)
- Cross-agent knowledge sharing becomes a requirement

Per-agent lore exceeding ~100 topics is a rough trigger to start measuring. Below that, the LLM-driven subagent scan produces higher-quality semantic matches than embedding similarity, with no infrastructure cost.

## Design Sketch

Treat Chroma as **derived state**, never a source of truth — same role as `.git/` or `node_modules/`. Markdown files remain canonical.

**Constraints:**
- Markdown stays canonical; index is rebuildable from scratch
- Local embedding only (e.g., `sentence-transformers` `all-MiniLM-L6-v2`) — no API keys, no network
- Per-agent index at `agents/<name>/.lore-index/`, gitignored
- No runtime failure mode — if Chroma is missing/down, agents fall back to subagent scan
- Read-only at runtime; updates only on knowledge change

**Incremental update via git-based change detection:**
- Index stores last-indexed commit SHA in `.lore-index/last-indexed`
- On reindex: `git diff --name-only <last>..HEAD -- lore/` gives changed files
- For modified/added: `collection.upsert(ids=[<relpath>], documents=[...])`
- For deleted: `collection.delete(ids=[<relpath>])`
- First build / missing metadata: full scan
- Update `last-indexed` to current HEAD on success

**Triggers:**
- `/lr:reindex` — manual
- Auto-rebuild during `/lr:merge` (after lore changes are integrated)
- Optional git post-commit hook

**Embedding ID** = relative path from `lore/` (stable across edits, handles renames via `git diff --find-renames`).

## What Vector Search Does NOT Solve

- Authoring/editing topics — still markdown
- Git history / temporal reasoning — Chroma is ahistorical
- The judgment in merge (update vs create vs delete) — still the agent's call
- The reflection process — orthogonal

Vector search would be a **retrieval enhancement only**. It does not replace `lore-context.md` (which is the agent's compressed working memory at boot, not a search index).

## Why Parked

At the time this was discussed, lore was small (~12 topics per agent). Subagent scan handles current scale comfortably. Building vector DB machinery for hypothetical future scale would violate the "minimal and essential" principle from `system-design-principles.md`.

When the trigger conditions above are met, this document is the design starting point.

## See Also

- `system-design-principles.md` — minimal-and-essential principle that justifies parking
- `architecture-overview.md` — current framework structure
- Framework `docs/lore-search.md` — current subagent-scan search pattern
- `workdir-as-reference-library.md` — another parked exploration following the same "no new machinery" stance

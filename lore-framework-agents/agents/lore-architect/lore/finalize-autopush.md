Framework change (v9+) removing the two user-approval gates from the finalization flow. `/lr:finalize` now runs end-to-end without prompts.

## Gates Removed

1. **Summary approval** (`summarize.md` step 10) — previously showed composed host summary + all guest summaries to the user for batch approval before any file was written. Removed. Summarize writes directly.
2. **Commit+push approval** (`finalize.md` phase 4) — previously printed pending diff + proposed message per-repo and waited for approval before commit. Removed. Each repo is staged (`agents/`), committed with `Finalize session <short-uuid>`, pushed without interaction.

## What Replaces the Gates

- **Inline summary display** (summarize step 12): after writing, the host summary contents are printed inline in the conversation so the user sees what was recorded without opening the file. This is the "show" half of the original gate — minus the approval wait.
- **Post-hoc review via git history**: the user sees what was pushed after the fact and can amend or revert. Stronger-than-nothing review channel; weaker than pre-commit review.

## Privacy Implications

The only remaining privacy defense is the **narrative-guidance prompt** baked into summarize's composition step (public-audience aware, no secrets, ask mid-compose if unsure). The agent is the sole filter at write time. No automated scrubbing.

This is an explicit tradeoff: throughput over belt-and-suspenders safety. A model that cannot produce a publication-safe summary on the first pass should report an error rather than writing something compromised. Failure modes involving user rejection were removed from the summarize failure table accordingly.

When guest summaries land in differently-visible repos (cross-repo guests), the narrative-guidance prompt still instructs the agent to consider each destination repo specifically. But the fine-grained "drop this guest's summary without blocking the host" behavior that the review gate enabled is gone — if a guest summary is risky, the agent should either produce a safe version or error out entirely.

## Escape Hatch

Users wanting the old pre-commit review can invoke `/lr:reflect`, `/lr:merge`, `/lr:summarize` separately — standalone skills still don't commit or push. Review manually between phases, commit and push themselves. Only `/lr:finalize` is the auto-push entry point.

## Design Stance

User's explicit direction: "just push everything and show the summary, thats it." The removed gates were belt-and-suspenders — protecting against agent misjudgment at the cost of interrupting the flow. With Opus-level agents composing narrative and commit messages, the tradeoff favors flow. Revisit if real incidents occur.

## Doc Impact

- `summarize.md` — step 10 removed (was "show and wait"); steps 11/12/13 renumbered to 10/11/12; step 12 extended with inline summary display; failure-modes table trimmed; Privacy section rewritten.
- `finalize.md` — phase 4 compressed to 3 steps (add / commit / push); "Review gate is mandatory" invariant replaced with "Fully automated"; "Summarize skipped" → "Summarize failed" in failure handling (skipping is no longer possible).

## See Also

- `finalization-process.md` — overall four-phase structure (phases 1–3 otherwise unchanged)
- `reflect-merge-execution-asymmetry.md` — the inline-vs-subagent split for reflect/merge (unchanged by this)
- `session-summaries-feature.md` — prior privacy model (two-layer defense); this topic supersedes that layer discussion

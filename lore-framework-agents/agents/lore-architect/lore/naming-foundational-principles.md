**Foundational design principles should be named as standalone lore topics, not left implicit in the mechanisms they motivate.**

A meta-rule for lore curation, surfaced this session by the missing `team-shared-knowledge-principle.md`. If multiple mechanisms in lore only make sense under a particular framing, the framing itself deserves its own topic. Otherwise it has to be reverse-engineered each time from the mechanisms — and reverse-engineering is unreliable under context pressure.

## The Concrete Instance

The principle "lore agents are team-shared knowledge containers, not personal notebooks" was implicitly encoded across many existing topics:

- `push-conflict-resolution.md` (concurrent contributors expected)
- `merge-in-booted-subagents.md` (per-agent lens for cross-contributor coherence)
- `finalize-autopush.md` (publication as default)
- `session-summaries-feature.md` (sessions written for future readers)
- The multi-author finalization machinery generally

The mechanisms were all in lore. The underlying principle they all served had never been named as a topic.

Result: when the architect reasoned about whether to host itself in the framework repo, it defaulted to a "personal notebook" framing — despite already having all the multi-contributor machinery in lore-context. The principle was *re-derivable* but *invisible* during synthesis. The user had to surface it explicitly. The fix was to name it: `team-shared-knowledge-principle.md`.

## Why This Matters

A new reader (or a future session under context pressure) reads `lore-context.md` and the lore topics that catch its eye. If the foundational framing isn't named, it has to be inferred. Inference under pressure is exactly when wrong instincts win — and the wrong instinct is hard to spot precisely because the right framing is invisible.

Naming the principle makes it part of the index, part of the search surface, part of what a recall hit will return. It stops being tacit and starts being explicit.

## Diagnostic

When designing a new feature, if the rationale traces back to a principle that isn't named in lore — **name it before continuing**. Treat unnamed foundational principles as missing lore, not as background knowledge.

Practical heuristic: when you find yourself writing "because [framing]" in a topic body, and that framing has no link, that's the signal to extract it into its own topic.

## Format for a Principle Topic

A principle topic typically has:

- One-sentence statement of the principle (boldfaced lead).
- *Why it matters* — what would go wrong without it, what design instincts it corrects.
- *Diagnostic signals* — what wrong instincts look like in practice (the negative space helps as much as the positive statement).
- *Operational guidance* — how to apply it to new design decisions.
- *Known gaps* — where the principle's guarantees don't yet hold.
- *See also* — the mechanisms it explains (so a reader landing on the mechanism can navigate up to the principle).

The cross-referencing direction matters: mechanism topics should link *up* to the principle, and the principle should link *down* to the mechanisms. Bidirectional navigation in the knowledge graph.

## Composition

This rule composes with:

- `system-design-principles.md` — the index of named principles; new foundational principles get a bullet here pointing to their own topic.
- `lore-topic-format.md` — mechanics of how a topic looks. This rule is *what* deserves a topic, that one is *how* to format one.
- `framework-scope-vs-agent-scope.md` — itself an example of a principle worth naming; it crystallized during the `contributions-feature.md` debate.

## See Also

- `team-shared-knowledge-principle.md` — the topic born from this lesson; the canonical example
- `system-design-principles.md` — where new named principles get indexed
- `lore-topic-format.md` — mechanics of topic structure
- `framework-scope-vs-agent-scope.md` — another principle that crystallized only when named

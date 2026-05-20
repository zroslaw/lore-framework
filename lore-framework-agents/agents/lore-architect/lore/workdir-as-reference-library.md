Design exploration (parked, not decided): using `workdir/` as a structured reference library alongside lore.

## The Distinction

Lore and reference docs serve different purposes:
- **Lore** = internalized experiential knowledge (in your head) — grows organically through sessions via reflect/merge
- **Workdir docs** = curated structured reference material (on your desk) — hierarchical, systematic, managed directly by the agent

Both are needed; they complement each other. The analogy: lore is your field notebook, workdir docs are the reference manual.

## Proposal

Use the existing `workdir/` directory — no new framework machinery. Agents already control its structure.

Benefits: dual audience (agents and humans can browse), no finalization overhead, no token pressure on `lore-context.md`, fits the existing boot model (boot with lore-context, consult workdir on demand).

## Where It Matters

Most valuable for domain-heavy agents (tax-advisor, masschallenge-judge) with inherent taxonomies — tax rules, scoring rubrics, API specs. Less critical for agents like lore-architect where the knowledge graph model works well.

## Open Questions

- Recommended sub-structure within workdir (e.g., `workdir/docs/` for reference material)?
- Should `agent-boot.md` explicitly frame this dual purpose?
- Should finalization prompt about workdir updates?
- How do agents know when to consult workdir vs. lore?

A draft ideation document exists at `workdir/draft-workdir-as-knowledge-base.md`.

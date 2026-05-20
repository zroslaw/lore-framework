# Draft: Workdir as Structured Knowledge Base

Status: ideation, parked for later

## The Problem

Lore is a flat collection of atomic experiential topics — good for storing lessons learned, decisions, and discoveries. But agents also need structured, hierarchical reference material: API specs, process docs, taxonomies, guides.

Currently there's no clear place or convention for this.

## Core Insight

Lore = what's in your head (internalized knowledge, grows through experience).
Workdir docs = reference material on your desk (curated, structured, consulted on demand).

This is a dual-audience resource: agents consult it during sessions, humans browse it in the repo.

## Proposal

Use `workdir/` (which already exists) as the home for structured reference documents alongside its current role as a workspace for scripts/tools/artifacts.

No new framework machinery needed — just better framing and a light convention.

## Why This Works

- `workdir/` already exists with agent-controlled structure
- Separate from lore lifecycle — no reflect/merge overhead, agent manages docs directly
- No token budget pressure on `lore-context.md` — heavy reference material loaded on demand
- Fits the boot model — agent boots with lore-context (head), reaches for workdir (desk) when needed

## Where It Helps Most

- Agents in domains with inherent taxonomy (tax-advisor: rules, deductions, entity types; masschallenge-judge: evaluation criteria, scoring rubrics)
- Less critical for agents like lore-architect where knowledge is mostly design decisions (graph model works fine)

## Open Questions

1. Should workdir have a recommended sub-structure? (e.g., `workdir/docs/` for reference material, separate from scripts/tools)
2. Should `agent-boot.md` be updated to explicitly frame this dual purpose?
3. Should finalization have any awareness of workdir? (e.g., "should session findings become reference docs?")
4. Is `workdir/` the right place, or should this be a separate top-level directory like `kb/`?
5. How do agents know when to consult workdir vs. lore? (Boot instructions could guide this)

## Proposed Changes (Minimal)

1. Update `agent-boot.md` — reframe workdir section to describe the dual purpose (workspace + reference library)
2. Suggest a convention for organizing reference docs within workdir

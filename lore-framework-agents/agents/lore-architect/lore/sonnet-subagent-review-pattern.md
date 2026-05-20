**For high-stakes lore additions (principle topics, structural changes), spawn a sonnet subagent booted as the same agent to review the changes before finalizing.**

Validated this session: after writing `team-shared-knowledge-principle.md` plus edits to `system-design-principles.md`, `lore-context.md`, and `lore-framework/README.md`, spawned a sonnet `general-purpose` subagent that booted as lore-architect, read the relevant existing lore topics, and produced a structured review.

## What the Pattern Catches

From the live trial:

- **Duplicated wording** — the principle's leading sentence and the system-design-principles bullet had overlapping content. Rewritten so lore-context is a signpost, not a mini-summary.
- **Muddled diagnostic signals** — a draft signal conflated drafting (reflect writes to temporary `reflections/`) with publication (finalize-autopush publishes to remote). Replaced with a stronger signal explicitly about auto-push.
- **Imprecise See Also descriptions** — one entry implied a referenced topic was about framing, when it's about mechanics.
- **Known gaps in claims** — the principle's "concurrent contributions are safe" claim doesn't yet apply to `/lr:spawn-teammate` BETA (last-write-wins). Added as a Known Gaps section.
- **Pre-existing broken cross-references** — `framework-scope-vs-agent-scope.md` See Also points to `contributions-feature.md` which doesn't exist in `lore/`. Pre-dates the session; logged to `framework-improvements-backlog.md`.

## Why Booting as the Same Agent Matters

Booting the reviewer as the same agent gives it the role lens automatically. It evaluates style, density, cross-reference accuracy, and coherence with existing lore from *inside the agent's own perspective*. Same machinery as `merge-in-booted-subagents.md`, applied to review instead of merge.

A reviewer that doesn't boot as the target agent would lack the "what does coherent lore look like for this agent" calibration — and would produce generic editorial feedback rather than role-specific signal.

## Operational Guidance

- Spawn via the `Agent` tool with `subagent_type: "general-purpose"`, `model: "sonnet"`, `run_in_background: true`.
- Brief the subagent explicitly with:
  1. Background context — *why* the change was made (the session-shaped reasoning the reviewer won't otherwise have).
  2. Precise list of files touched and what each change is.
  3. What to evaluate — correctness, completeness, placement, style, cross-references, risks.
  4. Expected output shape — verdict + strengths + issues with severity + open questions + cross-ref verification.
- Instruct extended thinking in the prompt itself — the `Agent` tool has no thinking-effort knob, so careful reasoning has to be requested in language.
- Run in background; continue other work; address findings on completion notification.

## When to Use

- Principle-class topic additions (new foundational framings).
- Major structural changes (agent moves, repo reorganizations, distribution-story changes).
- Content that will be read by other contributors — README sections, public-facing docs.
- Cross-repo consistency changes (e.g., README + lore + role.md edits in concert).

Skip for routine edits — the overhead isn't worth it for small refinements.

## Composition with Existing Patterns

This is the third place the framework boots an agent inside a subagent:

- **`/lr:consult`** — ephemeral one-shot question. Subagent answers, exits.
- **Merge** — file-driven integration of reflections. Parallel per active agent.
- **Sonnet review (this pattern)** — pre-publication critique by the agent's own role-lens.

All three exploit the same `role.md` + `lore-context.md` boot to give the subagent a coherent perspective. The pattern is now generic enough to be worth naming. See `reflect-merge-execution-asymmetry.md` for the broader "delegate when file-driven" rule.

## See Also

- `merge-in-booted-subagents.md` — same role-as-lens pattern, applied to merge
- `consult-pattern.md` — same boot mechanism, applied to one-shot consultation
- `reflect-merge-execution-asymmetry.md` — when to delegate vs run inline
- `design-doc-before-implement.md` — composes naturally: review the design draft before publishing

Skills are thin references; docs carry the logic.

Every plugin skill (`skills/<name>/SKILL.md`) is a one-line pointer to a detailed doc (`docs/<name>.md`). The skill contains only:
- YAML frontmatter (`description`, `argument-hint`)
- A single-line body: `Read ${CLAUDE_PLUGIN_ROOT}/docs/<name>.md and execute it. Arguments: $ARGUMENTS`

All operational instructions — steps, error handling, edge cases, examples — live in the doc. Claude reads the doc at invocation time.

## Why

- **Single source of truth.** Behavior is defined in one place. Changing the skill body and the doc separately causes drift.
- **Concise skills, detailed docs.** Keeps the skill file short enough to read at a glance. The doc can be as long as needed without polluting context when the skill isn't invoked.
- **Maintainability.** Editing logic means editing one file. No inline code in skill frontmatter.
- **Consistent pattern across all skills.** Reviewer knows where to look.

## Applied to generated artifacts too

The same principle extends to files the framework generates:

- **Registered per-agent commands** (`/lr-<name>-agent`) are one-line delegations: `Read lore-framework/docs/agent-boot.md and boot as agent <name>.` No inlined operating instructions. `agent-boot.md` is the single source of truth for both boot procedure and operating rules.
- Any future generated artifact should follow the same shape: minimal custom content (just the parameters unique to this instance), delegation to a framework doc for the logic.

## Orchestration refinement (v8)

Edge case surfaced while designing v8 finalize: when a skill **orchestrates across multiple sub-skills** (like `/lr:finalize` calling reflect + merge + summarize + commit), the orchestration itself has content — phase descriptions, failure handling, invariants, cross-phase coordination. Putting this content in the skill file bloats the thin-pointer convention.

**Refinement:** create `docs/<skill>.md` for the orchestration logic, keep the skill file a thin pointer as usual. For `/lr:finalize`:

- `skills/finalize/SKILL.md` — thin pointer to `docs/finalize.md`
- `docs/finalize.md` — the four phases, failure handling, cross-repo handling, invariants
- `docs/finalize.md` in turn references `docs/process-reflection.md`, `docs/process-merge.md`, `docs/summarize.md`, `docs/resolve-conflicts.md` for phase-specific procedures

This preserves the thin-pointer convention uniformly across all skills while giving orchestration a proper home. The same refinement applies to any future skill that coordinates multiple existing docs.

Not a replacement of the skill-doc pattern — a refinement for orchestration cases. The trigger for moving content into a dedicated doc is **when the skill file starts growing inline step-by-step content**. That's the signal to extract.

## Anti-patterns

- Inlining operating instructions into generated files "so they work without the plugin" — creates drift, violates single-source-of-truth.
- Putting logic in skill frontmatter bodies beyond the delegation line.
- Having the skill doc duplicate content that already exists in another doc — prefer cross-reference.
- Letting an orchestrator skill accumulate phase-by-phase content in its SKILL.md — extract to a dedicated `docs/<skill>.md` as soon as it crosses beyond the thin pointer.

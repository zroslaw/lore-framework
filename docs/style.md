# Style

`/lr:style` is the single public entry point for Lore communication styles. It selects an
**exact** set of internal components for the rest of the session; it does not add to a previous
selection.

The examples below use Claude Code syntax. In Cursor, use `/lr-style`; in Codex, use `$lr:style`.

## Selectors

Accept selectors separated by spaces or commas. The allowed selectors are:

| Selector | Component |
|---|---|
| `plain` | Plain language — simple wording and one idea at a time |
| `dialogue` | Dialogue — short, incremental conversational turns |
| `follow` | Follow — the user directs the thinking; offer small suggestions only |
| `all` | All three components |
| `off` | No style components |

- With no selector, use `all`.
- `all` and `off` must be used alone.
- Reject an unknown selector, a duplicate selector, or `all`/`off` combined with another selector.
  Do not guess the user's intent. Briefly show the valid forms instead.

## Procedure

1. Parse the invocation into selectors and validate it against the rules above.
2. Resolve the selected components. `all` (or no selector) resolves to `plain`, `dialogue`, and
   `follow`; `off` resolves to none.
3. Replace the session's active style set with that result. Explicitly disable any previously
   active style component that is not selected now.
4. Read and apply each selected component's canonical behavior document:
   - `docs/plain-language.md` for `plain`
   - `docs/dialogue.md` for `dialogue`
   - `docs/follow-me.md` for `follow`
5. Confirm in one short sentence: `Style set: <names>.` — where `<names>` lists **the components
   you actually selected in step 2**, in the canonical order `plain`, `dialogue`, `follow`. Never
   copy the component names from this document; substitute your own resolved set.

   Punctuation of `<names>`, by count: three → `a, b, and c`; two → `a and b` (no comma); one →
   `a`; none (`off`) → the word `off`.

   Then keep that exact style set until the user calls `/lr:style` again or selects `off`.

   **This confirmation is mandatory and is the skill's only observable result.** Adopting the
   style silently looks identical to ignoring the invocation, because the components change *how*
   you write, not *whether* you reply. If your turn does not contain a `Style set: ...` line, you
   have not completed this procedure. When the same turn also answers a user question, print the
   confirmation first, then answer — in the newly selected style.

Examples:

- `/lr:style` or `/lr:style all` — plain + dialogue + follow
- `/lr:style plain` — plain only
- `/lr:style dialogue follow` — dialogue + follow only
- `/lr:style off` — disable all style components

`/lr:consult` asks an unloaded lore agent a focused question. A subagent boots the consultant, searches its lore, synthesizes a response with pointers to specific files, and exits. The host receives the synthesis + pointers; the consultant itself is unaffected — no reflection, no merge.

Introduced in framework v4 alongside `/lr:attach`. Consult is the lightweight sibling: one-shot, no loading into host context. See `attach-pattern.md` for the heavyweight option.

## Design decisions

- **Lightweight by construction.** Consultant boots in a subagent. Boot output, lore scan, and tool use all stay in the subagent's context. Host sees only the final synthesis + file pointers.
- **Handover, not loading.** Response includes pointers to specific lore topics or workdir tools the host may read or use directly. Domain visibility makes these reads free. But the host does NOT search the consultant's lore further — that boundary is what keeps consult cheap.
- **No finalization for the consultant.** The consult is read-only from the consultant's perspective. Its lore is queried, nothing is written back. No reflection subagent, no merge. Future consult-feedback mechanism deferred — a formal back-channel was considered and parked.
- **Version reconcile comes for free.** The subagent follows `agent-boot.md`, which invokes version-check automatically. Any release-notes text is returned to the host for relay to the user.
- **Refuse when recall is strictly better.** Consulting the host is refused (use `/lr:recall`). Consulting an already-attached guest is refused (use `/lr:recall` — the guest is already loaded).

## Procedure shape

1. Preconditions (host booted, consultant exists, not host, not already-attached guest).
2. Build a 4-part brief from session + user hint: task, session context, question/angle, output shape.
3. Dispatch general-purpose subagent: boot → search lore → synthesize → return. Nested subagent dispatch inside the consult subagent is allowed (Explore-from-Explore).
4. Present synthesis to the user (labeled by consultant name). Read pointed-to files into host context if load-bearing.
5. Host carries the consult's answer forward as working context.

## Escalation to attach

If the task needs sustained engagement with the consultant's knowledge, the clean transition is `/lr:attach <same-agent>`. This is deliberate: consult is a deliberately narrow handover; attach is the mechanism for repeated use.

## Why introduce it

Same problem attach solves — shared knowledge across agents — but for the common case where a single focused question (+ maybe a recipe file) is enough. Avoids paying attach's context cost for shallow needs. Also cheap to try: if the response is insufficient, escalate.

## Output shape conventions

Consultant's synthesis should:
- Direct answer, ≤400 words
- Pointers to specific lore topics (absolute paths)
- Pointers to specific workdir tools/recipes (absolute paths)
- Optional recommended next steps
- Say `"Nothing relevant in my lore"` rather than fabricate

Keep total response (synthesis + pointers) ≤600 words.

## Implementation

- Skill: `skills/consult/SKILL.md` (thin pointer)
- Doc: `docs/consult.md` (full procedure)
- Cross-references: `attach.md`, `recall.md`, `lore-search.md`, `agent-boot.md`

## Related topics

- `attach-pattern.md` — the sustained sibling
- `lore-search-pattern.md` — lore-search mechanics used inside the consult subagent
- `skill-doc-pattern.md` — thin-skill + detailed-doc convention
- `versioning-release-types.md` — v4 is release-notes-only (additive, no user-side migration)

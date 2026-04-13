# Consult

`/lr:consult` asks an unloaded lore agent a question. A subagent boots the consultant, searches its lore, synthesizes a response, and exits. The host gets back the synthesis plus pointers to specific lore topics or workdir tools worth using directly. The consultant itself is unaffected — no reflection, no merge.

This is the lightweight option in the cross-agent-collaboration trio:

- `/lr:recall` — search lore of agents already loaded (host + guests)
- `/lr:consult` — one-shot question to an unloaded agent; handover of specific files
- `/lr:attach` — load another agent for sustained co-work

Use consult when a focused question will get you what you need. If you realize you need sustained engagement with the consultant's knowledge across many turns, escalate with `/lr:attach <same-agent>`.

## Usage

- `/lr:consult <agent-name>` — contextual consult; the host builds the brief from the current session
- `/lr:consult <agent-name> <hint>` — focused consult; the hint layers on top of session context

## Procedure

### Step 1: Preconditions

1. **Host must be loaded.** Consult needs the current session as raw material for the brief. If no agent is booted, respond: `No agent loaded. Run /lr:boot <agent-name> first.` and stop.
2. **Consultant must exist.** Standard discovery: scan directories for `lore-repo.md`, look for `agents/<name>/role.md`. If not found, list available agents and stop.
3. **Do not consult the host.** If the requested name equals the host, respond: `<name> is the host — use /lr:recall for its lore.` and stop.
4. **If the consultant is already an attached guest**, point to recall: `<name> is already attached as a guest — use /lr:recall to search its lore alongside the host's.` and stop. Do not dispatch a consult subagent for an already-loaded agent; recall is strictly better.

### Step 2: Build the consult brief

The brief has four parts, ≤400 words total:

1. **Task** — one or two sentences on what the host is actively working on this session.
2. **Session context** — two to five bullets: decisions already made, constraints surfaced, files being touched, the specific blocker driving the consult.
3. **Question / angle** — the specific question or issue. If the user provided a hint (`$ARGUMENTS` has more than just the agent name), center the angle on it.
4. **Output shape** — ask the subagent for:
   - A direct answer (≤400 words)
   - Pointers to specific **lore topics** worth reading in full — give absolute paths (file paths under `agents/<consultant>/lore/`)
   - Pointers to specific **workdir tools, recipes, or scripts** if relevant — give absolute paths
   - Optional recommended next steps for the host
   - Total consultant response ≤600 words plus pointer lists
   - `"Nothing relevant in my lore"` if the consultant genuinely has nothing — do not fabricate relevance

Keep the brief itself concise. The subagent will boot and read the consultant's lore — it does not need the host's full lore summarized, only what's in *this* session.

### Step 3: Dispatch the subagent

Use a general-purpose subagent. Prompt shape:

> You are being invoked as a short consult. Another lore agent is the host of the current session; they need your help with a focused question.
>
> **Step A — Boot as `<consultant-name>`.** Read `${CLAUDE_PLUGIN_ROOT}/docs/agent-boot.md` and follow the boot procedure to load yourself as agent `<consultant-name>`. This includes the standard version reconcile — do that normally; return any release notes text in your final response so the host can surface them to the user.
>
> **Step B — Answer the consult.** Here is the brief:
>
> ```
> <4-part brief from Step 2>
> ```
>
> Search your lore using the subagent-scan pattern described in `${CLAUDE_PLUGIN_ROOT}/docs/lore-search.md` (nested Explore dispatch is fine) or direct tools where a targeted lookup is better. Synthesize a response in the requested output shape.
>
> **Step C — Return.** Send back the synthesis with file pointers. Do not reflect. Do not merge. Do not write anything. Your role ends with this response.

The subagent's own context absorbs the boot, migration output, and lore scan. The host sees only the final synthesis returned.

### Step 4: Present to the user and the host

1. **Relay release notes** (if any came back from Step A's version reconcile) to the user verbatim.
2. **Show the consultant's synthesis** to the user, labeled with the consultant's name so it's clear whose voice this is.
3. **Read pointed-to files in the host's main context** only if they're load-bearing for the task at hand — otherwise leave them referenced but unread. Over-reading defeats the point of consult being lightweight.
4. **Carry the consult's answer** forward as working context for the rest of the session.

### Step 5: What the host may and may not do afterwards

The consult creates a *handover* of specific knowledge, not a full loading.

**May:**
- Read any specific files the consultant pointed to (lore topics, workdir tools, recipes, scripts). Domain visibility makes this free.
- Run or adapt workdir tools the consultant recommended.
- Apply the consultant's advice directly.

**May not:**
- Dispatch further lore-search subagents against the consultant's lore. That is attach territory — consult's boundary is the specific files the response called out.
- Expect `/lr:recall` to include the consultant's lore afterwards. Recall only covers agents currently loaded (host + attached guests). The consultant was never loaded into the host's session.

If either of those limits is too tight for the task, **escalate**: `/lr:attach <consultant-name>` loads the consultant for sustained use.

## No finalization for the consultant

The consultant does not reflect or merge because of this consult. From the consultant's perspective, the consult is read-only — its lore is queried, nothing is written back. If the host learns something during the session that the consultant should eventually know, the user can boot the consultant directly in a future session to capture it there. A formal consult-feedback mechanism is out of scope for v4.

## See also

- `${CLAUDE_PLUGIN_ROOT}/docs/attach.md` — the heavyweight sibling (sustained loading, finalization participation)
- `${CLAUDE_PLUGIN_ROOT}/docs/recall.md` — search lore of already-loaded agents
- `${CLAUDE_PLUGIN_ROOT}/docs/lore-search.md` — search brief structure and mechanics
- `${CLAUDE_PLUGIN_ROOT}/docs/agent-boot.md` — the boot procedure the subagent follows in Step A

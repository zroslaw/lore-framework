# Teammate Conventions — Standing Rules for Spawned Teammates

> **Audience note.** This is a **shared procedure doc**, not a skill — there is no `/lr:teammate-conventions` slash command. It is loaded implicitly by `agent-boot.md` Step 5 when boot detects that the current Claude Code process was started as an Agent Teams teammate (parent process has `--agent-id` — the canonical marker — and typically `--parent-session-id` in its args). It is **not** loaded for normal `/lr:boot` sessions or for the team lead. The rules below are the durable replacement for a one-shot spawn-prompt paragraph that empirically does not stick past the first few turns.

## Why these rules exist

When the user invokes `/lr:spawn-teammate <agent>`, the **express purpose** is to give the user a **parallel pane to work with that agent directly**. The user is sitting in the teammate's own pane, ready to talk to it. The team lead is the *conduit* that spawned the teammate — not the teammate's interlocutor.

Empirically, spawned teammates default to the wrong interlocutor: they route status updates, clarification questions, and approval requests to the team lead via SendMessage instead of to the user in their own pane. The lead is then forced into a relay role, which loops badly. The spawn prompt's one-shot paragraph telling the teammate this is wrong tends to wash out after a few turns; baking the rules into boot fixes them in place from the start of every session, freshly re-emitted every time the teammate boots.

## Standing Rules

### Rule 1 — The user in your own pane is your interlocutor

The user invoked `/lr:spawn-teammate` to talk to **you** in **your own pane**. They are there. When you have something to ask, report, or decide, talk to them in your pane via your normal text output — same as any non-teammate session.

This includes:
- Status updates and progress narration.
- Clarifying questions on requirements, scope, ambiguous instructions.
- Approval requests for risky / irreversible actions.
- Findings, recommendations, deliverables, errors, blockers.
- "I'm done" — the result is delivered in your pane, not relayed via the lead.

### Rule 2 — SendMessage to the lead is for explicit user-requested coordination only

Use `SendMessage(to: "team-lead", ...)` **only** when the user, in your pane, explicitly asks you to share or coordinate something with the lead or another teammate. Examples of legitimate use:

- *"Tell the lead I'm done with task X."*
- *"Ask the activity-supply-manager teammate whether their JIRA ticket is merged yet."*
- *"Send my findings to the lead so they can include it in the team summary."*

Examples of **illegitimate** use (do **not** SendMessage for these — talk to the user in your pane instead):

- "I need clarification on the requirements." → ask the user in your pane.
- "Should I proceed with this risky change?" → ask the user in your pane.
- "Here's my progress so far." → narrate in your pane.
- "I'm blocked on X." → tell the user in your pane.
- "I'm done." → say so in your pane.

If the lead sends you a message asking for one of these, the lead is acting on the user's behalf only when the user *in your pane* has asked them to. Otherwise, the lead is forwarding noise — respond in your pane to the user, not back to the lead.

### Rule 3 — Don't paraphrase or relay user messages on the user's behalf

If the user in your pane asks you something, the answer goes **back to the user in your pane**. Do not paraphrase the user's message and forward it to the lead "for awareness," "for context," or "in case they need to know." The user is the source of truth for what the lead needs to know; the user can SendMessage the lead themselves, or ask you to do it explicitly.

The narrow exception is a one-time relay when the user **explicitly** says *"tell the lead X"* or *"send this to Y"* — that's Rule 2, not Rule 3.

### Rule 4 — Idle notifications from the lead need no response

Agent Teams emits `{"type":"idle_notification",...}` messages as status pings. They are not requests. Do not respond, do not act on them, do not interpret them as the lead asking you a question.

## Operating cadence

Treat your pane like a normal interactive Claude Code session. The team-membership context (you have a lead, you have other teammates, you can SendMessage them) is **available capability**, not a default communication channel. Default communication is your own pane, with the user.

A useful self-check before any `SendMessage` call: *"Did the user in my pane just ask me to send this?"* If the answer is no, the message belongs in your pane to the user, not in a SendMessage to anyone.

## See Also

- `<framework-root>/docs/spawn-teammate.md` — the skill that creates teammates (and the lead-side redirect protocol that is the team-lead's mirror of these rules).
- `<framework-root>/docs/agent-boot.md` § Step 5 — where this doc is loaded.
- `<framework-root>/docs/conventions.md` § Teammate Discipline — the framework-level summary of the asymmetry between the lead-side and teammate-side rules.

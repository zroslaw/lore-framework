# Dialogue Mode

When the user invokes `/lr:dialogue` (or says "dialogue", "let's talk it through", "one step at a
time"), switch into dialogue mode for the rest of the session, until the user turns it off.

The user is the main collaborator and the driver. Your job is to keep their mental picture current:
give them the piece that matters now, let them react, and steer from there. Do not bury them in a
long, detailed article they have to dig through.

While dialogue mode is on:

- **Short turns.** Give the one essential thing now; hold the details until the user asks.
- **Keep their context in sync.** Lead with what changed, or what they need to know right now —
  especially easy-to-miss things, since the user is often multitasking and may have lost track.
- **One step at a time.** Move incrementally; let the user react and steer between steps.
- **No long articles.** If a reply is growing long, stop and check in instead of dumping everything.
- **Details on demand.** The user will ask when they want more depth.

## Re-asserting / turning off

- **Re-assert:** say "dialogue" or "keep it short" any time the agent slips into article-style dumps.
- **Off:** the user says so explicitly (e.g. "you can drop dialogue mode").

## Relationship to the sibling skills

Three independent *style* skills, each on a different level — they compose, invoke each as needed:

- **`plain-language`** — how each *sentence* reads (simple words, one idea at a time).
- **`dialogue`** — how much you say per *turn*, and the rhythm (short, incremental).
- **`follow-me`** — who drives the *thinking* (the user leads; don't race ahead).

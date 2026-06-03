**Goal:** find potential bugs in this unit — or immediately adjacent to it — with the focus anchored on *this* unit.

**You may read** the unit's code, the rest of the file, and other files in the repo you need for context (callers, callees, types, related modules). Gather as much context as you need to reason well; use your own judgement about how far to look.

**Do:**
1. Understand what the unit is supposed to do and how it connects to the rest of the system (its inputs, outputs, callers, side effects, shared state).
2. Trace the unit's execution paths and enumerate **edge cases** — empty/null/malformed inputs, boundary values, error and failure paths, concurrency/ordering hazards, unexpected states, resource/lifecycle issues, locale/encoding quirks where relevant.
3. Identify **potential** problems: wrong logic, missing validation, off-by-one, dropped/ swallowed errors, mishandled edge cases, incorrect assumptions about callers or environment, contract violations.

**Important constraints:**
- These are **potential** issues, not confirmed defects. Do **not** try to verify or fix them — a separate track handles confirmation and fixing.
- Stay anchored on this unit. A problem that merely passes *through* a neighbour is in scope only if it bears on this unit's correctness.
- If you find no plausible issues, return an **empty** `bugs` list — do not invent filler.

**Per bug, fill:**
- **`id`** — a slug from the bug's essence (e.g. `nil-notification-object-crash`), unique within this unit.
- **`title`** — short: *what* the bug is and *how it impacts us*.
- **`description`** — detailed enough to understand **and reproduce**: how to trigger it, the conditions required, and which other components are involved.

**Output:** the `bugs` artifact (`unit`, `signature`, `bugs[]`) conforming to the bugs schema.

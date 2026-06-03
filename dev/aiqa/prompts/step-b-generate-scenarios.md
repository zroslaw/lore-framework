**Goal:** design the set of **unit test-case scenarios** that would give this unit the fullest possible coverage — lines/statements, branches, and conditions. Aim as close to complete coverage as your judgement allows.

**HARD CONSTRAINT — clean room.** You must **not** read, open, search, or otherwise look at any existing test files during this step. Generate scenarios purely from the unit's code and behavior. (A later step compares your scenarios against the existing tests; that comparison is only meaningful if you did not peek.)

**Inputs you may use:** the unit's code and its context (as in Step A), and the **`bugs` artifact from Step A** — only to know what to exclude.

**Exclude bug behavior.** Do **not** create any scenario whose purpose is to test a behavior tied to a bug you reported in Step A. Bugs go down a separate track: if a bug is later confirmed, it gets a fix plus its own coverage tests; if rejected, scenarios for that behavior are generated then. So here, simply leave bug-related behavior out.

**Each scenario must be implementation-agnostic** — describe *what* to test and *what* the expected outcome is, not how to wire a specific test framework. The description must contain enough for *another agent* to write the unit test from it.

**Per scenario, fill:**
- **`id`** — a slug from the scenario's essence (e.g. `initializes-status-bar-on-normal-launch`), unique within this unit.
- **`title`** — short: what is being tested.
- **`description`** — precondition/input → action → expected outcome; note what to stub and what to assert.
- **`coverage-intent`** — one or more entries, each declaring what this scenario is meant to exercise:
  - **`kind`** — exactly one of: `statement`, `branch`, `condition`, `path`.
    - `statement` — a specific statement/line that must execute.
    - `branch` — a specific decision arm (if/else, switch case, guard-else).
    - `condition` — one boolean sub-condition's true/false outcome.
    - `path` — a specific end-to-end sequence of branches.
  - **`target`** — a *semantic* description of the specific thing covered (e.g. "branch: notification.object == nil"). **No line numbers.**

The union of all scenarios' `coverage-intent` is your claim of what covers the unit — make it as complete as you can.

**Output:** the `scenarios` artifact (`unit`, `signature`, `scenarios[]`) conforming to the scenarios schema.

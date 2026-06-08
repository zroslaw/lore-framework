You are running one **ULA unit pass** on a single unit of a source file.

You will perform **five steps in strict order: A → B → C → D → E.** Complete each step fully before starting the next.

**The cardinal rule of this pass:** you run all five steps in a *single context*, so isolation is **not** automatic — you must enforce it by discipline. Treat each step as if it were handed to a different person who sees only the previous step's artifact: Step B works from the unit's code plus Step A's `bugs` artifact, and **must not read, open, search, or recall any existing test** until Step C. The clean-room property of Step B — and your ability to later split these into independent agents — depends entirely on you honoring this now.

Steps **D and E** come *after* Step C, so the clean-room constraint no longer applies to them — they may read anything (callers, tests, the whole repo). They add **no new artifact**: they verify and correct the Step A `bugs` — revising each severity to its real impact, and moving findings judged not-real into a preserved `dismissed` list (originals kept, never deleted).

You return three artifacts at the end as one object `{ bugs, scenarios, gap }` — the `bugs` being the Step D/E-verified version. Each artifact must conform to its schema and must carry the unit slug and signature in its header.

Work carefully — this analysis is meant to be comprehensive, not quick.

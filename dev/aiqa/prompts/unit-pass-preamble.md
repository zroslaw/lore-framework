You are running one **ULA unit pass** on a single unit of a source file.

You will perform **three steps in strict order: A → B → C.** Complete each step fully before starting the next.

**The cardinal rule of this pass:** you run all three steps in a *single context*, so isolation is **not** automatic — you must enforce it by discipline. Treat each step as if it were handed to a different person who sees only the previous step's artifact: Step B works from the unit's code plus Step A's `bugs` artifact, and **must not read, open, search, or recall any existing test** until Step C. The clean-room property of Step B — and your ability to later split these into three independent agents — depends entirely on you honoring this now.

You return all three artifacts at the end as one object `{ bugs, scenarios, gap }`. Each artifact must conform to its schema and must carry the unit slug and signature in its header.

Work carefully — this analysis is meant to be comprehensive, not quick.

**Goal:** compare the ULA scenarios against the unit's **existing implemented tests**, in **both directions**, and record where they diverge. The divergence is the quality signal.

**Inputs:** the **`scenarios` artifact from Step B**, and the existing tests — which you now **may and should** read. Locate the test files in the repo that target this unit (search the repo's test directories / conventions).

**Matching rule (the definition everything depends on):**
> A ULA scenario is **implemented** if some existing test exercises the *same behavior* the scenario describes — judged by **intent**, not by test name or code structure. Conversely, an existing test is a **ULA miss** if it exercises a behavior that **no** ULA scenario describes.

**Do:**
1. **Record what you considered.** List in `considered-tests` every test source file you actually read for this unit. If you find none, use an empty list.
2. **Direction A — not implemented.** For each ULA scenario with no matching existing test (per the rule), add an entry to `not-implemented` with its `scenario` id and a one-line `note` on what behavior is left uncovered. These are the actionable gaps.
3. **Direction B — ULA missed.** For each existing test whose behavior **no** ULA scenario describes, add an entry to `ula-missed` with the `test` name, the `file` it lives in, and a `description` of the behavior ULA failed to anticipate.
4. **Summary counts** (real counts):
   - `totalUlaScenarios` — number of scenarios in the Step B artifact.
   - `totalImplementedTests` — number of existing tests targeting this unit.
   - `ulaNotImplemented` — **must equal** the length of `not-implemented`.
   - `ulaMissed` — **must equal** the length of `ula-missed`.

**Invariants you must satisfy:**
- `ulaNotImplemented == len(not-implemented)` and `ulaMissed == len(ula-missed)`.
- Every `not-implemented[].scenario` is a real scenario id from the Step B artifact.
- Every `ula-missed[].file` appears in `considered-tests`.

Do **not** report the match count as the headline — the mismatches (`ulaNotImplemented`, `ulaMissed`) are the metric.

**Output:** the `gap` artifact (`unit`, `signature`, `summary`, `considered-tests`, `not-implemented`, `ula-missed`) conforming to the gap schema.

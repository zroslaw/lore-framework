**Goal:** find potential bugs whose defect is in *this* unit, and — as a byproduct — capture any bugs you notice *elsewhere* while doing so. The focus stays anchored on this unit; the surrounding context is **mandatory input**, not optional.

**First, understand how the unit connects (required — read, don't skim).** You **must** read the unit's code, the rest of the file, and the other repo files you need to judge it — its callers, callees, types, shared/global state, ownership/lifetime, and threading/reentrancy. This is not optional background: which bugs exist, how severe they are, and what cross-unit issues surface all depend on it. Actually trace the callers and neighbours — don't assume.

**Find bugs in this unit:**
1. Trace the unit's execution paths and enumerate **edge cases** — empty/null/malformed inputs, boundary values, error/failure paths, concurrency/ordering hazards, unexpected states, resource/lifecycle issues, locale/encoding quirks where relevant.
2. Identify **potential** problems whose defect is *in this unit*: wrong logic, missing validation, off-by-one, dropped/swallowed errors, mishandled edge cases, incorrect assumptions about callers or environment, contract violations.
3. Record each in `bugs[]`, stating the precondition it rests on (e.g. "assumes the caller never invokes this concurrently").

**Capture cross-unit findings (don't drop them).** While reading callers, callees, and neighbours you may notice a bug *there* too — **record it** in `crossUnit[]` rather than discarding it. Two kinds:
- `external` — the defect lives in *one other* unit/file. Name it in `targets`.
- `interaction` — each unit may be correct alone, but their *combination* is the bug. List all involved units/files in `targets` (two or more) and explain the interaction in `description`.

These are recorded here because *this* unit's pass found them; a later aggregation step dedups and routes them — don't worry about that now. Stay disciplined: a `crossUnit` entry is a real defect you actually noticed, not a licence to audit the whole repo.

**For every finding (`bugs` and `crossUnit` alike), also write:**
- `impact-summary` — a plain-language summary of the bug's essence and impact that **any** engineer can grasp regardless of the stack; use general engineering terms, not stack-specific jargon. (Keep the deep technical detail in `description`.)
- `nature` — `product` (affects the product / user experience: wrong, inconsistent, or unexpected behaviour a user can hit) or `technical` (affects system internals: memory growth, leaks, inefficiency, excessive CPU, technical crashes). Classify by the dominant nature.
- `severity` — impact **if real** (not how sure you are): `critical` (data loss/corruption, security, crash/wrong-result on a normal path) · `high` (serious but bounded — edge-triggered/recoverable/workaround) · `medium` (limited blast radius) · `low` (minor/robustness/hardening) · `negligible` (not a behavioral defect — smell/cosmetic/deprecation/deliberate simplification).
- `confidence` — how sure it **is** a bug: `high` (solid reasoning) · `medium` (rests on unverified assumptions about callers/inputs/environment) · `low` (speculative lead). Do **not** mark anything "confirmed" — confirming is a separate track's job.
- `category` *(optional)* — the bug's **type** (e.g. `concurrency`, `error-handling`, `resource-lifecycle`), not its importance. Use `other` + `tags` if nothing fits.

**Important constraints:**
- These are **potential** issues, not confirmed defects. Do **not** verify or fix them — a separate track handles confirmation, severity adjudication, and fixing. Be **high-recall**: report a plausible issue even if context might later discharge it, and record your `confidence` honestly rather than self-censoring.
- Keep the defect-location split clean: a defect *in this unit* → `bugs[]`; a defect *elsewhere or emergent* → `crossUnit[]`.
- If you find no plausible issues, return **empty** `bugs` / `crossUnit` lists — do not invent filler.

**Output:** the `bugs` artifact (`unit`, `signature`, `bugs[]`, `crossUnit[]`) conforming to the bugs schema.

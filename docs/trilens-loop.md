# Trilens Loop

`/lr:trilens-loop` reviews a set of changes from **three independent perspectives**, triages the
findings, fixes what matters, and **repeats until the changes come back clean**.

The three reviewers are subagents. They did not author the changes, so they do not carry the
session's bias toward its own work. The host session — which did author the changes — owns triage
and all edits.

```
scope the changes → pick 3 lenses → 3 independent reviewers → triage → fix → repeat → stop when clean
```

## Usage

```
/lr:trilens-loop
/lr:trilens-loop only one round, no fixes
/lr:trilens-loop use security, performance and API compatibility as the lenses
/lr:trilens-loop review only the changes under tests/
/lr:trilens-loop max 5 rounds
```

There are no flags. The single optional argument is **free text**, and it may amend any part of the
flow below — scope, lens count, lens choice, round cap, whether fixes are applied at all.

**Free text outranks every default in this doc, including the two rails** — the round cap and
reviewer independence. The user may ask for a single round, for twelve, or for you to review the
changes yourself with no subagents at all. Do it.

The one thing you owe in exchange is **visibility**. When an amendment removes a rail, say so in
your output: name the rail, state that the user asked for it, and state the consequence. In
particular, if the user asks you to review your own changes, label the result plainly as a
**self-review, not an independent review** — the findings come from the session that authored the
changes and carry its bias. Never remove a rail silently, and never call a self-review a trilens
review.

This is different from an engine that *cannot* spawn subagents. That is not an instruction from the
user, and it is the one case where you stop — see the next section.

## When to use it

Reach for it when the change has real blast radius: a new skill or script, a procedure-doc change, a
schema or vocabulary change, a doc sweep, anything about to be shipped or committed to a shared
branch.

Skip it for trivial edits. Three subagents per round over two or three rounds is proportionate to a
substantive change and wasteful for a one-line fix.

## Requirement: native subagents, no fallback

This skill needs your engine's **native subagent mechanism**. It has no host-side fallback, and
that is deliberate.

Everywhere else in this framework a subagent is an *optimization* — parallelism and context
isolation, where serial host-side execution reaches the same answer more slowly. Here the subagent
is the *semantics*: independence from the author is the entire deliverable. A host reviewing its own
changes is not a slower review, it is not a review at all.

Therefore:

- **Never spawn a context-inheriting subagent.** A subagent that inherits this conversation
  inherits the bias the skill exists to remove. Your engine profile's **subagent-spawn** binding
  names the mechanisms and their traps — read it before spawning.
- **If your engine profile declares no subagent mechanism at all, stop and report it.** Do not
  quietly review the changes yourself under this skill's name. (A user who explicitly *asks* for
  self-review is a different case — see § Usage.)

**A mechanism the engine profile documents but the framework has not yet validated end-to-end is
good enough for this skill.** Use it, and say in your output that the path is unvalidated. The bar
is "the profile names a real mechanism", not "the framework has a passing test for it" — otherwise
the skill would be unavailable on an engine that plainly supports it.

## Procedure

### Step 1: Resolve the scope

Default scope is **everything this session changed** — not a git range. It is the **union** of the
two sources below, not source 1 with source 2 as a sanity check:

1. The files you created or edited this session. You know these directly.
2. The uncommitted changes in every repo those files live in — `git -C <repo> status --porcelain`
   and `git -C <repo> diff`. This catches what you missed and produces the diffs reviewers read. Use
   `git -C`; never `cd` (see `conventions.md` § Tooling: CWD Safety).

Taking the union matters: a session that was *asked* to review work it did not author itself (a
fresh session opened onto a dirty tree) has an empty source 1, and treating source 2 as subordinate
would resolve the scope to nothing.

3. If the session also committed, include those commits in the scope.
4. A session in a lore workspace often spans repos (e.g. the plugin plus a dev repo). Group the file
   list by repo.
5. **If the resolved scope is empty, stop and report it** — say that nothing was found to review and
   that the user can name a scope in free text. Do not spawn reviewers over nothing.
6. **Print the resolved scope before spawning anything.** A wrong scope caught here costs nothing;
   caught after dispatch it costs three agents.

Free text can narrow the scope ("only the changes under `tests/`") or replace it entirely ("review
the diff against `origin/main`").

### Step 2: Choose three lenses

Pick the three perspectives from which *these particular* changes most need reviewing. The choice
depends on the change and the project — it is a judgement call, not a lookup.

Rules:

- **A lens is a way of looking, not a place to look.** "Correctness", "security", "newcomer
  experience" are lenses. A filename, a directory, a diff, or "references" is a *target*, not a lens —
  splitting the work by target gives you three reviewers doing the same kind of thinking on different
  files, which is the opposite of what this skill buys. Every reviewer sees the whole scope; what
  differs is the question each one asks of it.
- **Mutually exclusive.** If two reviewers would surface the same issues, you have wasted a slot.
- **Tell each reviewer what to skip**, including what the other two lenses own.
- **Apply the don't-fan-out test:** *would a single agent looking at all N items produce the same
  verdicts as N separate agents?* If yes, batch that work into one lens instead. A fan-out across
  items sharing a uniform property adds cost without adding rejection power.

A starter catalog to choose from — a menu, not a default:

| Lens | Looks for |
|---|---|
| Correctness | bugs, races, edge cases, wrong assumptions |
| Security / adversarial input | hostile input, injection, path traversal, unsafe parsing |
| UX & discoverability | will a real user find this, understand it, and act on it |
| Architectural consistency | does it compose with the project's own stated patterns |
| Terminology coherence | did a vocabulary change hold together across every site |
| Newcomer experience | walk it as a first-time reader; where does the path break |
| Release readiness | breaking changes disclosed, versions and stamps consistent |
| Literal-execution fidelity | read it as the agent that must execute it word for word |
| Filesystem-grounded verification | run the commands the change promises; verify claims live |

When one lens is architectural and a lore agent is booted, point that reviewer at the agent's
`lore-context.md` as its baseline, so it applies the agent's own stated meta-rules to the change.

Announce the three chosen lenses and one line of reasoning each before dispatching.

**The three lenses are then fixed for the whole loop.** Later rounds re-spawn the same three lenses,
not newly chosen ones — the round-N+1 brief has to hand each lens its own prior findings (Step 6),
which a lens introduced mid-loop would not have. The one exception is the optional single-reviewer
final round described in Step 6.

### Step 3: Spawn three independent reviewers

> **Engine note.** Spawn via your engine profile's **subagent-spawn** binding
> (`<framework-root>/docs/engines/<engine>.md`). That profile is the single description of the
> mechanism, its roles, its caps and its traps, and it is where corrections land — do not work from a
> copy. **Read the whole binding before spawning:** more than one engine has a trap that silently
> costs you the reports. On Claude Code, for illustration, the binding is the `Agent` tool with the
> three calls issued in one message and `subagent_type: "general-purpose"`; the profile says why the
> other subagent types are wrong for this job.

Four requirements on however you spawn:

- **A regular model tier, not a flagship one.** Review is a well-shaped, bounded task, and the
  mid-tier models do it well — spend the budget on *rounds and independence*, not on the largest
  model. Default to the engine's regular tier: **sonnet** on Claude Code, **gpt-4.5** on Codex,
  **composer-2.5** on Cursor. Escalate a single lens to a flagship model only when that lens has
  already shown it needs the depth, and say so in your output. Free text overrides this like any
  other default.

- **Read-only.** A reviewer reports; it never edits. Prefer a structurally read-only role where your
  engine has one; otherwise state the constraint in the brief. Every edit belongs to the host.
- **Cold context.** No inherited conversation — see § Requirement above.
- **The report must actually come back to you.** Confirm the spawn mode you chose returns the
  subagent's final message. Some engines have a spawn mode that does not; if the binding names one,
  either avoid it or instruct the reviewer explicitly to send its report back before finishing.
  Three reviewers that silently never report leave Step 4 with nothing to triage.

Each brief contains, in this order:

1. **Context** — what changed, and **what it is for**.
2. **Files** — the concrete list with absolute paths. Include anything adjacent that is *not* in
   scope but might need a look; that boundary is where misses hide.
3. **This lens** — what to look for, with example failure modes.
4. **What to skip** — nits, generic advice, low-confidence guesses, and explicitly what the other
   two lenses are covering.
5. **Output format** — findings as severity (`BLOCKER` / `HIGH` / `MEDIUM` / `LOW`), `file:line`,
   the issue, a one-sentence fix; then a closing **verdict line**: `SHIP`, `SHIP-WITH-FIXES`, or
   `BLOCK`. Cap the report at ~600 words.

**Give the goal, not your rationale.** The reviewer needs to know what the change is *for*, so it
can judge fitness for purpose. It must not be told why you made each individual decision —
rationale pre-empts exactly the criticism you are spawning reviewers to get. Independence at the
spawn level (no inherited context) and independence at the brief level (no supplied justification)
are the same rule applied twice.

### Step 4: Triage the findings

This is the host's job, and the one place where having authored the changes is an advantage.

1. **Verify every `BLOCKER` and `HIGH` against the actual file before acting on it.** Reviewers
   sometimes hallucinate or reason from stale state. Confirm the claim, then fix.
2. **Accept or decline each finding, with a one-line reason.** Declining is legitimate — a lens can
   be wrong about this change, or right in general but out of scope here. The reason is what makes a
   decline stick.
3. **Cross-check overlap.** Two lenses hitting one issue from different angles is one fix, recorded
   against both.
4. Order the work `BLOCKER` → `HIGH` → `MEDIUM`, then judge the `LOW`s.

Maintain a **dispositions ledger** across the whole loop: for each finding, its lens, its severity,
and one of three states with a reason. The ledger drives the next round and is part of the final
output.

| State | Meaning |
|---|---|
| `APPLIED` | Accepted and fixed. |
| `DECLINED` | Rejected on the merits — wrong about this change, or out of scope. Give the reason. |
| `ACCEPTED (not applied — report-only)` | Judged real and in scope, but a free-text amendment forbids edits this run. |

The third state exists because "no fixes" is a legitimate amendment, and folding those findings into
`DECLINED` would misreport them as rejected. A reader of the ledger must be able to tell "we judged
it wrong" from "we agreed but were told not to touch anything."

### Step 5: Apply the accepted fixes

The host makes every edit. Keep the fixes scoped to what was accepted — a review round is not a
licence for unrelated refactoring.

If a finding is real but genuinely out of scope, record it as `DECLINED (out of scope)` and say so
in the final summary, so it is visible rather than lost.

### Step 6: Next round, or stop

If anything was fixed, run another round — subject to the round cap, see § Termination. Spawn
**fresh** reviewers: independence is the point, so they start cold with no memory of the previous
round. That memory has to be supplied deliberately:

Each round-N+1 brief **must** open with:

1. A numbered **APPLIED / DECLINED (+reason)** list of *that lens's own* findings from the previous
   round.
2. A short digest of what the *other* lenses' fixes changed inside this lens's territory.

Without that ledger, declined findings resurface every round and the loop never converges. With it,
settled items stay settled and each round reads as a delta rather than a re-review.

Expect round N's findings to cluster around round N−1's **edits** — fixes create new seams. That is
normal convergence behaviour, not a sign the process is failing.

**Optional shape for the last round.** Once the loop is clearly converging, the final round may be a
*single* reviewer given the whole diff and filesystem access, instead of three lens-isolated ones.
Round 1 and the final round are different jobs: breadth, parallel and isolated versus depth,
sequential and whole. One reviewer holding the entire diff catches cross-file drift that per-lens
reviewers structurally cannot see.

## Termination

Stop when a round produces nothing worth fixing. Shrinking findings counts are the signal —
two to three rounds is typical; a change that reshapes several cross-cutting files can take more.

**A silent round is not a clean round.** "Nothing worth fixing" means reviewers looked and found
little. If *no* reviewer returned a report, you have no signal at all, and the two states are not
interchangeable — terminating there would declare success on a review that never happened. At least
one reviewer must have actually returned findings-or-a-verdict before a round may count as clean.
If none did, treat the round as failed: retry it once, and if that also comes back empty, stop and
report that the review could not be obtained.

**The silence retry does not count against the round cap.** A failed round produced no review, so it
is not one of the rounds the cap is counting — including when the cap is pinned at 1. Otherwise
`one round only` plus one silent round would mean the user gets no review at all and no error saying
so.

Three guards:

- **Round cap — default 3.** Amendable by free text. It stops an unattended loop from spending
  agents indefinitely.
- **Reviewer-gated stop.** Do not terminate while any reviewer's most recent verdict is `BLOCK`.
  You may override that — but state the override and the reason explicitly. Without this guard the
  same session writes the fixes *and* grades its own convergence; the guard puts part of the
  stopping decision in the reviewers' hands.
- **At least one report per round** — see the paragraph above.

If the cap is reached with findings still open, **report what remains** instead of declaring
success. Note that hitting the cap while a verdict is still `BLOCK` is itself an override of the
reviewer-gated stop — a framework-driven one rather than a user-driven one, and it must be disclosed
the same way.

## Final output

All five items below are **required**, not a suggested shape. A bare list of findings is not a
report — most of what makes this skill auditable is in items 1, 2 and 5. Print every one of them
even when the answer is short or empty ("no rails overridden").

1. **Scope** — what was reviewed, grouped by repo.
2. **Lenses and verdicts** — the three lenses used each round, and each reviewer's verdict line.
3. **The dispositions ledger** — every finding, its lens, its severity, and its state
   (`APPLIED` / `DECLINED` / `ACCEPTED (not applied — report-only)`) with the reason.
4. **What was fixed.**
5. **Anything still open, deferred, or overridden.** This covers **every** rail that did not hold,
   not only user-requested ones: a rail the free text switched off, a `BLOCK` verdict you overrode, a
   round cap reached with findings open, a lens that never reported, and an engine path you used that
   the profile marks as unvalidated.

The ledger is printed, not filed. This skill writes no records of its own.

## When reviewers fall short

- **A partial return is additive evidence.** A reviewer that reports one finding and then stalls has
  done useful work. Read what came back; do not discard the round.
- **Fewer than three returning is still a round.** Continue, and say which lens is missing so the
  gap is visible. **Zero returning is not** — see § Termination.
- **Reviewers may disagree with each other.** Decide yourself, after reading the actual files.
  Reviewers work from limited context; consensus is not the standard, correctness is.
- **If your engine profile names no subagent mechanism, stop** and report the limitation rather than
  quietly substituting self-review. A user who explicitly asks for self-review gets it, labelled as
  such (§ Usage) — that is their call to make, not yours.

## Boundaries

- **Not `/lr:check`** — that checks the domain's own content consistency. **Not `/lr:doctor`** — that
  diagnoses runtime ailments. Both are state-scoped; this is change-scoped.
- **Not part of finalization.** It never writes lore, never reflects, never merges, never commits.
- It **does** edit the files under review — that is the loop. For a review with no edits, say so in
  the free text ("no fixes").

## See also

- `<framework-root>/docs/engines/claude.md`, `codex.md`, `cursor.md` — the subagent-spawn bindings
  this skill depends on.
- `<framework-root>/docs/conventions.md` § Tooling: CWD Safety — why scope resolution uses
  `git -C <repo>`.
- `<framework-root>/docs/check.md` — domain content consistency, the state-scoped sibling.
- `<framework-root>/docs/spawn-teammate.md` — named teammates do not auto-return reports; this skill
  deliberately uses plain background subagents instead.

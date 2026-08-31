# Trilens Loop

`/lr:trilens-loop` reviews the session's changes from **three** independent, cold-context
perspectives — three by default because differing perspectives are the whole idea, and never
subagents that inherit this conversation, since independence from the author is the entire point.

## Step 0 — Announce

Print this to the user before doing anything else, filling in any `<placeholder>`:

> Reviewing this session's changes from three independent angles. **Each reviewer is a subagent that
> starts cold, knowing nothing about this conversation** — that's the whole point, because a reviewer
> who watched me make a decision tends to agree with it. I pick three genuinely different
> perspectives, fix what's worth fixing, and repeat until a round comes back clean. I'll tell you
> what I applied and what I declined.

## The loop

1. **Scope.** Resolve it yourself: the files you changed, union with `git status`/`diff` in every
   repo involved. You need this to know which trees and which files to name for reviewers — not to
   hand them a diff. **If the scope comes out empty, stop and say so**; don't spawn reviewers over
   nothing.
2. **Lenses.** A lens is a *way of looking* — one perspective from which this session's changes
   deserve to be examined. Pick the three that matter most for *these* changes, and make them
   genuinely different from each other: not places to look, not overlapping targets. Three
   different lenses over the same whole scope beats three reviewers splitting it between them,
   which just buys you the same thinking three times.

   **Choosing them is your job, and yours alone.** Nobody else in the loop knows what you just did;
   the reviewers arrive cold by design. So reason from the change itself — what kind of work was
   this, and what are the three ways it is most likely to be wrong? A schema migration, a rewritten
   procedure doc, and a new CLI command each deserve a different trio. Reaching for the same three
   lenses every time defeats the point as surely as picking three lenses that say the same thing.
3. **Spawn.** Spawn **subagents** — one cold, read-only subagent per lens, using whatever subagent
   mechanism your engine gives you. You don't need to look anything up first. What you do need is
   real independence: it is the deliverable here, not a speed-up, so there is **no host-side
   fallback**. If you cannot spawn independent subagents at all, stop and say so — running the
   lenses yourself, in sequence, is a different procedure wearing this one's name. Each reviewer
   returns findings tagged `BLOCKER` / `HIGH` / `MEDIUM` / `LOW`, and one overall verdict: `SHIP`,
   `SHIP-WITH-FIXES`, or `BLOCK`. See the exchange contract below for what may cross the wire.

   Run reviewers on a **regular model tier, not a flagship one** — sonnet on Claude Code,
   composer-2.5 on Cursor, gpt-5.4 on Codex. Those are illustrations, not a lookup table: pick
   whichever current model is your engine's regular tier. What buys quality here is more rounds and
   genuinely independent lenses, not a more expensive reviewer. Escalate a single lens only when
   that lens has demonstrably failed at the regular tier.
4. **Triage — yours alone.** Check every `BLOCKER` and `HIGH` against the file it points at (lower
   severities at your discretion), decide whether it is real and worth addressing, apply what is,
   decline the rest with a one-line reason. Each finding ends in exactly one of three states:
   `APPLIED`, `DECLINED`, or `ACCEPTED` — the last for a finding you agree with but are not acting
   on *here* (out of scope, or fixes were turned off), which is a legitimate outcome and must not be
   filed as either of the other two.
5. **Repeat, if the changes are considerable.** Re-resolve the scope first — your own fixes just
   changed it. Fresh reviewers each round, each told how the previous round disposed of every
   finding, accepted ones included, so settled findings don't resurface. Stop as soon as a round
   comes back with nothing worth fixing — if that is round one, you are done, that is a good
   outcome and not a reason to keep looking. **Never more than three rounds.**
6. **Report, briefly.** Close with a few lines, not an essay: rounds run, the three lenses, each
   finding as one line with its state, and anything you overrode.

## Stopping rules

- A round where a lens did not actually report is **not** a clean round for that lens — retry the
  missing ones once, and that retry does not count against the three-round ceiling. If they come
  back silent again, say which lenses never reported and stop; never bank a silent round as clean.
- Never call it done while a reviewer's latest verdict is `BLOCK`, without saying out loud that you
  are overriding it.

## Exchange contract

Keep both sides lean. This is how the loop is meant to run at any scale, not a fallback for tight
budgets.

- **Host → reviewer:** which repos and working trees to look at, the plain list of files that
  changed, a sentence or two on what you were trying to do, and which lens it owns. The file list
  and the task give the reviewer its bearings — what the change is *for* — without telling it what
  to think. **Don't hand it the diff or the contents of anything**; it reads the files itself. The
  fresh look is most of what you are paying for, so stop at orientation: no walkthrough of your
  reasoning, no account of what you believe you got right.
- **Reviewer → host:** the findings and the verdict, nothing else. Each finding is a pointer into
  code or docs that already exists — path, line, and the signature or heading sitting there — plus
  roughly a paragraph on what is wrong at that spot, plus its severity.
- **Never crosses the wire:** pasted files, quoted excerpts, or a blow-by-blow account of what you
  changed and why it is right. Orientation is a sentence or two; past that you are reviewing your
  own work on the reviewer's behalf, which is the one thing you spawned it to avoid.

## Overrides

Free text overrides any of the above — fewer rounds, narrower scope, even a self-review. Just
disclose whatever you turned off. The three-round ceiling is the one thing it does not lift.

# Trilens Loop

`/lr:trilens-loop` reviews the session's changes from three independent, cold-context subagent
perspectives — never subagents that inherit this conversation, since independence from the author
is the entire point. Resolve the scope (files you changed, union with `git status`/`diff` in every
repo involved), pick three lenses that are *ways of looking*, not places to look or overlapping
targets, and spawn one cold, read-only reviewer per lens with the whole diff, asking for
`BLOCKER`/`HIGH`/`MEDIUM`/`LOW` findings plus a `SHIP`/`SHIP-WITH-FIXES`/`BLOCK` verdict. Triage
yourself: verify every `HIGH`+ against the real files, apply what's real, decline the rest with a
one-line reason. Repeat with **fresh** reviewers — each handed its own prior round's
applied/declined findings so nothing resurfaces — until a round comes back with nothing worth
fixing; a round where no reviewer actually reported is not a clean round, retry it once. Default cap
3 rounds, and never call it done while a reviewer's latest verdict is `BLOCK` without saying so.
Free text overrides any of this (fewer/more rounds, narrower scope, even self-review) — just
disclose whatever you turned off.

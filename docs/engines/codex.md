# Engine Profile — Codex CLI

Selected by boot (`agent-boot.md` Step 0) when `<framework-root>` lives under `~/.codex/…`
(e.g. `~/.codex/plugins/cache/<marketplace>/lr/<version>/`). Fills the same five bindings as
`claude.md` (the reference profile). **Where a value here conflicts with a shared procedure doc,
this profile wins for that step.**

Empirical basis: Codex trials on `codex-cli 0.142.5`, 2026-07-05 — boot, recall, and full
finalize, plus binary ground-truth of the multi-agent subsystem. See lore
`codex-cli-plugin-loading-findings.md` and workdir `codex-multiagent-live-capture.md`.

## Binding values

| Binding | Value on Codex |
|---|---|
| **framework-root** | `${CLAUDE_PLUGIN_ROOT}` is **empty** here — never rely on it. Use the absolute path self-located in Step 0. When you spawn a subagent, **inline that absolute path** into its brief (the subagent cannot self-locate from your context). |
| **invocation-syntax** | Codex installs the `SKILL.md` skills natively; a **user** invokes them through Codex's own skill mechanism. **Do not type `/lr:<skill>` as an agent** — in `codex exec` it falls through to the shell and fails. When you need a skill's behavior mid-task, **read `<framework-root>/docs/<skill>.md` and follow it directly.** |
| **subagent-spawn** | Use Codex's native **`spawn_agent`** tool (feature `multi_agent`, on by default). Roles: `worker` (write), `explorer` (read-only). Collect results with `wait_agent` (call it sparingly — only when blocked on a result). **These tools are in-session model actions — they CANNOT be called from a shell command.** Caps: `agents.max_threads` ≈ 6, `agents.max_depth` = 1 (you may spawn; your subagents may not spawn again). See the fan-out override below. |
| **memory-file** | `AGENTS.md` (not `CLAUDE.md`). |
| **runtime-bounding** | No Bash-tool timeout flag; a long command is bounded by the Codex sandbox / `agents.job_max_runtime_seconds`. Ignore "set the Bash-tool timeout" prose. |

## Capability gates

- **teammate-detection** — `ps -o args= -p $PPID` is **blocked** in Codex's sandbox
  (`operation not permitted`). Treat any error as "not a teammate" and continue as a normal host
  session. Claude Agent-Teams / `spawn-teammate` features are gated off here. (Codex *does* have a
  native multi-agent subsystem — see workdir `codex-multiagent-live-capture.md` — but porting
  `spawn-teammate` onto it is a separate future task, not part of this profile.)

## Fan-out override (merge / recall / consult)

The shared procedures (`process-merge.md`, `recall.md`, `lore-search.md`, `consult.md`) describe
the Claude fan-out: N parallel `Agent` calls, and each subagent reads the procedure doc itself.
On Codex, run the **same procedure** with these substitutions:

1. **Mechanism.** Express fan-out as **`spawn_agent`** calls (one per active agent), not `Agent`
   tool calls, and not shell calls. Spawn them to run concurrently; gather with `wait_agent`.
   Use role `worker` for merge (needs write), `explorer` for recall (read-only).
2. **Host reads the procedure; subagent gets the steps inline.** Codex convention: *the main
   agent reads instruction/reference files itself and does not delegate reading skill
   instructions to a subagent.* So **you (the host) read the procedure doc** (`process-merge.md`
   etc.) and put the concrete steps into each subagent's brief — instead of telling the subagent
   to open the doc. The subagent still **boots as its target agent** (loading that agent's
   `role.md` + `lore-context.md` is identity loading, not skill-reading, and stays).
3. **Inline the resolved `<framework-root>`** absolute path into every brief (see framework-root
   binding).
4. **Respect the caps.** Depth-1 fan-out is fine (host → subagents, no re-spawn). If a session
   ever has more active agents than `max_threads` (≈6), spawn in chunks and note the chunking —
   do not silently cap coverage.

## Git & the sandbox (operational)

Codex's `workspace-write` sandbox **blocks writes to `.git/`** even inside the working directory
(`Operation not permitted` on `.git/index.lock`, `.git/FETCH_HEAD`, …). Consequences:

- **auto-pull** (boot) will fail its `git pull` — that is fine, boot already degrades on pull
  failure; nothing to fix.
- **finalize's commit** (and any framework `git commit`/`git pull`) cannot run under the default
  sandbox. To let it through, run Codex with `.git` writable — e.g. `--sandbox
  danger-full-access` for a trusted local run, or add the repo's `.git` to the writable roots
  (`-c sandbox_workspace_write.writable_roots=[…]`). Otherwise **leave the merged changes
  uncommitted and have the user commit by hand** — merge itself completes and writes lore to
  disk; only the commit is gated. Report this rather than treating it as a merge failure.

## Notes

- All values above are **facts to follow**, so you do not rediscover them at runtime.
- This profile targets the **stable** `multi_agent` feature only. `multi_agent_v2` /
  `enable_fanout` are under development and off by default — do not depend on them.

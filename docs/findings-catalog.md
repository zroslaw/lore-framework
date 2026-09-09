# Health findings catalog

This is the single wording and repair catalog for `check`, workspace initialization, and
boot's workspace-refresh report. Scripts emit evidence, not user-facing sentences.
A finding is an observation, not authorization to repair it. Never infer a clean check from
missing evidence or a scan warning.

## Rendering and fix tiers

Summary counts come from `check`'s `summary`. With no workspace descriptor, routine setup
findings S4/S5/S10/S17/S18 collapse into the workspace-init suggestion (`collapsed: true`).
Unsafe enclosing Git state and unparseable plugin settings remain visible. Other consumers
render their scan's findings directly. S11 and R10 test the same registration predicate:
full `check` uses R10; workspace-only check and existing scanner consumers use S11.

- **1:** propose the named Lore command; run it only after approval, using its skill procedure.
- **2:** show the concrete shell command or file repair; do not execute as part of `check`.
- **3:** show engine/system repair instructions; never clear the running plugin or restart it.
- **none:** informational; no repair offered.

Do not ask again for an unchanged action already approved in this session. Bind a proposed
repair to the actual affected paths; never substitute placeholders into shell commands.

## Plugin findings

| ID | Say using the finding data | Fix | Fix tier |
|---|---|---|---|
| P1 | Installed version is behind the latest published release. Name both versions. | Engine-specific plugin refresh in `INSTALL-<ENGINE>.md`, then restart. | 3 |
| P2 | A newer local plugin tree exists than the loaded one. Name both paths and versions. | `fix-stale-plugin-cache.md`; use the engine's own refresh instructions. | 3 |
| P3 | The running engine could not be identified. | Re-run with the user's known `--engine claude`, `codex`, or `cursor`. | 2 |
| P4 | Plugin VERSION or manifest versions are missing, invalid, or disagree. Name each file and expected/actual value. | End users: reinstall/refresh the plugin. Framework developers: reconcile the named files with VERSION. | 3 |
| P5 | An older Codex temporary marketplace copy is present and may interfere with loading. Presence is not proof it won. | Inspect `fix-stale-plugin-cache.md` and `INSTALL-CODEX.md` before changing engine state. | 3 |
| P6 | Migration Write Paths is missing or malformed. Name the file and invalid lines. | Repair per `conventions.md` § Migration Write Paths; end users refresh the plugin. | 3 |
| P7 | Cursor skill wrappers are missing, orphaned, or differ from the canonical generator. | Developers: `python3 scripts/sync-cursor-skills`; end users refresh the plugin. | 3 |

**Bootstrap trap:** a session running an old `check` cannot compute new P findings. If the
report has no plugin layer, open `fix-stale-plugin-cache.md` directly. When no skills exist,
start with the appropriate install guide; a missing command cannot diagnose itself.

## Repo findings

| ID | Say using the finding data | Fix | Fix tier |
|---|---|---|---|
| R1 | Repo descriptor metadata is missing or malformed. Name fields. | Repair `lore-repo.md` per `conventions.md` § Descriptor Files. | 2 |
| R2 | Repo version stamp differs from the running framework version. | If repo is behind: `update`; if ahead: refresh the plugin first, never downgrade the repo. | 3 |
| R3 | No agents were found in this repo. | `create-agent` when the user wants an agent. An empty repo is supported. | 1 |
| R4 | Role description is missing/malformed, a legacy role version field remains, or `reason: unreadable_role` means role metadata could not be checked. | `workspace-init` for routing descriptions; `update` for legacy metadata. For an unreadable role, show the affected path and ask the user to restore read access before rerunning; do not regenerate its content. | 1; unreadable role: 2 |
| R5 | Agent files or directories are missing. List them. An absent optional `lore-context.md` is informational (boot supports a new agent without it); a context path that is not a file is an error. | Restore the missing content from Git or repair the agent structure per `agent-boot.md`; do not invent lost knowledge. | 2 |
| R6 | Lore validation or reference caution. Name the agent, file, issue, and evidence. Coverage is reported separately. | `lore-structure.md` and `groom` for structural repair; repair references against actual targets. | 2 |
| R7 | Pending reflections have not been merged. | `merge` for that agent, only when approved. | 1 |
| R8 | Lore changes are uncommitted. List paths. | Preserve through the agent's normal finalization workflow when requested; do not trigger finalization automatically. | 1 |
| R9 | Topics were committed after the context summary. List topics and summary date; this suggests staleness, not proof of inaccurate content. | Review the summary against those topics and update it if needed. | 2 |
| R10 | Agent has no registered shortcut. It can still be loaded with `boot`. | `register-agent` or `register-repo`. | 1 |
| R11 | Shortcut target is missing or cannot be parsed/resolved. | `register-agent`/`register-repo` for the intended target. | 1 |
| R12 | Shortcut format differs from current registration rules. List reasons. | `fix-stale-shortcut-bootstrap.md`; re-register the affected shortcut. | 1 |
| R13 | Role changed after the shortcut file. | Review whether refresh is needed; `register-agent` if so. | 1 |
| R14 | A pre-plugin local command duplicates a current plugin skill. | Review the named file and remove the obsolete duplicate. | 2 |
| R15 | Shortcut agent name and target role heading differ, or could not be compared. Show both. | AI may explain an intentional alias; correct a real mismatch only after approval. | 2 |

## Findings catalog

| # | Fires when | Severity | Say | Fix | Fix tier |
|---|---|---|---|---|---|
| S1 | `managed_paths.dirty` is non-empty | warn | N framework-managed workspace file(s) have uncommitted changes — they exist only on this filesystem, and a teammate's `workspace-pull` receives a stale state. Name the paths. | `workspace-push` | 1 |
| S2 | `git.ahead > 0` | warn | N workspace commit(s) are not pushed. | `workspace-push` | 1 |
| S3 | git-tracked, no `origin`, and no `sharing: local` | info | The workspace is git-tracked but unshareable — `workspace-pull` phase 0 and the README join path are inert until a remote exists. | `git -C "<workspace>" remote add origin <url>`, or `workspace-init`, which also offers to record a deliberately local-only workspace instead | 2 |
| S4 | descriptors present, workspace not its own git root | info; **warn** when `data.enclosing_root` is set | This is a local-only workspace — a supported mode. Nothing here can be shared with a team until git tracking is enabled. If `data.enclosing_root` is set, say instead that the workspace sits inside another git repo at that path, which is a different and more serious condition: no workspace-level git operation is safe. | `workspace-init` (offers tracking); for the enclosing-repo case, move the workspace out or make it its own repo | 2 |
| S5 | top-level git repos on disk that no descriptor declares | info | Name them with their origin URLs. They are pulled (phase 4) but never cloned for a teammate, so a fresh checkout of this workspace will not contain them. | `workspace-init` (offers to declare them) | 1 |
| S6 | declared repos absent from disk, excluding any whose directory name is claimed by two URLs | warn | Name them. Declared repos that are missing mean this workspace is not fully materialized. A repo caught in a dirname collision is deliberately absent from this list and appears under S13 instead — `workspace-pull` cannot place it, so offering pull as the remedy would send the user into a second failure. | `workspace-pull` | 1 |
| S7 | a child git repo has no `/<dirname>/` line, or a standard ignore line is missing | warn | Report the two groups separately — uncovered child repos (their contents could be committed into the workspace repo) and missing standard ignore lines (`/.worktrees/`, `/.lr-beings/`, `/.tmp/`). | `workspace-pull` (phase 3 appends both) | 1 |
| S8 | a top-level repo is not on its default branch, or is on a detached HEAD | warn | **Check `detached` first.** When it is true, say the repo is **on a detached HEAD** and do not print a current branch — there is none, and `current` is null. Reported even when the default branch is unknown: being on no branch is off production state whatever the default is, and a commit made there is lost by the next checkout. **Otherwise** name the repo, its current branch, and its default. Either way: top-level repos hold production state, and branch work belongs in a worktree. | `docs/worktrees.md` — move the work to `.worktrees/<repo>/<slug>/`; for a detached child, `git -C <dirname> checkout <default>` — and when `default` is null, say to check out the repo's own default branch rather than printing a placeholder there is no value for | 2 |
| S9 | worktrees are registered on the workspace repo | info | Inventory them. Mark any the scanner reports `prunable` as stale (their directory is gone). | prune manually — `git -C "<workspace>" worktree prune` | 2 |
| S10 | any memory-file contract violation | warn | Translate each entry in `data.violations`: `agents_md_absent` (the workspace has no memory payload at all), `legacy_marker_format` (pre-v3 HTML-comment markers), `payload_in_claude_md` (the payload sits in `CLAUDE.md`, where other engines cannot read it), `claude_md_import_missing` (**Claude Code reads `CLAUDE.md`, not `AGENTS.md` — without the import line, every Claude Code session in this workspace starts with no workspace memory at all**), `section_<name>_missing`, `section_<name>_duplicated`, `stale_command_list` (**the routing map every session loads advertises skills this framework no longer ships — name each one from `data.unknown_skills`**; every heading is correct, so nothing else reports it, and an upgrade that removed a skill is the ordinary cause). | `workspace-init` (converges the memory file and offers the marker migration) | 1 |
| S11 | agents on disk whose exact agent-directory path has no registered shortcut in any of the four shortcut locations (three workspace-local, plus legacy `~/.codex/skills/`) | info | Name them. When the same agent name exists in more than one repo, the scanner emits `<repo>/<agent>` so the target remains unambiguous. Registration is optional — they are always loadable via `boot <agent>` — but a shortcut is the faster entry point. | `register-agent <name>` (include the repo when the name is ambiguous), or `register-repo <repo>` for all of a repo's agents | 1 |
| S12 | dirty workspace-root paths outside the managed set, excluding framework scratch state (`.worktrees/`, `.lr-beings/`, `.tmp/`) | info | List them for visibility only. These are the user's own files; no framework command will touch them, and `workspace-push` deliberately leaves them alone. Framework scratch directories are excluded because they are neither: when they show as dirty the cause is a missing ignore line, which S7 reports and fixes. | none — informational | none |
| S13 | a declared child on disk is not a git repo, has no origin, or its origin disagrees with the declaration; two declared URLs derive to the same directory name; a declared URL yields an unsafe directory name; a child git repo's own name is unsafe for a `.gitignore` line; or a child symlink escapes the workspace | warn | Name the child and the reason. For two URLs claiming one directory, name both — `declared` is the first declarer, `actual` the second — and say that `workspace-pull` cannot place either until a descriptor is edited. A declared repo simply *absent* from disk is S6's, not this one's; a collision suppresses both S6 and the origin-mismatch reason for that directory, so one condition yields one row. When `dirname` is null there is no child to name — name the declared URL instead. An origin mismatch is the one to read carefully: `workspace-pull` will refuse to pull that repo until it is resolved. An unsafe *child* directory name cannot be ignored automatically at all: say so, and that renaming the directory is the fix — `workspace-pull` cannot help here | resolve per the `workspace-pull` conflict table (`docs/workspace-pull.md` § Conflict Handling); rename the directory for an unsafe name | 2 |
| S14 | `git.behind > 0` | info | N commit(s) are waiting upstream — **as of the last fetch**. `check --workspace` never fetches, so this figure can be stale in either direction; absence of S14 is not evidence of being current. | `workspace-pull` (phase 0) | 1 |
| S15 | a `~/.codex/skills/lr-*-agent/` shortcut exists for an agent in this workspace | info | Name the agents in `data.agents`. Since v37 Codex shortcuts are workspace-local (`.codex/skills/`), where git carries them to the team; these are in the user's home directory, outside the workspace repo, so no publish path reaches them and a teammate cloning this workspace does not get them. Name separately the subset in `data.also_workspace_local`, which already have a workspace copy — those are pure duplicates, listed twice in every Codex session. **That directory is user-global and agent names collide across repos by design, so a matched name is not proof the shortcut is this workspace's** — say to check the shortcut's own `from <agent-dir>` before deleting it. | `/lr:update` (migration 37 relocates them), or `register-agent <name>` per agent followed by deleting the home copy | 1 |
| S16 | the workspace repo itself is on a detached HEAD | warn | Say the workspace root is on a detached HEAD, and name the commit in `data.head` when present. This is the git state that makes the rest of this section quiet rather than loud: a detached HEAD has no upstream, so S2 and S14 cannot fire and their silence means nothing here. Any commit made in this state — by this session or an unattended one — belongs to no branch and is dropped by the next checkout, so say plainly that `workspace-push` must not be run until it is resolved. | `git -C "<workspace>" checkout <branch>`; if commits were already made detached, `git -C "<workspace>" branch <name> <sha>` first to keep them | 2 |
| S17 | a declared repo or registered agent has no canonical routing description, or `repo-context` is malformed/stale | warn | Name missing repositories and agents separately; duplicate agent names arrive as `<repo>/<agent>`. Render each `repo_context_issues` item with every location field it supplies (`repo`, `index`, or `line`) plus its reason. This is only the deterministic floor: `workspace-init` also judges whether present descriptions are useful and distinct enough for routing. | `workspace-init` investigates the affected repos/agents, aligns the whole routing set, updates canonical descriptions, and regenerates `AGENTS.md` | 1 |
| S18 | `plugin_config.missing` or `plugin_config.unresolvable` is non-empty | info | The committed project-scope plugin settings are absent or unresolvable, so a teammate who clones this workspace does not get `lr` without installing it by hand. Name the files and which condition each is in. **`missing` and `unresolvable` route differently:** `missing` means a key is absent and `workspace-init` will add it; `unresolvable` means the file cannot be read or safely merged — bad encoding, invalid JSON, or one of our own keys holding a value of the wrong type — and `workspace-init` will refuse to touch it, so a human must fix it first. Never report an `unresolvable` file as something `workspace-init` will write. Anything in `data.disabled` is **not** drift: an explicit `false` is a deliberate choice, so name it only as context and never route the user to a fix that undoes it. Codex has no project-scope plugin mechanism at all, so it is absent from this finding by design rather than by omission. | `workspace-init` (writes both files; an unparseable file must be fixed by hand first) | 2 |
| S19 | last verified per-repo check >24h old, or unavailable | warn | Name the repo, check time and age; distinguish stale information from unknown time. This does not prove missing upstream commits. | `workspace-pull`; without a workspace descriptor, propose the single-repo freshness repair below. | 2 |

## Single-repo freshness repair

For S19 without a workspace descriptor, show this command with the affected repo and the
active framework's absolute paths substituted and safely shell-quoted. Verify the repo is
its own Git root first. This is a Tier 2 repair, displayed rather than executed by `check`.

```sh
git -C "<repo>" pull --ff-only && python3 "<framework-root>/scripts/record-repo-pull" "<repo>"
```

The hook records freshness only after Git succeeds, including an already-up-to-date pull.
A failed pull leaves the previous marker intact. Report marker-write errors and rerun the
check after repair; a plain Git pull alone does not update the framework's freshness evidence.

## Authoring a repair document

Keep one root cause per `fix-<slug>.md`, with Symptoms, Diagnosis (manual verification and
expected output), Remedy (exact commands), Why It Happens, and See Also. Retain the existing
manual Diagnosis sections for now, including the case where the diagnostic skill is absent.
Link each new finding to its repair here; do not duplicate the catalog in procedure docs.

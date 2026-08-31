# Update

Reconcile user-side state with the currently-installed framework version.

**Scope:** this command does NOT update the plugin itself. Use your engine's own plugin mechanism for that. `/lr:update` only migrates local artifacts — per-agent shortcuts, repo files, and agent files — to match whatever framework version is currently installed.

## Step 0 — Announce

Print this to the user before doing anything else, filling in any `<placeholder>`:

> Bringing your local files in line with the framework version you have installed. **This does not
> update the plugin itself** — your engine does that; this migrates your lore agent repos and
> shortcuts to match. Each repo records the version it was last brought up to, so I walk the versions
> in between and apply each one's changes in order, then commit and push just those changes — or, on
> `--dry-run`, report what they would change and write nothing. **Files that live in the workspace
> rather than in a lore agent repo — registered shortcuts among them — are left uncommitted for
> `/lr:workspace-push`**, and I'll say so if any were touched.

## Input

Optional argument: `--dry-run` — print what would change without writing any files. No frontmatter updates, no regenerations, no deletions. Use this to preview before applying.

## Core Concept

A single repo-level version identifier is the source of truth. The framework version lives in `<framework-root>/VERSION`. Each lore agent repo stamps this version in its `lore-repo.md` frontmatter. When the framework is ahead of a repo, `/lr:update` walks intermediate versions in sequence — applying migrations from `<framework-root>/migrations/` and displaying release notes from `<framework-root>/release-notes/` — then stamps the new version, but only after all steps succeed. It then tries to commit and push only those update-owned repo changes so a successful update does not remain local by accident.

There is no per-agent version stamp. Agents within a repo migrate together with the repo.

## Migrations vs Release Notes

A version bump may carry one or both of:

- **Migration** (`migrations/<N>.md`) — physical instructions to modify user-side files (frontmatter changes, file regenerations, directory restructures). Consumed and executed by the update process.
- **Release notes** (`release-notes/<N>.md`) — informational content describing what's new in version `N`. Displayed to the user; no file modifications.

Versions that need both have both files. Versions that introduce features without requiring user-side file changes have only release notes. Versions that quietly fix things may have only a migration. **At least one must exist for any version bump** — otherwise the update process treats it as a packaging bug.

## Flow

### 1. Read framework version

Read `<framework-root>/VERSION`. Trim whitespace. This is the target version `F`.

### 2. Discover repos

Scan all directories in the current working directory for directories containing `lore-repo.md` at the root. Each is a lore agent repo.

If no repos are found, report "no lore agent repos in this workspace" and stop.

### 3. For each repo, determine migration state

Read the `version` field from `lore-repo.md` frontmatter → repo version `R`.

- **If `R == F`**: report `<lore-agent-repo>: already at version F`. If Git metadata contains a
  valid pending-update marker created by this procedure, retry its exact push as described in
  **Automatic Publication**; otherwise skip.
- **If `R > F`**: warn `<lore-agent-repo>: stamped as version R, but framework is at F — plugin may be out of date`. Do not migrate this repo.
- **If `R < F`**: this repo needs migration. Continue to step 4.

Before writing an `R < F` repo, capture the publication pre-state described in **Automatic
Publication**. This snapshot is what prevents unrelated local work from entering the update
commit.

Also resolve the declared migration write paths for the full `R+1 ... F` range and compare them
with the captured dirty paths before applying anything. If any update target was already dirty,
do not write that repo: report the exact colliding paths and ask the user to commit, stash, or
otherwise resolve them, then rerun `/lr:update`. If a migration has no usable `Write Paths`
declaration, conservatively treat every dirty repo path as a collision. An explicit update is not
permission to overwrite uncommitted work.

### 4. Apply migrations and release notes in order

For `v` in `R+1` through `F` inclusive:

1. **Migration**: if `<framework-root>/migrations/<v>.md` exists, read it and follow its instructions, scoped to the current repo. The migration doc is plain markdown; interpret its steps and execute them.

2. **Release notes**: if `<framework-root>/release-notes/<v>.md` exists, read it and display the contents to the user.

3. **At least one** must exist for version `v`. If neither `migrations/<v>.md` nor `release-notes/<v>.md` is present, this is a framework packaging bug — report it and stop the upgrade for this repo.

4. If a migration step fails, stop the upgrade for this repo. Do **not** apply any further versions to this repo. Do **not** stamp the new version. Report the failure with enough context for the user to investigate.

### 5. Stamp the new version

Only after all upgrade steps in step 4 succeed:

1. Read `lore-repo.md` frontmatter.
2. Update the `version` field to `F` (quoted string).
3. Write the file back, preserving the rest of the frontmatter and the body.

If any upgrade step failed in step 4, skip this step — leave the repo at its previous version so the next `/lr:update` run can retry.

### 6. Publish the completed update

Immediately after stamping, follow **Automatic Publication** below. Commit only repo-contained
files written by this update, including `lore-repo.md`, then try to push that commit to the current
branch's existing upstream. Publication failure does not undo a successful migration or version
stamp.

### 7. Report

For each repo processed, print one line per outcome:
- `<lore-agent-repo>: upgraded from R to F; committed and pushed` (fully synchronized)
- `<lore-agent-repo>: upgraded from R to F; committed locally, push failed: <reason>`
- `<lore-agent-repo>: upgraded from R to F; committed locally, push skipped: <reason>`
- `<lore-agent-repo>: upgraded from R to F; publication skipped: <reason>`
- `<lore-agent-repo>: already at version F` (skipped, current)
- `<lore-agent-repo>: stamped as R, framework is F — plugin may be out of date` (warning)
- `<lore-agent-repo>: upgrade to v failed: <reason>` (error)

At the end, print a summary: total repos, upgraded, pushed, push-failed, push-skipped,
publication-skipped, skipped, warned, failed.

## Dry-Run Mode

If `--dry-run` is passed:

- Follow the flow above, but do NOT write any files. No frontmatter updates. No regenerations. No deletions.
- For each step that would modify a file, print what would change:
  - `would create: <path>`
  - `would modify: <path>` — include a unified diff preview
  - `would delete: <path>`
- For the version stamp step, print `would stamp <lore-agent-repo>: version R → F`.
- Print `would commit and push: <repo-relative update-owned paths>` when publication preconditions
  are satisfied, or `would skip publication: <reason>` when they are not.
- For manual-edit detection, report `manual edits detected in: <path>` and describe what a merge would propose, but do NOT prompt the user.
- For dirty migration targets, report `would defer: dirty update target(s): <paths>` and make no
  write or publication claim for that repo.
- At the end, print the same summary format as normal mode, prefixed with `[DRY RUN]`.

## Handling Manual Edits to Generated Files

Migrations may need to regenerate files the framework owns as templated output — for example,
per-agent shortcuts (`.claude/commands/lr-*-agent.md` on Claude Code,
`.cursor/skills/lr-*-agent/SKILL.md` on Cursor, `.codex/skills/lr-*-agent/SKILL.md` on Codex — and
`~/.codex/skills/lr-*-agent/SKILL.md` for a Codex shortcut written before v37). If a user has manually edited such a file, naive regeneration would destroy their edits.
Handle this case explicitly.

### Divergence detection

For a file the current migration intends to overwrite:

1. Compute what the **previous-version** template would have generated for this file (the migration doc provides the known previous templates).
2. If the on-disk content matches any known previous-version template exactly, the file is **clean** — safely overwrite with the new content.
3. If the on-disk content does not match any known previous template, the file has been **manually edited** — go to merge handling.

### Merge handling

When manual edits are detected:

1. Compute three pieces of content:
   - `old`: what the previous-version template would have generated (choose the closest match, or the latest known template for that version if multiple exist)
   - `new`: what the current template generates
   - `current`: the on-disk content (with the user's manual edits)

2. Attempt a three-way merge: apply the diff from `old` → `new` onto `current`. If the merge is clean (no conflicts), produce a merged result.

3. Present the situation to the user:
   - Show the path of the file
   - Show a short description of what the user's edits appear to be (compared to `old`)
   - Show the suggested merged content
   - Offer three choices:
     - **Accept** — write the merged content
     - **Edit** — user provides their own merged content
     - **Skip** — leave the file as-is and continue with other migration steps (this may leave the repo in a partially migrated state; warn the user)

4. Proceed based on the user's choice. Record which files required manual resolution in the final report.

In **dry-run mode**, detect divergence and describe the proposed merge, but do not prompt — just report `manual edits detected: <path>`.

## Automatic Publication

Publication is best-effort and conservative. Its purpose is to synchronize framework-owned update
changes, not to publish arbitrary user work.

### Before writing

For each repo that needs an update, record:

1. The exact Git top-level from `git -C <repo> rev-parse --show-toplevel`. It must equal the Lore
   repo's real path. An enclosing workspace repository is not a valid publication target.
2. The current branch and its existing upstream. Detached HEAD disables the automatic commit; no
   upstream disables only the push. Do not guess a remote or create a branch.
3. Staged paths from `git diff --cached --name-only` and dirty paths from porcelain status.
4. The count of commits already ahead of the upstream.

Keep an exact list of repo-contained files actually created, modified, or deleted by the update.
External shortcut files may still be updated by migrations, but never belong in the Lore repo
commit. Always include the final `lore-repo.md` stamp in the owned list.

Before any migration write, intersect the range's declared repo-contained write paths (plus
`lore-repo.md`) with the captured dirty paths. Any intersection defers the entire repo update with
no writes. A missing or malformed declaration uses the conservative fallback described above.
The separate generated-file divergence procedure still applies to targets that this Git gate does
not defer, especially external shortcuts outside the Lore repo. It never overrides a dirty
repo-contained target.

### Commit gate

After a successful stamp, automatically commit only when all of these hold:

- the Lore repo is its own Git root and is on a branch;
- no update-owned path was already dirty before the update;
- there were no staged changes before the update;
- every repo path changed by the update is in the recorded update-owned list.

Unrelated **unstaged** dirty paths do not block publication and must not be staged. A pre-existing
dirty update target or any staged work does block publication because committing it could absorb
user changes. If a gate fails, leave the update changes uncommitted and report the exact reason.

When the gate passes:

1. Stage only the recorded update-owned paths, using explicit path arguments and deletion-aware
   staging. Never use `git add .`, `git add -A` without paths, or a wildcard.
2. Commit only those paths with subject `chore(lore): update framework to v<F>`. Preserve any
   unrelated unstaged changes.
3. Verify the created commit contains no path outside the update-owned list. If verification fails,
   do not push and report the unexpected paths.

### Push attempt and retry

After the narrow commit succeeds, attempt a push only when the branch has an existing upstream and
it had zero commits ahead of that upstream before this update. Otherwise keep the new update commit
local and report why the push was skipped; unrelated unpublished commits must never ride along
automatically.

Immediately before writing the pending marker or pushing, freshly resolve the current branch,
upstream, `HEAD`, and commits ahead of that upstream. Continue only when the branch and upstream are
unchanged, `HEAD` is the exact update commit just created, and that commit is the sole commit ahead.
If any value differs, skip the push and report the changed precondition. This second gate prevents
a concurrent or newly-created local commit from riding along after the earlier snapshot.

When the push gate passes, push the current branch to its existing upstream with non-interactive
credentials and the engine profile's normal runtime bound. Never force-push. Immediately before
the attempt, write a small `lr-update-pending` marker inside the absolute Git directory (resolve it
with `git rev-parse --absolute-git-dir`), containing the exact update commit ID, branch, and
upstream. Use this exact format so a later engine can validate it deterministically:

```yaml
version: 1
commit: "<full-commit-id>"
branch: "<branch>"
upstream: "<upstream>"
```

Remove the marker only after a successful push. If the marker cannot be written, still try the
immediate push; if that push fails, report that automatic retry is unavailable.

A rejected, unauthenticated, timed-out, or otherwise failed push leaves the update commit and
marker local and must be reported with the short commit ID and Git's useful error line. Do not roll
back the migration, stamp, or commit.

On a later `/lr:update` where `R == F`, retry only when the marker still names the current branch
and upstream, `HEAD` equals the recorded commit, and that commit is the sole commit ahead of the
upstream. If any check differs, do not push and report the stale marker; a later user commit must
never ride along. A successful retry removes the marker. With no marker, ordinary
`already at version F` handling applies.

Use `git -C <lore-agent-repo>` for every Git command rather than changing directories; the command
iterates across repositories.

## Ordering Rules

- **Within a repo**, apply upgrades in strict version order (`R+1`, `R+2`, …, `F`). Never skip versions.
- **Between repos**, process independently. A failure in one repo does not affect others.
- **Within a migration**, follow the steps in the order given by the migration doc.

## Error Handling

If the framework version file (`<framework-root>/VERSION`) is missing or unreadable, stop with a clear error — the plugin is broken or not installed.

If neither a migration doc nor a release-notes doc exists for a version in the range `R+1 ... F`, stop upgrading that repo and report the gap — this is a framework packaging bug.

If a migration step throws an error (file not found, permission denied, malformed YAML, etc.), stop upgrading that repo and report the specific failure. Other repos continue.

## What `/lr:update` Does NOT Do

- Does not update the plugin itself (that's Claude Code's job).
- Does not touch lore topics, `lore-context.md`, or `workdir/` contents — those are agent-owned and not templated.
- Does not commit or push unrelated user changes, create an upstream, or force-push.
- Does not auto-resolve manual edits without user confirmation.
- Does not overwrite a dirty migration target; resolve it and rerun the update.
- Does not skip versions.
- Does not diagnose runtime/environmental issues — if a skill expected from a freshly-applied version isn't appearing, an old skill lingers, or behavior reflects the prior version after a successful update, see `/lr:doctor`. Plugin-cache staleness is the most common cause and is a known ailment.

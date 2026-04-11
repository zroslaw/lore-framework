# Update

Reconcile user-side state with the currently-installed framework version.

**Scope:** this command does NOT update the plugin itself. Use Claude Code's own plugin mechanism (`/plugin update lr` or marketplace refresh) for that. `/lr:update` only migrates local artifacts — per-agent boot commands, repo and agent files — to match whatever framework version is currently installed.

## Input

Optional argument: `--dry-run` — print what would change without writing any files. No frontmatter updates, no regenerations, no deletions. Use this to preview before applying.

## Core Concept

A single repo-level version identifier is the source of truth. The framework version lives in `${CLAUDE_PLUGIN_ROOT}/VERSION`. Each lore agent repo stamps this version in its `lore-repo.md` frontmatter. When the framework is ahead of a repo, `/lr:update` applies the migration docs in `${CLAUDE_PLUGIN_ROOT}/migrations/` in sequence to bring the repo to the current version, then stamps the new version — but only after all migrations succeed.

There is no per-agent version stamp. Agents within a repo migrate together with the repo.

## Flow

### 1. Read framework version

Read `${CLAUDE_PLUGIN_ROOT}/VERSION`. Trim whitespace. This is the target version `F`.

### 2. Discover repos

Scan all directories in the current working directory for directories containing `lore-repo.md` at the root. Each is a lore agent repo.

If no repos are found, report "no lore agent repos in this domain" and stop.

### 3. For each repo, determine migration state

Read the `version` field from `lore-repo.md` frontmatter → repo version `R`.

- **If `R == F`**: report `<repo>: already at version F`, skip.
- **If `R > F`**: warn `<repo>: stamped as version R, but framework is at F — plugin may be out of date`. Do not migrate this repo.
- **If `R < F`**: this repo needs migration. Continue to step 4.

### 4. Apply migrations in order

For `v` in `R+1` through `F` inclusive:

1. Read the migration doc at `${CLAUDE_PLUGIN_ROOT}/migrations/<v>.md`. If it does not exist, this is a framework bug — report it and stop migrating this repo.

2. Follow the instructions in the migration doc, scoped to the current repo. The migration doc is plain markdown; interpret its steps and execute them.

3. If any step fails, stop the migration for this repo. Do **not** apply any further migrations to this repo. Do **not** stamp the new version. Report the failure with enough context for the user to investigate.

### 5. Stamp the new version

Only after all migrations in step 4 succeed:

1. Read `lore-repo.md` frontmatter.
2. Update the `version` field to `F` (quoted string).
3. Write the file back, preserving the rest of the frontmatter and the body.

If any migration failed in step 4, skip this step — leave the repo at its previous version so the next `/lr:update` run can retry.

### 6. Report

For each repo processed, print one line per outcome:
- `<repo>: migrated from R to F` (success)
- `<repo>: already at version F` (skipped, current)
- `<repo>: stamped as R, framework is F — plugin may be out of date` (warning)
- `<repo>: migration to v failed: <reason>` (error)

At the end, print a summary: total repos, migrated, skipped, warned, failed.

## Dry-Run Mode

If `--dry-run` is passed:

- Follow the flow above, but do NOT write any files. No frontmatter updates. No regenerations. No deletions.
- For each step that would modify a file, print what would change:
  - `would create: <path>`
  - `would modify: <path>` — include a unified diff preview
  - `would delete: <path>`
- For the version stamp step, print `would stamp <repo>: version R → F`.
- For manual-edit detection, report `manual edits detected in: <path>` and describe what a merge would propose, but do NOT prompt the user.
- At the end, print the same summary format as normal mode, prefixed with `[DRY RUN]`.

## Handling Manual Edits to Generated Files

Migrations may need to regenerate files the framework owns as templated output — for example, `.claude/commands/lr-*-agent.md`. If a user has manually edited such a file, naive regeneration would destroy their edits. Handle this case explicitly.

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

## Commit Policy

Do not run git commands that modify state. Leave all changes uncommitted so the user can review with `git diff` and commit themselves. This applies to both the migrated files and the version stamp in `lore-repo.md`.

It is acceptable to run read-only git commands (`git status`, `git diff`, `git log`) during migration if needed for context.

## Ordering Rules

- **Within a repo**, apply migrations in strict version order (`R+1`, `R+2`, …, `F`). Never skip versions.
- **Between repos**, process independently. A failure in one repo does not affect others.
- **Within a migration**, follow the steps in the order given by the migration doc.

## Error Handling

If the framework version file (`${CLAUDE_PLUGIN_ROOT}/VERSION`) is missing or unreadable, stop with a clear error — the plugin is broken or not installed.

If a migration doc is missing for a version in the range `R+1 ... F`, stop migrating that repo and report the gap — this is a framework packaging bug.

If a migration step throws an error (file not found, permission denied, malformed YAML, etc.), stop migrating that repo and report the specific failure. Other repos continue.

## What `/lr:update` Does NOT Do

- Does not update the plugin itself (that's Claude Code's job).
- Does not touch lore topics, `lore-context.md`, or `workdir/` contents — those are agent-owned and not templated.
- Does not commit changes.
- Does not auto-resolve manual edits without user confirmation.
- Does not skip versions.

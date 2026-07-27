# Version Check

Invoked from `agent-boot.md` when the agent's repo `version` differs from the framework `VERSION`. Reconciles the booting agent's repo to the current framework version automatically.

## Inputs

- `R` — `version` field from the booting agent's repo `lore-repo.md`
- `F` — contents of `<framework-root>/VERSION` (trimmed)

## Cases

### `R == F`

You should not be reading this doc — `agent-boot.md`'s version check skipped this file. Treat as a no-op and continue boot.

### `R > F`

The repo is stamped at a version newer than the installed framework. The plugin may be out of date.

- Print a warning to the user. Use the active engine profile to give the engine-specific next step:
  - **Codex:** `<lore-agent-repo>: stamped as version R, but framework is at F — your Codex plugin is older than the repo. Refresh the plugin (`codex plugin add lr@lore-framework`; if the marketplace is Git-backed, run `codex plugin marketplace upgrade lore-framework` first), restart Codex, then boot again. See <framework-root>/INSTALL-CODEX.md.`
  - **Cursor:** `<lore-agent-repo>: stamped as version R, but framework is at F — your Cursor plugin/session is older than the repo. Refresh the plugin source per your install method, start a fresh Cursor session, then boot again. See <framework-root>/INSTALL-CURSOR.md.`
  - **Other engines:** `<lore-agent-repo>: stamped as version R, but framework is at F — your plugin may be out of date. Refresh or reinstall the plugin using your engine's normal install flow, then boot again.`
- Do NOT modify any files.
- Continue boot in degraded mode.

### `R < F`

The repo is behind. Run the upgrade procedure below.

### Neither — `R` and `F` are not both numeric

`lr-core preflight` reports this as `data.version.verdict == "differs"`: the two stamps are
unequal, but at least one is not an integer, so there is no ordering between them and none of the
cases above applies. **Do not guess a direction** — picking `R > F` or `R < F` here is a coin flip
that either skips a needed migration or tells the user to reinstall a perfectly current plugin.

- Print one line: `<lore-agent-repo>: version stamp R does not compare with framework version F — reconcile manually.`
- Do NOT modify any files and do NOT run the upgrade procedure.
- Continue boot in degraded mode.

## Upgrade Procedure

### Step 1: Pre-flight collision check

A blanket "any uncommitted change blocks the upgrade" rule was the historical gate, but it overfired in normal use: lore agent repos routinely carry uncommitted runtime state (other agents' `workdir/*` files — pulse logs, watch markers, scratch artifacts) that cannot collide with what the upgrade writes. The gate is now scoped to **actual collisions** — files git would refuse to overwrite cleanly when the upgrade applies its writes — and to **structural inconsistencies** (conflict markers).

**First, confirm the repo is its own git root — with this exact comparison, not an equivalent-seeming one.** Run both of the following and compare their output as plain strings:

```
git -C "<lore-agent-repo>" rev-parse --show-toplevel
python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "<lore-agent-repo>"
```

**Use `python3 -c` for the second command, not `cd "<lore-agent-repo>" && pwd`.** They look equivalent and usually agree, but on macOS `pwd` (without `-P`) returns the *logical* path — it does not resolve symlinks — while git's `--show-toplevel` always returns the *physical*, symlink-resolved one. `/var` is itself a symlink to `/private/var` on macOS, so a repo under a `/var/...` tmpdir (a `TMPDIR`-based fixture, for instance) makes the two commands disagree even when the repo genuinely is its own git root — a false mismatch that skips a real, needed upgrade. `os.path.realpath()` resolves symlinks the same way `git_toplevel()` does in `scripts/lr-core`, so it's the one method guaranteed to agree with the script's own verdict; treat it as the specified command, not one option among several.

If the two outputs differ, the lore repo is *not* its own repository — it sits inside an enclosing one (the workspace-meta-repo layout is supported), and `git -C` silently retargets every command at that enclosing repo. **Do not run the collision check in that case**: the status output would be rooted at the wrong repo, so Step 1c's write-set intersection would compare repo-relative globs against wrong-rooted paths, find a false-empty intersection, and let Step 2 overwrite the user's uncommitted edits. Instead print `<lore-agent-repo>: not its own git root — skipping automatic upgrade, reconcile manually.`, do not modify any files, and continue boot in degraded mode. (This is the same guard `git_toplevel()` applies in `scripts/lr-core`; the rule is stated there in full.)

Then run `git -C "<lore-agent-repo>" status --porcelain` (quote the substituted path so it survives spaces; use `git -C` rather than `cd`ing — the shell CWD is shared with Glob, Grep, and subsequent git calls, so a stray `cd` silently shifts their root for the rest of the session). Untracked files (`??`) are ignored throughout — the upgrade never overwrites a file git doesn't already track.

#### 1a. Conflict markers — always defer

`git status --porcelain` exposes two distinct signals of an in-progress merge:

- **Unmerged status codes:** `UU`, `AA`, `DD`, `AU`, `UA`, `UD`, `DU` — git itself is reporting the file as actively conflicted. Treat any such code as a hard-defer condition without further inspection.
- **Modified files containing conflict markers:** for files marked with the modified codes (`M `, ` M`, `MM`, `AM`, `MD`, `RM`, `CM`, etc. — anything where the working-tree side is `M`), scan for unresolved markers.

The marker scan must use **precise anchors** to avoid false-positives on legitimate Markdown:

- The string `=======` at the start of a line matches setext H1 underlines (`Title\n=======`) — extremely common in lore docs. **Do not** flag a file on `=======` alone.
- Require **all three markers** (`<<<<<<<`, `=======`, `>>>>>>>`) to appear in the same file, each anchored to the start of a line and followed by a space or end-of-line. The git-emitted form is `<<<<<<< <ref>`, `=======` (alone), `>>>>>>> <ref>`. Concretely:

  ```
  grep -lE '^<<<<<<< ' <file> >/dev/null \
    && grep -lE '^=======($| )' <file> >/dev/null \
    && grep -lE '^>>>>>>> ' <file> >/dev/null
  ```

  All three must match the same file. If any one of the three is absent, the file is not in a real conflict state — likely it's a doc that quotes one or two markers as documentation (this very release's `release-notes/15.md` quotes all three; the framework's `docs/resolve-conflicts.md` and lore topics about merge handling do too — these are not conflicts).

If any unmerged-state file (any of `UU`/`AA`/`DD`/`AU`/`UA`/`UD`/`DU`) **or** any modified file matching the all-three-markers test is found:

- Print: `<lore-agent-repo>: cannot auto-upgrade from R to F — unresolved merge-conflict markers in <file(s)>. Resolve the conflict and commit before booting again.`
- Do NOT modify any files. Continue boot in degraded mode. **This deferral is NOT a boot failure** — return to `agent-boot.md` and finish loading the agent; do not emit any boot-failed signal or stop the boot.

This is the only **always-defer** condition. A conflict-marker file is structurally broken regardless of upgrade scope.

#### 1b. Compute the upgrade write-set

Build the set of repo-relative paths the upgrade is about to write:

1. Always include `lore-repo.md` (the final version stamp in Step 3).
2. For each `v` in `R+1 .. F`:
   - If `<framework-root>/migrations/<v>.md` exists, look for a `## Write Paths` section (see `conventions.md` § Migration Write Paths). The section content is **only** what lies inside the first fenced code block (` ``` … ``` `) immediately following the `## Write Paths` heading. Any prose paragraphs after the closing fence belong to the next subsection, not to the write-set — they are commentary for human readers and the parser MUST NOT consume them. If no fenced block is present between the `## Write Paths` heading and the next `## ` (or `### `) heading, the section is malformed — treat as missing (fall back to blanket-dirty, see below) and warn the user.

     Inside the fenced block, parse the lines using these rules **in order**:
     1. **Strip blank lines and comment lines** (lines starting with `#`, or having `# comment` after a path — strip the trailing comment).
     2. **Sentinel detection**: if any remaining line matches the `(none)` sentinel as defined in `conventions.md` § Migration Write Paths § *Empty write-sets — sentinel forms* (the canonical grammar — do not restate the accepted forms here), this is the **explicit empty write-set sentinel**. Contribute nothing for this version. Do **not** treat `(none)` as a glob, and do **not** fall back to blanket-dirty.
     3. **Glob lines**: every other remaining line is a repo-relative glob — add to the write-set.
     4. **Zero remaining lines** (after blanks/comments stripped, and no `(none)` sentinel) is also an explicit empty write-set — same treatment as the sentinel.
   - If a migration exists but the `## Write Paths` **section is absent entirely** (the heading itself is missing), treat its write-set as **unknown** — fall back to the conservative gate: defer on **any** dirty tracked file (the historical behavior, but only for this version range, not as a global default). Note: an empty fenced block is *not* the same as a missing section — the section's presence with empty content is an explicit declaration of "writes nothing" and proceeds without deferral.
   - If only `release-notes/<v>.md` exists for that version (no migration), it contributes nothing to the write-set — release-notes-only versions don't write to user repos.

#### 1c. Intersect dirty tracked files with the write-set

Match each dirty tracked file's repo-relative path against the write-set globs.

- **Empty intersection** (no dirty file collides) → proceed to Step 2.

- **Exact `lore-repo.md`-only collision on a stamp-only upgrade** → proceed to Step 2. If the
  colliding set is exactly `lore-repo.md`, and the computed write-set is also exactly
  `lore-repo.md` (that is: no migration in `R+1 .. F` writes any repo file beyond the final
  version stamp), do **not** defer. This is the common "release-notes-only versions plus a dirty
  stamp file" case. It is safe to continue because Step 3 reads the current working-tree
  `lore-repo.md` and updates only its `version` field while preserving the rest of the file.
  This also covers a previously-deferred local stamp such as committed `17`, working tree `18`,
  now advancing to `23`: the earlier dirty stamp is not a reason to block the later stamp-only
  upgrade.

- **Non-empty intersection** → defer. Print a precise message naming the colliding files and the right command. Substitute `<lore-agent-repo>` with the actual repo path and quote it if it contains spaces — emit literal commands, not template placeholders:

  ```
  <lore-agent-repo>: cannot auto-upgrade from R to F — uncommitted changes in files the upgrade would write:
    <file-1>
    <file-2>
    ...
  Resolve by either committing the changes:
    git -C "<lore-agent-repo>" commit <files>
  or reverting them:
    git -C "<lore-agent-repo>" checkout -- <files>
  Then boot again or run /lr:update.
  ```

  **This deferral is NOT a boot failure.** Print the message above, then return to `agent-boot.md` and finish loading the agent in degraded mode — do not emit any boot-failed signal or stop the boot.

In deferred cases: do NOT modify any files; continue boot in degraded mode. **A deferred upgrade is not a boot failure** — return to `agent-boot.md` Step 2 and proceed to Step 3; the agent still loads.

### Step 2: Walk versions from R+1 to F

For each version `v` in `R+1` through `F` inclusive, in order:

1. **Apply migration** if `<framework-root>/migrations/<v>.md` exists. Read the doc and follow its instructions, scoped to the booting agent's repo. Migrations are idempotent and may modify files.

2. **Display release notes** if `<framework-root>/release-notes/<v>.md` exists. Print the contents to the user so they see what's new in this version.

3. **At least one** must exist for version `v`. If neither `migrations/<v>.md` nor `release-notes/<v>.md` is present, this is a framework packaging bug — print an error, stop the upgrade for this repo, do NOT stamp the new version, continue boot in degraded mode.

4. If a migration step fails, stop the upgrade for this repo. Do NOT apply any further versions. Do NOT stamp the new version. Print the failure with enough context for the user to investigate. Continue boot in degraded mode.

### Step 3: Stamp the new version

Only after all versions in step 2 succeed:

1. Read `lore-repo.md` frontmatter from the booting agent's repo.
2. Update the `version` field to `F` (quoted string).
3. Write the file back, preserving the rest of the frontmatter and the body.

### Step 4: Inform the user

Print a brief summary:
- `<lore-agent-repo>: upgraded from R to F`
- The changes are uncommitted and ready for `git diff` review

Then return to `agent-boot.md` Step 3 and continue with reading `role.md` and `lore-context.md`.

## Invariants

- **Boot never fails on version errors.** Any failure here results in degraded-mode boot with a visible warning. The agent still loads.
- **No file the upgrade would write is overwritten while dirty.** The collision gate guarantees this — git's own write-time refusal is the second line of defense. Files the upgrade does *not* touch (other agents' `workdir/*`, unrelated scratch state) never block.
- **Conflict markers always defer.** A repo with unresolved conflict markers is structurally broken regardless of upgrade scope; the gate refuses uniformly.
- **Version stamps are atomic.** Either all migrations for the range succeed and the version is stamped, or no version is stamped — the next boot or `/lr:update` run can retry.
- **No commits.** The user reviews and commits the upgraded files themselves.

## Relationship to `/lr:update`

`/lr:update` is the user-triggered, manual entry point — it processes all repos in the workspace and supports `--dry-run`. The boot-time check described here is a per-repo automatic reconciliation that runs only for the booting agent's repo, with no dry-run and no user prompt. Both share the same migration/release-notes data and the same version-stamping logic.

**Asymmetry note:** the **write-aware collision gate (Step 1) lives only on the boot-time path.** `/lr:update` is user-triggered — the user has direct visibility of the workspace state, can `git diff` before running, and accepts that running `/lr:update` against dirty files may overwrite them. The boot-time path is automatic and unattended, so it carries the gate. `/lr:update` writes through dirty files unconditionally; the user is expected to commit/stash first. (Bringing the gate to `/lr:update` is a possible future enhancement.)

## For Framework Authors

When writing a new `migrations/<N>.md`, **declare its write-set** under a `## Write Paths` section (see `conventions.md` § Migration Write Paths). Without it, the boot-time gate falls back to the conservative blanket-dirty rule for the version range that includes your migration — meaning users with any unrelated dirty file will be blocked from auto-upgrading through your version. The declaration is mechanical (it's the same paths your migration's "Steps" section already touches) and the cost of omitting it is real friction.

When changes touch plugin-cached state (skills, slash commands, scripts, SKILL.md-referenced docs), include the **Clear Plugin Cache** footer per `docs/conventions.md` § Migration / Release-Note Authoring. The cache-stale failure mode is invisible to the user until they invoke a missing skill — the footer makes the fix discoverable from the doc the user is already reading. See also `docs/doctor-stale-plugin-cache.md` for the underlying ailment.

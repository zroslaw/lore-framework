# Version Check

Invoked from `agent-boot.md` when the agent's repo `version` differs from the framework `VERSION`. Reconciles the booting agent's repo to the current framework version automatically.

## Inputs

- `R` — `version` field from the booting agent's repo `lore-repo.md`
- `F` — contents of `${CLAUDE_PLUGIN_ROOT}/VERSION` (trimmed)

## Cases

### `R == F`

You should not be reading this doc — `agent-boot.md`'s version check skipped this file. Treat as a no-op and continue boot.

### `R > F`

The repo is stamped at a version newer than the installed framework. The plugin may be out of date.

- Print a warning to the user: `<lore-agent-repo>: stamped as version R, but framework is at F — your plugin may be out of date. Run /plugin update lr or refresh the marketplace.`
- Do NOT modify any files.
- Continue boot in degraded mode.

### `R < F`

The repo is behind. Run the upgrade procedure below.

## Upgrade Procedure

### Step 1: Safety check — uncommitted changes

Run `git -C <lore-agent-repo> status --porcelain` (where `<lore-agent-repo>` is the booting agent's repo path). Use `git -C` rather than `cd`ing into the repo — the shell CWD is shared with Glob, Grep, and subsequent git calls, so a stray `cd` silently shifts their root away from the domain for the rest of the session.

If there are uncommitted changes:
- Print a warning: `<lore-agent-repo>: cannot auto-upgrade from R to F — uncommitted changes present. Commit or stash them and run /lr:update manually.`
- Do NOT modify any files.
- Continue boot in degraded mode.

If the repo is clean, proceed.

### Step 2: Walk versions from R+1 to F

For each version `v` in `R+1` through `F` inclusive, in order:

1. **Apply migration** if `${CLAUDE_PLUGIN_ROOT}/migrations/<v>.md` exists. Read the doc and follow its instructions, scoped to the booting agent's repo. Migrations are idempotent and may modify files.

2. **Display release notes** if `${CLAUDE_PLUGIN_ROOT}/release-notes/<v>.md` exists. Print the contents to the user so they see what's new in this version.

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

Then return to `agent-boot.md` and continue with reading `role.md` and `lore-context.md`.

## Invariants

- **Boot never fails on version errors.** Any failure here results in degraded-mode boot with a visible warning. The agent still loads.
- **Uncommitted changes are never overwritten.** A dirty repo defers the upgrade entirely.
- **Version stamps are atomic.** Either all migrations for the range succeed and the version is stamped, or no version is stamped — the next boot or `/lr:update` run can retry.
- **No commits.** The user reviews and commits the upgraded files themselves.

## Relationship to `/lr:update`

`/lr:update` is the user-triggered, manual entry point — it processes all repos in the domain and supports `--dry-run`. The boot-time check described here is a per-repo automatic reconciliation that runs only for the booting agent's repo, with no dry-run and no user prompt. Both share the same migration/release-notes data and the same version-stamping logic.

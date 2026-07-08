# Consistency Checks

Work through the following checks in order. Report each issue found. At the end, print a summary: total issues found, or "All checks passed" if none.

> **Scope note.** `/lr:check` covers content-level static consistency — descriptors, references, structure, drift. Runtime/environmental issues that escape static checks (a skill not appearing despite the current `VERSION`, an old skill lingering after a rename, plugin-cache effects after an upgrade) are not detected here. For those, use `/lr:doctor`.

---

## 1. Agent repo discovery

Scan all directories in the working directory for lore agent repos — directories containing a `lore-repo.md` file at the root. If no agent repos are found, flag it: no lore agent repos exist in this workspace.

## 2. lore-repo.md validation

For each repo found in step 1, verify that `lore-repo.md` has valid YAML frontmatter containing:
- `description` — a non-empty string
- `version` — a non-empty string

Report any repos with missing or malformed frontmatter fields.

## 3. Framework version consistency (repo level)

Read the framework version from `<framework-root>/VERSION`. For each repo, compare the `version` field in `lore-repo.md` frontmatter against the framework version. Report any mismatches as **warnings** — the repo may need migration.

## 4. Agent discovery

For each repo found in step 1, scan `agents/` for agent directories (subdirectories containing `role.md`). Report any repo that has `lore-repo.md` but no agents as **informational**.

## 5. role.md frontmatter validation

For every agent found in step 4, verify that `role.md` has valid YAML frontmatter containing:
- `description` — a non-empty string

Report any agents with missing or malformed frontmatter fields.

Note: `role.md` does not carry a `version` field at framework version 2+. Agent-level version stamping was removed — only `lore-repo.md` tracks the framework version, one per repo. If a `version` field is present in `role.md`, flag it as **informational** — the repo likely predates migration 2 and can be reconciled with `/lr:update`.

## 6. Agent discovery vs registration

For each agent found in step 4, check whether an engine-native registered shortcut exists:

- **Claude Code:** `lr-<agent-name>-agent.md` in `.claude/commands/`
- **Codex:** `lr-<agent-name>-agent/` in `~/.codex/skills/` containing `SKILL.md`

Report any agents without a registered shortcut as **informational** (registration is optional — agents are always loadable via `/lr:boot`).

Conversely, for every registered shortcut artifact found in those locations, verify the agent directory it references actually exists. Report any shortcuts pointing to missing agent directories as **errors**.

## 7. Registered shortcut link validity

For every registered shortcut artifact:

- **Claude Code:** `lr-*-agent.md` in `.claude/commands/`
- **Codex:** `lr-*-agent/SKILL.md` in `~/.codex/skills/`

Extract all file paths referenced in the content. Verify each path resolves to an existing file. Report any broken paths.

## 8. Agent directory structure

For every agent found in step 4, verify the directory contains all required files and directories:
- `role.md`
- `lore-context.md`
- `lore/` directory
- `workdir/` directory

Report any missing components.

## 9. lore-context.md topic references

For every agent, read `lore-context.md` and extract any lore topic filenames referenced (e.g. `topic-name.md`). Verify each referenced file exists in the agent's `lore/` directory. Report any broken references.

## 10. Lore topic cross-references

For every `.md` file in each agent's `lore/` directory, extract any `.md` filenames referenced in the content. Verify each referenced file exists in the same `lore/` directory. Report any broken references.

## 11. lore-context.md size

For every agent, check the size of `lore-context.md`. Warn if it exceeds 40K tokens (approaching the 50K limit) or flag as a violation if it exceeds 50K tokens.

## 12. Pending reflections

For every agent directory, check if a `reflections/` directory exists and is non-empty. If so, flag it: reflection has been run but merge has not — lore is not yet up to date.

## 13. Uncommitted changes in lore files

For every lore agent repo in the workspace, run `git -C <lore-agent-repo> status` (where `<lore-agent-repo>` is the current iteration's repo path) to detect any lore files that are modified but not committed. Flag these: the knowledge exists only on the local filesystem and is not preserved in git history. This is especially critical for `lore-context.md`, `role.md`, and any `lore/` topic files.

Always use `git -C <lore-agent-repo>` rather than `cd`ing into each repo — the shell CWD is shared with Glob, Grep, and other git calls, and a `cd` here will silently shift subsequent checks' root.

## 14. lore-context.md staleness (git timestamps)

For every agent, use `git -C <lore-agent-repo> log -1 --format=%ci -- <file>` to get the last commit date of `lore-context.md` and of each lore topic in `lore/`. If any topic was committed more recently than `lore-context.md`, flag it: the summary may not reflect the latest state of that topic. List the topic name and how far out of date the summary is.

## 15. lore-context.md semantic consistency

For every agent, for each lore topic referenced in `lore-context.md`: read the topic file and compare its heading (first `#` line) and opening sentence against what `lore-context.md` says about it. Flag any cases where the topic's actual title or subject clearly differs from the description in lore-context — this indicates the summary was not updated after the topic was substantially revised.

## 16. Registered shortcut vs role.md

For every registered shortcut artifact, compare its last modification date against the last commit date of the agent's `role.md`. If `role.md` was updated more recently, flag it: the shortcut may not accurately describe the agent's current role. Also do a quick semantic check: verify the agent name in the shortcut matches the heading in `role.md`.

## 17. Orphaned pre-plugin skill commands

Scan `<workspace>/.claude/commands/` for files matching `lr-*.md` that do **not** match `lr-*-agent.md` AND whose content does **not** contain the phrase `boot as agent`. For each such file, extract `<skill-name>` from the filename (strip the `lr-` prefix and `.md` suffix) and check whether `<framework-root>/skills/<skill-name>/SKILL.md` exists.

- If the plugin skill exists, flag the file as an **orphaned pre-plugin skill duplicate** — `/lr:<skill-name>` is now provided by the plugin, so the local command is redundant and typically references stale sibling paths (`lore-framework/docs/...`). Report the file path and the covering plugin skill. Suggest: run `/lr:update` (migration 5 prompts to delete these per file) or delete manually.
- If no matching plugin skill exists, the file is a user-authored command — do not flag it.

## 18. Legacy registered shortcut formats

For every Claude shortcut file `lr-*-agent.md` in `<workspace>/.claude/commands/` whose content contains `boot as agent`, check the format. The current Claude form uses absolute paths and includes the agent directory:

```
Read `<absolute-path>/docs/agent-boot.md` and boot as agent `<agent-name>` from `<absolute-agent-dir>`.
```

Flag any Claude file that instead uses:
- `lore-framework/docs/agent-boot.md` (pre-v5 sibling-path form)
- `<framework-root>/docs/agent-boot.md` (v5 form — unresolved in `.claude/commands/`)
- Any form lacking the `from <agent-dir>` suffix

These legacy Claude formats cause slower or broken boots. Suggest: run `/lr:update` (migration 6 regenerates them) or re-register with `/lr:register-repo`.

For every Codex shortcut skill `lr-*-agent/SKILL.md` in `~/.codex/skills/` whose content contains
`boot as agent`, flag it if it lacks the `from <agent-dir>` suffix or does not point at an
absolute `agent-boot.md` path. Suggest: re-register with `/lr:register-agent` or
`/lr:register-repo`.

For every Cursor shortcut skill `lr-*-agent/SKILL.md` in `<workspace>/.cursor/skills/` whose
content contains `boot as agent`, flag it if any of the following is missing:

- frontmatter `name: lr-<agent-name>-agent`
- `disable-model-invocation: true`
- a `paths:` block scoping the shortcut to the matching repo
- the `from <agent-dir>` suffix on the boot line
- an absolute `agent-boot.md` path

These are the current Cursor registration invariants. Suggest: re-register with
`/lr:register-agent` or `/lr:register-repo`.

## 19. Plugin manifest version

Read the framework version `N` from `<framework-root>/VERSION`. Read the `version` field from both `<framework-root>/.claude-plugin/plugin.json` and the `lr` plugin entry in `<framework-root>/.claude-plugin/marketplace.json`.

Both must equal **`1.<N>.0`** (e.g. `VERSION` 14 → `1.14.0`), per `conventions.md` § Plugin Manifest Versioning. Report:

- Either manifest version ≠ `1.<N>.0` → **error**. The usual cause is a `VERSION` bump whose author forgot the manifest — which is exactly what stops Claude Code from detecting the release and refreshing its plugin cache. Fix: set both manifests to `1.<N>.0`. (For an *end user* rather than a framework developer, a mismatch more likely signals a stale plugin cache — see `/lr:doctor`.)
- `plugin.json` and `marketplace.json` disagree with each other → **error**: reconcile both to the same `1.<N>.0`.

This check has teeth mainly when the plugin source is the loaded plugin (e.g. `claude --plugin-dir ./lore-framework` during framework development); for a marketplace install it confirms the shipped manifest is internally consistent.

## 20. Migration Write Paths declaration

For every file `<framework-root>/migrations/<N>.md`, verify a `## Write Paths` section is present and well-formed per `conventions.md` § Migration Write Paths.

**Step 20.1 — section presence.** The heading `## Write Paths` (anchored at column 0) must exist. If absent → **error**: the boot-time auto-upgrade gate (`docs/version-check.md` Step 1b) falls back to the conservative blanket-dirty rule for any version range that includes this migration, meaning every user with any unrelated dirty file is blocked from upgrading through this version. Fix: add a `## Write Paths` section.

**Step 20.2 — fenced body.** Locate the first fenced code block (` ``` … ``` `) immediately following the `## Write Paths` heading and before the next `## ` / `### ` heading. If absent → **error**: the parser only consumes fenced bodies; an unfenced section is malformed and the parser will treat as missing.

**Step 20.3 — body content.** Inside the fenced block, after stripping blank lines and `#`-comment lines, every remaining line must be either:
- The **`(none)` sentinel** — see `conventions.md` § Migration Write Paths § *Empty write-sets — sentinel forms* for the exact accepted forms.
- A **glob token** — see `conventions.md` § Migration Write Paths § *Glob token grammar* for the canonical character class and "no internal whitespace" rule.

If a remaining line matches neither shape → **error**: the migration's body contains free-form prose that the parser would consume as a (non-matching) pseudo-glob, silently producing an empty or partial write-set. The blast radius is the same as a missing section — the gate either over-defers or, worse, fails to defer when it should — so the severity matches Steps 20.1 and 20.2. Fix: move the prose outside the fenced block (after the closing fence, where the parser ignores it) or rewrite as a `#`-prefixed comment inside the fence.

This check has teeth mainly when reviewing newly-authored migrations during framework development. For a marketplace install it confirms shipped migrations follow the convention.

## 21. Cursor skill tree parity

The Cursor engine loads skills from `.cursor-skills/` (see `.cursor-plugin/plugin.json` and `docs/engines/cursor.md`). Each canonical plugin skill must have a matching prefixed wrapper.

For every directory `<framework-root>/skills/<name>/` containing a `SKILL.md`, verify:

- `<framework-root>/.cursor-skills/lr-<name>/SKILL.md` exists.
- Its frontmatter `name` field equals `lr-<name>`.
- Its self-location line references `.cursor-skills/lr-<name>/SKILL.md` (not the canonical `skills/<name>/` path).

Conversely, every `.cursor-skills/lr-<name>/` directory must have a matching canonical `skills/<name>/SKILL.md`. Orphaned cursor wrappers → **error** (stale after a rename/delete).

If canonical and cursor wrappers drift (same doc target but different `$ARGUMENTS` handling or body text beyond the expected path/depth/`name`/`description` invocation-syntax differences), flag as **error** and suggest: run `python3 scripts/sync-cursor-skills` from the framework root to regenerate the cursor tree from canonical skills.

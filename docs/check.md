# Consistency Checks

Work through the following checks in order. Report each issue found. At the end, print a summary: total issues found, or "All checks passed" if none.

> **Scope note.** `/lr:check` covers content-level static consistency — descriptors, references, structure, drift. Runtime/environmental issues that escape static checks (a skill not appearing despite the current `VERSION`, an old skill lingering after a rename, plugin-cache effects after an upgrade) are not detected here. For those, use `/lr:doctor`.

> **Which diagnostic do I want?** `/lr:workspace-status` diagnoses this workspace's git and
> descriptor state; `/lr:check` verifies content consistency inside agent repos; `/lr:doctor`
> diagnoses engine and plugin runtime problems.

> **Checks #22–#24 are workspace-scoped and share one scan.** Run it once, before check #22, and
> read all three from its output:
>
> ```
> python3 "<framework-root>/scripts/lr-core" workspace-scan --workspace "<cwd>"
> ```
>
> `data.applicable: false` → skip #22, #23, and #24 entirely; this directory is not a workspace root.
> The scanner is a **literate accelerator**: on failure apply the Script Fallback Contract
> (`docs/conventions.md`) and execute `scripts/lr_core/workspace_scan.py`'s documented steps by hand.
> Each check below names the findings it owns; `/lr:workspace-status` renders the complete set.

---

## 1. Agent repo discovery

Scan all directories in the working directory for lore agent repos — directories containing a `lore-repo.md` file at the root.

**Anchor the scan to your actual current working directory** — run `pwd` first if unsure. This is the directory the session was invoked from. It is **not** `<framework-root>` (the plugin/framework directory you just read this file from), and **not** `<framework-root>`'s parent. Do not scan the framework directory or walk up to a parent directory looking for a workspace: a lore agent repo that is not under the current working directory is out of scope for this run. (Booting has the same guard — see `agent-boot.md` Step 1.)

If no agent repos are found, flag it: no lore agent repos exist in this workspace.

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
- **Cursor:** `lr-<agent-name>-agent/SKILL.md` in `.cursor/skills/`
- **Codex:** `lr-<agent-name>-agent/` in `~/.codex/skills/` containing `SKILL.md`

Report any agents without a registered shortcut as **informational** (registration is optional — agents are always loadable via `/lr:boot`).

Conversely, for every registered shortcut artifact found in those locations, verify the agent directory it references actually exists. Report any shortcuts pointing to missing agent directories as **errors**.

## 7. Registered shortcut link validity

For every registered shortcut artifact:

- **Claude Code:** `lr-*-agent.md` in `.claude/commands/`
- **Cursor:** `lr-*-agent/SKILL.md` in `.cursor/skills/`
- **Codex:** `lr-*-agent/SKILL.md` in `~/.codex/skills/`

Extract only the absolute agent directory following `from` in the boot instruction. Verify that
directory exists. Do **not** treat the relative prose references `SKILL.md` and
`docs/agent-boot.md` as filesystem links: they intentionally describe the session's active boot
skill rather than a pinned installation path. Report any missing agent directory as an error.

## 8. Agent directory structure

For every agent found in step 4, verify the directory contains all required files and directories:
- `role.md`
- `lore-context.md`
- `lore/` directory
- `workdir/` directory

Report any missing components.

## 9. Lore structure and references

For every agent, use the deterministic validator for Lore structure, recursive paths, and the
bounded formal-link grammar. Write the detailed census to a temporary file so it does not flood
the model context:

```
python3 "<framework-root>/scripts/lr-core" lore-map --agent-dir "<agent-dir>" --view boot
python3 "<framework-root>/scripts/lr-core" lore-map --agent-dir "<agent-dir>" --view detailed > "<temporary-map>"
```

Take coverage status and file/token percentages from the compact view. Inspect only `validation`
and relevant mapped or uncovered reference records in the temporary detailed map, then delete it.
Do not read or print
the taxonomy body wholesale. Report every validation item.
Legacy, invalid, unreachable, and unsupported-version counts are findings, not command failures.
Unsupported future versions are informational unless another procedure edited them. The validator
checks v1 schema, the fixed context, parent confinement/types, cycles, topic children, reachability,
context-size thresholds, formal links, and conservative legacy-reference ambiguity.

If this command fails, report that Lore v1 validation could not complete. It is an implementation
script, so do not imitate the validator manually or invoke the Script Fallback Contract.

## 10. Legacy reference cautions

The detailed map also reports conservative plain-filename, backticked, and raw-HTML references.
Report unresolved and ambiguous legacy references. They are safety cautions for future path-changing
operations, not formal graph edges.

## 11. lore-context.md size

Use the detailed map's `context_size_warning` / `context_size_error` findings. For a v1 context, warn above 10,000 estimated
tokens and report an error above 20,000. For a legacy context, retain the historical 50,000-token
ceiling until it migrates. Do not apply exact-token language to the dependency-free estimate.

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

For every Claude shortcut file `lr-*-agent.md` in `<workspace>/.claude/commands/` whose content contains `boot as agent`, check the current active-boot-skill form. It must name the installed `/lr:boot` skill, include the `from <agent-dir>` suffix, and contain no plugin-cache or absolute `agent-boot.md` path.

```
Read the `SKILL.md` for the installed `/lr:boot` skill available in this session. Follow its self-location instruction to resolve `<framework-root>`, then read its `docs/agent-boot.md` and boot as agent `<agent-name>` from `<agent-dir>`.
```

Flag any Claude file that lacks the active `/lr:boot` skill reference or `from <agent-dir>` suffix,
or contains `plugins/cache/`, an absolute `agent-boot.md` path, `lore-framework/docs/agent-boot.md`,
or `<framework-root>/docs/agent-boot.md`.

**Also flag any shortcut whose bootstrap spans more than one line** (ignoring a trailing newline,
and, on Cursor and Codex, the frontmatter block). The content can be entirely correct and still be
wrong in shape: `migrations/33.md` classifies a shortcut as `current` only on a byte-for-byte match
with a freshly generated artifact, so a wrapped one is rewritten at every upgrade instead of being
recognised, and Claude Code renders a command's description from the file's first line, so a
wrapped bootstrap shows in the command list as a sentence fragment. Fix by re-registering with the
engine-native registration skill. See `register-repo.md` § Resolve the shortcut bootstrap.

These legacy formats can break after a plugin upgrade. On framework v33 or later, run the normal
engine-specific boot or update entry: Claude Code `/lr:boot` or `/lr:update`; Cursor `/lr-boot` or
`/lr-update`; Codex's installed `lr:boot` or `lr:update` skill through its native skill mechanism.
Migration 33 refreshes a registered shortcut that belongs to the repo being migrated, including
customized generated content. Otherwise, re-register it using the equivalent engine-native
registration skill. Do not run migration 6: its
historical template writes the cache-vulnerable absolute boot path this check rejects.

For every Codex shortcut skill `lr-*-agent/SKILL.md` in `~/.codex/skills/` whose content contains
`boot as agent`, flag it if it lacks the installed `lr:boot` skill reference or `from <agent-dir>`
suffix, or contains `plugins/cache/` or an absolute `agent-boot.md` path. On framework v33 or
later, migration 33 refreshes owned shortcuts during the normal engine-specific boot or update
entry; otherwise re-register with the equivalent native registration skill.

For every Cursor shortcut skill `lr-*-agent/SKILL.md` in `<workspace>/.cursor/skills/` whose
content contains `boot as agent`, flag it if any of the following is missing:

- frontmatter `name: lr-<agent-name>-agent`
- `disable-model-invocation: true`
- a `paths:` block scoping the shortcut to the matching repo
- the `from <agent-dir>` suffix on the boot line
- an installed `/lr-boot` skill reference

Flag a Cursor shortcut if it contains a plugin-cache or absolute `agent-boot.md` path.

These are the current Cursor registration invariants. Suggest: re-register with
`/lr:register-agent` or `/lr:register-repo`.

## 19. Plugin manifest version

Read the framework version `N` from `<framework-root>/VERSION`. Read the `version` field from **all four** version-bearing plugin manifests:

1. `<framework-root>/.claude-plugin/plugin.json`
2. The `lr` plugin entry in `<framework-root>/.claude-plugin/marketplace.json` (if `marketplace.json` is missing, skip this file gracefully — see `framework-improvements-backlog` for the open item; do not error solely on absence)
3. `<framework-root>/.cursor-plugin/plugin.json`
4. `<framework-root>/.codex-plugin/plugin.json` (if missing, skip gracefully — do not error solely on absence)

The Codex native marketplace file `<framework-root>/.agents/plugins/marketplace.json` is **not** in this list: the Codex marketplace schema carries no per-plugin `version` field (Codex reads the plugin version from `.codex-plugin/plugin.json`), so there is nothing to compare there.

Every manifest that was read must equal **`1.<N>.0`** (e.g. `VERSION` 14 → `1.14.0`), per `conventions.md` § Plugin Manifest Versioning. Report:

- Any read manifest version ≠ `1.<N>.0` → **error**. The usual cause is a `VERSION` bump whose author forgot a manifest — which is exactly what stops Claude Code from detecting the release and refreshing its plugin cache. Fix: set all four to `1.<N>.0`. (For an *end user* rather than a framework developer, a mismatch on the Claude manifests more likely signals a stale plugin cache — see `/lr:doctor`.)
- Among the manifests that were read, any pairwise disagreement → **error**: reconcile all to the same `1.<N>.0`.

**Note:** `.cursor-plugin/plugin.json` is **consistency hygiene / mechanical parity** with `VERSION` — it is not a verified Cursor cache-detection lever (that mechanism is verified for Claude Code only). `.codex-plugin/plugin.json` **is** the version Codex reads for the plugin (verified: `codex plugin add` resolves the installed version from it); for a git marketplace install `codex plugin marketplace upgrade` then picks up the bumped version. Drift on any manifest still blocks ship because it signals an incomplete version bump.

This check has teeth mainly when the plugin source is the loaded plugin (e.g. `claude --plugin-dir ./lore-framework` during framework development); for a marketplace install it confirms the shipped manifests are internally consistent.

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

## 22. Workspace gitignore coverage

**Workspace-scoped** — read from the shared scan. Report finding **S7** if present.

S7 carries two groups, and they read differently, so report them separately:

- `data.repos` — child git repos on disk with no `/<dirname>/` line in `<cwd>/.gitignore` → **warn**:
  the child repo's contents could be committed into the workspace meta-repo. Note that this covers
  **every** child git repo on disk, declared or not: declaration governs cloning and pulling, but an
  undeclared clone can be committed just as easily as a declared one.
- `data.standard_lines` — any of `/.worktrees/`, `/.lr-beings/`, `/.tmp/` missing → **warn**.

Fix for both: run `/lr:workspace-pull` (phase 3 appends them), or add the missing lines by hand.
`/lr:workspace-init` also writes them as part of its convergence pass.

Also report finding **S6** (declared repos absent from disk → **warn**, fix `/lr:workspace-pull`) and
finding **S13** (a declared child that is not a git repo, has no origin, or whose origin disagrees
with the declaration → **warn**; `workspace-pull` will refuse to pull it until resolved — see
`docs/workspace-pull.md` § Conflict Handling).

Do not re-derive the declared set or the ignore lines by hand; the scanner already did, using the
same dirname derivation `workspace-pull` uses. See `docs/workspace-status.md` for the full wording of
each finding.

## 23. Legacy memory-file format

**Workspace-scoped** — read from the shared scan. Report finding **S10** if present.

S10's `data.violations` lists what is wrong with the workspace memory-file contract. Report each,
with `/lr:workspace-init` as the fix for all of them (its convergence pass rewrites the memory file
and offers the one-time marker migration):

| Violation | Means | Severity |
|---|---|---|
| `legacy_marker_format` | `AGENTS.md` still uses HTML-comment markers — either `lr:workspace-init:*` or the pre-v25 `lr:init:*` | warn |
| `payload_in_claude_md` | The payload sits in `CLAUDE.md`, where Cursor and Codex cannot read it | warn |
| `claude_md_import_missing` | No `@AGENTS.md` line in `CLAUDE.md`. **Claude Code does not read `AGENTS.md`** — without that line, every Claude Code session in this workspace starts with no workspace memory at all, silently | warn |
| `agents_md_absent` | The workspace has no memory payload | warn |
| `section_<name>_missing` / `_duplicated` | A canonical level-2 heading is gone or appears twice | warn |

Section-level violations are suppressed while the file is still in marker format — the single
`legacy_marker_format` entry already names the whole remedy.

See `docs/workspace-init.md` § The memory-file contract.

## 24. Workspace publication state

**Workspace-scoped** — read from the shared scan. Report findings **S1**, **S2**, **S3**, and **S4**
if present.

Framework skills write workspace-root files but none of them commits (`docs/workspace-push.md`
explains the gap this check watches).

| Finding | Means | Severity | Fix |
|---|---|---|---|
| S1 | Framework-managed workspace files are dirty — the changes exist only on this filesystem, and a teammate's `workspace-pull` phase 0 receives a stale state. Name the paths from `data.paths` | warn | `/lr:workspace-push` |
| S2 | N workspace commit(s) not pushed | warn | `/lr:workspace-push` |
| S3 | Git-tracked but no `origin` — `workspace-pull` phase 0 and the README join path are inert until a remote exists | info | `git -C "<cwd>" remote add origin <url>`, or `/lr:workspace-init`, which also offers to record a deliberately local-only workspace as `sharing: local` |
| S4 | Not a git repo (a supported local-only mode), or — when `data.enclosing_root` is set — sitting inside another git repo, where no workspace-level git operation is safe | info | `/lr:workspace-init` (offers tracking) |

The **framework-managed path set is defined in code** (`scripts/lr_core/workspace_scan.py`) and
rendered in `docs/workspace-push.md` § Framework-managed paths. Do not restate it here, and do not
carry a remembered copy of it.

Dirty workspace paths *outside* that set are not findings here — they are the user's own files
(finding S12, informational, rendered by `/lr:workspace-status`).

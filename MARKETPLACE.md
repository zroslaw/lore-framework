# Marketplace Submission Metadata

Canonical copy for submitting or registering Lore Framework in Claude Code, Codex, and Cursor
plugin marketplaces.

## Release

- Plugin id: `lr`
- Display name: `Lore`
- Repository / marketplace name: `lore-framework`
- Version: `1.25.0`
- Runtime release tag: `lr--v1.25.0`
- Runtime release commit: `09fe4f0`
- Submission metadata: this file on `main`
- Repository: `https://github.com/zroslaw/lore-framework`
- License: `MIT`
- Author / developer: `Yaroslav Panasyuk`
- Website / homepage: `https://github.com/zroslaw/lore-framework`
- Category: `Productivity`

## Descriptions

Short description:

> Persistent, self-improving knowledge for AI coding agents.

Medium description:

> Lore is a persistent knowledge system for AI coding agents. Agents accumulate decisions, domain
> knowledge, and operational wisdom across sessions as a team-shared markdown knowledge graph.

Long description:

> Lore turns coding agents into persistent, team-shared collaborators. Each lore agent lives in a
> git-backed markdown repository with a role, compact working context, and a knowledge graph of
> decisions, domain facts, operational runbooks, and session learnings. The framework provides skills
> to boot agents, recall their lore, reflect and merge new knowledge at session end, manage agent
> repos, initialize workspaces, and move sessions across Claude Code, Codex, and Cursor.

## Keywords

`agents`, `skills`, `knowledge`, `memory`, `lore`, `context`, `persistent`, `markdown`, `git`,
`workspace`, `collaboration`, `productivity`

## Capabilities And Data Handling

- Reads and writes local workspace files in user-selected repositories.
- Stores knowledge as plain markdown under user-owned git repos.
- Uses git remotes only when the user invokes flows that pull, commit, or push.
- Does not require a hosted service, external database, API key, or vendor account beyond the host
  coding agent itself.
- Does not collect telemetry.
- Does not exfiltrate source code or lore automatically; network effects are explicit git/plugin
  install/update actions initiated by the user or documented workflow.

## Engine Status

### Claude Code

Status: ready for community marketplace submission.

Packaging:

- `.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`
- Release tag `lr--v1.25.0`

Validation:

```bash
claude plugin validate /path/to/lore-framework --strict
claude plugin tag /path/to/lore-framework --dry-run
```

Submission path:

1. Submit via Claude Console plugin form: `https://platform.claude.com/plugins/submit`
2. Use repository URL `https://github.com/zroslaw/lore-framework`.
3. Use release tag `lr--v1.25.0` / runtime commit `09fe4f0` if a version or commit field is requested.
4. Paste the short, medium, long descriptions above as needed.

Current direct install before community approval:

```bash
claude plugin marketplace add zroslaw/lore-framework
claude plugin install lr@lore-framework
```

### Codex

Status: native repo packaging ready; public marketplace submission path not separately verified.

Packaging:

- `.codex-plugin/plugin.json`
- `.agents/plugins/marketplace.json`
- `INSTALL-CODEX.md`

Current install:

```bash
codex plugin marketplace add zroslaw/lore-framework
codex plugin add lr@lore-framework
```

Notes:

- Codex reads the plugin version from `.codex-plugin/plugin.json`.
- `.agents/plugins/marketplace.json` points Codex at the root plugin source and sets availability
  and authentication policy.
- The plugin interface metadata already includes display name, category, capabilities, website URL,
  long description, logo, and composer icon.

### Cursor

Status: local `--plugin-dir` packaging ready; team/native marketplace flow still needs validation
with Cursor's current distribution process.

Packaging:

- `.cursor-plugin/plugin.json`
- `.cursor-skills/lr-*/SKILL.md`
- `INSTALL-CURSOR.md`

Current verified install:

```bash
git clone https://github.com/zroslaw/lore-framework.git "${LORE_FRAMEWORK_DIR:-$HOME/src/lore-framework}"
bash "${LORE_FRAMEWORK_DIR:-$HOME/src/lore-framework}/scripts/install-cursor-plugin" "${LORE_FRAMEWORK_DIR:-$HOME/src/lore-framework}"
cursor-agent --plugin-dir "${LORE_FRAMEWORK_DIR:-$HOME/src/lore-framework}"
```

Submission / distribution notes:

- Use the repository URL and metadata above for Cursor team marketplace review or private team
  distribution.
- The Cursor manifest already carries display name, description, version, author, repository,
  license, keywords, logo, and the `.cursor-skills/` path override.
- Do not claim seamless Cursor marketplace auto-refresh until the team marketplace + auto-refresh
  path has been validated on the target Cursor installation.

## Reviewer Notes

Lore is intentionally file- and git-native. Its core artifacts are human-readable markdown files in
the user's repositories, so teams can inspect, review, diff, revert, branch, and merge the agent's
knowledge using their normal development workflow.

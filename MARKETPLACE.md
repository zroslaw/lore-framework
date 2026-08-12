# Marketplace Submission Metadata

Canonical copy for submitting or registering Lore Agents in Claude Code, Codex, and Cursor
plugin marketplaces.

## Release

- Plugin id: `lr`
- Display name: `Lore Agents`
- Repository / marketplace name: `lore-framework`
- Version: `1.26.0`
- Runtime release tag: `lr--v1.26.0`
- Runtime release commit: `3909129`
- Submission metadata: this file on `main`
- Repository: `https://github.com/zroslaw/lore-framework`
- License: `MIT`
- Author / developer: `Yaroslav Panasyuk`
- Website / homepage: `https://github.com/zroslaw/lore-framework`
- Privacy policy: `https://github.com/zroslaw/lore-framework/blob/main/PRIVACY.md`
- Category: `Productivity`

## Descriptions

Short description:

> Named AI specialists that learn and grow with you.

Medium description:

> Lore Agents helps you organize long-term work with AI around a team of named specialists. Each
> specialist develops durable knowledge from experience — decisions, feedback, domain context, and
> operational wisdom — stored as Markdown in Git and shared with your team.

Long description:

> Lore Agents helps you build a team of named AI specialists that learns and grows with you. Each
> specialist has a role, durable identity, and git-backed Markdown knowledge base. As you work
> together, it captures useful decisions, feedback, domain knowledge, and operational wisdom, so future
> sessions start with experience instead of repeated context. The framework provides skills to boot
> agents, recall and share their knowledge, reflect and merge new learning at session end, manage agent
> repos, initialize workspaces, and work across Claude Code, Codex, and Cursor.

## Keywords

`agents`, `skills`, `knowledge`, `memory`, `lore`, `context`, `persistent`, `markdown`, `git`,
`workspace`, `collaboration`, `productivity`

## Capabilities and data handling

- Reads and writes local workspace files in user-selected repositories.
- Stores knowledge as plain markdown under user-owned git repos.
- Uses git remotes only when the user invokes flows that pull, commit, or push.
- Does not require a hosted service, external database, API key, or vendor account beyond the host
  coding agent itself.
- Does not collect telemetry.
- Does not exfiltrate source code or lore automatically; network activity happens only through
  explicit git or plugin install/update actions, initiated by the user or a documented workflow.

## Engine status

### Claude Code

Status: ready for community marketplace submission.

Packaging:

- `.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`
- Release tag `lr--v1.26.0`

Validation:

```bash
claude plugin validate /path/to/lore-framework --strict
claude plugin tag /path/to/lore-framework --dry-run
```

Submission path:

1. Submit via Claude Console plugin form: `https://platform.claude.com/plugins/submit`
2. Use repository URL `https://github.com/zroslaw/lore-framework`.
3. Use release tag `lr--v1.26.0` / runtime commit `3909129` if a version or commit field is requested.
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

## Reviewer notes

Lore is intentionally file- and git-native. Its core artifacts are human-readable markdown files in
the user's repositories, so teams can inspect, review, diff, revert, branch, and merge the agent's
knowledge using their normal development workflow.

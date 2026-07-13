# Privacy Policy

Lore Framework is a local, git-backed plugin for AI coding agents. It does not run a hosted service
and does not collect telemetry.

## Data Storage

Lore stores agent knowledge as plain markdown files in repositories chosen by the user. These files
may include agent roles, lore topics, session summaries, workspace descriptors, and reflection notes.

## Data Access

Lore reads and writes files only through the host coding agent's normal workspace permissions. It can
access files in repositories and directories that the user has made available to the host coding
agent.

## Network Use

Lore does not automatically send source code, lore, session summaries, or workspace files to the
plugin author or to a Lore service.

Network activity occurs only when the user or host coding agent runs documented workflows that use
external tools, such as:

- `git pull`, `git commit`, or `git push`
- plugin installation or refresh commands
- host-engine operations provided by Claude Code, Codex, or Cursor

Those actions are governed by the user's configured git remotes, host coding agent, and execution
environment.

## Telemetry

Lore Framework does not include analytics, tracking, telemetry, or a remote reporting endpoint.

## Third-Party Services

Lore runs inside host coding agents such as Claude Code, Codex, and Cursor. Those hosts may process
conversation, file, and tool-use data according to their own terms and privacy policies. Lore does
not change or bypass those host policies.

## Contact

For privacy questions or security reports, open an issue at:

https://github.com/zroslaw/lore-framework/issues


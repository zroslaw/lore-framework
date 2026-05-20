When the framework migrates from "sibling-path form" (`lore-framework/docs/...`) to "plugin form" (`${CLAUDE_PLUGIN_ROOT}/docs/...`), it's not enough to fix the runtime code that reads files. Every **template** that emits file content must also be audited — otherwise the generator keeps producing pre-plugin artifacts indefinitely.

## The v5 leak

Framework went plugin-first at v3. But two template-emission sites kept emitting the old sibling-path form, and no one noticed because the author's dev machine had `lore-framework/` as a literal sibling of the domain:

- `lore-framework/docs/register-repo.md:20` — template for generated `.claude/commands/lr-<agent-name>-agent.md`
- `lore-framework/migrations/2.md` (Step 2) — same template embedded in the migration that regenerated those commands

On plugin installs (no sibling dir), the generated boot commands were broken. Users saw `/lr-<agent-name>-agent` fail to resolve the boot doc.

v5 fixed both sites to `${CLAUDE_PLUGIN_ROOT}/docs/agent-boot.md` and added `migrations/5.md` to regenerate broken commands on user machines.

## Rule

**Plugin-compatibility is a property of emitted artifacts, not just of the framework's own runtime.** When going plugin-first, audit every doc that contains a template a user (or Claude acting on their behalf) will execute — `register-repo.md`, `create-repo.md`, migration docs — and make sure the emitted content uses `${CLAUDE_PLUGIN_ROOT}`.

Sibling-path forms should appear in framework docs only as:
- Historical templates frozen in old migrations (for content-matching divergence detection) — preserve verbatim
- Examples discussing the pre-plugin era

Never as live output.

## Detection (belt and suspenders)

v5 added **check 18** (`/lr:check`): scans `.claude/commands/lr-*-agent.md` for the sibling-path pattern. Catches the leak post-hoc on any machine, even if a future migration forgets to regenerate. Migrations are the primary fix; the check is the safety net.

## Frozen templates vs emission templates

Migration 2's body lists "known v1 templates" — frozen strings used for clean-vs-edited file matching. Those must be preserved exactly, including their pre-plugin form. Only the **new** template that migration 2 writes was updated. The explanatory prose around the frozen templates was clarified to say they're v1 placeholders, not current output.

Don't conflate the two when auditing. Emission templates change; frozen matching templates don't.

See also `migration-ownership.md` for handling user-machine files the framework once produced.

# `dev/` — Development & SDLC automation (BETA)

This directory houses the **dev module** of the `lr` plugin: features for development and software-quality automation. All dev skills are prefixed `lr:dev-…` and their artifacts live here under `dev/`.

> **BETA.** These features are under active design. Interfaces, artifact shapes, and skill names may change.

## Subsystems

- **`aiqa/` — AIQA (AI-based Quality Assurance).** Automated, agent-driven QA across testing *levels*. The first level is **ULA (Unit-Level Analysis)**. See `aiqa/README.md`.

## Skills in this module

| Skill | Purpose |
|---|---|
| `/lr:dev-aiqa-repo-init` | Create the `<repo>-aiqa` sibling repo for a source repository |
| `/lr:dev-ula-file` | Run a ULA single-file pass on one source file |

Each skill's `SKILL.md` (in `skills/`) is a thin pointer into the detailed doc here under `dev/aiqa/`.

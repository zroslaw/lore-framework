# `df/` — Dark Factory / SDLC automation (BETA)

This directory houses the **DF module** of the `lr` plugin: the **Dark Factory (DF)** — features driving toward an autonomous, AI-run SDLC. All DF skills are prefixed `lr:df-…` and their logic lives here under `df/`.

> **BETA.** These features are under active design. Interfaces, artifact shapes, and skill names may change.

## DF-core

- **`repo-init.md` — `/lr:df-repo-init`.** Stands up the per-repo **DF backbone** `<repo>-df` (the `repo-lore/` tree). Aspect-agnostic; every aspect writes into it.

## Aspects

- **`aiqa/` — AIQA (AI-based Quality Assurance).** Automated, agent-driven QA across testing *levels*. The first level is **ULA (Unit-Level Analysis)**. See `aiqa/README.md`.

## Skills in this module

| Skill | Purpose |
|---|---|
| `/lr:df-repo-init` | Create the `<repo>-df` backbone repo for a source repository |
| `/lr:df-ula-file` | Run a ULA single-file pass on one source file |

Each skill's `SKILL.md` (in `skills/`) is a thin pointer into the detailed doc here under `df/`.

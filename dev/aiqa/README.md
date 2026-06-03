# AIQA — AI-based Quality Assurance (BETA)

**AIQA** is an umbrella for automated, AI-agent-driven quality assurance. It grows across testing *levels*:

- **ULA — Unit-Level Analysis** ← the level implemented here (file/unit: find bugs → generate test scenarios → gap-analyse against existing tests)
- *(future)* feature/flow-level, integration-level (ILA), e2e-level …

> **BETA.** Under active design. Notably, the file pass runs as a **dynamic Workflow** (see `workflows/`), which depends on the Claude Code dynamic-workflow runtime being available in the session. Where it isn't, the same orchestration can be simulated with subagents.

## Skills

| Skill | `SKILL.md` | Detailed doc |
|---|---|---|
| `/lr:dev-aiqa-repo-init` | `skills/dev-aiqa-repo-init/` | `dev/aiqa/repo-init.md` |
| `/lr:dev-ula-file` | `skills/dev-ula-file/` | `dev/aiqa/ula-file.md` |

## How the pieces connect

```
dev points /lr:dev-ula-file at a file
        │
        ▼
  dev-ula-file ──(repo missing?)──▶ dev-aiqa-repo-init ──▶ creates  <repo>-aiqa  sibling
        │                                                   (asks the user first)
        │ loads prompts/ + schemas/, detects language, reads file
        ▼
  workflow: workflows/ula-file-pass.js
        │  Split  → units
        │  Unit Pass (parallel, one agent per unit): A find bugs → B scenarios (clean-room) → C gap
        ▼  returns schema-validated {bugs, scenarios, gap} per unit
  dev-ula-file persists YAML artifacts into <repo>-aiqa/ula/<file>/<unit>/
```

## What lives where (all under `dev/aiqa/`)

| Path | Role | Canonical for |
|---|---|---|
| `repo-init.md`, `ula-file.md` | skill logic (Claude-run) | the *orchestration* |
| `artifact-specs.md` | artifact index | points at `schemas/` + `prompts/` (no restating) |
| `prompts/` | the agent prompts, one file per step | **authoring semantics** (handed to agents, self-contained) |
| `schemas/` | JSON Schema per artifact | **structure** (machine-enforced) |
| `workflows/ula-file-pass.js` | the dynamic workflow | orchestration only (no IO) |

Single-source rule: structure → `schemas/`, authoring semantics → `prompts/`, and `artifact-specs.md` only *points* at those (no drift).

## The output repo (`<repo>-aiqa`, created per source repo)

```
My-Turbo-Boost-Switcher-aiqa/
├── aiqa.config.yaml
└── ula/<source/relative/path/File.ext>/<unit-slug>/{bugs,scenarios,gap}.yaml
```

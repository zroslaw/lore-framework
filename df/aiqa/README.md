# AIQA — AI-based Quality Assurance (BETA)

**AIQA** is an umbrella for automated, AI-agent-driven quality assurance — one aspect of the **Dark Factory (DF)** backbone. It grows across testing *levels*:

- **ULA — Unit-Level Analysis** ← the level implemented here (per file: split into units → find bugs → generate test scenarios → gap-analyse against existing tests → verify bugs)
- *(future)* feature/flow-level, integration-level (ILA), e2e-level …

> **BETA.** Under active design. Notably, the file pass runs as a **dynamic Workflow** (see `workflows/`), which depends on the Claude Code dynamic-workflow runtime being available in the session. Where it isn't, the same orchestration can be simulated with subagents.

## Skills

| Skill | `SKILL.md` | Detailed doc |
|---|---|---|
| `/lr:df-ula-file` | `skills/df-ula-file/` | `df/aiqa/ula-file.md` |

(The backbone-init skill `/lr:df-repo-init` is DF-core, not AIQA-specific — see `df/repo-init.md`.)

## How the pieces connect

```
user points /lr:df-ula-file at a file
        │
        ▼
  df-ula-file ──(backbone missing?)──▶ df-repo-init ──▶ creates  <repo>-df  sibling
        │                                                (asks the user first)
        │ loads prompts/ + schemas/, detects language, reads file
        ▼
  workflow: workflows/ula-file-pass.js
        │  Split  → units
        │  Unit Pass (parallel, one agent per unit): A find bugs → B scenarios (clean-room) → C gap → D verify bugs → E guardrail
        ▼  returns schema-validated {bugs, scenarios, gap} per unit
  df-ula-file aggregates per file + writes YAML into
      <repo>-df/repo-lore/<file>/ula/{bugs,scenarios,gap}.yaml
        │ then spawns 1 subagent: re-verify all bugs cross-unit (re-applies D/E)
        ▼ aggregator moves any it rejects → dismissed[] (dismissed-by: aggregator)
```

## What lives where (all under `df/aiqa/`)

| Path | Role | Canonical for |
|---|---|---|
| `ula-file.md` | skill logic (Claude-run) | the *orchestration* |
| `artifact-specs.md` | artifact index | points at `schemas/` + `prompts/` (no restating) |
| `prompts/` | the agent prompts, one file per step | **authoring semantics** (handed to agents, self-contained) |
| `schemas/` | JSON Schema per artifact | **structure** (machine-enforced) |
| `workflows/ula-file-pass.js` | the dynamic workflow | orchestration only (no IO) |

(Backbone init lives one level up at `df/repo-init.md` — it's DF-core, aspect-agnostic.)

Single-source rule: structure → `schemas/`, authoring semantics → `prompts/`, and `artifact-specs.md` only *points* at those (no drift).

## Where ULA artifacts land (in the `<repo>-df` backbone)

```
<repo>-df/repo-lore/<source/relative/path/File.ext>/
├── file-lore.md            ← the file's lore landing (future "context" aspect; ULA doesn't write it)
└── ula/
    ├── bugs.yaml           ← provenance header + all units' bugs
    ├── scenarios.yaml
    └── gap.yaml
```

Per **file**, not per unit (the unit is a field inside each artifact). Each artifact carries a **Provenance Header** (`source-sha` + `config`). See `df/repo-init.md` for the full backbone layout and `artifact-specs.md` for the artifact shapes.

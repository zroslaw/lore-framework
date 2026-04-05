# Conventions

## Naming

- **Agent names**: lowercase kebab-case (e.g., `code-reviewer`, `data-analyst`)
- **Lore topic filenames**: lowercase kebab-case, descriptive (e.g., `api-retry-behavior.md`)
- **Role update reflections**: prefixed with `role-update-` (e.g., `role-update-scope-change.md`)
- **Agent commands**: `/lr-<agent-name>-agent`
- **Framework commands**: `/lr-<action>` (no `-agent` suffix)

## Directory Structure

### Agent repo
```
<repo>/
└── agents/
    └── <agent-name>/
        ├── role.md              # Identity and responsibilities
        ├── lore-context.md      # Compacted working knowledge (≤10K tokens)
        ├── lore/                # Knowledge graph of atomic topics
        ├── reflections/         # Temporary — exists only during finalization
        └── workdir/             # Persistent workspace for artifacts
```

### Domain directory (after framework setup)
```
<domain>/
├── lore-framework/              # Framework repo
├── <agent-repo>/                # One or more agent repos
└── .claude/commands/            # Installed commands
```

## Lore Topics

- **Atomic** — one concept or lesson per file
- **Compact** — under 1K tokens preferred, flexible when needed
- **Plain markdown** — no frontmatter, no metadata fields
- **Git tracks metadata** — creation date, update history, authorship all come from git
- **Obsolete topics are deleted** — git preserves history, no need for status markers
- **Cross-references by filename** — topics reference each other to form a knowledge graph
- **Summary topics** — serve as entry points to clusters of related topics

## Lore Context

- **Budget**: 10K tokens maximum
- **Content mix**: inline summarized knowledge + topic summaries with filename references
- **Prioritization**: recent and frequently relevant knowledge first
- **Compaction**: when approaching the budget, summarize older entries and replace inline details with topic references

## What Belongs in Lore

- Decisions and their reasoning
- Domain knowledge and discoveries
- Operational recommendations from experience
- Practical context about systems and environment
- Approaches that worked or failed, and why

## What Does NOT Belong in Lore

- General knowledge anyone could look up
- Information obvious from reading the code
- Temporary session state
- Verbatim conversation excerpts

# Lore Structure v1

This document is the canonical contract for Lore file structure. Parsing, coverage, and
mechanical validation are implemented by `scripts/lr-core lore-map`.

## Knowledge Model

Each agent has one recursive taxonomy:

```text
one lore-context
├── lore-area
│   ├── lore-area
│   └── lore-topic
└── lore-topic
```

- **Context** — the fixed root `lore-context.md`, loaded at boot. It holds essential agent-wide
  knowledge and high-level navigation.
- **Area** — a category and knowledge hub. It owns area-wide principles and routes to children;
  it is not merely an index.
- **Topic** — one focused leaf. Topics cannot have taxonomic children.

The `parent` hierarchy is the primary taxonomy. Normal Markdown links form the wider knowledge
graph and may cross area boundaries. Children are always derived by reversing `parent`; no child
list is stored as metadata.

## Canonical Frontmatter

Every v1 Lore file starts on line one with this exact scalar subset:

```yaml
---
lore: 1
type: area
summary: "Keeps Lore compact, structured, and easy to retrieve."
parent: lore/lore-architecture.md
---
```

The fixed root omits `parent`:

```yaml
---
lore: 1
type: context
summary: "Root working knowledge and navigation for the agent."
---
```

Fields:

- `lore` — file-format version, independent of framework version;
- `type` — `context`, `area`, or `topic`;
- `summary` — one retrieval sentence: what is here and when to open it;
- `parent` — agent-root-relative path to the primary parent.

## Scalar Grammar

V1 uses UTF-8 and accepts LF or CRLF plus an optional UTF-8 BOM. The opening and closing
delimiters are exact `---` lines. Each field is a unique one-line scalar; key order is free.
Spaces and tabs after a scalar are ignored.

- `lore` is the unquoted integer `1`.
- `type` is an unquoted enum.
- `summary` is a non-empty double-quoted JSON-compatible string, at most 240 Unicode characters.
- `parent` is an unquoted safe relative path matching `[A-Za-z0-9][A-Za-z0-9._/-]*`.
- A parent contains no empty, `.` or `..` segment and is either `lore-context.md` or a `.md` path
  below `lore/`.
- Comments, blank lines, collections, aliases, tags, multiline values, duplicate keys, and unknown
  keys make a `lore: 1` block invalid.

Only `lore-context.md` may use `type: context`, and it has no parent. Every area and topic has one
parent whose type is context or area. Depth is unlimited. Siblings use path order. Titles come
from the first H1, with filename fallback.

## Markdown Responsibilities

The context contains essential knowledge used across many sessions, a high-level taxonomy view,
and links to top-level areas plus a few genuinely root-level topics. A v1 context targets at most
10,000 estimated tokens; validation warns above 10,000 and errors above 20,000.

An area contains its scope, boundaries, stable area-wide knowledge, and concise navigation to
direct children. A topic contains focused durable knowledge and useful cross-links explained by
surrounding prose. A fact lives at the highest level where it remains specific and useful.

Canonical cross-links use normal Markdown links. An area may carry a convenient prose child list,
but generated children from `parent` remain authoritative.

## Maps and Token Estimates

Frontmatter is canonical. `lr-core lore-map` derives compact and detailed maps, including child,
token, formal-link, conservative-reference, Git-date, Git-dirty, coverage, and validation data.
Conservative references include non-link mentions such as `` `build.md` ``. Computed values do not
belong in frontmatter and no persistent map cache is created.

The compact map also carries `stats.lore_files`, `stats.lore_context_estimated_tokens`,
`stats.boot_role_estimated_tokens`, `stats.boot_system_prompts_estimated_tokens`, and
`stats.boot_footprint_estimated_tokens`. Boot uses them with total Lore size, map size, and coverage
to produce one standard concise report.

Token estimates use `ceil(Unicode characters / 4)`. They are budgeting estimates, not exact model
token counts.

## Backward Compatibility

- No parseable `lore` field means legacy.
- `lore: 1` with invalid required metadata is invalid v1, not legacy.
- A parseable version other than `1` is unsupported and read-only to v1 merge and grooming.
- Invalid UTF-8 is excluded from taxonomy and grooming without disabling the map. Coverage reports
  only the number of such files, not their paths. Its token size remains a rough replacement-text
  estimate.
- A valid v1 child may temporarily point to the fixed legacy root. It is `unreachable_v1`, not
  invalid, until the root migrates.
- Legacy, partial, and complete agents remain usable. Boot and mapping never infer and persist
  missing taxonomy.

Each uncovered file receives exactly one coverage reason, in order:

1. `invalid_utf8`
2. `unsupported_version`
3. `legacy`
4. `invalid_v1`
5. `unreachable_v1`

Broken cross-links and context-size limits are separate findings and do not change coverage.

## Mechanical Validation

Run:

```text
python3 "<framework-root>/scripts/lr-core" lore-map --agent-dir "<agent-dir>" --view detailed
```

The validator checks supported versions and types, the single fixed context, summaries and
parents, path confinement, parent types, cycles, children under topics, root reachability, and
Lore link targets. Legacy and pre-existing mixed coverage are reported rather than treated as a
script failure. Invalid UTF-8 is also a counted coverage gap rather than a map failure.

V1 deliberately excludes children, metrics, dates, authors, grooming state, tags, link categories,
importance scores, confidence scores, and knowledge-type labels from frontmatter.

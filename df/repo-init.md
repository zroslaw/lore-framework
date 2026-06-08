# /lr:df-repo-init — Initialize the DF backbone repo (BETA)

> **Audience note.** This document is the logic of the `/lr:df-repo-init` skill. Claude runs these steps; the user does not run them manually.

## Goal

Ensure a source repository has its **DF backbone repo** `<repo>-df` (DF = Dark Factory) — the per-repo home for all context, knowledge, and generated artifacts the factory produces that don't belong in the source repo. Creating it is **gated on explicit user confirmation**.

This skill is **aspect-agnostic**: it stands up the backbone that any aspect (ULA today, more later) writes into. It runs no analysis itself.

## Inputs

- **source repo** — the repository under the factory. Default: the current working directory's enclosing git repo. A caller (e.g. `/lr:df-ula-file`) may pass it explicitly.

## Procedure

1. **Resolve the source repo** and its name (e.g. `My-Turbo-Boost-Switcher`).
2. **Derive the sibling path** — `<repo>-df` *as a sibling directory* (same parent as the source repo). Example: `…/git-repos/My-Turbo-Boost-Switcher` → `…/git-repos/My-Turbo-Boost-Switcher-df`.
3. **Idempotency check** — if `<repo>-df/` already exists and contains `df.config.yaml`, report "already initialized" and stop. Never overwrite an existing repo.
4. **Confirm with the user.** Show exactly what will be created (the path, that it will be `git init`-ed, the scaffold below) and ask for explicit confirmation. Do not create anything until the user agrees.
5. **On confirmation, scaffold:**
   - `mkdir <repo>-df` and `git init` it.
   - Write `df.config.yaml` (see below).
   - Create the empty `repo-lore/` directory (with a `.gitkeep`) — the lazily-grown per-source-file tree.
   - Write a short `README.md` saying this is the DF backbone repo for `<repo>`.
   - Optional first commit: `DF init for <repo>`.
6. **Report** the created location back to the user (and to the caller, if invoked).

## `df.config.yaml` scaffold

```yaml
sourceRepoName: My-Turbo-Boost-Switcher
sourceRepoPath: ../My-Turbo-Boost-Switcher   # relative to this -df repo
dfVersion: "0"                               # BETA
createdAt: 2026-06-03
```

## The backbone layout

```
<repo>-df/
├── df.config.yaml
├── README.md
└── repo-lore/                          all lore for the repo (lazy per-file tree)
    └── <source/rel/path/File.ext>/     a Source File Lore dir (created on first analysis)
        ├── file-lore.md                the file's lore landing  (future "context" aspect)
        └── ula/                        the ULA aspect
            └── {bugs,scenarios,gap}.yaml
```

Lazy creation = the tree is a sparse **coverage map**: a `<source-file>/` dir exists iff that file has been analyzed.

## Out of scope (future)

- **Initial repo analysis + prioritized file list.** The broader vision has an "understand the repo, produce a prioritized list of files to analyze" step. That is intentionally *not* part of repo-init — this skill only stands up the backbone. The prioritized-list step will be its own skill (likely `/lr:df-analyze`) that writes into this same `-df` repo.

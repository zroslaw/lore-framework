When implementing a significant framework feature, draft a design doc in `workdir/` *before* touching framework files.

The doc serves three purposes:
1. **Shared reasoning surface** — user and agent can read and react to the design before anything is committed to framework files. Cheaper to revise a doc than a set of cross-referenced files.
2. **Implementation checklist** — listing all files to be created/updated makes scope visible and prevents omissions.
3. **Persistent rationale** — stays in `workdir/` after implementation as the record of why decisions were made. Lore topics capture *what*; design docs capture *why* and *alternatives considered*.

This complements lore topics rather than replacing them: lore topics are atomic, operational, meant to survive many sessions; design docs are session-scoped artifacts that justify the lore.

**When to use:** any feature involving 5+ framework files, cross-cutting changes, or design decisions that need user sign-off before committing scope.

**When to skip:** small fixes, single-file updates, or changes where the scope is obvious from the task description.

**Example:** `workdir/draft-attach-consult-design.md` — created before implementing attach + consult (v4). Listed all files to be written, captured all design decisions with rationale, served as the spec the user reviewed before implementation began.

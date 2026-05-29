# /lr:doctor

Diagnose and heal **framework runtime issues** — the things that go wrong with the framework itself rather than with the agent's content. The user describes a symptom; `/lr:doctor` matches it against a catalog of known ailments and applies (or guides) the fix.

> **When to use.** When something feels off about the framework's behavior — a skill that should exist isn't showing up, a boot command is broken, a plugin update doesn't appear to have landed, a script seems to be running an old version. Anything that smells like "the framework is misbehaving."
>
> Not for content issues. Use `/lr:check` for descriptor validity, references, staleness; use `/lr:update` to reconcile a repo behind the framework's `VERSION`.

## How It Works

`/lr:doctor` is a **catalog of ailments**. *Ailment* is the framework's term for one well-understood runtime failure mode, with a known signature and a known fix. Each ailment is its own topic doc (`doctor-<slug>.md`) describing:

- **Symptoms** — what the user sees that hints at this ailment
- **Diagnosis** — how to confirm it (commands to run, files to check)
- **Remedy** — the fix, with the exact commands or steps
- **Why it happens** — root cause, so the agent can extrapolate

The skill itself is thin — it reads this orchestrator doc, then matches the user's described symptom (or runs through the catalog if no symptom was given) and follows the matching ailment's topic.

The user can also invoke it as a focused query: `"/lr:doctor — my plugin updates aren't showing up"` or `"/lr:doctor — boot command can't find the agent"`. The doctor matches the symptom against the catalog.

## Procedure

1. **Identify the symptom.**
   - If the user supplied a description with their `/lr:doctor` invocation, use it as the matching key.
   - If not, ask: "What are you seeing? Examples: 'a skill I expected after upgrading isn't in the available list', 'a slash command still references the old name', 'a SKILL.md edit doesn't seem to apply'. If you're not sure, describe what you tried and what happened instead — I'll match it against the catalog."

2. **Match against the catalog.** Read the **Catalog** section below. For each ailment, compare its symptom signature against the user's description. If multiple match, list them with their slugs and ask the user which to investigate first.

3. **Load the matching ailment topic.** Read `${CLAUDE_PLUGIN_ROOT}/docs/doctor-<slug>.md`.

4. **Run the diagnosis steps.** Execute the commands and inspect the output exactly as the topic prescribes. Confirm the diagnosis before proceeding.

5. **Apply the remedy.** Follow the remedy steps. For destructive actions (cache wipes, file removals, restarts), state what's about to happen and ask the user to confirm before executing.

6. **Verify.** Re-run a check that proves the symptom is gone (re-list skills, re-boot the agent, re-run the failing command). If the symptom persists, return to step 2 — there may be a second ailment, or the catalog may not yet cover this case.

7. **If no ailment matches:** tell the user the catalog doesn't yet have an entry for this symptom. Offer to investigate manually (read logs, inspect plugin install paths, etc.). If a real root cause is identified, propose adding a new ailment topic during the next session reflection.

## Catalog

Each ailment is owned by a `doctor-<slug>.md` topic. To add a new ailment, write a new topic following the **Authoring an Ailment** schema below and register it here. New ailments go under the relevant category as a `### <slug>` subsection — order ailments within a category by frequency (most-common first).

### Plugin & runtime

#### `doctor-stale-plugin-cache`

*Skills, slash commands, or skill content appear to be running an old version after a plugin update or framework version bump.*

Symptom signatures:

- A skill known to exist in the current `VERSION` is missing from the available-skills list (e.g. `/lr:workspace-sync` on a v11+ install).
- An old skill name lingers after a hard rename (e.g. `/lr:pull-domain` after the v11 rename).
- A SKILL.md or doc edit in the marketplace install doesn't seem to take effect.
- A `/plugin update` or marketplace refresh appears to succeed but Claude Code's behavior reflects the prior version.

*(More ailments accrue here as real-world failures surface and get distilled into topics. The catalog is the framework's accumulated healing wisdom.)*

## What Belongs in the Catalog

The catalog is **universal** — every install of the framework carries every ailment topic. An ailment earns a place only if it can affect any user of the current framework version, regardless of repo, workflow, or host environment.

What does **not** belong:

- **Workspace-specific** — a particular team's setup quirk, a custom helper script's path expectations. Capture these in the workspace's own `CLAUDE.md` or in agent lore.
- **Agent-specific** — issues tied to one agent's role, lore, or workdir contents. These belong in the agent's own lore (or in a specialist agent reachable via `/lr:consult`).
- **Host-specific** — macOS-vs-Linux quirks for a script the framework doesn't ship; tooling-version oddities only some users hit. Address these in the affected script or surface them as separate optional notes, not framework ailments.

If an issue surfaces that's tempting to add but only one user (or one workspace) can hit, write it down somewhere local and let the catalog grow from genuinely shared failures.

## Authoring an Ailment

A `doctor-<slug>.md` topic uses this skeleton:

```markdown
# Stale Plugin Cache

## Symptoms

- *(bulleted list of concrete user-visible signs — what the user sees that points here)*

## Diagnosis

*(steps and commands to confirm this is the actual problem, with expected output)*

## Remedy

*(exact commands to fix it; if multi-step, number them; if destructive, flag what gets removed)*

## Why It Happens

*(one or two paragraphs of root cause — enough that an agent can extrapolate to a related-but-not-identical symptom)*

## See Also

*(links to related topics, ailments, or framework docs)*
```

**Slug format:** lowercase, hyphens, descriptive of the ailment (`stale-plugin-cache`, not `cache`).

**Ailment scope:** atomic. One ailment = one root cause. If two superficially similar symptoms have different causes, write two ailments and cross-reference them.

**Where ailments come from:** real-world failures surfaced during sessions. When a user hits a framework runtime issue and `/lr:doctor` doesn't yet have an entry, the fix is captured during finalization and added as a new ailment topic.

## Relationship to Other Skills

- **`/lr:check`** — content-level consistency (descriptor validity, references, staleness). Covers what the framework can detect statically. `/lr:doctor` is for runtime/environmental issues that escape static checks.
- **`/lr:update`** — applies version migrations and release notes. If the issue is "I'm behind on framework versions," that's `/lr:update`, not `/lr:doctor`. Some ailments (e.g. stale cache after an update) emerge **as a side effect of** a successful `/lr:update` and belong here.
- **`/lr:workspace-sync`** — git-level sync. If a sibling repo is missing or behind, that's `/lr:workspace-sync`. If `/lr:workspace-sync` itself is missing from the available skills, that's a doctor case.

## Limitations

- The catalog is bounded by what's been observed and distilled. The first time a new ailment surfaces, the doctor cannot match it — the user falls back to manual investigation, and the new ailment is added afterward.
- The doctor does not run automatically. A user has to suspect something is wrong and invoke it.
- Each ailment's remedy is only as accurate as the time it was authored. When the framework changes underneath an ailment (paths, command names, install mechanism), the topic must be updated. Treat catalog topics as living docs.

## See Also

- `docs/check.md` — content-level consistency checks.
- `docs/update.md` — version reconciliation.
- `docs/conventions.md` — framework-managed file locations referenced by ailments.

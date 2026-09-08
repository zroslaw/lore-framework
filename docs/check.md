# Lore installation health

One front door for plugin, agent-repo, and workspace health. The script checks structure;
the agent explains findings and reviews meaning. Checking never repairs or pulls repos.

## Step 0 — Announce

> Checking the Lore installation here: the loaded plugin, available agent repos, and workspace
> setup. I’ll report the current configuration and any problems, then offer fixes for approval.

## Run the scanner

Use the session directory, not the plugin root. Resolve the active framework from this skill's
self-location; do not choose a newer cached copy. Run once:

```
python3 "<framework-root>/scripts/lr-core" check --workspace "<session-directory>"
```

Use the current engine profile; on Codex pass `--engine codex`. A user's explicit engine
argument takes precedence. Save large JSON to a temporary file and inspect `summary`,
`warnings`, coverage, and requested findings; never dump the whole graph or raw JSON.

Arguments:

- Default: all layers, compact report.
- `--full`: show every finding and perform the semantic review below. All mechanical Lore
  validation already runs in the script; this flag does not control a second validator.
- `--plugin`, `--repos`, or `--workspace`: pass `--scope plugin`, `repos`, or `workspace` to
  the script. At most one scope. The script's `--workspace <path>` always names the directory;
  the skill's bare `--workspace` selects the layer.
- `--no-network`: skip the bounded upstream plugin-release probe. Repo checks are always local.
- A free-text symptom focuses the explanation; it does not hide other measured problems.

The script reads only the session directory's repos. Context probes inspect descriptor
presence upward and one child level downward to explain a wrong-directory launch; they do
not scan or modify the repos found there. The plugin's own files and engine install inventory
are necessarily outside that directory. `.agents/skills` support is postponed.

If the script exits nonzero or returns `fatal`, report the command and error. Do not invent
an exact count from a manual approximation. This is an implementation script, not a literate
fallback. Findings do not cause a nonzero process exit; scan failure does.

## Render the report

**Print the state line first:** `Lore health — state <N> of 3: <label>`.
Labels: 1 = plugin only; 2 = lore repos, no workspace; 3 = workspace.
Presence describes capability, not health: a configured layer may still have errors.

Show Plugin, Repos, and Workspace rows. Each checked layer gets its count and plain-language
category breakdown from `summary` (separate errors, warnings, and informational cautions); unselected layers say "not checked", never "passed".
For repos show per-repo agent counts. In state 1, explain location context instead of saying
no repos exist when the user is inside one. Display `plugin.root` and installed version;
only say upstream was checked when `upstream == checked`. Otherwise say "upstream not checked".
A local newer tree does not prove which cache-loading mechanism selected the running copy.

Use `findings-catalog.md` for wording, fix tiers and the setup-collapse rule. `collapsed`
rows are replaced by the setup suggestion and excluded from visible counts. Do not count
S11 again when R10 represents it. On `--full`, show every visible finding, keeping exact
paths and IDs available for choosing repairs. On a follow-up request for detail, reuse the
saved scan unless state may have changed.

Always show scan warnings. `complete: false` means some checks were unavailable, not a clean
installation. Semantic accuracy is separately "not reviewed" unless actually reviewed below.
All Lore token counts are estimates; computed finding counts are exact for completed checks.
Do not infer freshness from a recent commit or from an empty behind count. S19 reports the
last recorded successful framework pull; Git behind counts reflect the last fetch only.

When state is below 3, explain the next step:

- Context 1b/1c: name the repo/workspace root and suggest restarting there. Do not change cwd
  and silently scan it. Context 1d: list the immediate child workspace choices.
- Context 1a: no nearby workspace was found within the stated bounds; `create-repo` creates
  a repo with agents. Do not claim a whole-disk search.
- State 2: `workspace-init` adds the shared repo list, routing instructions, and supported
  project plugin settings. Missing initialization is a supported configuration, not corruption.

Keep the default report short. Offer details and repairs once; do not print all repair
commands when the user only asked for a summary.

## Semantic review — AI only

On `--full` with repos selected, inspect each context summary's references to Lore topics.
Compare the referenced topic's heading and opening with what the context says about it.
Report clear meaning mismatches separately from scripted counts. State which agents/topics
were reviewed; if coverage is partial, say so. Never label omitted work as reviewed.

R15 already compares shortcut names mechanically (case, whitespace and hyphens normalized).
AI may interpret an intentional alias, but must preserve the measured discrepancy in the
report. A name difference alone does not prove the shortcut targets the wrong agent.

## Offer and apply repairs

Report first. Propose concrete actions for the actual findings using `findings-catalog.md`.
Ask once for approval of the selected repair set. On approval, invoke the owning skill for
Tier 1 actions, respecting its write boundaries and the user's existing authorization.
Tier 2 shell/file repairs and Tier 3 engine-state repairs are displayed, not executed by
`check`. Do not finalize, publish, reset caches, or restart the engine as a side effect.

After approved repairs complete, rerun the applicable checks and report remaining findings.
A pull which fails or is skipped does not make a repo freshly checked.

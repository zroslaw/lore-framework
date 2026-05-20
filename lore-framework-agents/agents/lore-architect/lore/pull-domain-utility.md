The `pull-domain` utility pulls all git repos in the domain directory in parallel.

**Script:** `lore-framework/scripts/pull-domain [path]`
- Defaults to `.` if no path given
- Runs `git pull` per repo in parallel background subshells
- Streams output in real time, each line prefixed with `[repo-name]`
- Captures exit codes via temp files using the tee + subshell pattern
- Prints a list summary with status icon and note per repo

**Skill:** `/lr:pull-domain`
- Delegates directly to the script via `${CLAUDE_PLUGIN_ROOT}/scripts/pull-domain`
- No Claude reasoning — pure shell delegation

**Skill-to-script delegation pattern:**
When a skill is purely mechanical (no Claude judgment needed), it should call a shell script rather than instruct Claude to perform the steps itself. Benefits: script is independently usable without Claude, skill stays thin, `${CLAUDE_PLUGIN_ROOT}` resolves the path regardless of install location.

**Registered commands scope:**
`/lr:register-repo` writes per-agent boot commands to `.claude/commands/` in the domain directory — project-level only. Plugin skills (`lr:*`) are always available when the plugin is loaded, regardless of directory.

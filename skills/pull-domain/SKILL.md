---
description: "Pull all git repos in the domain directory in parallel."
---

Pull all git repos in the current working directory in parallel and report status in real time.

## Steps

1. **Find repos.** Scan the current working directory for subdirectories containing a `.git` folder. These are the repos to pull.

2. **If none found**, report it and stop.

3. **Pull in parallel.** For each repo, run `git pull` as a background job. Prefix every line of output with `[repo-name]` so the interleaved real-time output stays readable.

4. **Wait** for all background jobs to finish.

5. **Print a summary** listing each repo with a ✓ (success) or ✗ (failed), and a final count.

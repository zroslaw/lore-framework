"""Workspace discovery, repository refresh, and agent preflight."""

from .common import *

# --------------------------------------------------------------------------
# Discovery
# --------------------------------------------------------------------------

def find_repos(workspace):
    """Top-level dirs of `workspace` containing lore-repo.md.

    Top-level only, deliberately: nested repos are invisible to the framework
    (docs/conventions.md § Directory Structure). Hidden dirs are skipped, which
    also excludes the .worktrees/ convention.
    """
    repos = []
    try:
        entries = sorted(os.listdir(workspace))
    except (IOError, OSError):
        return repos
    for name in entries:
        if name.startswith("."):
            continue
        path = os.path.join(workspace, name)
        if not os.path.isdir(path):
            continue
        descriptor = os.path.join(path, "lore-repo.md")
        if os.path.isfile(descriptor):
            repos.append(path)
    return repos


def describe_repo(repo_path):
    fm = parse_frontmatter(read_text(os.path.join(repo_path, "lore-repo.md")))
    repos_field = fm.get("repos", [])
    if isinstance(repos_field, str):
        repos_field = [repos_field] if repos_field else []
    return {
        "path": repo_path,
        "name": os.path.basename(repo_path),
        "description": fm.get("description"),
        "version": fm.get("version"),
        "repos": repos_field,
    }


def repo_agents(repo_path):
    """Agents in one repo: agents/<name>/ containing role.md."""
    agents = []
    agents_dir = os.path.join(repo_path, "agents")
    if not os.path.isdir(agents_dir):
        return agents
    try:
        names = sorted(os.listdir(agents_dir))
    except (IOError, OSError):
        return agents
    for name in names:
        if name.startswith("."):
            continue
        agent_dir = os.path.join(agents_dir, name)
        role = os.path.join(agent_dir, "role.md")
        if not os.path.isfile(role):
            continue
        fm = parse_frontmatter(read_text(role))
        agents.append({
            "name": name,
            "dir": agent_dir,
            "repo": repo_path,
            "description": fm.get("description"),
            "has_lore_context": os.path.isfile(
                os.path.join(agent_dir, "lore-context.md")),
        })
    return agents


def discover_workspace(workspace):
    repos, agents = [], []
    for repo_path in find_repos(workspace):
        info = describe_repo(repo_path)
        found = repo_agents(repo_path)
        info["agents"] = [a["name"] for a in found]
        repos.append(info)
        agents.extend(found)
    return repos, agents


# --------------------------------------------------------------------------
# Git: TTL-cached auto-pull
# --------------------------------------------------------------------------

def absolute_git_dir(repo):
    rc, out, _ = git(repo, ["rev-parse", "--absolute-git-dir"], timeout=15)
    if rc == 0 and out.strip():
        return out.strip()
    return None


def git_toplevel(repo):
    """The root of the git repo that `repo` belongs to, or None.

    Load-bearing: `git -C <dir>` walks UP to the enclosing repository when
    <dir> is merely inside one. A lore repo that was never `git init`ed but
    sits in a git workspace (the workspace-meta-repo layout is a supported
    one) would otherwise have every git operation silently retargeted at the
    workspace — pulling it, stamping it, and reading its history — while the
    output still names the lore repo. Callers compare this against the path
    they were given and refuse to act when they differ.
    """
    rc, out, _ = git(repo, ["rev-parse", "--show-toplevel"], timeout=15)
    if rc == 0 and out.strip():
        return os.path.realpath(out.strip())
    return None


def _stamp_path(repo):
    gd = absolute_git_dir(repo)
    if not gd:
        return None
    # Inside the git dir: never committed, no .gitignore change needed, and it
    # follows the checkout when the worktree convention moves it.
    return os.path.join(gd, "lr-last-pull")


def _read_stamp(repo):
    path = _stamp_path(repo)
    if not path:
        return None
    text = read_text(path)
    if not text:
        return None
    try:
        return float(text.strip())
    except ValueError:
        return None


def _write_stamp(repo):
    path = _stamp_path(repo)
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("%d\n" % int(time.time()))
    except (IOError, OSError):
        pass  # A stamp we cannot write only costs us the TTL optimization.


def pull_repo(repo, ttl=DEFAULT_PULL_TTL_SEC, fresh=False, do_pull=True):
    """Manual fallback: the exact TTL-cached auto-pull procedure for one repo.

    Step 1: if `do_pull` is False (--no-pull), do nothing — report "disabled".

    Step 2: `git -C <repo> rev-parse --is-inside-work-tree`. A git that never
    gave an answer — missing binary, broken PATH, timeout, or killed by a
    signal — is a "failed" result, never a "skipped" one; see git_answered
    above for why that distinction matters. If it ran and printed `false`,
    that is a bare repo with no work tree: "skipped". If it ran and exited
    non-zero, read the message: git's own "not a git repository" wording means
    a genuine non-repo ("skipped", the ordinary case for a repo not under git
    at all); any *other* error means git ran but could not answer — report
    "failed" and carry its message, rather than asserting a non-repo we did
    not actually establish.

    Step 3: `git -C <repo> rev-parse --show-toplevel` and require it to equal
    <repo>. `git -C` silently walks UP to the enclosing repository, so a lore
    repo that is merely a directory *inside* someone else's git repo would
    otherwise have this whole procedure retargeted at that outer repo — we
    would pull it, stamp it, and read its history while reporting the lore
    repo's path. Not equal — "skipped", and do not run any further git
    command against this path.

    Step 4: `git -C <repo> remote get-url origin`. No origin remote — again
    "skipped", not a failure. Stop here.

    Step 5 (TTL check): unless `fresh` or `ttl<=0`, read the timestamp at
    `<absolute-git-dir>/lr-last-pull` (never committed, resolved via
    `git rev-parse --absolute-git-dir` so it follows a worktree checkout). If
    it exists and is younger than `ttl` seconds, report "fresh" and stop —
    skip the network round-trip entirely.

    Step 6 (the pull itself): run `git -C <repo> pull --ff-only` with
    `GIT_TERMINAL_PROMPT=0` and `GIT_SSH_COMMAND='ssh -o BatchMode=yes -o
    ConnectTimeout=10'` so an unauthenticated HTTPS/SSH remote fails fast
    instead of hanging on a prompt, and bound the whole call to ~60s.
    Executing this by hand: apply that bound with your engine profile's
    **runtime-bounding** binding (`docs/engines/<engine>.md`) — on Claude Code
    the Bash tool's own timeout parameter. Do NOT wrap it in a `timeout`/
    `gtimeout` binary: GNU coreutils, absent on stock macOS/BSD, where it
    fails with `command not found` and silently disables the pull. The bound
    is the transport-agnostic backstop that stops a boot hanging on any remote
    type; the env vars above are per-transport fast-fail niceties on top of
    it. Non-zero exit — "failed", with git's own error line as detail; the
    surrounding flow continues in degraded mode, this is not fatal.

    Step 7: on success, write the current time into the TTL stamp file (a
    write failure here only costs the TTL optimization, not correctness).
    Report "up-to-date" if the output says so, else "pulled" — try to count
    commits via `git rev-list HEAD@{1}..HEAD --count` and include the count
    when it parses.

    Returns a dict; never raises. Statuses:
      disabled     — caller passed --no-pull
      fresh        — skipped, pulled within the TTL window
      up-to-date   — pull ran, nothing to fetch
      pulled       — fast-forwarded (commits counted when derivable)
      skipped      — not a git repo, a bare repo, not the root of its own git
                     repo, or no origin remote (all legitimate states)
      failed       — network/auth/non-fast-forward, or git could not answer;
                     caller continues degraded
    """
    if not do_pull:
        return {"status": "disabled", "detail": "pull suppressed by --no-pull"}

    rc, out, err = git(repo, ["rev-parse", "--is-inside-work-tree"], timeout=15)
    if not git_answered(rc):
        return _git_unrunnable(err, rc)
    if rc != 0:
        # Only git's own "not a git repository" wording establishes a non-repo.
        # Anything else (a broken `git` shim, a dangling worktree, a permission
        # error) is git failing to answer — say so instead of inventing a reason.
        if "not a git repository" in err.lower():
            return {"status": "skipped",
                    "detail": _git_error_line(err, "not a git repo")}
        return {"status": "failed",
                "detail": "git could not determine repo status: %s"
                          % _git_error_line(err, "unknown error")}
    if out.strip() == "false":
        # Exits 0 inside a bare repo's own directory, but there is no work tree.
        return {"status": "skipped", "detail": "bare repository (no work tree)"}

    top = git_toplevel(repo)
    if top and top != os.path.realpath(repo):
        # Every later git call would silently act on `top`, not `repo`.
        return {"status": "skipped",
                "detail": "not the root of its own git repo (encloses under %s)" % top}

    rc, _, err = git(repo, ["remote", "get-url", "origin"], timeout=15)
    if not git_answered(rc):
        return _git_unrunnable(err, rc)
    if rc != 0:
        return {"status": "skipped", "detail": "no origin remote"}

    if not fresh and ttl > 0:
        stamp = _read_stamp(repo)
        if stamp is not None:
            age = time.time() - stamp
            if 0 <= age < ttl:
                return {
                    "status": "fresh",
                    "detail": "pulled %ds ago (ttl %ds)" % (int(age), ttl),
                    "age_seconds": int(age),
                }

    # Per-transport fast-fail niceties over the subprocess-timeout backstop.
    # GNU `timeout` is deliberately not used — it is absent on macOS/BSD
    # (docs/conventions.md § Tooling: Portable Shell).
    env = {
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_SSH_COMMAND": "ssh -o BatchMode=yes -o ConnectTimeout=10",
    }
    rc, out, err = git(repo, ["pull", "--ff-only"], env_extra=env)
    if not git_answered(rc):
        return _git_unrunnable(err, rc)
    if rc != 0:
        return {"status": "failed",
                "detail": _git_error_line(err or out, "unknown error")}

    _write_stamp(repo)

    if "Already up to date" in out or "Already up-to-date" in out:
        return {"status": "up-to-date", "detail": "already up to date"}

    commits = None
    crc, cout, _ = git(repo, ["rev-list", "HEAD@{1}..HEAD", "--count"], timeout=15)
    if crc == 0 and cout.strip().isdigit():
        commits = int(cout.strip())
    result = {"status": "pulled", "detail": "fast-forwarded"}
    if commits:
        result["commits"] = commits
        result["detail"] = "fast-forwarded %d commit(s)" % commits
    return result


# --------------------------------------------------------------------------
# Version comparison (detection only — migrations stay with the model)
# --------------------------------------------------------------------------

def compare_versions(repo_version, fw_version):
    """Manual fallback: how to read repo_version against fw_version by hand.

    Either missing/unreadable -> "unknown". Equal as strings -> "match". Else
    try both as integers: equal as integers -> "match" too (`031` and `31` are
    the same version differently spelled; without this check they fall through
    to a skew verdict and the caller tells the user to go reinstall a plugin
    that is already correct). Lower repo version -> "repo-behind", higher ->
    "repo-ahead". If either isn't a plain integer -> "differs" ("compare
    manually" — some agent repos may use a non-numeric scheme).

    This function only detects skew; it never decides what to do about it.
    Applying migrations is judgment work: docs/version-check.md.
    """
    out = {"repo": repo_version, "framework": fw_version}
    if repo_version is None or fw_version is None:
        out["verdict"] = "unknown"
        out["detail"] = "missing or unreadable version stamp"
        return out
    if str(repo_version).strip() == str(fw_version).strip():
        out["verdict"] = "match"
        return out
    try:
        rv, fv = int(str(repo_version).strip()), int(str(fw_version).strip())
    except ValueError:
        out["verdict"] = "differs"
        out["detail"] = "non-numeric version stamp(s); compare manually"
        return out
    if rv == fv:
        out["verdict"] = "match"
        return out
    out["verdict"] = "repo-behind" if rv < fv else "repo-ahead"
    return out


# --------------------------------------------------------------------------
# Process ancestry: engine selection + teammate detection
# --------------------------------------------------------------------------

def _ps_field(pid, field):
    """Read one ps field for one pid.

    One field per call, deliberately: `ps -o ppid=,args=` packs multiple fields
    onto a single line, which has already produced a real parsing bug in this
    codebase (lore: macos-ps-o-multi-field-single-line.md). Trailing `=`
    suppresses the header.
    """
    rc, out, _ = run(["ps", "-o", field + "=", "-p", str(pid)], PS_TIMEOUT_SEC)
    if rc != 0:
        return None
    val = out.strip()
    return val if val else None


def _walk_ancestors():
    """Yield `(pid, args)` for this process's ancestors, nearest first.

    Step 1: start at `os.getppid()` (this process's immediate parent).

    Step 2: for each ancestor pid, up to ANCESTOR_SCAN_DEPTH (6) hops or until
    pid 1: run `ps -o args= -p <pid>` (one field per call — packing multiple
    `-o` fields onto one line has already caused a real parsing bug here, see
    lore macos-ps-o-multi-field-single-line.md). If `ps` returns nothing
    (blocked/unavailable), stop climbing: callers distinguish "read nothing"
    from "read some and found nothing" by counting what this yields.

    Step 3: fetch that process's ppid via another single-field `ps` call and
    climb to it; stop if the parent is unreadable/non-numeric or would loop
    back to the same pid.

    Both ancestry-based checks below share this walk so that one `ps` trap,
    one depth cap, and one set of stop conditions apply to both.
    """
    pid = os.getppid()
    depth = 0
    while pid and pid > 1 and depth < ANCESTOR_SCAN_DEPTH:
        args = _ps_field(pid, "args")
        if args is None:
            return
        yield pid, args
        parent = _ps_field(pid, "ppid")
        if not parent or not parent.strip().isdigit():
            return
        nxt = int(parent.strip())
        if nxt == pid:
            return
        pid = nxt
        depth += 1


def _engine_from_args(args):
    """Map one process's `ps args` line to an engine name, or None.

    Matches the **program** — the first whitespace-separated field's basename —
    against ENGINE_PROGRAMS. If that program is a known interpreter
    (ENGINE_RUNTIMES), also test each later argv token's basename, because an
    engine shipped as a script appears as `node /path/to/claude ...`.

    Deliberately not a substring search over the whole line: an ancestor shell
    sourcing `~/.claude/shell-snapshots/snapshot-zsh-*.sh` would otherwise read
    as Claude Code, and the same trap exists for any engine name that appears in
    a path. Only a program name is evidence about what is executing.
    """
    fields = args.split()
    if not fields:
        return None
    program = os.path.basename(fields[0])
    hit = ENGINE_PROGRAMS.get(program)
    if hit:
        return hit
    if program in ENGINE_RUNTIMES:
        for token in fields[1:]:
            hit = ENGINE_PROGRAMS.get(os.path.basename(token))
            if hit:
                return hit
    return None


def detect_engine(root, override=None):
    """Select the engine profile whose bindings govern this session.

    Boot (docs/agent-boot.md) consumes this at its Step 2 and keeps the named
    profile's bindings for the whole session: the profile decides invocation
    syntax, subagent mechanism, memory file, and how commands are time-bounded.
    It used to be an ordered prose ladder the model walked by hand, which is the
    one part of boot most exposed to being decided by what the model believes
    about itself rather than by what is observable.

    Signals, strongest first. The first that fires wins:

    Step 1: `--engine` override, if given. An explicit caller (a test harness,
    a user debugging a profile) outranks every inference.

    Step 2: a non-empty `CLAUDE_PLUGIN_ROOT` in the environment -> claude. Only
    Claude Code sets it. Empty or absent proves nothing: Claude Code sessions
    started with `--plugin-dir` against a checkout do not set it either.

    Step 3: process ancestry (`_walk_ancestors`), nearest ancestor first, via
    `_engine_from_args`. This is the only signal that observes which engine is
    actually running, so it outranks every filesystem heuristic below. Nearest
    wins: `claude` launched from Cursor's integrated terminal must resolve to
    claude, and its `claude` ancestor is closer than the `Cursor` app process.

    Step 4: containment — <framework-root> lives inside an engine's plugin
    store (ENGINE_HOME_DIRS), compared on path boundaries rather than string
    prefixes, and in both logical and symlink-resolved form (see the comment at
    the loop for why one form alone is wrong in each direction). This answers
    "which engine installed this tree", which is good evidence when `ps` is
    blocked (Codex's sandbox) and the plugin was installed natively.

    Step 5: default to DEFAULT_ENGINE ("claude", the reference profile) with
    confidence "assumed", so the caller can say so rather than presenting a
    guess as a finding. The detail distinguishes the two ways of getting here,
    because they need different remedies: ancestry that ran and found nothing
    (an unrecognised launcher — the program table may need a name) versus
    ancestry that could not run at all (`ps` blocked). The second is the
    dangerous one and is a real, reachable case, not a hypothetical: Codex's
    sandbox blocks `ps`, so a Codex session against a tree outside
    `~/.codex` — a worktree or dev checkout, which is how this framework's own
    contributors run it (docs/worktrees.md) — has no signal on any rung and
    lands here, silently profiled as claude. `--engine codex` is the remedy;
    docs/engines/codex.md says so at the point of use.

    Note what this costs: the removed "~/.codex exists" rung happened to catch
    that case, by accident and for the wrong reason. Removing a signal that is
    wrong in general but right in one case is still the right trade — a rung
    that fires for every session on a multi-engine machine cannot be kept for
    the sake of the sessions it accidentally gets right — but the case it
    covered has to be handled deliberately somewhere, and that somewhere is
    this branch's detail string plus the profile's own guidance.

    NOT a signal, deliberately: whether `~/.codex` or `~/.cursor` merely
    *exists*. That tests whether another engine is installed on this machine,
    never whether it is the one running — and on any workstation with more than
    one engine installed it fires for every session, which is exactly how the
    prose ladder came to route Claude Code sessions to the codex profile.

    Returns {name, signal, confidence, detail, profile}. `profile` is the
    absolute docs/engines/<name>.md path so the caller reads one file instead
    of re-deriving the mapping.
    """
    def _result(name, signal, confidence, detail):
        return {
            "name": name,
            "signal": signal,
            "confidence": confidence,
            "detail": detail,
            "profile": os.path.join(root, "docs", "engines", "%s.md" % name),
        }

    if override:
        return _result(override, "override", "confident",
                       "engine forced by --engine")

    if os.environ.get("CLAUDE_PLUGIN_ROOT", "").strip():
        return _result("claude", "env", "confident",
                       "CLAUDE_PLUGIN_ROOT is set")

    scanned = 0
    for pid, args in _walk_ancestors():
        scanned += 1
        hit = _engine_from_args(args)
        if hit:
            return _result(hit, "ancestry", "confident",
                           "ancestor pid %d runs %s" % (pid, args.split()[0]))

    # Both the logical and the resolved path count, on both sides. Resolving is
    # required for the /var -> /private/var class of trap (see version-check.md,
    # where bare `pwd` vs git's --show-toplevel produced a false verdict), but
    # resolving *alone* breaks the case this signal exists for: Cursor's local
    # plugin surface is `~/.cursor/plugins/local/<name>` symlinked at an
    # arbitrary checkout, so realpath lands outside ~/.cursor and containment
    # never fires for the very install layout it is named after. Test both forms
    # and take a hit on either.
    roots = {os.path.abspath(root), os.path.realpath(root)}
    for home, name in ENGINE_HOME_DIRS:
        expanded = os.path.expanduser(home)
        for base in {expanded, os.path.realpath(expanded)}:
            if any(r == base or r.startswith(base + os.sep) for r in roots):
                return _result(name, "containment", "confident",
                               "framework root is under %s" % home)

    if scanned:
        detail = ("no engine signal in %d readable ancestor(s); assuming the "
                  "reference profile" % scanned)
    else:
        detail = ("no engine signal and ps could not be read (blocked or "
                  "unavailable); assuming the reference profile")
    return _result(DEFAULT_ENGINE, "default", "assumed", detail)


def detect_teammate():
    """Manual fallback: walk process ancestry for the Agent-Teams marker.

    Step 1: walk ancestors nearest-first via `_walk_ancestors` (see there for
    the `ps` invocation, the depth cap, and the stop conditions).

    Step 2: test each process's args against `--agent-id` using a
    flag-boundary regex, not a substring search — `--agent-idle-timeout=30`
    in some unrelated ancestor must not false-positive. A match is an
    immediate "yes": report only that one matching pid/args (truncated to 200
    chars), not the full ancestry — the point of doing this in code instead
    of prose is exactly to avoid spending tokens on the whole chain.

    Step 3: if the walk yielded zero ancestors -> "unknown" ("ps unavailable
    or blocked; assume host session"). If it read at least one ancestor
    without a match -> "no", even if `ps` then failed partway up: we saw real
    process args and none matched. (Zero ancestors also covers an orphaned
    process whose parent is already pid 1, where `ps` is fine and there is
    simply nothing above us to inspect — "unknown" is still the honest answer,
    since we did not rule the marker out.)

    Returns verdict yes/no/unknown. `unknown` is a first-class answer:
    sandboxed engines block `ps`, and the profiles' capability gates expect
    that.
    """
    scanned = 0
    for pid, args in _walk_ancestors():
        scanned += 1
        if TEAMMATE_MARKER_RE.search(args):
            # Only the matching process is echoed back. The full ancestry is
            # noise the caller pays input tokens for; brevity is the point of
            # moving this off the prose path in the first place.
            return {
                "verdict": "yes",
                "detail": "found %s in ancestor pid %d" % (TEAMMATE_MARKER, pid),
                "matched": {"pid": pid, "args": args[:200]},
                "scanned": scanned,
            }
    if not scanned:
        return {
            "verdict": "unknown",
            "detail": "ps unavailable or blocked; assume host session",
            "scanned": 0,
        }
    return {
        "verdict": "no",
        "detail": "no %s in %d ancestor(s)" % (TEAMMATE_MARKER, scanned),
        "scanned": scanned,
    }
def cmd_discover(args, res):
    """Manual fallback (§ Script Fallback Contract): enumerate agents by hand.

    Step 1: resolve <workspace> to an absolute path. If it isn't a directory,
    stop — report "workspace not found" and return empty repos/agents.

    Step 2: list top-level entries of <workspace> (skip dotfiles/dirs — this
    also skips the .worktrees/ convention) and keep the ones that are
    directories containing a lore-repo.md file. Each one is a lore agent repo
    (see find_repos above for the exact listing logic).

    Step 3: for each repo found, read lore-repo.md's frontmatter for
    description/version/repos (see describe_repo), then list agents/*/ and
    keep the subdirectories that contain a role.md (see repo_agents) — read
    each role.md's frontmatter for its description.

    Step 4: report the combined repos + agents list. If zero repos were found,
    that is a failure (ok:false), not silence — the caller needs to know no
    lore agent repos exist at this workspace root.
    """
    workspace = os.path.abspath(args.workspace)
    if not os.path.isdir(workspace):
        res.fail("workspace not found: %s" % workspace)
        res.data = {"workspace": workspace, "repos": [], "agents": []}
        return res

    repos, agents = discover_workspace(workspace)
    res.data = {
        "workspace": workspace,
        "repos": repos,
        "agents": [{"name": a["name"], "repo": a["repo"], "dir": a["dir"],
                    "description": a["description"]} for a in agents],
    }
    if not repos:
        res.fail("no lore agent repos found in %s "
                 "(no top-level directory contains lore-repo.md)" % workspace)
    return res


def _resolve_agent(args, res, workspace):
    """Manual fallback: locate the target agent by hand.

    Step 1: if --agent-dir was given, use it directly. Require a role.md
    inside it (else fail: "not an agent directory"). Derive the repo root by
    walking up two directories and checking for lore-repo.md there; if that
    check fails, warn (don't fail) that repo-scoped steps (pull, version) will
    be skipped for this agent. Read role.md's frontmatter for description.

    Step 2: otherwise, discover every repo under <workspace> (see
    discover_workspace above) and filter its agents to the one(s) named
    --agent. Zero matches -> fail "agent not found", and report the full
    available_agents list so the caller can show it to the user. More than
    one match (same agent name in two repos) -> warn about the ambiguity and
    use the first one, arbitrarily.

    Returns an agent dict, or None with res populated.
    """
    if args.agent_dir:
        if args.agent and os.path.basename(os.path.abspath(args.agent_dir)) != args.agent:
            res.warn("--agent-dir overrides --agent; resolving %s and ignoring "
                     "--agent %s" % (args.agent_dir, args.agent))
        agent_dir = os.path.abspath(args.agent_dir)
        role = os.path.join(agent_dir, "role.md")
        if not os.path.isfile(role):
            res.fail("no role.md at %s — not an agent directory" % agent_dir)
            return None
        repo = _repo_root_for(agent_dir)
        if not repo:
            res.warn("agent dir %s is not two levels below a lore-repo.md; "
                     "repo-scoped steps (pull, version) will be skipped" % agent_dir)
        fm = parse_frontmatter(read_text(role))
        return {
            "name": os.path.basename(agent_dir),
            "dir": agent_dir,
            "repo": repo,
            "description": fm.get("description"),
            "has_lore_context": os.path.isfile(
                os.path.join(agent_dir, "lore-context.md")),
        }

    _, agents = discover_workspace(workspace)
    matches = [a for a in agents if a["name"] == args.agent]
    if not matches:
        res.fail("agent '%s' not found in %s" % (args.agent, workspace))
        res.data["available_agents"] = [
            {"name": a["name"], "repo": a["repo"], "description": a["description"]}
            for a in agents
        ]
        return None
    if len(matches) > 1:
        res.warn("agent name '%s' is ambiguous across %d repos; using %s"
                 % (args.agent, len(matches), matches[0]["repo"]))
    return matches[0]


def cmd_preflight(args, res):
    """The boot/attach/consult/merge preflight. This function's steps ARE the
    normative procedure (docs/conventions.md § Script Fallback Contract) — if
    this script cannot run, read the seven steps below (and the referenced
    helper functions for their own exact commands) and execute them by hand.

    Step 1: resolve <framework-root> (this script's grandparent dir, or
    --framework-root) and read its VERSION file. Missing/unreadable VERSION is
    a warning, not a failure — the version check below just becomes
    inconclusive.

    Step 2: select the engine profile that governs this session (see
    detect_engine below for the ordered signals and for the one that was
    deliberately removed). The caller reads `data.engine.profile` — an absolute
    docs/engines/<name>.md path — and keeps its bindings for the whole session.

    Step 3: resolve the target agent. If --agent-dir was given, use it
    directly: require a role.md there, and derive the repo root by walking up
    two directories and checking for lore-repo.md (warn, don't fail, if that
    check comes up empty — repo-scoped steps 4-5 below are skipped for a
    repo-less agent). Otherwise, discover every repo under <workspace> and
    match --agent by name; no match is a failure (report available_agents);
    more than one match is a warning (use the first, arbitrarily). See
    _resolve_agent below for the exact logic.

    Step 4: record the agent's role.md and lore-context.md paths as
    `read_next`. Reading and interpreting those files is the caller's job —
    their content is judgment material, not something this script parses.

    Step 5: if the agent sits under a real lore repo, auto-pull it (TTL-cached
    — see pull_repo below for the exact `git pull --ff-only` invocation, the
    fast-fail env vars, and the `.git/lr-last-pull` TTL stamp file), then
    compare the repo's lore-repo.md version stamp against the framework
    VERSION read in Step 1 (see compare_versions below for the exact match/
    skew rules). A failed pull is a warning ("continue in degraded mode"), not
    a stopping condition. Version skew other than an exact match is recorded
    in `data.version`; the caller reads docs/version-check.md to render the
    engine-specific remedy.

    Step 6: otherwise (no enclosing repo — the warning from Step 3), skip both
    of those: report pull as "skipped" and version as "unknown", and run no
    git subprocess at all.

    Step 7: after the whole Step 5/6 `if/else` block and before Step 8's
    teammate detection, run the workspace-level auto-refresh leg (see
    `lr_core.workspace_refresh.run_workspace_refresh`): TTL/lock-guarded,
    resolves the true workspace root under the `.worktrees/<repo>/<slug>/`
    convention, and pulls every top-level repo via `scripts/workspace-pull`
    when the last attempt is older than `--workspace-ttl` seconds (default
    16h). This runs whether or not Step 5/6 found an enclosing agent repo —
    an agent booted via `--agent-dir` outside any lore repo says nothing about
    whether the surrounding workspace has repos worth pulling. `--no-pull` or
    `--no-workspace-refresh` disables it; `--fresh` bypasses its TTL the same
    way it bypasses the agent-repo pull's. Never raises: every outcome is a
    status value in `data.workspace_refresh`, never an exception that would
    turn this whole preflight call into the exit-2 manual-boot fallback.

    Step 8: detect an Agent-Teams teammate spawn (see detect_teammate below for
    the exact `ps -o args= -p <ppid>` walk and the `--agent-id` flag-boundary
    match), unless --no-teammate-check suppressed it.

    On engines whose profile gates teammate detection off, this step needs no
    suppression and the caller must not be asked to pre-decide it: Step 2 is
    what learns the engine, so a flag chosen before the call could only be
    guessed. Running the probe anyway is safe by construction — a sandbox that
    blocks `ps` yields "unknown", an engine that allows it yields "no", and
    every caller treats those two identically. --no-teammate-check remains for
    callers that want to skip the two `ps` calls outright.
    """
    workspace = os.path.abspath(args.workspace)
    root = resolve_framework_root(args.framework_root)
    fw_version = framework_version(root)
    if fw_version is None:
        res.warn("no readable VERSION at %s — version check will be inconclusive" % root)

    res.data["framework_root"] = root
    res.data["workspace"] = workspace

    # Step 2: engine profile. Before agent resolution, because everything the
    # caller does after this call — including how it reports failures — is
    # governed by the profile's bindings.
    res.data["engine"] = detect_engine(root, override=getattr(args, "engine", None))
    if res.data["engine"]["confidence"] == "assumed":
        res.warn("engine could not be determined (%s); assuming the %s profile "
                 "— re-run with --engine <claude|codex|cursor> if that is wrong"
                 % (res.data["engine"]["detail"], res.data["engine"]["name"]))

    agent = _resolve_agent(args, res, workspace)
    if agent is None:
        return res

    role_file = os.path.join(agent["dir"], "role.md")
    lore_context_file = os.path.join(agent["dir"], "lore-context.md")
    if not agent["has_lore_context"]:
        res.warn("no lore-context.md at %s — agent has no compacted knowledge yet"
                 % agent["dir"])

    res.data["agent"] = {
        "name": agent["name"],
        "dir": agent["dir"],
        "repo": agent["repo"],
        "description": agent["description"],
        "role_file": role_file,
        "lore_context_file": lore_context_file if agent["has_lore_context"] else None,
    }
    # The files the caller must read into context next. Reading them is the
    # caller's job: their content is judgment material, not script output.
    res.data["read_next"] = [p for p in (role_file, lore_context_file if
                                         agent["has_lore_context"] else None) if p]

    if agent["repo"]:
        # Step 5 (repo branch): TTL-cached pull, then version compare.
        res.data["pull"] = pull_repo(
            agent["repo"], ttl=args.ttl, fresh=args.fresh, do_pull=not args.no_pull)
        if res.data["pull"]["status"] == "failed":
            res.warn("auto-pull failed for %s: %s — continue in degraded mode"
                     % (agent["repo"], res.data["pull"]["detail"]))
        repo_version = parse_frontmatter(
            read_text(os.path.join(agent["repo"], "lore-repo.md"))).get("version")
        res.data["version"] = compare_versions(repo_version, fw_version)
        verdict = res.data["version"]["verdict"]
        # A skew is reported through data.version ONLY — deliberately never as a
        # warning. version-check.md owns the user-facing message for every skew
        # verdict, and on repo-ahead that message is engine-specific: it names the
        # caller's own plugin-refresh commands. A warning here would be a second,
        # blander rendering of the same fact, and a caller whose doc says "surface
        # warnings in one line each" will print it and consider the skew handled.
        # That is exactly how the Codex repo-ahead scenario came to print
        # "version skew: repo=32 framework=31 (repo-ahead)" and stop, instead of
        # the plugin-refresh remedy. Emit the data; let the doc own the words.
        if verdict == "unknown":
            # Not a skew, but not a clean match either: we could not read a
            # stamp. Silence here reads as "versions agree", which is a
            # different and unearned claim.
            #
            # Deliberately does NOT point at version-check.md: that procedure
            # reconciles two comparable versions, and here at least one is
            # absent. Callers (agent-boot.md, attach.md) say to report and
            # continue instead, so this message must not send them elsewhere.
            res.warn("could not read a version stamp (repo=%s framework=%s) — "
                     "version state unverified; continuing without a version check"
                     % (repo_version, fw_version))
    else:
        # Step 6 (no-repo branch): hardcode skipped/unknown, no subprocess runs.
        res.data["pull"] = {"status": "skipped", "detail": "no enclosing lore repo"}
        res.data["version"] = {"verdict": "unknown", "repo": None,
                               "framework": fw_version,
                               "detail": "no enclosing lore repo"}

    # Step 7: workspace-level auto-refresh, regardless of which branch above
    # ran — a repo-less agent dir says nothing about the surrounding
    # workspace. Deferred import: workspace_refresh imports workspace_scan,
    # which imports this module at load time, so importing it at this
    # module's top level would be a circular import.
    from . import workspace_refresh as _workspace_refresh
    res.data["workspace_refresh"] = _workspace_refresh.run_workspace_refresh(
        cwd=workspace,
        ttl=getattr(args, "workspace_ttl", DEFAULT_WORKSPACE_TTL_SEC),
        fresh=args.fresh,
        do_refresh=not (args.no_pull or getattr(args, "no_workspace_refresh", False)),
        framework_root=args.framework_root,
    )

    # Step 8: teammate detection, unless suppressed.
    res.data["teammate"] = detect_teammate() if not args.no_teammate_check else {
        "verdict": "unknown", "detail": "check suppressed by --no-teammate-check",
        "scanned": 0}
    return res

__all__ = [name for name in globals() if not name.startswith("__")]

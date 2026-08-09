"""Legacy Lore census and its CLI adapter."""

from .common import *
from .preflight import _resolve_agent, git_toplevel

# --------------------------------------------------------------------------
# Lore topic scan
# --------------------------------------------------------------------------

def topic_title(path):
    text = read_text(path)
    if not text:
        return None
    lines = text.split("\n")
    # Both v1 and some legacy topics can carry frontmatter. The fence is never
    # a title, so skip a leading block before choosing the first content line.
    if lines and lines[0].strip() == "---":
        for idx in range(1, len(lines)):
            if lines[idx].strip() == "---":
                lines = lines[idx + 1:]
                break
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        stripped = re.sub(r"^#+\s*", "", stripped)
        stripped = re.sub(r"^[*_]+|[*_]+$", "", stripped).strip()
        if stripped:
            return stripped[:TITLE_MAX_CHARS]
    return None


def git_last_modified(repo, rel_dir):
    """Map repo-relative topic path -> last commit ISO date, in ONE git call.

    Per-file `git log` would be one subprocess per topic (~175 today). The log
    walks newest-first, so the first date seen for a path is its last change.

    Returns (dates, error). `error` is non-None only when git could not be run —
    the caller must not report committed topics as "undated" in that case, which
    would explain a broken toolchain as missing commits.
    """
    dates = {}
    # core.quotepath=false: with the default (true) git C-quotes any non-ASCII
    # path in --name-only ("caf\303\251.md"), which never matches the raw
    # filename we look up, so every such topic reads as never committed.
    # LC_ALL=C does not affect quotepath — this has to be set explicitly.
    rc, out, err = git(
        repo,
        ["-c", "core.quotepath=false",
         "log", "--format=%x1e%cI", "--name-only", "--", rel_dir],
        timeout=GIT_TIMEOUT_SEC,
    )
    if not git_answered(rc):
        return dates, "could not run git: %s" % (err.strip()[:200] or "unknown")
    if rc != 0:
        return dates, None
    current = None
    for line in out.split("\n"):
        if line.startswith("\x1e"):
            current = line[1:].strip()
            continue
        name = line.strip()
        if name and current and name not in dates:
            dates[name] = current
    return dates, None


def _age_days(iso_date):
    if not iso_date:
        return None
    try:
        # %cI is strict ISO-8601 with a numeric offset (e.g. +02:00). Python
        # 3.9's fromisoformat does not accept the colon in the offset on all
        # builds, so normalize before parsing.
        import datetime
        normalized = re.sub(r"([+-]\d{2}):(\d{2})$", r"\1\2", iso_date)
        parsed = datetime.datetime.strptime(normalized, "%Y-%m-%dT%H:%M:%S%z")
        delta = datetime.datetime.now(datetime.timezone.utc) - parsed
        return max(0, int(delta.total_seconds() // 86400))
    except (ValueError, ImportError):
        return None


def scan_lore(agent_dir, stale_days=DEFAULT_STALE_DAYS):
    lore_dir = os.path.join(agent_dir, "lore")
    if not os.path.isdir(lore_dir):
        return None, "no lore/ directory at %s" % lore_dir

    names = []
    try:
        for dirpath, dirnames, filenames in os.walk(lore_dir, topdown=True,
                                                    followlinks=False):
            dirnames[:] = sorted(
                name for name in dirnames
                if not name.startswith(".")
                and not os.path.islink(os.path.join(dirpath, name)))
            for name in sorted(filenames):
                path = os.path.join(dirpath, name)
                if (name.startswith(".") or not name.endswith(".md")
                        or os.path.islink(path) or not os.path.isfile(path)):
                    continue
                names.append(os.path.relpath(path, lore_dir).replace(os.sep, "/"))
    except (IOError, OSError) as exc:
        return None, str(exc)
    names.sort()

    repo = _repo_root_for(agent_dir)
    dates, git_error = {}, None
    # `git log --name-only` prints paths relative to the git TOPLEVEL, which is
    # not the lore repo when that repo is merely a directory inside a larger
    # git repo. Key the lookup off the toplevel or none of the paths match and
    # every topic reads as never committed.
    path_base = repo
    if repo:
        # realpath both sides before any relpath: git reports the toplevel with
        # symlinks resolved (on macOS /var/... is a symlink to /private/var/...),
        # so mixing a resolved base with an unresolved path yields a nonsense
        # `../../..`-style relative path that matches no git output at all.
        path_base = git_toplevel(repo) or os.path.realpath(repo)
        rel_dir = os.path.relpath(os.path.realpath(lore_dir), path_base)
        # Run git FROM the toplevel too: `git -C <dir> log -- <pathspec>`
        # resolves the pathspec against <dir>, so a toplevel-relative path
        # handed to a `-C <lore-repo>` call matches nothing at all.
        dates, git_error = git_last_modified(path_base, rel_dir)

    topics, undated, stale_count = [], 0, 0
    for name in names:
        path = os.path.join(lore_dir, *name.split("/"))
        rel = os.path.relpath(os.path.realpath(path), path_base) if repo else name
        iso = dates.get(rel)
        age = _age_days(iso)
        if iso is None:
            undated += 1
        is_stale = age is not None and age > stale_days
        if is_stale:
            stale_count += 1
        try:
            size = os.path.getsize(path)
        except (IOError, OSError):
            size = None
        topics.append({
            "file": name,
            "title": topic_title(path),
            "last_modified": iso,
            "age_days": age,
            "stale": is_stale,
            "bytes": size,
        })

    return {
        "lore_dir": lore_dir,
        "git_error": git_error,
        "count": len(topics),
        "stale_days_threshold": stale_days,
        "stale_count": stale_count,
        "undated_count": undated,
        "topics": topics,
    }, None
def cmd_scan(args, res):
    """Manual fallback: build a lore-topic manifest by hand.

    Step 1: resolve the agent directory — either --agent-dir directly, or
    discover-and-match --agent by name against the workspace (see
    _resolve_agent below, same resolution as preflight Step 2).

    Step 2: recursively list regular <agent-dir>/lore/**/*.md files. Skip
    hidden paths and symlinks, and skip anything that is a directory rather
    than a file, since a dir named `x.md` is not a topic.

    Step 3: for each topic, take the first non-blank line, strip leading `#`
    markdown-heading markers and surrounding `*`/`_` emphasis, and truncate to
    120 chars — that's its title (see topic_title below).

    Step 4: get each topic's last-modified date in ONE `git log
    --format=%x1e%cI --name-only -- <lore-dir>` call scoped to the agent's
    enclosing repo (see git_last_modified below) rather than one `git log`
    per topic. If git could not run at all, record that as `git_error` and do
    not claim the topics are undated — say the dates are unavailable, not that
    the files are new/untracked.

    Step 5: flag a topic `stale` when its age in days exceeds --stale-days
    (default 180). Report topic count, stale count, and undated count
    alongside the per-topic list.
    """
    if args.agent_dir:
        agent_dir = os.path.abspath(args.agent_dir)
    else:
        workspace = os.path.abspath(args.workspace)
        agent = _resolve_agent(args, res, workspace)
        if agent is None:
            return res
        agent_dir = agent["dir"]

    if not os.path.isdir(agent_dir):
        res.fail("agent directory not found: %s" % agent_dir)
        return res

    data, err = scan_lore(agent_dir, stale_days=args.stale_days)
    if err:
        res.fail(err)
        res.data["agent_dir"] = agent_dir
        return res
    data["agent_dir"] = agent_dir
    res.data = data
    if data.get("git_error"):
        # Dates are missing because git could not run, not because the topics
        # are new. Saying "uncommitted or untracked" here would be a confident
        # wrong explanation.
        res.warn("could not read git history, so no topic dates or staleness "
                 "flags are available: %s" % data["git_error"])
    elif data["undated_count"]:
        res.warn("%d topic(s) have no git date (uncommitted or untracked)"
                 % data["undated_count"])
    return res

__all__ = [name for name in globals() if not name.startswith("__")]

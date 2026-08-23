"""Automatic workspace-level refresh: TTL/lock-guarded, invoked from
`preflight.cmd_preflight` after the whole agent-repo `if/else` block, before
teammate detection. This is the mechanism that keeps a whole multi-repo
workspace fresh without a human remembering to run `/lr:workspace-pull`.

Two on-disk files under `<workspace-root>/.tmp/lr-state/`:
  workspace-refresh       readable state — when, whether, why (persistent)
  workspace-refresh.lock  mutual exclusion + crash detection (only while a
                           refresh runs; empty file, mtime is the only signal)

This leg NEVER clones. A workspace whose declared repos are not yet on disk
short-circuits to `setup-required` and defers to the user (`_do_refresh`'s S6
check) — cloning several repos routinely exceeds the bound this leg holds
`workspace-pull` to, and a first-ever boot is exactly the moment a human is
present to run the command themselves.

Exception discipline is the load-bearing property of this whole module: an
uncaught exception anywhere in a preflight leg does not produce a quiet
warning, it makes `cli.main`'s outer catch-all return exit 2 — which routes
*every* boot into the full manual fallback procedure. Every public entry
point here degrades to a status value instead.
"""

import signal

from .common import *
from .workspace_scan import run_workspace_scan, ensure_tmp_ignored

STATE_SUBDIR = os.path.join(".tmp", "lr-state")
STATE_FILE = "workspace-refresh"
LOCK_FILE = "workspace-refresh.lock"
WORKSPACE_PULL_TIMEOUT_SEC = 90


def _state_dir(root):
    return os.path.join(root, STATE_SUBDIR)


def _state_path(root):
    return os.path.join(_state_dir(root), STATE_FILE)


def _lock_path(root):
    return os.path.join(_state_dir(root), LOCK_FILE)


def resolve_workspace_root(cwd):
    """The true workspace root for a session cwd (docs/worktrees.md).

    Sessions routinely work from `<workspace>/.worktrees/<repo>/<slug>/`; if
    `cwd` resolves inside one, the workspace root is the parent of
    `.worktrees/`. Unresolved, this leg would run `workspace-pull` against a
    worktree path, find no descriptors, and write `.tmp/lr-state/` plus a
    `.gitignore` edit inside a disposable feature worktree — and each worktree
    cwd would get its own independent state file, producing more refresh
    attempts than the TTL intends, not fewer.

    Compares resolved real paths: on macOS `/var` is a symlink to
    `/private/var`, so a logical (non-realpath) comparison would false-mismatch.

    Returns None if `cwd` cannot be resolved to a real directory.
    """
    try:
        real = os.path.realpath(cwd)
    except (OSError, ValueError):
        return None
    if not os.path.isdir(real):
        return None
    parts = real.split(os.sep)
    if ".worktrees" in parts:
        idx = parts.index(".worktrees")
        root = os.sep.join(parts[:idx])
        return root if root else os.sep
    return real


# --------------------------------------------------------------------------
# State file: extensionless, minimal-YAML, atomic write, read-refresh rules
# --------------------------------------------------------------------------

def read_state(root):
    """The state file's fields as raw strings (`last-attempt`, `last-success`,
    `result`, `reason`), or `{}` if the file is absent or empty. Never raises.
    """
    text = read_text(_state_path(root))
    if not text:
        return {}
    return parse_yaml_subset(text.split("\n"))


def write_state(root, last_attempt=None, last_success=None, result=None, reason=None):
    """Atomic write: a temp file in the same directory, then `os.replace()`.

    Never raises — a state write we cannot make only costs the TTL
    optimization (the next boot refreshes again too), never boot itself.
    Timestamps are quoted: the framework parser returns strings regardless,
    but quoting keeps the field a string if this file is ever read by a real
    YAML parser, which would otherwise auto-type an unquoted ISO timestamp
    into a datetime.
    """
    state_dir = _state_dir(root)
    try:
        os.makedirs(state_dir, exist_ok=True)
    except OSError:
        return
    lines = [
        "# Lore workspace refresh state. Written automatically at agent boot.",
        "# Delete this file to force a refresh on the next boot.",
    ]
    if last_attempt:
        lines.append('last-attempt: "%s"' % last_attempt)
    if last_success:
        lines.append('last-success: "%s"' % last_success)
    if result:
        lines.append("result: %s" % result)
    if reason:
        lines.append("reason: %s" % reason)
    content = "\n".join(lines) + "\n"
    tmp_path = _state_path(root) + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp_path, _state_path(root))
    except OSError:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def _now_iso():
    """Local offset, not `Z`: `16:14:03+07:00` is readable at a glance;
    `09:14:03Z` forces timezone arithmetic to answer "was this this morning?".
    """
    return datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(
        timespec="seconds")


def needs_refresh(root, ttl):
    """Every failure mode below collapses to "refresh now", so a fresh
    workspace, a corrupted stamp, and a hand-edited file all self-heal at the
    cost of one extra refresh:

    - The file does not exist, or `last-attempt` is missing.
    - `last-attempt` cannot be parsed as an ISO 8601 timestamp.
    - `last-attempt` is not offset-aware (`fromisoformat` on a bare date/time
      returns a naive datetime; comparing it to an aware "now" would raise
      `TypeError` — refuse it explicitly instead of letting that propagate).
    - `last-attempt` is in the future — the clock changed; do not wait it out.
    - `now - last-attempt >= ttl`.

    `ttl <= 0` always refreshes without a special case: once the future-clock
    branch above is excluded, age is never negative, so `age >= ttl` is always
    true for `ttl <= 0`.
    """
    state = read_state(root)
    raw = state.get("last-attempt")
    if not raw:
        return True
    try:
        dt = datetime.datetime.fromisoformat(raw)
    except (TypeError, ValueError):
        return True
    if dt.tzinfo is None:
        return True
    now = datetime.datetime.now(datetime.timezone.utc)
    if dt > now:
        return True
    age = (now - dt).total_seconds()
    return age >= ttl


# --------------------------------------------------------------------------
# Lock: exclusive create, mtime-based staleness, never waits
# --------------------------------------------------------------------------

def _claim_lock(lock_path):
    """One of `"claimed"`, `"in-progress"` (another session holds a live
    lock), or `"error"` (the state directory or lock file could not be
    created — e.g. a read-only `.tmp/` or a full disk). Never waits — a
    caller that loses the race reports `in-progress` and moves on; the two
    failure shapes are kept distinguishable so a permissions error does not
    masquerade as a concurrent session.

    The lock file is empty. Its mtime is the only thing read, and the
    filesystem maintains that for free, so there is no format to parse and no
    way for the lock's contents to be malformed.
    """
    # The state directory may not exist yet on a workspace's very first ever
    # refresh attempt — without this, `os.open(O_CREAT|O_EXCL)` below fails
    # with ENOENT (parent missing), which would otherwise be indistinguishable
    # from a genuine lock contention.
    try:
        os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    except OSError:
        return "error"
    try:
        if os.path.exists(lock_path):
            try:
                mtime = os.stat(lock_path).st_mtime
            except OSError:
                mtime = 0
            if (time.time() - mtime) < WORKSPACE_LOCK_STALE_SEC:
                return "in-progress"
            try:
                os.remove(lock_path)
            except OSError:
                pass  # another session may have reclaimed it first; the
                       # O_EXCL create below is still the real arbiter.
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
        return "claimed"
    except FileExistsError:
        return "in-progress"
    except OSError:
        return "error"


def _release_lock(lock_path):
    try:
        os.remove(lock_path)
    except OSError:
        pass


# --------------------------------------------------------------------------
# Git snapshot / derivation — never from workspace-pull's prose output
# --------------------------------------------------------------------------

def _top_level_git_repos(workspace_root):
    """Every non-hidden, non-symlinked top-level directory containing `.git`
    (a directory in the normal case, a file for a worktree checkout).
    """
    repos = []
    try:
        entries = sorted(os.listdir(workspace_root))
    except OSError:
        return repos
    for name in entries:
        if name.startswith("."):
            continue
        path = os.path.join(workspace_root, name)
        if os.path.islink(path) or not os.path.isdir(path):
            continue
        if os.path.isdir(os.path.join(path, ".git")) or os.path.isfile(
                os.path.join(path, ".git")):
            repos.append((name, path))
    return repos


def _head(path):
    rc, out, _ = git(path, ["rev-parse", "HEAD"], timeout=5)
    return out.strip() if git_answered(rc) and rc == 0 and out.strip() else None


def _is_dirty(path):
    rc, out, _ = git(path, ["status", "--porcelain"], timeout=5)
    return bool(out.strip()) if git_answered(rc) and rc == 0 else False


def _snapshot(repos):
    """`{name: {"head": sha_or_None, "dirty": bool}}`, taken before the pull."""
    return {name: {"head": _head(path), "dirty": _is_dirty(path)}
            for name, path in repos}


def _pulled_list(repos, before):
    """Repos whose HEAD advanced, each carrying the dirty flag sampled BEFORE
    the pull — that is the state that existed when the decision to pull was
    made, and the fact the user needs told, not whatever the repo looks like
    by the time this function runs.
    """
    pulled = []
    for name, path in repos:
        prior = before.get(name) or {}
        if prior.get("head") is None:
            continue
        after = _head(path)
        if after is not None and after != prior["head"]:
            pulled.append({"repo": name, "dirty": bool(prior.get("dirty"))})
    return pulled


def _blocked_repos(repos):
    """Dirty AND behind, checked only after a pull has already failed
    (`--ff-only` still succeeds on a dirty repo when the incoming commits
    don't touch the dirty files, so dirty alone does not mean blocked).
    Anything that raises or returns non-zero is skipped silently — this is a
    diagnostic, never a gate.
    """
    blocked = []
    for name, path in repos:
        if not _is_dirty(path):
            continue
        rc, out, _ = git(path, ["rev-list", "--count", "HEAD..@{u}"], timeout=5)
        if not (git_answered(rc) and rc == 0):
            continue
        try:
            behind = int(out.strip())
        except ValueError:
            continue
        if behind > 0:
            blocked.append(name)
    return blocked


# --------------------------------------------------------------------------
# Bounded subprocess with process-group kill
# --------------------------------------------------------------------------

def _run_workspace_pull(script_path, workspace_root, timeout=WORKSPACE_PULL_TIMEOUT_SEC):
    """`(rc, out, err)`; `rc` is `None` if the script never gave an answer.

    `workspace-pull` forks parallel `git clone`/`git pull` jobs with `&` and
    traps INT/TERM to clean them up on a signal — but a plain
    `subprocess.run(timeout=)` sends SIGKILL to bash alone on expiry. Bash
    cannot trap SIGKILL, so its trap never runs and its git children are
    orphaned, still writing to the workspace after this call has already
    reported failure and moved on — reintroducing, through the timeout path,
    the exact lock contention this feature's own lock exists to avoid.

    `start_new_session=True` plus an explicit process-group kill on timeout
    closes that gap. `Popen` + `communicate(timeout=)` rather than
    `subprocess.run` so the group kill is reachable from this function at all.
    """
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes -o ConnectTimeout=10"
    try:
        proc = subprocess.Popen(
            [script_path, workspace_root],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=env, start_new_session=True)
    except OSError as exc:
        return (None, "", str(exc))
    try:
        out, err = proc.communicate(timeout=timeout)
        return (proc.returncode,
                out.decode("utf-8", "replace"), err.decode("utf-8", "replace"))
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass
        try:
            proc.communicate(timeout=5)
        except Exception:
            pass
        return (None, "", "timed out after %ss" % timeout)


# --------------------------------------------------------------------------
# The leg itself
# --------------------------------------------------------------------------

def _do_refresh(workspace_root, framework_root, script_path):
    """Runs one refresh attempt and returns the `data.workspace_refresh`
    result (minus `last_attempt`/`last_success`, which the caller stamps).

    Two scans, deliberately: this pre-scan decides whether cloning is
    required (never attempted by this leg — see the module docstring); a
    second, post-pull scan decides what to report. A single pre-pull scan
    would report findings the pull is about to resolve. The cost is
    negligible: both scans are in-process, deterministic, and do no network
    I/O of their own.
    """
    pre_scan, _ = run_workspace_scan(workspace_root, framework_root=framework_root)
    pre_findings = {f["id"]: f for f in pre_scan.get("findings", [])}
    if "S6" in pre_findings:
        missing = sorted({
            (m.get("dirname") or m.get("url")) for m in pre_findings["S6"]["data"]})
        return {"status": "setup-required", "missing_repos": missing}

    if not script_path or not os.path.isfile(script_path):
        return {"status": "failed", "reason": "invocation"}

    repos = _top_level_git_repos(workspace_root)
    before = _snapshot(repos)

    rc, out, err = _run_workspace_pull(script_path, workspace_root)
    if rc is None:
        reason = "timeout" if "timed out" in (err or "") else "invocation"
        return {"status": "failed", "reason": reason}
    if rc not in (0, 1):
        # 2 is workspace-pull's own "invalid invocation"; anything else is
        # unexpected and gets the same catch-all reason (§ 8.5: exactly three
        # reason values, one per exit-code family the script documents).
        return {"status": "failed", "reason": "invocation"}

    pulled = _pulled_list(repos, before)
    post_scan, _ = run_workspace_scan(workspace_root, framework_root=framework_root)
    findings = [f for f in post_scan.get("findings", []) if f.get("severity") == "warn"]

    if rc == 0:
        result = {"status": "refreshed", "pulled": pulled}
        if findings:
            result["findings"] = findings
        return result

    result = {"status": "partial", "reason": "pull-failed", "pulled": pulled}
    blocked = _blocked_repos(repos)
    if blocked:
        result["blocked_repos"] = blocked
    if findings:
        result["findings"] = findings
    return result


def run_workspace_refresh(cwd, ttl=DEFAULT_WORKSPACE_TTL_SEC, fresh=False,
                          do_refresh=True, framework_root=None, script_path=None):
    """The workspace-refresh leg. Called from `cmd_preflight` after the whole
    agent-repo `if/else` block, before teammate detection.

    Never raises: every failure mode degrades to a status value, because an
    uncaught exception here does not produce a quiet warning, it routes every
    future boot into the full manual fallback (see the module docstring) —
    the exact regression this feature exists to prevent. Individual steps
    below are already guarded at their own risky calls; the outer `try` is
    the backstop that makes the guarantee unconditional.

    Returns the `data.workspace_refresh` object (see docs/agent-boot.md § 2).
    """
    if not do_refresh:
        return {"status": "disabled"}
    try:
        workspace_root = resolve_workspace_root(cwd)
        if not workspace_root:
            return {"status": "skipped"}

        ensure_tmp_ignored(workspace_root)

        if not fresh and not needs_refresh(workspace_root, ttl):
            return {"status": "fresh"}

        lock_path = _lock_path(workspace_root)
        claim = _claim_lock(lock_path)
        if claim == "in-progress":
            return {"status": "in-progress"}
        if claim == "error":
            return {"status": "failed", "reason": "invocation"}

        try:
            # The winner of a race with a run that just finished may find the
            # stamp already fresh by the time the lock is claimed.
            if not fresh and not needs_refresh(workspace_root, ttl):
                return {"status": "fresh"}

            now_iso = _now_iso()
            prior = read_state(workspace_root)
            write_state(workspace_root, last_attempt=now_iso,
                       last_success=prior.get("last-success"),
                       result=prior.get("result"), reason=prior.get("reason"))

            root = resolve_framework_root(framework_root)
            resolved_script = script_path or os.path.join(
                root, "scripts", "workspace-pull")
            result = _do_refresh(workspace_root, framework_root, resolved_script)

            status = result.get("status")
            if status == "refreshed":
                write_state(workspace_root, last_attempt=now_iso,
                           last_success=now_iso, result="ok")
            elif status == "partial":
                write_state(workspace_root, last_attempt=now_iso,
                           last_success=prior.get("last-success"),
                           result="partial", reason=result.get("reason"))
            elif status == "failed":
                write_state(workspace_root, last_attempt=now_iso,
                           last_success=prior.get("last-success"),
                           result="failed", reason=result.get("reason"))
            else:
                # setup-required: still stamp last-attempt so the TTL applies
                # and the message does not repeat every boot. Not one of the
                # three terminal `result` values, so the prior human-readable
                # result/reason (if any) is preserved rather than replaced.
                write_state(workspace_root, last_attempt=now_iso,
                           last_success=prior.get("last-success"),
                           result=prior.get("result"), reason=prior.get("reason"))
            return result
        finally:
            _release_lock(lock_path)
    except Exception:
        return {"status": "failed", "reason": "invocation"}


__all__ = [name for name in globals() if not name.startswith("__")]

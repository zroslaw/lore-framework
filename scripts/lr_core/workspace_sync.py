"""Workspace-wide git reconciliation: commit, integrate, publish, prune.

This module is a **literate accelerator** (docs/conventions.md § Script Fallback
Contract): these docstrings are the normative procedure, and `docs/workspace-sync.md`
carries only a pointer plus the user-facing words. If this module cannot run, execute
the steps described here by hand, in order.

What the command does, per repository, in this order:

    Phase 0  resume a merge THIS command left behind    (publish repos only)
    Phase 1  inventory: branch, remote, integration target — and refuse to guess
    Phase 2  commit local changes                       (publish repos only)
    Phase 3  fetch and merge the upstream branch
    Phase 4  push                                       (publish repos only)
    Phase 5  worktree hygiene

**The ordering is the safety.** Committing before fetching means the merge is between
two commits rather than between a commit and a dirty working tree: nothing the user
has is unsaved when remote content arrives, `git merge --abort` restores an exact
prior state, and conflict markers only ever land on content already in the object
database. It is also why `--ff-only`'s file-granular failure modes mostly stop
applying to publish repos. *Mostly*: the paths this command deliberately holds back
(below) stay untracked, so an incoming commit that adds one of them still makes git
decline the merge. That outcome is `refused` — reported, never pushed past.

**Operations this module must never perform**, because each one destroys work to make
a sync succeed: `reset --hard`, `checkout --force`, `push --force` (or
`--force-with-lease`), `stash`, `clean`, `--autostash`, `rebase`, and deleting any
tracked or untracked file. `tests/test_workspace_sync.py` asserts both their absence
from this source and, more usefully, the absence of their *effects*.

**What this command deliberately does not decide.** It never creates a branch on a
remote, never resumes an operation somebody else started, never commits in a source
repository, and never publishes a file whose name says credential or whose size says
binary asset. Each of those refusals is reported with the remedy, because a refusal
nobody can see is indistinguishable from a bug.
"""


from .common import *
from .preflight import find_repos

# One commit message for every repo this command publishes. Deliberately generic: the
# script cannot know what the changes mean, and a message that guessed would be worse
# than one that plainly names its origin. A human or agent is free to amend.
COMMIT_MESSAGE = "workspace-sync: publish local state"
# Total push attempts, each preceded by a re-integration. Survives ordinary races with
# a concurrent session; refuses to spin under a busy remote.
MAX_PUSH_ATTEMPTS = 3
FETCH_TIMEOUT_SEC = 120
PUSH_TIMEOUT_SEC = 120
# Editor and merge debris. Never staged (publishing it pollutes a shared repo) and
# never deleted (this command does not remove files).
JUNK_SUFFIXES = (".swp", ".swo", ".orig", ".rej", ".pyc", "~")
JUNK_NAMES = (".DS_Store", "Thumbs.db")
JUNK_DIRS = ("__pycache__", ".pytest_cache", ".venv", "node_modules")
# Held back from every commit, whatever else is true. These names mean "credential" on
# sight, and a push cannot be taken back: the only repair is a history rewrite, which
# this command's own invariants prohibit. Matched on the basename, case-insensitively.
SECRET_NAMES = ("id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", ".netrc", ".npmrc",
                "credentials", "credentials.json", "settings.local.json")
SECRET_PREFIXES = (".env",)
SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".keystore", ".jks", ".ppk")
# A file this large is an asset, not a finding. Committing one can make the repository
# permanently unpushable (hosts reject large blobs), and the commit cannot be undone
# without a rewrite — so it is held back rather than published.
MAX_COMMIT_BYTES = 25 * 1024 * 1024
# Git's own markers for in-progress operations that are NOT a merge. Any of these
# means a human or another tool is mid-operation.
OTHER_OPERATION_MARKERS = (
    ("CHERRY_PICK_HEAD", "cherry-pick"),
    ("REVERT_HEAD", "revert"),
    ("rebase-merge", "rebase"),
    ("rebase-apply", "rebase"),
    ("sequencer", "cherry-pick or revert sequence"),
    ("BISECT_LOG", "bisect"),
)
# Written beside the merge this command leaves in progress, so a later run can tell
# its own unfinished work from a merge somebody else opened. Per-checkout state, so it
# lives in the checkout's own git dir, not the common dir.
MERGE_MARKER = "lr-workspace-sync-merge"
CONFLICT_MARKER_RE = re.compile(r"^(<{7}|={7}|>{7})(\s|$)", re.M)
# Terminal states. Every repo gets exactly one, initialized to `not-attempted`, so a
# run that dies mid-way cannot read as success.
STATUS_NOT_ATTEMPTED = "not-attempted"


# --------------------------------------------------------------------------
# Repository discovery and classification
# --------------------------------------------------------------------------

def classify_repos(workspace):
    """Every git repository this command acts on, with the treatment it gets.

    Manual fallback:

    Step 1: the workspace root itself. It participates only when it is its own git
    root — `git -C <workspace> rev-parse --show-toplevel` must resolve (compared via
    `os.path.realpath`, since on macOS `/var` is a symlink and the logical path
    disagrees with git's physical one) to the workspace. A workspace nested inside an
    enclosing repo is skipped: every git answer would be about that other repo.

    Step 2: every non-hidden top-level directory holding a `.git` entry. A *file*
    counts — that is what a linked worktree and a submodule have. Hidden directories
    are skipped, which also excludes the `.worktrees/` convention.

    Step 3: classify. `lore-repo.md` in the directory means a Lore agent repo; those
    and the workspace root are **publish** repos. Everything else is a **source**
    repo, integrated but never committed and never pushed: committing somebody's
    in-progress source work and pushing it is a destructive act dressed as
    helpfulness, whereas an uncommitted Lore file is a finding nobody else can see.
    """
    repos = []
    ws = os.path.abspath(workspace)
    rc, out, _ = git(ws, ["rev-parse", "--show-toplevel"], timeout=15)
    if git_answered(rc) and rc == 0 and out.strip():
        if os.path.realpath(out.strip()) == os.path.realpath(ws):
            repos.append({"name": os.path.basename(ws.rstrip(os.sep)) or ws,
                          "path": ws, "kind": "workspace"})

    lore_dirs = {os.path.realpath(p) for p in find_repos(ws)}
    try:
        entries = sorted(os.listdir(ws))
    except (IOError, OSError):
        entries = []
    for name in entries:
        if name.startswith("."):
            continue
        path = os.path.join(ws, name)
        if not os.path.isdir(path) or not os.path.exists(os.path.join(path, ".git")):
            continue
        kind = "lore" if os.path.realpath(path) in lore_dirs else "source"
        repos.append({"name": name, "path": path, "kind": kind})
    return repos


def is_publish_repo(kind):
    """Publish repos get phases 0, 2 and 4 (resume, commit, push); source repos do not."""
    return kind in ("workspace", "lore")


# --------------------------------------------------------------------------
# What may be staged
# --------------------------------------------------------------------------

def is_junk(path):
    """Editor/merge debris: never staged, never deleted."""
    base = posixpath.basename(path)
    if base in JUNK_NAMES:
        return True
    if any(base.endswith(suffix) for suffix in JUNK_SUFFIXES):
        return True
    return any(part in JUNK_DIRS for part in path.split("/"))


def looks_secret(path):
    """Does this path's name say 'credential'?

    Name-shaped, not content-scanning: a name test is deterministic, cheap and
    explainable, and the cost of a false positive (one path reported as held) is
    nothing beside the cost of a false negative (a key pushed to a shared remote,
    repairable only by a history rewrite this command forbids itself).
    """
    base = posixpath.basename(path).lower()
    if base in SECRET_NAMES or any(base.startswith(p) for p in SECRET_PREFIXES):
        return True
    return any(base.endswith(s) for s in SECRET_SUFFIXES)


def hold_reason(repo, code, path):
    """Why this dirty path must not be staged, or None when it may be.

    Four holds, each for a distinct irreversible failure:

    - **junk** — publishing editor debris pollutes a shared repo.
    - **nested repository** — an untracked entry git reports with a trailing `/` is a
      directory it would not walk into, which in practice means a repo inside the
      repo. Staging it records a *gitlink* to a commit that exists only on this
      machine: teammates clone an empty directory, and the report would claim the
      content was published.
    - **credential-shaped name** — see `looks_secret`.
    - **oversized** — see `MAX_COMMIT_BYTES`.

    **A deletion is never held, for any reason.** Every hold above exists to keep
    something *out* of the shared history; a deletion is the opposite operation, and
    holding one keeps the very thing the hold objects to alive on the remote. Refusing
    to record `git rm --cached .env` would leave the leaked credential tracked forever
    while reporting "publish it deliberately if it belongs here", which is nonsense
    addressed to somebody who has already decided.
    """
    if code[0] == "D" or code[1] == "D":
        return None
    if is_junk(path):
        return "editor or build debris"
    if code == "??" and path.endswith("/"):
        return "nested git repository — publish it from its own checkout"
    if looks_secret(path):
        return "credential-shaped name — publish it deliberately if it belongs here"
    full = os.path.join(repo, path)
    try:
        if os.path.isfile(full) and os.path.getsize(full) > MAX_COMMIT_BYTES:
            return "larger than %d MB" % (MAX_COMMIT_BYTES // (1024 * 1024))
    except OSError:
        return "could not be read"
    return None


def status_entries(repo):
    """`(code, path)` for every dirty path, or None when git could not answer.

    Manual fallback: `git -C <repo> status --porcelain -z --untracked-files=all`.

    `-z` rather than plain `--porcelain`, because git otherwise quotes and
    backslash-escapes any path with a space or a non-ASCII byte, and the escaped name
    matches nothing on disk — such a path would be silently dropped from the commit.
    Records are NUL-terminated; a rename or copy (`R`/`C`) is two NUL-separated
    fields, the new path first then the original, so the original must be consumed and
    staged too, or the commit records an add without its matching delete.

    `--untracked-files=all` rather than the default, because git otherwise collapses a
    wholly-untracked directory to a single `dir/` entry, and the per-file holds below
    could never see inside it. What still arrives with a trailing `/` after `-uall` is
    a directory git refused to walk — a nested repository, which `hold_reason` catches.

    Returns None — not an empty list — when git did not answer, so that "could not
    look" stays distinguishable from "nothing is dirty".
    """
    rc, out, _ = git(repo, ["status", "--porcelain", "-z", "--untracked-files=all"],
                     timeout=60)
    if not git_answered(rc) or rc != 0:
        return None
    fields = out.split("\0")
    entries, index = [], 0
    while index < len(fields):
        record = fields[index]
        index += 1
        if len(record) < 4:
            continue
        code, path = record[:2], record[3:]
        entries.append((code, path))
        if code[0] in ("R", "C"):
            if index < len(fields) and fields[index]:
                entries.append((code, fields[index]))
            index += 1
    return entries


def unmerged_paths(entries):
    """Paths git reports as conflicted (any `U`, plus the `DD`/`AA` both-changed pair)."""
    out = []
    for code, path in entries or []:
        if "U" in code or code in ("DD", "AA"):
            out.append(path)
    return sorted(set(out))


def has_conflict_markers(repo, paths):
    """Paths still carrying `<<<<<<<` / `=======` / `>>>>>>>` at line start.

    `git add` on a conflicted file clears its unmerged index entry whether or not the
    markers were removed, so "no unmerged paths" is not evidence of resolution — and a
    caller working through the conflict with a broad `git add` produces exactly that
    state. This is the check that stops a commit of live markers.
    """
    dirty = []
    for rel in paths or []:
        text = read_text(os.path.join(repo, rel))
        if text and CONFLICT_MARKER_RE.search(text):
            dirty.append(rel)
    return sorted(dirty)


# --------------------------------------------------------------------------
# In-progress operations and merge ownership
# --------------------------------------------------------------------------

def _git_dir(repo):
    rc, out, _ = git(repo, ["rev-parse", "--absolute-git-dir"], timeout=15)
    if git_answered(rc) and rc == 0 and out.strip():
        return out.strip()
    return None


def _in_progress(repo):
    """`"merge"`, another operation's name, or None.

    Checking only for `MERGE_HEAD` would let a `git cherry-pick` or `git rebase`
    stopped at a conflict look like an ordinary dirty repo — phase 2 would then stage
    the conflicted files *with their markers*, commit them, and push.
    """
    gd = _git_dir(repo)
    if not gd:
        return None
    for marker, label in OTHER_OPERATION_MARKERS:
        if os.path.exists(os.path.join(gd, marker)):
            return label
    if os.path.exists(os.path.join(gd, "MERGE_HEAD")):
        return "merge"
    return None


def _merge_head(repo):
    gd = _git_dir(repo)
    text = read_text(os.path.join(gd, "MERGE_HEAD")) if gd else None
    return text.strip() if text else None


def claim_merge(repo, target_sha, conflicts=None):
    """Record that the merge about to run — or now running — is this command's own.

    **Written before `git merge`, never after.** Writing it afterwards leaves a window
    between git creating `MERGE_HEAD` and this marker landing; a kill inside that
    window (an outer timeout, an OOM, a closed terminal) leaves a real merge this
    command started and no evidence it did, so every later run disowns it and the
    documented "re-running is always the continuation" guarantee fails permanently for
    the one interruption pattern it exists to survive. Claiming first inverts the
    failure: the leftover is a marker with no merge, which `read_merge_claim` discards
    on sight because no `MERGE_HEAD` matches it.

    The marker is a *hint*, never a verdict: the resume path re-derives everything it
    acts on from git, and uses the marker only for the one question git cannot answer
    — "did I start this?".
    """
    gd = _git_dir(repo)
    if not gd:
        return
    payload = {"target": target_sha, "conflicts": conflicts or []}
    try:
        with open(os.path.join(gd, MERGE_MARKER), "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
    except (IOError, OSError):
        pass  # A missing marker costs a refusal on the next run, never data.


def read_merge_claim(repo):
    gd = _git_dir(repo)
    if not gd:
        return None
    text = read_text(os.path.join(gd, MERGE_MARKER))
    if not text:
        return None
    try:
        claim = json.loads(text)
    except ValueError:
        return None
    # The recorded target must be the commit git is actually merging. This is what
    # makes a marker left over from an aborted or completed merge inert.
    return claim if claim.get("target") == _merge_head(repo) else None


def clear_merge_claim(repo):
    gd = _git_dir(repo)
    if not gd:
        return
    try:
        os.remove(os.path.join(gd, MERGE_MARKER))
    except OSError:
        pass


# --------------------------------------------------------------------------
# Phase 1 — inventory
# --------------------------------------------------------------------------

def repo_facts(repo):
    """Branch, remote, integration target and divergence — or the reason to refuse.

    Manual fallback, all with `git -C <repo>`:

    Step 1: `symbolic-ref -q --short HEAD`. No symbolic ref means a detached HEAD:
    there is no branch to integrate with or push to, and choosing one would be a guess
    about where the user's work belongs. Refuse.

    Step 2: the tracking configuration, read as two exact values rather than by
    splitting `@{u}` on a slash — a branch name may contain slashes, so `fork/feature/x`
    cannot be decomposed reliably:

        git config --get branch.<branch>.remote   ->  remote name, e.g. origin
        git config --get branch.<branch>.merge    ->  refs/heads/<remote branch>

    Both the fetch and the push then use *that* remote and *that* branch. Assuming
    `origin` and the local branch name instead is how a repo tracking `fork/main` gets
    merged from the wrong history and pushed to a brand-new remote branch while the
    tracked one never receives the work.

    Step 3: no tracking configuration. If `refs/remotes/<origin>/<branch>` exists, use
    it — a branch that exists on the remote but was never tracked locally is ordinary.
    Otherwise there is nothing to integrate with and publishing would *create* a remote
    branch; that is a decision for a person, so the repo is marked `publish_blocked`
    and still gets phase 2, because committing locally loses nothing and leaves the
    work safe.

    Step 4: `rev-list --left-right --count <target>...HEAD` -> `behind<TAB>ahead`,
    against the remote-tracking ref as it stands now. Phase 3 recomputes after
    fetching; this reading drives the dry-run report.
    """
    facts = {"branch": None, "remote": None, "remote_branch": None, "target": None,
             "ahead": None, "behind": None, "refuse": None, "skip": None,
             "publish_blocked": None}

    rc, out, _ = git(repo, ["symbolic-ref", "-q", "--short", "HEAD"], timeout=15)
    if not git_answered(rc):
        facts["refuse"] = "git could not answer; repository skipped"
        return facts
    if rc != 0 or not out.strip():
        facts["refuse"] = "detached HEAD — no branch to integrate or publish"
        return facts
    branch = facts["branch"] = out.strip()

    rc, out, _ = git(repo, ["remote"], timeout=15)
    if not git_answered(rc) or rc != 0 or not out.strip():
        facts["skip"] = "no remote configured — nothing to synchronize with"
        return facts
    remotes = out.split()

    rc, remote_name, _ = git(repo, ["config", "--get", "branch.%s.remote" % branch],
                             timeout=15)
    rc2, merge_ref, _ = git(repo, ["config", "--get", "branch.%s.merge" % branch],
                            timeout=15)
    if (git_answered(rc) and rc == 0 and remote_name.strip()
            and git_answered(rc2) and rc2 == 0 and merge_ref.strip()):
        facts["remote"] = remote_name.strip()
        facts["remote_branch"] = merge_ref.strip().split("refs/heads/", 1)[-1]
    else:
        fallback = "origin" if "origin" in remotes else remotes[0]
        ref = "refs/remotes/%s/%s" % (fallback, branch)
        rc3, _, _ = git(repo, ["rev-parse", "--verify", "--quiet", ref], timeout=15)
        if git_answered(rc3) and rc3 == 0:
            facts["remote"], facts["remote_branch"] = fallback, branch
        else:
            facts["publish_blocked"] = (
                "branch '%s' has no upstream and no %s/%s — run "
                "`git -C %s push -u %s %s` yourself if it should be published"
                % (branch, fallback, branch, repo, fallback, branch))
            return facts

    facts["target"] = "%s/%s" % (facts["remote"], facts["remote_branch"])
    facts["behind"], facts["ahead"] = _divergence(repo, facts["target"])
    return facts


def _divergence(repo, target):
    """`(behind, ahead)` against `target`, or `(None, None)` if git could not say."""
    rc, out, _ = git(repo, ["rev-list", "--left-right", "--count",
                            "%s...HEAD" % target], timeout=30)
    if git_answered(rc) and rc == 0:
        parts = out.split()
        if len(parts) == 2 and all(p.isdigit() for p in parts):
            return int(parts[0]), int(parts[1])
    return None, None


# --------------------------------------------------------------------------
# Phase 2 — commit
# --------------------------------------------------------------------------

def _pathspec_file(repo, paths):
    """A NUL-separated pathspec file, so a large change set cannot overflow argv.

    Written inside the repository's own git directory rather than the OS temp dir:
    it is guaranteed writable wherever the repo itself is (a sandboxed engine may
    refuse writes outside the project tree), it lands on the same filesystem, and an
    orphan left by a killed process sits where its owner is obvious instead of
    accumulating anonymously in `/tmp`.
    """
    gd = _git_dir(repo) or repo
    path = os.path.join(gd, "lr-workspace-sync-paths")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\0".join(paths))
    return path


def commit_local(repo, entries):
    """Stage every eligible dirty path and commit exactly those. Returns a result dict.

    Manual fallback: partition `status_entries` with `hold_reason`, then

        git -C <repo> add --pathspec-from-file=<f> --pathspec-file-nul
        git -C <repo> commit -m "workspace-sync: publish local state" \\
            --pathspec-from-file=<f> --pathspec-file-nul

    Three details carry weight:

    - **`add` with an explicit pathspec, never `add -A`.** The holds exist precisely to
      keep some dirty paths out; a wholesale add re-adds them.
    - **`commit` with the same pathspec, never a bare `commit`.** A bare commit
      publishes whatever is in the index, including files a concurrent session staged
      between the scan and here — this workspace runs concurrent sessions, and
      `docs/workspace-push.md` carries the same rule for the same reason.
    - **A pathspec file rather than argv**, because a first-ever registration of a
      large tree can exceed the exec argument limit.

    `git add` of a deleted path stages the deletion, so deletions need no special
    handling. Nothing eligible produces no commit rather than an empty one.
    """
    result = {"committed": [], "held": [], "left_dirty": [], "commit": None,
              "error": None}
    eligible, held = [], {}
    for code, path in entries:
        reason = hold_reason(repo, code, path)
        if reason:
            # One entry per path, not per status record: `git rm --cached` on a file
            # still on disk yields both `D` and `??` for the same path, and a report
            # told to read this list verbatim would name the same problem twice.
            held.setdefault(path, reason)
        else:
            eligible.append(path)
    result["held"] = [{"path": p, "reason": held[p]} for p in sorted(held)]
    result["left_dirty"] = sorted(held)
    eligible = sorted(set(eligible))
    if not eligible:
        return result

    spec = _pathspec_file(repo, eligible)
    try:
        rc, _, err = git(repo, ["add", "--pathspec-from-file=" + spec,
                                "--pathspec-file-nul"], timeout=120)
        if not git_answered(rc) or rc != 0:
            result["error"] = explain_git_failure(err, "git add failed")
            return result
        rc, _, err = git(repo, ["commit", "-m", COMMIT_MESSAGE,
                                "--pathspec-from-file=" + spec,
                                "--pathspec-file-nul"], timeout=120)
        if not git_answered(rc) or rc != 0:
            result["error"] = explain_git_failure(err, "git commit failed")
            return result
    finally:
        try:
            os.remove(spec)
        except OSError:
            pass

    result["committed"] = eligible
    rc, out, _ = git(repo, ["rev-parse", "--short", "HEAD"], timeout=15)
    if git_answered(rc) and rc == 0:
        result["commit"] = out.strip()
    return result


# --------------------------------------------------------------------------
# Phase 3 — integrate
# --------------------------------------------------------------------------

def integrate(repo, remote, target):
    """Fetch `remote` and merge `target` in. Returns a result dict.

    Manual fallback: `git -C <repo> fetch <remote>`, then
    `git -C <repo> merge --no-edit <target>`.

    A merge, never a rebase: rebase rewrites local commits and can drop them while
    resolving, whereas a merge keeps both histories intact — which is what "preserve as
    much as possible" means in git terms.

    Statuses: `up-to-date`, `fast-forward`, `merged`, `conflict`, `refused`, `failed`.

    **`refused` is its own outcome, not a failure to explain away.** A non-zero merge
    that leaves no `MERGE_HEAD` and no unmerged paths is git declining to clobber
    something local — an untracked file the incoming commit also adds (the junk this
    command deliberately leaves in place is exactly such a file), or uncommitted
    changes in a source repo. Nothing is half-done, nothing needs aborting, and the
    repo must not be pushed afterwards: git's own message names the paths.

    **A conflict is left in progress on purpose**, and claimed as this command's own.
    The markers sit on content committed on both sides, so nothing can be lost;
    resolving Lore prose needs a reader of the content, which the caller is and this
    script is not.
    """
    result = {"status": None, "conflicts": [], "detail": None}
    rc, _, err = git(repo, ["fetch", remote], timeout=FETCH_TIMEOUT_SEC,
                     env_extra=network_env())
    if not git_answered(rc) or rc != 0:
        result["status"] = "failed"
        result["detail"] = explain_git_failure(err, "git fetch failed")
        return result

    behind, ahead = _divergence(repo, target)
    if behind == 0:
        result["status"] = "up-to-date"
        return result

    rc, target_sha, _ = git(repo, ["rev-parse", "--verify", target], timeout=15)
    if not git_answered(rc) or rc != 0 or not target_sha.strip():
        result["status"] = "failed"
        result["detail"] = "could not resolve %s to a commit" % target
        return result

    # Claim first (see `claim_merge`), then merge. Clear the claim on every path that
    # leaves no merge behind, so a stale marker never outlives the merge it describes.
    claim_merge(repo, target_sha.strip())
    rc, _, err = git(repo, ["merge", "--no-edit", target], timeout=120)
    if git_answered(rc) and rc == 0:
        clear_merge_claim(repo)
        result["status"] = "fast-forward" if ahead == 0 else "merged"
        return result

    conflicts = unmerged_paths(status_entries(repo) or [])
    if conflicts:
        result["status"] = "conflict"
        result["conflicts"] = conflicts
        claim_merge(repo, target_sha.strip(), conflicts)
        return result

    if _in_progress(repo) == "merge":
        # Half-done for some other reason: undo it, since nothing here can finish it.
        git(repo, ["merge", "--abort"], timeout=60)
        result["status"] = "failed"
    else:
        result["status"] = "refused"
    clear_merge_claim(repo)
    result["detail"] = explain_git_failure(err, "git merge did not complete")
    return result


# --------------------------------------------------------------------------
# Phase 4 — push
# --------------------------------------------------------------------------

REJECTION_MARKERS = ("non-fast-forward", "fetch first", "rejected",
                     "tip of your current branch is behind")


def explain_git_failure(err, default):
    """Git's own error line, except where relaying it verbatim would be dangerous.

    `index.lock` is the case that matters. Git's message ends with "remove the file
    manually to continue", which is right after a crash and wrong while a second
    session is mid-write — and the doc instructs the caller to relay a blocked reason
    verbatim, so that advice would reach a user who cannot tell the two apart.
    """
    line = _git_error_line(err, default)
    if "index.lock" in (err or "") or "Another git process" in (err or ""):
        return ("another git process is using this repository — most likely a "
                "concurrent session; re-run once it finishes. Do not delete "
                "index.lock unless you are certain no other process is running")
    return line


def push(repo, remote, remote_branch, target, attempts=MAX_PUSH_ATTEMPTS):
    """Publish to the tracked branch, re-integrating once per rejection.

    Manual fallback: `git -C <repo> push <remote> HEAD:refs/heads/<remote branch>`.

    The fully qualified destination is deliberate — a bare `git push` obeys
    `push.default` and `remote.<name>.push`, either of which can send HEAD somewhere
    the caller never named — and the destination is the *tracked* branch, not the local
    branch's name, or a repo tracking `origin/main` from a local `work` branch would
    quietly grow a new `work` branch on the remote while `main` never received a thing.

    A rejection means the remote moved while this run was working, so the remedy is to
    integrate again and retry, up to `MAX_PUSH_ATTEMPTS`. Never `--force` and never
    `--force-with-lease`: the whole point of a rejection is that somebody else's
    commits are on the other end.

    `local-only` is the honest outcome when the push could not land: the work is
    committed and safe, and it is **pending publication, not success**.
    """
    result = {"status": None, "attempts": 0, "detail": None, "conflicts": []}
    for _ in range(max(1, attempts)):
        result["attempts"] += 1
        rc, _, err = git(repo, ["push", remote, "HEAD:refs/heads/%s" % remote_branch],
                         timeout=PUSH_TIMEOUT_SEC, env_extra=network_env())
        if git_answered(rc) and rc == 0:
            result["status"] = "pushed"
            return result
        low = (err or "").lower()
        if not any(marker in low for marker in REJECTION_MARKERS):
            result["status"] = "local-only"
            result["detail"] = _git_error_line(err, "git push failed")
            return result
        again = integrate(repo, remote, target)
        if again["status"] in ("conflict", "failed", "refused"):
            result["status"] = "local-only"
            result["conflicts"] = again["conflicts"]
            result["detail"] = (again["detail"]
                                or "the remote advanced and the re-merge conflicted")
            return result
    result["status"] = "local-only"
    result["detail"] = ("the remote kept advancing; %d attempts exhausted"
                        % result["attempts"])
    return result


# --------------------------------------------------------------------------
# Phase 5 — worktree hygiene
# --------------------------------------------------------------------------

def worktree_hygiene(repo, prune_dirs=False, dry_run=False):
    """Prune dead registrations when that is provably safe; remove directories only on request.

    Manual fallback: `git -C <repo> worktree list --porcelain` emits stanzas of
    `worktree <path>` / `HEAD <sha>` / `branch <ref>`, with `prunable <reason>` on any
    whose directory is gone. The first stanza is the main worktree and is never a
    candidate.

    **`git worktree prune` is not unconditionally safe, and it is all-or-nothing.** It
    has no grace period when invoked directly, so a worktree on an unmounted volume
    looks exactly like a deleted one — pruning it destroys the admin tree, and when the
    volume comes back the checkout is `fatal: not a git repository` with any
    uncommitted work inside it stranded. A detached-HEAD worktree additionally leaves
    its commits unreferenced, one `git gc` from gone. So a registration is pruned only
    when **both** hold, and if any single candidate fails either test, prune does not
    run at all:

    - its *parent* directory still exists (a deleted worktree; an absent parent is the
      signature of an unmounted volume), and
    - its recorded HEAD is reachable from some ref, or is not a commit this repo has —
      `git rev-list --single-worktree --max-count=1 <sha> --not --all` prints nothing
      when reachable. `--single-worktree` is load-bearing: without it `--all` counts
      every *other* worktree's HEAD as a ref, including the dead worktree's own, so an
      orphaned commit reads as reachable and the registration is pruned away from it.

    Removing a worktree *directory* is opt-in (`--prune-worktrees`) and additionally
    requires: the checkout is clean, its branch has no commits missing from the default
    branch, and it is not the directory this command runs from. Anything else is
    retained with the reason. The commands, when they do run, are
    `git -C <repo> worktree prune` and `git -C <repo> worktree remove <path>`.

    Under `--dry-run` nothing is pruned or removed, but every decision is still
    computed and reported — the checks are all reads — so the preview names exactly
    what a real run would delete. A dry run that skipped the checks would be silent
    about the one action a user most wants previewed.
    """
    out = {"pruned": [], "removed": [], "retained": []}
    rc, listing, _ = git(repo, ["worktree", "list", "--porcelain"], timeout=30)
    if not git_answered(rc) or rc != 0:
        return out

    entries, current = [], None
    for line in listing.split("\n"):
        if line.startswith("worktree "):
            if current:
                entries.append(current)
            current = {"path": line[len("worktree "):].strip(), "branch": None,
                       "head": None, "prunable": False}
        elif current is None:
            continue
        elif line.startswith("HEAD "):
            current["head"] = line[len("HEAD "):].strip()
        elif line.startswith("branch "):
            current["branch"] = line[len("branch "):].strip().split("refs/heads/", 1)[-1]
        elif line.startswith("prunable"):
            current["prunable"] = True
    if current:
        entries.append(current)
    entries = entries[1:]  # the main worktree is not a candidate

    dead = [e for e in entries if e["prunable"]]
    live = [e for e in entries if not e["prunable"]]

    # `git worktree prune` is all-or-nothing, so one unsafe candidate withholds it for
    # the whole repo. Each entry still reports its own reason: an aggregate verdict
    # applied as a per-entry label would tell a user a safe registration was itself
    # the problem.
    unsafe = [(entry, _unsafe_to_prune(repo, entry)) for entry in dead]
    withheld = any(why for _, why in unsafe)

    for entry, why in unsafe:
        if why:
            out["retained"].append({"path": entry["path"], "reason": why})
        elif withheld:
            out["retained"].append(
                {"path": entry["path"],
                 "reason": "prune withheld — another registration in this repo is unsafe"})
        elif dry_run:
            out["retained"].append({"path": entry["path"], "reason": "would be pruned"})
    if dead and not withheld and not dry_run:
        git(repo, ["worktree", "prune"], timeout=30)
        out["pruned"] = sorted(entry["path"] for entry in dead)

    if not live:
        return out
    if not prune_dirs:
        for entry in live:
            out["retained"].append(
                {"path": entry["path"],
                 "reason": "kept (pass --prune-worktrees to remove clean, merged worktrees)"})
        return out

    default_branch = _default_branch(repo)
    here = os.path.realpath(os.getcwd())
    for entry in live:
        why = _unsafe_to_remove(repo, entry, default_branch, here)
        if why:
            out["retained"].append({"path": entry["path"], "reason": why})
            continue
        if dry_run:
            out["retained"].append({"path": entry["path"], "reason": "would be removed"})
            continue
        rc, _, err = git(repo, ["worktree", "remove", entry["path"]], timeout=60)
        if git_answered(rc) and rc == 0:
            out["removed"].append(entry["path"])
        else:
            out["retained"].append(
                {"path": entry["path"],
                 "reason": explain_git_failure(err, "git worktree remove failed")})
    return out


def _unsafe_to_prune(repo, entry):
    """The reason this dead registration must be kept, or None."""
    if os.path.isdir(entry["path"]):
        # Registration dead, directory alive: `git worktree remove` empties the
        # directory before updating the admin data, so a kill part-way through leaves
        # exactly this. Pruning here would strip git's last record of a directory that
        # still holds files, so name it instead and let a person look.
        return ("its directory still exists — looks like wreckage from an interrupted "
                "removal; inspect it before pruning")
    parent = os.path.dirname(entry["path"].rstrip(os.sep))
    if parent and not os.path.isdir(parent):
        return ("its parent directory is absent — not pruning, in case the volume "
                "is merely unmounted")
    head = entry.get("head")
    if head:
        rc, _, _ = git(repo, ["rev-parse", "--verify", "--quiet", head + "^{commit}"],
                       timeout=15)
        if git_answered(rc) and rc == 0:
            rc, out, _ = git(repo, ["rev-list", "--single-worktree", "--max-count=1",
                                    head, "--not", "--all"], timeout=30)
            if not git_answered(rc) or rc != 0:
                return "could not prove its commits are reachable from a ref"
            if out.strip():
                return "holds commits no branch points at"
    return None


def _default_branch(repo):
    rc, out, _ = git(repo, ["symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
                     timeout=15)
    if git_answered(rc) and rc == 0 and out.strip():
        return out.strip().split("/", 1)[-1]
    return None


def _unsafe_to_remove(repo, entry, default_branch, here):
    """The reason this live worktree must be kept, or None when all checks pass."""
    path = entry["path"]
    if not os.path.isdir(path):
        return "directory missing"
    real = os.path.realpath(path)
    if here == real or here.startswith(real + os.sep):
        return "this command is running inside it"
    if not os.path.exists(os.path.join(path, ".git")):
        # `git worktree remove` empties the directory before updating the admin data,
        # so a kill part-way leaves a directory that is neither present nor gone. Say
        # so: every other retention reason describes a worktree somebody is using.
        return "no .git entry — looks like wreckage from an interrupted removal"
    entries = status_entries(path)
    if entries is None:
        return "could not read its status"
    if entries:
        return "has uncommitted changes"
    if not entry["branch"]:
        return "detached HEAD — cannot prove its commits are merged"
    if not default_branch:
        return "repository has no known default branch to compare against"
    rc, out, _ = git(repo, ["rev-list", "--count",
                            "%s..%s" % (default_branch, entry["branch"])], timeout=30)
    if not git_answered(rc) or rc != 0 or not out.strip().isdigit():
        return "could not compare its branch against %s" % default_branch
    if int(out.strip()) != 0:
        return "holds %s commit(s) not in %s" % (out.strip(), default_branch)
    return None


# --------------------------------------------------------------------------
# Per-repo driver
# --------------------------------------------------------------------------

def _entry(repo_info):
    return {"name": repo_info["name"], "path": repo_info["path"],
            "kind": repo_info["kind"], "status": STATUS_NOT_ATTEMPTED,
            "branch": None, "target": None, "actions": [], "committed": [],
            "held": [], "left_dirty": [], "commit": None, "integrate": None,
            "conflicts": [], "push": None,
            "worktrees": {"pruned": [], "removed": [], "retained": []},
            "blocked": None, "skipped": None}


def _finish(entry, status, blocked=None, skipped=None):
    entry["status"] = status
    if blocked:
        entry["blocked"] = blocked
    if skipped:
        entry["skipped"] = skipped
    return entry


def sync_repo(repo_info, dry_run=False, no_push=False, prune_worktrees=False):
    """Run the phases against one repository and return its report entry.

    Manual fallback: phases 0-5 in this module's header order, using the functions
    above. Every exit sets a terminal `status`, which starts at `not-attempted` so a
    run that dies mid-way cannot be mistaken for one that succeeded, and every early
    exit names either a `blocked` reason (somebody must act) or a `skipped` one (an
    ordinary state with nothing to do).
    """
    path, kind = repo_info["path"], repo_info["kind"]
    entry = _entry(repo_info)
    publish = is_publish_repo(kind)

    # Phase 0 — an operation already in progress.
    operation = _in_progress(path)
    if operation and operation != "merge":
        return _finish(entry, "blocked",
                       "%s in progress — finish or abort it, then re-run" % operation)
    if operation == "merge":
        if not publish:
            return _finish(entry, "blocked",
                           "merge in progress in a source repository — finish it yourself")
        claim = read_merge_claim(path)
        conflicts = unmerged_paths(status_entries(path) or [])
        if not claim:
            entry["conflicts"] = conflicts
            return _finish(entry, "blocked",
                           "a merge this command did not start is in progress — "
                           "finish it with `git -C %s commit` (after resolving any "
                           "conflicts) or discard it with `git -C %s merge --abort`, "
                           "then re-run" % (path, path))
        if conflicts:
            entry["conflicts"] = conflicts
            entry["integrate"] = "conflict"
            return _finish(entry, "blocked", "merge conflict awaiting resolution")
        unresolved = has_conflict_markers(path, claim.get("conflicts") or [])
        if unresolved:
            entry["conflicts"] = unresolved
            entry["integrate"] = "conflict"
            return _finish(entry, "blocked",
                           "conflict markers are still present in the resolved files")
        if dry_run:
            entry["actions"].append("would commit the resolved merge")
            return _finish(entry, "skipped", skipped="dry run")
        rc, _, err = git(path, ["commit", "--no-edit"], timeout=120)
        if not git_answered(rc) or rc != 0:
            return _finish(entry, "blocked",
                           explain_git_failure(err, "could not commit the resolved merge"))
        clear_merge_claim(path)
        entry["actions"].append("committed the resolved merge")

    # Phase 1 — inventory.
    facts = repo_facts(path)
    entry["branch"], entry["target"] = facts["branch"], facts["target"]
    if facts["refuse"] or facts["skip"]:
        entry["worktrees"] = worktree_hygiene(path, prune_worktrees, dry_run)
        if facts["skip"]:
            return _finish(entry, "skipped", skipped=facts["skip"])
        return _finish(entry, "blocked", facts["refuse"])

    entries = status_entries(path)
    if entries is None:
        return _finish(entry, "blocked", "could not read the working tree state")
    stuck = unmerged_paths(entries)
    if stuck:
        # Defence in depth: no phase below may run against a conflicted index.
        entry["conflicts"] = stuck
        return _finish(entry, "blocked", "unresolved conflicts in the working tree")

    # Phase 2 — commit.
    if publish and entries:
        if dry_run:
            eligible = [p for c, p in entries if not hold_reason(path, c, p)]
            held = [{"path": p, "reason": hold_reason(path, c, p)}
                    for c, p in entries if hold_reason(path, c, p)]
            entry["held"] = sorted(held, key=lambda h: h["path"])
            entry["left_dirty"] = sorted({h["path"] for h in entry["held"]})
            if eligible:
                entry["actions"].append("would commit %d path(s)" % len(set(eligible)))
        else:
            done = commit_local(path, entries)
            entry["held"], entry["left_dirty"] = done["held"], done["left_dirty"]
            if done["error"]:
                return _finish(entry, "blocked", done["error"])
            entry["committed"], entry["commit"] = done["committed"], done["commit"]
            if done["committed"]:
                entry["actions"].append("committed %d path(s)" % len(done["committed"]))
    elif entries:
        entry["left_dirty"] = sorted({p for _, p in entries})

    # A branch with nowhere to go: the work is committed and safe, and publishing it
    # would create a remote branch, which is a person's decision.
    if facts["publish_blocked"]:
        entry["push"] = "local-only" if publish else None
        entry["worktrees"] = worktree_hygiene(path, prune_worktrees, dry_run)
        return _finish(entry, "local-only" if publish else "skipped",
                       blocked=facts["publish_blocked"] if publish else None,
                       skipped=None if publish else facts["publish_blocked"])

    # Phase 3 — integrate.
    if dry_run:
        if facts["behind"]:
            entry["actions"].append("would merge %s (%d commit(s) behind)"
                                    % (facts["target"], facts["behind"]))
        if publish and facts["ahead"]:
            entry["actions"].append("would push %d commit(s)" % facts["ahead"])
        entry["worktrees"] = worktree_hygiene(path, prune_worktrees, dry_run)
        return _finish(entry, "skipped", skipped="dry run")

    merged = integrate(path, facts["remote"], facts["target"])
    entry["integrate"] = merged["status"]
    entry["conflicts"] = merged["conflicts"]
    if merged["status"] in ("conflict", "refused", "failed"):
        entry["worktrees"] = worktree_hygiene(path, prune_worktrees, dry_run)
        reason = {"conflict": "merge conflict — resolve the listed paths, then re-run",
                  "refused": "git declined to merge: %s" % merged["detail"],
                  "failed": merged["detail"]}[merged["status"]]
        return _finish(entry, "blocked", reason)
    if merged["status"] in ("merged", "fast-forward"):
        entry["actions"].append(merged["status"].replace("-", " "))

    # Phase 4 — push.
    _, ahead = _divergence(path, facts["target"])
    if publish and no_push:
        entry["push"] = "local-only" if ahead else "nothing-to-push"
    elif publish and ahead:
        pushed = push(path, facts["remote"], facts["remote_branch"], facts["target"])
        entry["push"] = pushed["status"]
        if pushed["conflicts"]:
            entry["conflicts"] = pushed["conflicts"]
        if pushed["status"] == "pushed":
            entry["actions"].append("pushed %d commit(s)" % ahead)
        else:
            entry["blocked"] = pushed["detail"] or "the push did not land"
    elif publish:
        entry["push"] = "nothing-to-push"

    # Phase 5 — worktree hygiene.
    entry["worktrees"] = worktree_hygiene(path, prune_worktrees, dry_run)

    if entry["push"] == "local-only":
        return _finish(entry, "local-only")
    if entry["committed"] or entry["push"] == "pushed":
        return _finish(entry, "published")
    return _finish(entry, "up-to-date")


# --------------------------------------------------------------------------
# Command entry point
# --------------------------------------------------------------------------

def cmd_workspace_sync(args, res):
    """Reconcile every repository in the workspace. See this module's header.

    `ok` is false when any repository ended `blocked`, when work was committed but not
    published (`local-only` is pending publication, never success), or when any repo
    still carries the initial `not-attempted` status. `skipped` — an ordinary
    local-only repo, a dry run — is a warning, not a failure: a command that reports
    failure over a normal state teaches its reader to ignore failures.
    """
    workspace = os.path.abspath(args.workspace)
    if not os.path.isdir(workspace):
        res.fail("workspace not found: %s" % workspace)
        return

    repos = classify_repos(workspace)
    if not repos:
        res.warn("no git repositories found in %s" % workspace)

    # Each repo is isolated: an unexpected failure in one becomes that repo's blocked
    # entry, never the loss of the whole report. Repos earlier in the list may already
    # have pushed to a shared remote by then, and a run that did real work must not
    # come back saying nothing happened.
    reports = []
    for info in repos:
        try:
            reports.append(sync_repo(info,
                                     dry_run=args.dry_run,
                                     no_push=args.no_push,
                                     prune_worktrees=args.prune_worktrees))
        except Exception as exc:  # noqa: BLE001 - deliberate per-repo boundary
            entry = _entry(info)
            reports.append(_finish(entry, "blocked",
                                   "unexpected failure: %s: %s"
                                   % (type(exc).__name__, exc)))

    res.data["workspace"] = workspace
    res.data["dry_run"] = bool(args.dry_run)
    res.data["repos"] = reports
    res.data["summary"] = {
        "repos": len(reports),
        "published": sum(1 for r in reports if r["status"] == "published"),
        "blocked": sum(1 for r in reports if r["status"] == "blocked"),
        "local_only": sum(1 for r in reports if r["status"] == "local-only"),
        "skipped": sum(1 for r in reports if r["status"] == "skipped"),
        "held": sorted({h["path"] for r in reports for h in r["held"]}),
        "conflicts": sorted({r["name"] for r in reports if r["conflicts"]}),
    }
    for report in reports:
        if report["status"] == "blocked":
            res.fail("%s: %s" % (report["name"], report["blocked"] or "blocked"))
        elif report["status"] == "local-only":
            res.fail("%s: committed locally but not published%s"
                     % (report["name"],
                        (" — " + report["blocked"]) if report["blocked"] else ""))
        elif report["status"] == STATUS_NOT_ATTEMPTED:
            res.fail("%s: no terminal status recorded" % report["name"])
        elif report["skipped"]:
            res.warn("%s: %s" % (report["name"], report["skipped"]))
        if report["held"]:
            res.warn("%s: %d path(s) held back (%s)"
                     % (report["name"], len(report["held"]),
                        "; ".join("%s — %s" % (h["path"], h["reason"])
                                  for h in report["held"][:3])))


__all__ = [name for name in globals() if not name.startswith("__")]

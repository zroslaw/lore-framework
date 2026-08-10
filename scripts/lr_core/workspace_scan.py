"""Workspace-level state scan: git, descriptors, children, memory files, findings.

This module is a **literate accelerator** (docs/conventions.md § Script Fallback
Contract): the docstrings below ARE the normative procedure. If `workspace-scan`
cannot run, read them in order and execute the described commands by hand — the
flow must reach the same end state.

Four skills consume this one scan, so the rules live here once instead of being
restated in four docs:

  /lr:workspace-status  renders every finding
  /lr:check   #22-#24   renders the subset it owns
  /lr:workspace-init    interviews from the finding list (converge = drive it to zero)
  /lr:workspace-push    takes its framework-managed path set from `managed_paths.set`

**The script emits data; the doc owns the words.** A finding carries an `id`, a
`severity`, and structured `data` — never a finished user-facing sentence.
`docs/workspace-status.md` holds the message and the fix for each ID. A script
string that reads like a finished message gets printed as one, and printing it
*looks* like handling the situation, so the executor never reaches the doc that
owns the remedy.

**No network.** Every git query below reads local refs only, so this is safe to
run on every `/lr:check`. The cost is that `behind` reflects the last fetch;
S14 is `info` for exactly that reason. `workspace-init` Step 6 fetches on its
own, because it is about to make a publication decision.
"""

from .common import *
from .preflight import detect_engine, discover_workspace, find_repos

# --------------------------------------------------------------------------
# The framework-managed path set (docs/workspace-push.md § 7)
# --------------------------------------------------------------------------

# The single source of truth for "what the framework writes at the workspace
# root". Defined here as data, emitted as `data.managed_paths.set`, and rendered
# by the docs rather than restated in them — a remembered copy in prose is how
# `/lr:workspace-push` would come to stage a path nobody re-checked.
#
# All three engines' per-agent shortcuts are in this set as of v37. Codex
# discovers skills under `<repo-root>/.codex/skills/` as well as
# `~/.codex/skills/`, so its shortcuts are workspace-local and publishable like
# Claude's and Cursor's. Shortcuts still sitting in `~/.codex/skills/` are
# legacy: outside the workspace repo, unreachable by any publication path, and
# reported for relocation by finding S15.
MANAGED_PATHS = (
    "lore-workspace.md",
    "AGENTS.md",
    "CLAUDE.md",
    ".gitignore",
    "README.md",
    ".claude/commands/lr-*-agent.md",
    ".codex/skills/lr-*-agent/SKILL.md",
    ".cursor/skills/lr-*-agent/SKILL.md",
)

# The three ignore lines every git-tracked workspace carries, independent of
# which children exist. Distinct from MANAGED_PATHS: these are *content inside*
# `.gitignore`, not paths. Keeping the two terms apart is deliberate — the
# shipped docs once used "workspace-owned" for both, eleven lines apart in the
# same file.
STANDARD_IGNORE_LINES = ("/.worktrees/", "/.lr-beings/", "/.tmp/")

# The canonical level-2 headings of the v3 memory-file payload, in canonical
# order (docs/workspace-init.md § Canonical payload).
MEMORY_SECTIONS = (
    ("lore_framework", "## Lore Framework"),
    ("repositories", "## Repositories"),
    ("agents", "## Agents"),
)

CLAUDE_IMPORT_LINE = "@AGENTS.md"

MARKER_V25 = "<!-- lr:workspace-init:start -->"
MARKER_LEGACY = "<!-- lr:init:start -->"

# Characters that make a derived dirname unusable as a `.gitignore` entry or
# unsafe as a path. Same rule `workspace-pull` applies when it derives a clone
# target — the two must agree or a repo would be cloned under a name the
# scanner then reports as undeclared.
UNSAFE_DIRNAME_CHARS = ("*", "?", "[")


# --------------------------------------------------------------------------
# Small shared helpers
# --------------------------------------------------------------------------

def derive_dirname(url):
    """URL -> the directory name `workspace-pull` would clone it into, or None.

    Manual fallback: take the last path segment of the URL and strip a trailing
    `.git`. `git@github.com:foo/bar.git` -> `bar`. Return None — meaning
    "unsafe, skip and report" — when the result would escape the workspace
    (empty, `.`, `..`, contains a slash, starts with `-`) or would be
    misinterpreted as a `.gitignore` pattern (`*`, `?`, `[`, leading `!`).
    Callers must treat None as a warning, never as a silent skip: a repo whose
    name we refuse to derive is a repo we cannot ignore either.
    """
    if not url:
        return None
    cleaned = str(url).strip().rstrip("/")
    if not cleaned:
        return None
    # Both `host:path` (scp-like) and `scheme://host/path` end with the segment
    # after the last slash; the scp-like form falls back to the colon.
    segment = cleaned.rsplit("/", 1)[-1]
    if segment == cleaned:
        segment = cleaned.rsplit(":", 1)[-1]
    if segment.endswith(".git"):
        segment = segment[:-4]
    if not segment or segment in (".", ".."):
        return None
    if "/" in segment or "\\" in segment:
        return None
    if segment.startswith("-") or segment.startswith("!"):
        return None
    if any(ch in segment for ch in UNSAFE_DIRNAME_CHARS):
        return None
    return segment


def outside_fences(text):
    """The lines of `text` that are not inside a fenced code block.

    Manual fallback: walk the file line by line, toggling "inside a fence" on
    every line whose stripped form starts with ``` or ~~~. Only lines while
    outside count.

    Load-bearing for heading detection. This framework's own docs embed the
    canonical payload as a fenced example containing literal `## Lore Framework`
    lines, and a user who pastes such an example into their `AGENTS.md` would
    otherwise have it read as a real managed heading — which decides where a
    managed region *ends*, and therefore how much of their file a regeneration
    would overwrite.
    """
    lines, inside, out = (text or "").split("\n"), False, []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            inside = not inside
            continue
        if not inside:
            out.append(line)
    return out


def _frontmatter_of(path):
    return parse_frontmatter(read_text(path))


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    return list(value)


# --------------------------------------------------------------------------
# Git state
# --------------------------------------------------------------------------

def git_state(workspace):
    """Local-refs-only git facts about the workspace root itself.

    Manual fallback, in order, all with `git -C <workspace>`:

    Step 1: `rev-parse --show-toplevel`. Non-zero (or git could not answer) ->
    not tracked; stop, every field below stays null.

    Step 2: compare that toplevel against `os.path.realpath(<workspace>)`.
    Never against `pwd`: on macOS `/var` is a symlink to `/private/var`, so the
    logical path disagrees with git's physical one and a correct workspace
    reads as nested. Unequal -> `own_root: false`; the workspace sits inside an
    enclosing repo and every later git answer would be about that repo, so
    callers must refuse to act (see `docs/version-check.md` Step 1b).

    Step 3: `symbolic-ref -q HEAD` for the branch; failure means detached HEAD.

    Step 4: `remote get-url origin` for the origin URL; absent is an ordinary
    state, not an error.

    Step 5: `rev-parse --abbrev-ref --symbolic-full-name @{u}` for the upstream.
    With one, `rev-list --left-right --count @{u}...HEAD` gives
    `behind<TAB>ahead` — left is upstream-only, right is HEAD-only. Without one,
    both stay null rather than 0: "no upstream" and "in sync" are different
    facts and S2/S14 must not fire on the first.

    Step 6: `symbolic-ref --short refs/remotes/origin/HEAD` for the default
    branch. If absent (a common state — it is only written at clone time), leave
    it null and **do not guess `main`**; S8 is suppressed for that repo instead.
    """
    state = {"tracked": False, "own_root": False, "branch": None,
             "detached": False, "origin": None, "upstream": None,
             "ahead": None, "behind": None, "default_branch": None,
             "enclosing_root": None}

    rc, out, _ = git(workspace, ["rev-parse", "--show-toplevel"], timeout=15)
    if not git_answered(rc) or rc != 0 or not out.strip():
        return state
    toplevel = os.path.realpath(out.strip())
    state["tracked"] = True
    if toplevel != os.path.realpath(workspace):
        state["enclosing_root"] = toplevel
        return state
    state["own_root"] = True

    rc, out, _ = git(workspace, ["symbolic-ref", "-q", "HEAD"], timeout=15)
    if git_answered(rc) and rc == 0 and out.strip():
        state["branch"] = out.strip().split("refs/heads/", 1)[-1]
    else:
        state["detached"] = True

    rc, out, _ = git(workspace, ["remote", "get-url", "origin"], timeout=15)
    if git_answered(rc) and rc == 0 and out.strip():
        state["origin"] = out.strip()

    rc, out, _ = git(workspace, ["rev-parse", "--abbrev-ref",
                                 "--symbolic-full-name", "@{u}"], timeout=15)
    if git_answered(rc) and rc == 0 and out.strip():
        state["upstream"] = out.strip()
        rc, out, _ = git(workspace, ["rev-list", "--left-right", "--count",
                                     "@{u}...HEAD"], timeout=15)
        if git_answered(rc) and rc == 0:
            parts = out.split()
            if len(parts) == 2 and all(p.isdigit() for p in parts):
                state["behind"], state["ahead"] = int(parts[0]), int(parts[1])

    rc, out, _ = git(workspace, ["symbolic-ref", "--short",
                                 "refs/remotes/origin/HEAD"], timeout=15)
    if git_answered(rc) and rc == 0 and out.strip():
        state["default_branch"] = out.strip().split("/", 1)[-1]

    return state


def status_paths(workspace):
    """Every path `git status --porcelain` reports, untracked directories expanded.

    Manual fallback: run `git -C <workspace> status --porcelain -z`.

    `-z` rather than plain `--porcelain`: without it git quotes and
    backslash-escapes any path with a space or a non-ASCII byte, and the
    resulting name matches nothing in the managed-path set — a dirty
    `.claude/commands/lr-my agent-agent.md` would silently read as clean. With
    `-z`, records are NUL-terminated and a rename/copy (status `R`/`C`) is two
    NUL-separated fields: the new path first, then the original.

    Then expand: git collapses a wholly-untracked directory to a single `dir/`
    entry, so `.claude/` can stand for `.claude/commands/lr-x-agent.md`. Walk
    each such entry and yield the files beneath it, or the managed-path globs
    below would never match a first-ever registration.
    """
    rc, out, _ = git(workspace, ["status", "--porcelain", "-z"], timeout=30)
    if not git_answered(rc) or rc != 0:
        return None

    records = [r for r in out.split("\0") if r]
    paths = []
    idx = 0
    while idx < len(records):
        record = records[idx]
        idx += 1
        if len(record) < 4:
            continue
        code, path = record[:2], record[3:]
        if code and code[0] in ("R", "C"):
            idx += 1  # consume the original path of a rename/copy
        paths.append(path)

    expanded = []
    for path in paths:
        if not path.endswith("/"):
            expanded.append(path)
            continue
        base = os.path.join(workspace, path)
        if not os.path.isdir(base):
            expanded.append(path)
            continue
        found = False
        for root, _dirs, files in os.walk(base):
            for name in files:
                rel = os.path.relpath(os.path.join(root, name), workspace)
                expanded.append(rel.replace(os.sep, "/"))
                found = True
        if not found:
            expanded.append(path)
    return sorted(set(expanded))


def is_managed(path):
    """Does one repo-relative path belong to the framework-managed set?

    Exact match or glob match against MANAGED_PATHS. `fnmatch` treats `*` as
    matching a `/` too, so an explicit segment-count check keeps
    `.claude/commands/lr-x-agent.md` matching while a hypothetical
    `.claude/commands/nested/lr-x-agent.md` does not.
    """
    import fnmatch
    for pattern in MANAGED_PATHS:
        if path == pattern:
            return True
        if "*" not in pattern:
            continue
        if pattern.count("/") != path.count("/"):
            continue
        if fnmatch.fnmatchcase(path, pattern):
            return True
    return False


def worktree_inventory(workspace):
    """Worktrees registered on the workspace repo, with staleness noted.

    Manual fallback: `git -C <workspace> worktree list --porcelain` emits
    stanzas of `worktree <path>` / `HEAD <sha>` / `branch <ref>`, with `prunable
    <reason>` on any whose directory is gone. Skip the first stanza — it is the
    main worktree, not a `.worktrees/` checkout.
    """
    rc, out, _ = git(workspace, ["worktree", "list", "--porcelain"], timeout=15)
    if not git_answered(rc) or rc != 0:
        return []
    entries, current = [], None
    for line in out.split("\n"):
        if line.startswith("worktree "):
            if current:
                entries.append(current)
            current = {"path": line[len("worktree "):].strip(),
                       "branch": None, "prunable": False}
        elif current is None:
            continue
        elif line.startswith("branch "):
            current["branch"] = line[len("branch "):].strip().split(
                "refs/heads/", 1)[-1]
        elif line.startswith("prunable"):
            current["prunable"] = True
    if current:
        entries.append(current)
    return entries[1:]  # drop the main worktree


# --------------------------------------------------------------------------
# Descriptors and children
# --------------------------------------------------------------------------

def declared_repos(workspace):
    """The union of workspace-level and domain-level `repos:` declarations.

    Manual fallback: read `repos:` from `<workspace>/lore-workspace.md`
    (source `workspace`), then from every `<workspace>/<child>/lore-repo.md`
    (source `domain`). Derive each dirname with `derive_dirname` above. Dedupe
    by URL, keeping the first declarer — that is the one a conflict is reported
    against. A URL whose dirname is unsafe is kept in the list with
    `dirname: null` so the caller can warn rather than silently drop it.
    """
    seen, declared = set(), []

    def _add(urls, source):
        for url in urls:
            url = str(url).strip()
            if not url or url in seen:
                continue
            seen.add(url)
            declared.append({"url": url, "dirname": derive_dirname(url),
                             "source": source})

    ws_fm = _frontmatter_of(os.path.join(workspace, "lore-workspace.md"))
    _add(_as_list(ws_fm.get("repos")), "workspace")
    for repo_path in find_repos(workspace):
        fm = _frontmatter_of(os.path.join(repo_path, "lore-repo.md"))
        _add(_as_list(fm.get("repos")), "domain")
    return declared


def gitignore_lines(workspace):
    text = read_text(os.path.join(workspace, ".gitignore"))
    if text is None:
        return None
    return [line.strip() for line in text.split("\n")]


def scan_children(workspace, declared, ignore_lines):
    """Every top-level directory, with its git, declaration, and ignore status.

    Manual fallback, for each non-hidden top-level directory:

    Step 1: it is a **child git repo** when it contains a `.git` entry — a
    directory in the normal case, a *file* for a worktree checkout or a
    submodule. Testing only for a directory misses both.

    Step 2: it is a **lore agent repo** when it contains `lore-repo.md`.

    Step 3: it is **declared** when its name equals a dirname derived from any
    `repos:` entry (see `declared_repos`).

    Step 4: read `git -C <child> remote get-url origin` and
    `git -C <child> symbolic-ref --short HEAD` / `refs/remotes/origin/HEAD`.
    A missing `origin/HEAD` leaves `default_branch` null and suppresses S8 for
    that child — guessing `main` would fire S8 on every `master` repo.

    Step 5: it is **ignored** when `.gitignore` contains the exact line
    `/<dirname>/`. Exact-line matching only, no pattern interpretation: the
    writer emits only that form, so the reader only needs to find that form.

    A symlinked entry is resolved once; one that lands outside the workspace is
    reported via `escapes_workspace` so the caller can warn instead of walking
    into somebody else's tree.
    """
    declared_names = {d["dirname"] for d in declared if d["dirname"]}
    lines = set(ignore_lines or [])
    children = []
    try:
        entries = sorted(os.listdir(workspace))
    except (IOError, OSError):
        return children

    for name in entries:
        if name.startswith("."):
            continue
        path = os.path.join(workspace, name)
        if not os.path.isdir(path):
            continue
        escapes = False
        if os.path.islink(path):
            resolved = os.path.realpath(path)
            root = os.path.realpath(workspace)
            escapes = not (resolved == root or resolved.startswith(root + os.sep))

        # A directory name taken from the filesystem gets the same
        # metacharacter filter a URL-derived name gets. `!notes` or `logs*` is
        # creatable locally even though no git host allows it as a repo name,
        # and `/!notes/` in .gitignore is a negation that un-ignores something
        # else. Such a child is reported as a conflict (S13) rather than as
        # uncovered (S7) — S7's fix is "run workspace-pull", which cannot help.
        ignorable = not (name.startswith("!") or name.startswith("-")
                         or any(ch in name for ch in UNSAFE_DIRNAME_CHARS))
        entry = {
            "dirname": name,
            "ignorable": ignorable,
            "git": os.path.exists(os.path.join(path, ".git")),
            "lore_repo": os.path.isfile(os.path.join(path, "lore-repo.md")),
            "declared": name in declared_names,
            "origin": None,
            "default_branch": None,
            "current_branch": None,
            "ignored": ("/%s/" % name) in lines,
            "escapes_workspace": escapes,
        }
        if entry["git"] and not escapes:
            rc, out, _ = git(path, ["remote", "get-url", "origin"], timeout=15)
            if git_answered(rc) and rc == 0 and out.strip():
                entry["origin"] = out.strip()
            rc, out, _ = git(path, ["symbolic-ref", "--short", "HEAD"], timeout=15)
            if git_answered(rc) and rc == 0 and out.strip():
                entry["current_branch"] = out.strip()
            rc, out, _ = git(path, ["symbolic-ref", "--short",
                                    "refs/remotes/origin/HEAD"], timeout=15)
            if git_answered(rc) and rc == 0 and out.strip():
                entry["default_branch"] = out.strip().split("/", 1)[-1]
        children.append(entry)
    return children


# --------------------------------------------------------------------------
# Memory files
# --------------------------------------------------------------------------

def memory_state(workspace):
    """The state of `AGENTS.md` (canonical payload) and `CLAUDE.md` (import stub).

    Manual fallback:

    `AGENTS.md` — `format` is decided in this order, first match wins:
      `absent`         the file does not exist
      `legacy-markers` it contains `<!-- lr:init:start -->` and no
                       `lr:workspace-init` pair (the pre-v25 `/lr:init` shape)
      `markers`        it contains `<!-- lr:workspace-init:start -->`
      `v3`             it contains the `## Lore Framework` heading
      `none`           a real file with no framework content at all
    Then, for each canonical heading, count exact case-sensitive matches of a
    level-2 heading line: 0 -> `missing`, 1 -> `present`, >1 -> `duplicated`.
    Exact match matters — `## lore framework` is a user heading, and adopting it
    would put the framework's regenerator on top of the user's prose.

    `CLAUDE.md` — `import_stub` is true when any line's trimmed content is
    exactly `@AGENTS.md`. Line-level, not substring: the point is that the
    framework's only managed content in this file is that one line, and it is
    idempotent to re-assert.

    `payload_in_claude_md` records the pre-v3 layout — a Claude-founded
    workspace whose payload sits in `CLAUDE.md`. That is a migration input, not
    a user error.
    """
    agents_path = os.path.join(workspace, "AGENTS.md")
    claude_path = os.path.join(workspace, "CLAUDE.md")
    agents_text = read_text(agents_path) if os.path.isfile(agents_path) else None
    claude_text = read_text(claude_path) if os.path.isfile(claude_path) else None

    def _format(text):
        if text is None:
            return "absent"
        if MARKER_LEGACY in text and MARKER_V25 not in text:
            return "legacy-markers"
        if MARKER_V25 in text:
            return "markers"
        if any(ln.strip() == "## Lore Framework" for ln in outside_fences(text)):
            return "v3"
        return "none"

    def _sections(text):
        out = {}
        lines = outside_fences(text) if text else []
        for key, heading in MEMORY_SECTIONS:
            count = sum(1 for ln in lines if ln.rstrip() == heading)
            out[key] = "missing" if count == 0 else (
                "present" if count == 1 else "duplicated")
        return out

    claude_format = _format(claude_text)
    return {
        "agents_md": {
            "present": agents_text is not None,
            "format": _format(agents_text),
            "sections": _sections(agents_text),
        },
        "claude_md": {
            "present": claude_text is not None,
            "import_stub": bool(claude_text) and any(
                ln.strip() == CLAUDE_IMPORT_LINE
                for ln in claude_text.split("\n")),
            "payload_in_claude_md": claude_format in ("v3", "markers",
                                                      "legacy-markers"),
        },
    }


def shortcut_inventory(workspace):
    """Registered per-agent shortcuts, by engine, as bare agent names.

    Manual fallback — list each location and strip the `lr-`/`-agent` affixes:
      claude      `<workspace>/.claude/commands/lr-<agent>-agent.md`
      codex       `<workspace>/.codex/skills/lr-<agent>-agent/SKILL.md`
      cursor      `<workspace>/.cursor/skills/lr-<agent>-agent/SKILL.md`
      codex_home  `~/.codex/skills/lr-<agent>-agent/SKILL.md`  (legacy)

    All of them are inventoried on every engine, not just the running one: a
    workspace shared by a mixed-engine team carries all of them, and `init`
    renders the Agents section from the union.

    `codex_home` is a fourth *location*, not a fourth engine. Codex discovers
    skills under both the repo root and the user's home directory, so a home
    shortcut still boots — which is why it counts as registered for S11 — but it
    cannot be published to the team. S15 asks for it to be relocated. Keep the
    two keys apart: merging them would make an unpublishable shortcut
    indistinguishable from a published one.
    """
    def _names_from_files(directory, suffix):
        out = []
        try:
            entries = sorted(os.listdir(directory))
        except (IOError, OSError):
            return out
        for name in entries:
            if name.startswith("lr-") and name.endswith(suffix):
                out.append(name[len("lr-"):-len(suffix)])
        return out

    def _names_from_dirs(directory):
        out = []
        try:
            entries = sorted(os.listdir(directory))
        except (IOError, OSError):
            return out
        for name in entries:
            if not (name.startswith("lr-") and name.endswith("-agent")):
                continue
            if os.path.isfile(os.path.join(directory, name, "SKILL.md")):
                out.append(name[len("lr-"):-len("-agent")])
        return out

    return {
        "claude": _names_from_files(
            os.path.join(workspace, ".claude", "commands"), "-agent.md"),
        "codex": _names_from_dirs(
            os.path.join(workspace, ".codex", "skills")),
        "cursor": _names_from_dirs(
            os.path.join(workspace, ".cursor", "skills")),
        "codex_home": _names_from_dirs(
            os.path.expanduser("~/.codex/skills")),
    }


# --------------------------------------------------------------------------
# Findings
# --------------------------------------------------------------------------

def build_findings(data):
    """Derive S1-S15 from the collected facts. Pure — no I/O, no git.

    Manual fallback: the table in `docs/workspace-status.md` § Findings catalog
    lists every ID with its trigger, its severity, and its fix. This function is
    the trigger column, expressed once; that doc is the message and fix columns.
    Emit `data` payloads only. A finding is a result, never an exit code — the
    scan that produced fifteen of them still exits 0.
    """
    findings = []
    git_data = data["git"]
    usable_git = git_data["tracked"] and git_data["own_root"]

    def add(fid, severity, payload):
        findings.append({"id": fid, "severity": severity, "data": payload})

    managed_dirty = data["managed_paths"]["dirty"]
    other_dirty = data["managed_paths"]["other_dirty"]

    if usable_git and managed_dirty:
        add("S1", "warn", {"paths": managed_dirty})

    if usable_git and (git_data["ahead"] or 0) > 0:
        add("S2", "warn", {"count": git_data["ahead"],
                           "upstream": git_data["upstream"]})

    if usable_git and not git_data["origin"] and data["descriptors"]["sharing"] != "local":
        add("S3", "info", {})

    if not usable_git and data["applicable"]:
        # Two states, one finding, deliberately different severities: a local-only
        # workspace is a supported mode (info), while a workspace nested inside
        # someone else's repo makes every workspace-level git operation unsafe and
        # must not read as one more informational line (warn).
        add("S4", "warn" if git_data["enclosing_root"] else "info",
            {"enclosing_root": git_data["enclosing_root"]})

    undeclared = [c for c in data["children"]
                  if c["git"] and not c["declared"]]
    if undeclared:
        add("S5", "info", [{"dirname": c["dirname"], "origin": c["origin"]}
                           for c in undeclared])

    # Keep the *first* declarer of each dirname — `declared_repos` dedupes by URL,
    # so two different URLs can derive to one directory, and the first is the one a
    # conflict is reported against. A later declarer must not overwrite it: doing so
    # both hides the collision and checks the child's origin against the wrong URL.
    declared_by_dirname, dirname_collisions = {}, []
    for d in data["descriptors"]["declared"]:
        if not d["dirname"]:
            continue
        first = declared_by_dirname.setdefault(d["dirname"], d)
        if first is not d:
            dirname_collisions.append({"dirname": d["dirname"],
                                       "reason": "two declared URLs derive to the same "
                                                 "directory name",
                                       "declared": first["url"], "actual": d["url"]})
    collided = {c["dirname"] for c in dirname_collisions}

    on_disk = {c["dirname"] for c in data["children"]}
    # A dirname two URLs claim is not "missing, run workspace-pull" — pull refuses to
    # place either until a descriptor is edited. S13 owns that state; reporting it here
    # too would hand the user a remedy that cannot work.
    missing = [d for d in data["descriptors"]["declared"]
               if d["dirname"] and d["dirname"] not in on_disk
               and d["dirname"] not in collided]
    if missing:
        add("S6", "warn", [{"url": d["url"], "dirname": d["dirname"]}
                           for d in missing])

    if usable_git:
        uncovered = [c["dirname"] for c in data["children"]
                     if c["git"] and not c["ignored"] and c["ignorable"]]
        lines = data["descriptors"]["gitignore_lines"]
        missing_standard = [] if lines is None else [
            ln for ln in STANDARD_IGNORE_LINES if ln not in lines]
        if uncovered or missing_standard:
            add("S7", "warn", {"repos": uncovered,
                               "standard_lines": missing_standard})

    off_branch = [{"dirname": c["dirname"], "current": c["current_branch"],
                   "default": c["default_branch"]}
                  for c in data["children"]
                  if c["git"] and c["default_branch"] and c["current_branch"]
                  and c["current_branch"] != c["default_branch"]]
    if off_branch:
        add("S8", "warn", off_branch)

    if data["worktrees"]:
        add("S9", "info", data["worktrees"])

    memory = data["memory"]
    violations = []
    if not memory["agents_md"]["present"]:
        violations.append("agents_md_absent")
    if memory["agents_md"]["format"] in ("markers", "legacy-markers"):
        violations.append("legacy_marker_format")
    if memory["claude_md"]["payload_in_claude_md"]:
        violations.append("payload_in_claude_md")
    if not memory["claude_md"]["import_stub"]:
        violations.append("claude_md_import_missing")
    # Section-level violations are only meaningful once the file is *supposed*
    # to carry v3 sections. On a marker-format file every section reads as
    # missing, and reporting four violations for one condition trains the user
    # to skim the list — the single `legacy_marker_format` entry already names
    # the whole remedy.
    if memory["agents_md"]["present"] and \
            memory["agents_md"]["format"] not in ("markers", "legacy-markers"):
        for key, _heading in MEMORY_SECTIONS:
            state = memory["agents_md"]["sections"][key]
            if state != "present":
                violations.append("section_%s_%s" % (key, state))
    if violations:
        add("S10", "warn", {"violations": violations})

    registered = set()
    for names in data["shortcuts"].values():
        registered.update(names)
    unregistered = [a for a in data["agents"] if a not in registered]
    if unregistered:
        add("S11", "info", {"agents": unregistered})

    if usable_git and other_dirty:
        add("S12", "info", {"paths": other_dirty})

    conflicts = list(dirname_collisions)
    for child in data["children"]:
        decl = declared_by_dirname.get(child["dirname"])
        if child["escapes_workspace"]:
            conflicts.append({"dirname": child["dirname"],
                              "reason": "symlink escapes workspace"})
            continue
        if child["git"] and not child["ignorable"]:
            conflicts.append({"dirname": child["dirname"],
                              "reason": "directory name unsafe for a .gitignore "
                                        "line; cannot be ignored automatically"})
        if not decl:
            continue
        if not child["git"]:
            conflicts.append({"dirname": child["dirname"],
                              "reason": "declared but not a git repo"})
        elif child["origin"] is None:
            conflicts.append({"dirname": child["dirname"],
                              "reason": "declared but has no origin remote"})
        elif child["origin"] != decl["url"] and child["dirname"] not in collided:
            # Suppressed under a collision: `decl` is the first declarer, and a child
            # cloned from the second one would be reported as a mismatch against a URL
            # the user never pointed it at — two rows for one problem, whose single
            # remedy is already stated by the collision entry.
            conflicts.append({"dirname": child["dirname"],
                              "reason": "origin does not match declaration",
                              "declared": decl["url"], "actual": child["origin"]})
    unsafe = [d["url"] for d in data["descriptors"]["declared"] if not d["dirname"]]
    for url in unsafe:
        conflicts.append({"dirname": None, "reason": "unsafe derived dirname",
                          "declared": url})
    if conflicts:
        add("S13", "warn", conflicts)

    if usable_git and (git_data["behind"] or 0) > 0:
        add("S14", "info", {"count": git_data["behind"],
                            "upstream": git_data["upstream"]})

    # S15: Codex shortcuts still in `~/.codex/skills/`. Since v37 the framework
    # writes them to `<workspace>/.codex/skills/`, where git can carry them to
    # the team; a home-directory copy boots fine on this machine and reaches
    # nobody else.
    #
    # Reported per agent name, and only for names this workspace actually has an
    # agent for. `~/.codex/skills` is user-global while agent names collide
    # across repos by design (docs/register-repo.md § Collision rule), so an
    # unmatched home shortcut is more likely another workspace's than this one's
    # — claiming it here would tell the user to relocate a shortcut that does not
    # belong to this workspace. The matched ones carry the same ambiguity in
    # weaker form, which is why the severity is `info` and the doc says to check
    # the shortcut's own `from <agent-dir>` before deleting anything.
    #
    # Not gated on the running engine. The old S15 was, because its remedy wrote
    # into the user's home directory; this one asks for a workspace-local write
    # that is correct from any engine, and a mixed-engine team benefits from the
    # Claude session noticing it too.
    home_names = set(data["shortcuts"].get("codex_home") or [])
    workspace_agents = set(data["agents"])
    stale_home = sorted(home_names.intersection(workspace_agents))
    if stale_home:
        add("S15", "info", {"agents": stale_home,
                            "also_workspace_local": sorted(
                                set(data["shortcuts"]["codex"])
                                .intersection(stale_home))})

    order = {"error": 0, "warn": 1, "info": 2}
    findings.sort(key=lambda f: (order.get(f["severity"], 3),
                                 int(f["id"][1:])))
    return findings


# --------------------------------------------------------------------------
# Command
# --------------------------------------------------------------------------

def cmd_workspace_scan(args, res):
    """One read-only pass over the workspace. These steps ARE the procedure.

    Step 1: resolve `<workspace>` to an absolute path. Not a directory ->
    `emit_fatal` (exit 2): the caller cannot proceed on partial data.

    Step 2: decide **applicability**. This is a workspace root when
    `lore-workspace.md` exists, or at least one top-level subdirectory contains
    `lore-repo.md`. Not applicable -> emit `applicable: false` with no findings
    and exit 0. Every consumer skips on that flag; it is not an error, and a
    `/lr:check` run from inside an agent repo reaches it routinely.

    Step 3: collect git state (`git_state`), descriptors (`declared_repos`,
    `.gitignore`), children (`scan_children`), memory files (`memory_state`),
    shortcuts (`shortcut_inventory`), worktrees (`worktree_inventory`), and the
    agents present on disk (`preflight.discover_workspace`).

    Step 4: classify `git status --porcelain -z` output (`status_paths`) into
    `managed_paths.dirty` and `managed_paths.other_dirty` using `is_managed`.
    Emit `managed_paths.set` verbatim — `/lr:workspace-push` stages from this
    field, and no doc restates the set.

    Step 5: select the engine profile via `preflight.detect_engine` — never a
    second detector, and never the executing model's belief about itself. No
    finding is gated on it since v37 (S15 was, until Codex shortcuts became
    workspace-local); it is emitted as `data.engine` for consumers that render
    engine-native invocation syntax, and stays `unknown` on an `assumed`
    verdict rather than being guessed.

    Step 6: derive findings (`build_findings`) and emit. Findings never set a
    nonzero exit; exit 0 means the scan ran, exit 2 means it could not.
    """
    workspace = os.path.abspath(args.workspace)
    if not os.path.isdir(workspace):
        res.fail("workspace not found: %s" % workspace)
        res.data = {"workspace": workspace, "applicable": False}
        return res

    root = resolve_framework_root(getattr(args, "framework_root", None))
    engine = detect_engine(root, override=getattr(args, "engine", None))

    has_workspace_descriptor = os.path.isfile(
        os.path.join(workspace, "lore-workspace.md"))
    applicable = has_workspace_descriptor or bool(find_repos(workspace))

    res.data["workspace"] = workspace
    res.data["applicable"] = applicable
    res.data["engine"] = engine["name"] if engine["confidence"] != "assumed" \
        else "unknown"
    if not applicable:
        res.data["findings"] = []
        return res

    ws_fm = _frontmatter_of(os.path.join(workspace, "lore-workspace.md"))
    ignore_lines = gitignore_lines(workspace)
    declared = declared_repos(workspace)

    for entry in declared:
        if entry["dirname"] is None:
            res.warn("unsafe directory name derived from declared repo %s — "
                     "skipped (see derive_dirname)" % entry["url"])

    children = scan_children(workspace, declared, ignore_lines)
    for child in children:
        if child["escapes_workspace"]:
            res.warn("%s is a symlink resolving outside the workspace — not "
                     "inspected" % child["dirname"])

    gstate = git_state(workspace)
    if gstate["tracked"] and not gstate["own_root"]:
        res.warn("workspace is not the root of its own git repo (encloses under "
                 "%s) — git findings are suppressed" % gstate["enclosing_root"])

    dirty, other_dirty = [], []
    if gstate["tracked"] and gstate["own_root"]:
        paths = status_paths(workspace)
        if paths is None:
            res.warn("git status could not be read — dirty-path findings "
                     "(S1, S12) are suppressed")
        else:
            for path in paths:
                # Framework-owned scratch state (`.worktrees/`, `.lr-beings/`,
                # `.tmp/`) shows up here only when the standard ignore lines are
                # missing — which is exactly what S7 reports. It is neither
                # publishable (not in MANAGED_PATHS) nor the user's own content, so
                # it belongs in neither list: S12 would call it "yours, nothing will
                # touch it" and offer no fix, while the fix is S7's.
                if any(path == ln.strip("/") or path.startswith(ln.strip("/") + "/")
                       for ln in STANDARD_IGNORE_LINES):
                    continue
                (dirty if is_managed(path) else other_dirty).append(path)

    _, agents = discover_workspace(workspace)

    res.data["git"] = {k: v for k, v in gstate.items()}
    res.data["descriptors"] = {
        "lore_workspace": has_workspace_descriptor,
        "sharing": ws_fm.get("sharing") or None,
        "declared": declared,
        "gitignore_lines": ignore_lines,
    }
    res.data["children"] = children
    res.data["memory"] = memory_state(workspace)
    res.data["shortcuts"] = shortcut_inventory(workspace)
    res.data["agents"] = [a["name"] for a in agents]
    # Agent names grouped by their repo's directory name. No finding consumes
    # this since v37 (the old per-repo S15 did); it stays in the envelope
    # because the flat `agents` list cannot answer "which repo is this agent
    # from", which `register-repo`'s Agents-section rendering and any per-repo
    # report need.
    agents_by_repo = {}
    for agent in agents:
        repo_dir = os.path.basename(agent["repo"]) if agent["repo"] else "(no repo)"
        agents_by_repo.setdefault(repo_dir, []).append(agent["name"])
    res.data["agents_by_repo"] = agents_by_repo
    res.data["worktrees"] = worktree_inventory(workspace) \
        if gstate["tracked"] and gstate["own_root"] else []
    res.data["managed_paths"] = {
        "set": list(MANAGED_PATHS),
        "standard_ignore_lines": list(STANDARD_IGNORE_LINES),
        "dirty": dirty,
        "other_dirty": other_dirty,
    }
    res.data["findings"] = build_findings(res.data)
    return res


__all__ = [name for name in globals() if not name.startswith("__")]

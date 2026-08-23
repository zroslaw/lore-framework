"""Shared standard-library runtime for lr-core commands."""


import argparse
import datetime
import hashlib
import json
import os
import posixpath
import re
import subprocess
import sys
import time
import urllib.parse

# Bound every git subprocess. The Bash-tool timeout that bounds prose-driven
# pulls does not exist here, so the script owns its own backstop.
GIT_TIMEOUT_SEC = 60
PS_TIMEOUT_SEC = 10
# `run()` returns this when a command never executed — missing binary, broken
# PATH, or a timeout. Deliberately not an int: `subprocess` encodes death by
# signal as a *negative* returncode (SIGKILL -> -9, SIGHUP -> -1), so any
# integer sentinel would collide with a real outcome. -1 in particular used to
# mean both "never ran" and "killed by SIGHUP".
GIT_UNRUNNABLE = None
DEFAULT_PULL_TTL_SEC = 600
DEFAULT_STALE_DAYS = 180
# How far up the process tree to look for the Agent-Teams marker. The engine is
# typically the grandparent (script -> shell -> engine); the extra headroom
# covers wrapper scripts.
ANCESTOR_SCAN_DEPTH = 6
TEAMMATE_MARKER = "--agent-id"
# Flag-boundary match, not a substring test: `--agent-idle-timeout=30` in some
# unrelated ancestor must not read as the Agent-Teams marker.
TEAMMATE_MARKER_RE = re.compile(r"(?:^|\s)--agent-id(?:[\s=]|$)")
TITLE_MAX_CHARS = 120
LORE_FORMAT_VERSION = 1
SUMMARY_MAX_CHARS = 240
CONTEXT_WARN_TOKENS = 10000
CONTEXT_ERROR_TOKENS = 20000
LEGACY_CONTEXT_ERROR_TOKENS = 50000
BOOT_MAP_BUDGET = 8000
GROOMING_BUDGET = 30000
OVERSIZED_TOPIC_TOKENS = 5000
LORE_PARENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")

# Engine detection. Keys are program basenames as they appear in `ps args`;
# values are engine profile names (docs/engines/<name>.md).
#
# `cursor-agent` is listed but bare `cursor` deliberately is NOT: a Claude Code
# or Codex session started from Cursor's integrated terminal has
# `/Applications/Cursor.app/.../MacOS/Cursor` in its ancestry, and matching that
# would misreport the *host application* as the running engine. Only the CLI
# binary name is evidence about which engine is executing this procedure.
ENGINE_PROGRAMS = {
    "claude": "claude",
    "codex": "codex",
    "cursor-agent": "cursor",
}
# Engines shipped as scripts run under an interpreter, so the program field is
# the runtime and the engine name sits in a later argv token. Scanning later
# tokens is gated to these program names on purpose: an arbitrary command line
# may mention an engine's name in a path or argument without being that engine
# (a shell sourcing `~/.claude/shell-snapshots/...` is the common case).
ENGINE_RUNTIMES = frozenset((
    "node", "node.exe", "bun", "deno", "python", "python3", "electron",
))
# Containment fallback: which engine installs a plugin under which home dir.
# Checked against <framework-root> only — "this framework tree lives inside
# engine X's plugin store" is evidence; "engine X is installed on this machine"
# is not, and an ~/.codex existence test previously stood in for the latter.
ENGINE_HOME_DIRS = (
    ("~/.codex", "codex"),
    ("~/.cursor", "cursor"),
    ("~/.claude/plugins", "claude"),
)
DEFAULT_ENGINE = "claude"


# --------------------------------------------------------------------------
# Result plumbing
# --------------------------------------------------------------------------

class Result(object):
    """Accumulates the single JSON object a subcommand prints."""

    def __init__(self):
        self.ok = True
        self.data = {}
        self.warnings = []
        self.errors = []

    def warn(self, msg):
        self.warnings.append(msg)

    def fail(self, msg):
        """A determinate negative answer. Still exit 0 — the script functioned."""
        self.ok = False
        self.errors.append(msg)

    def emit(self):
        payload = {
            "ok": self.ok,
            "data": self.data,
            "warnings": self.warnings,
            "errors": self.errors,
        }
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=False) + "\n")
        return 0


def emit_fatal(msg):
    """The script could not complete: exit 2, caller falls back to prose.

    `fatal: true` is the in-band discriminator. Without it this payload is
    shape-identical to a determinate `ok:false` (exit 0, "no such agent"),
    whose documented handling is the opposite — stop the boot rather than take
    over by hand — leaving the exit code as the only thing telling them apart.
    """
    payload = {"ok": False, "fatal": True, "data": {},
               "warnings": [], "errors": [msg]}
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 2


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------

def read_text(path):
    try:
        # utf-8-sig, not utf-8: a leading BOM would otherwise survive into the
        # first line, so `lines[0] == "---"` fails and the whole frontmatter
        # block is silently read as absent (no version, no description).
        with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
            return fh.read()
    except (IOError, OSError):
        return None


def run(argv, timeout, env_extra=None, cwd=None):
    """Run a command. Returns (rc, stdout, stderr); rc is None if it never ran.

    Never raises — a missing binary or a hung remote is data for the caller,
    not an exception that aborts a boot.

    `rc is None` means the command did not execute at all. A *negative* rc means
    it executed and was killed by a signal (rc == -signum) — also not an answer
    about the world, which is why `git_answered()` below rejects both.
    """
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    try:
        proc = subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            env=env,
            cwd=cwd,
        )
        return (
            proc.returncode,
            proc.stdout.decode("utf-8", "replace"),
            proc.stderr.decode("utf-8", "replace"),
        )
    except subprocess.TimeoutExpired:
        return (GIT_UNRUNNABLE, "", "timed out after %ss" % timeout)
    except (OSError, ValueError) as exc:
        return (GIT_UNRUNNABLE, "", str(exc))


def git_answered(rc):
    """Did git actually run to completion and give us an answer about the world?

    False when it never executed (`rc is None`) and when it was killed by a
    signal (`rc < 0`: OOM killer, sandbox reaper, a `git` shim that suicides).
    Neither case is an answer, and both must stay distinguishable from git
    running and saying no.

    Apply this at EVERY git call site, not just the first one. Collapsing
    "could not run" into "ran and said no" lets a broken toolchain masquerade
    as a legitimate "not a repo" / "no origin remote" skip, under an exit code
    that promises the data is authoritative.
    """
    return rc is not None and rc >= 0


def _git_unrunnable(err, rc=None):
    """The uniform result for a git call that never gave an answer.

    A signal kill leaves stderr empty, so name the signal explicitly — a bare
    "unknown" tells a degraded-mode reader nothing they can act on.
    """
    reason = err.strip()[:200] if err and err.strip() else ""
    if not reason:
        reason = ("killed by signal %d" % -rc) if isinstance(rc, int) and rc < 0 \
            else "unknown"
    return {"status": "failed", "detail": "could not run git: %s" % reason}


def _git_error_line(text, default):
    """Pull the line that names the cause out of git's multi-line diagnostics.

    Not the last line: git prints the cause first and then an indented hint
    block, so `.split("\\n")[-1]` yields a fragment of the suggested remedy
    ("    git pull <remote> <branch>") and discards the actual reason ("You are
    not currently on a branch"). Both of those are ordinary states of the
    worktree/feature-branch convention, so this is the common case, not an
    exotic one. Prefer git's own `fatal:`/`error:` line, else the first
    non-indented, non-hint line.
    """
    lines = [ln.rstrip() for ln in (text or "").split("\n") if ln.strip()]
    for line in lines:
        low = line.strip().lower()
        if low.startswith("fatal:") or low.startswith("error:"):
            return line.strip()[:400]
    for line in lines:
        if not line.startswith((" ", "\t")) and not line.strip().lower().startswith("hint:"):
            return line.strip()[:400]
    return (lines[0].strip()[:400] if lines else default)


def git(repo, args, timeout=GIT_TIMEOUT_SEC, env_extra=None):
    """Run git against `repo` with -C. Never `cd` — the shell CWD is shared
    with the caller's other tools (docs/conventions.md § Tooling: CWD Safety).

    Every invocation is forced to the C locale: some outcomes are detected by
    reading git's human-readable stdout, which is translated under an NLS-
    enabled git in a non-English locale.
    """
    env = {"LC_ALL": "C", "LANGUAGE": "C"}
    if env_extra:
        env.update(env_extra)
    return run(["git", "-C", repo] + args, timeout, env_extra=env)


def parse_frontmatter(text):
    """Parse the minimal YAML subset the framework uses in descriptor files.

    Supports `key: value` (optionally quoted) and block sequences of the form
    `key:` followed by `  - item` lines. Not a general YAML parser and does not
    need to be — descriptor schemas are fixed by docs/conventions.md.
    """
    out = {}
    if not text:
        return out
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return out
    body = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        body.append(line)
    current_list_key = None
    for line in body:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = re.match(r"^\s+-\s+(.*)$", line)
        if item and current_list_key:
            out[current_list_key].append(_strip_item_comment(item.group(1)))
            continue
        kv = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not kv:
            continue
        key, val = kv.group(1), kv.group(2).strip()
        if val == "":
            # A repeated block key — a hand-merge artifact, or a conflict
            # resolved by keeping both sides — must not discard what the first
            # block declared. Keep accumulating into the existing list, which
            # is what `workspace-pull`'s awk parser already does; resetting
            # here made the two parsers disagree about the declared repo set,
            # and the Python side lost URLs silently.
            if not isinstance(out.get(key), list):
                out[key] = []
            current_list_key = key
        else:
            out[key] = _unquote(val)
            current_list_key = None
    return out


def _unquote(val):
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
        return val[1:-1]
    return val


def _strip_item_comment(raw):
    """A block-sequence item, with a trailing ` # comment` removed if unquoted.

    Mirrors `workspace-pull`'s awk parser exactly, and must keep mirroring it:
    that script parses the same `repos:` blocks to decide what to clone, so a
    rule only one side applies makes the scanner and the puller disagree about
    which repos are declared. Leaving the comment attached produced a URL whose
    derived directory name matched nothing on disk, so a repo that had been
    cloned correctly was reported missing (S6) forever.

    Quote-aware, like the awk side: a quoted value keeps its contents verbatim,
    since `#` inside quotes is data, not a comment.
    """
    value = raw.strip()
    if not value[:1] in ('"', "'"):
        value = re.sub(r"\s+#.*$", "", value)
    return _unquote(value.rstrip())


def resolve_framework_root(explicit):
    """Framework root = the directory containing VERSION.

    Defaults to this module's great-grandparent directory — the implementation
    lives at <framework-root>/scripts/lr_core/common.py.
    Boot Step 0 resolves the root for the *engine*; this is the script's own
    independent resolution so it can be run standalone.
    """
    if explicit:
        return os.path.abspath(explicit)
    return os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.realpath(__file__))))


def framework_version(root):
    text = read_text(os.path.join(root, "VERSION"))
    return text.strip() if text else None
def _repo_root_for(agent_dir):
    """agents/<name>/ -> repo root, verified by lore-repo.md."""
    candidate = os.path.dirname(os.path.dirname(os.path.abspath(agent_dir)))
    if os.path.isfile(os.path.join(candidate, "lore-repo.md")):
        return candidate
    return None

__all__ = [name for name in globals() if not name.startswith("__")]

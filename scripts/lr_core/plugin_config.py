"""Project-scope plugin configuration for a Lore workspace.

`/lr:workspace-init` writes two committed files so that a teammate who clones
this workspace gets the `lr` plugin without installing it by hand:

  .claude/settings.json   Claude Code — `extraKnownMarketplaces` + `enabledPlugins`
  .cursor/settings.json   Cursor      — `plugins.<marketplace>/<plugin>`

Codex has no equivalent. Repository-scoped marketplace registration plus a
per-repo enable is an open upstream request (openai/codex#18115), so this
module deliberately writes nothing for it and `cmd_workspace_plugin_config`
reports Codex as unsupported rather than silently covering two engines out of
three.

Manual fallback (Script Fallback Contract, `docs/conventions.md`): the payloads
are `CLAUDE_PAYLOAD` and `CURSOR_PAYLOAD` below; merge them into the two files
by hand, preserving every other key, then verify a re-run reports `unchanged`.

Three rules govern every write here, and each exists because of a way this
could go wrong:

1. **Merge, never rewrite.** Both files are the team's own — permissions,
   hooks, env. A whole-file write built from our payload would discard all of
   it. We touch only our own keys and re-serialise the rest verbatim.

2. **Never overwrite an existing value for our own keys.** A user who set
   `"lr@lore-framework": false` turned the plugin off on purpose. Converging
   that back to `true` would silently undo a deliberate choice, and the user
   would have no way to make it stick. We add when the key is absent and
   otherwise leave it, reporting the fact.

3. **Refuse to parse-and-clobber.** Cursor accepts JSONC (comments, trailing
   commas) and `json.loads` does not. A file we cannot parse is reported as an
   error and left untouched — losing a team's comments to a "converge" step is
   worse than not converging.
"""

from .common import *

import copy
import tempfile

MARKETPLACE_NAME = "lore-framework"
PLUGIN_NAME = "lr"

# Claude's marketplace source wants the fetchable git URL (`.git`); Cursor
# validates the same repo as a plain https:// remote. Same repository, two
# spellings, because the two engines validate the field differently.
GIT_URL = "https://github.com/zroslaw/lore-framework"
GIT_URL_FETCH = GIT_URL + ".git"

CLAUDE_SETTINGS_REL = os.path.join(".claude", "settings.json")
CURSOR_SETTINGS_REL = os.path.join(".cursor", "settings.json")

# `<plugin>@<marketplace>` on Claude, `<marketplace>/<plugin>` on Cursor. The
# order really is reversed between the two; do not "fix" one to match the other.
CLAUDE_PLUGIN_KEY = "%s@%s" % (PLUGIN_NAME, MARKETPLACE_NAME)
CURSOR_PLUGIN_KEY = "%s/%s" % (MARKETPLACE_NAME, PLUGIN_NAME)

CLAUDE_PAYLOAD = {
    "extraKnownMarketplaces": {
        MARKETPLACE_NAME: {
            "source": {"source": "git", "url": GIT_URL_FETCH},
            "autoUpdate": True,
        }
    },
    "enabledPlugins": {CLAUDE_PLUGIN_KEY: True},
}

# The self-contained form: `gitUrl` on the entry means a teammate needs no
# prior `plugin marketplace add`. No `gitRef` — omitting it tracks the repo's
# default branch, which is what every other freshness contract in the framework
# assumes.
CURSOR_PAYLOAD = {
    "plugins": {
        CURSOR_PLUGIN_KEY: {"enabled": True, "gitUrl": GIT_URL},
    }
}

ENGINE_FILES = (
    ("claude", CLAUDE_SETTINGS_REL),
    ("cursor", CURSOR_SETTINGS_REL),
)

# Engines with no project-scope plugin mechanism at all. Reported, never
# silently omitted: a summary that lists two engines reads as "all of them" to
# anyone who does not already know there are three.
UNSUPPORTED_ENGINES = ("codex",)


class PluginConfigError(Exception):
    """A settings file exists but cannot be safely merged into."""


def _merge_nested(doc, section, entries):
    """Add missing keys under `doc[section]`, preserving everything present.

    Returns (added, kept). `added` names keys this call created; `kept` names
    keys that were already there and were left exactly as found — rule 2. A
    `section` whose existing value is not an object is a structural conflict
    the caller must surface, not something to overwrite.
    """
    current = doc.get(section)
    if current is None:
        current = {}
        doc[section] = current
    if not isinstance(current, dict):
        raise PluginConfigError(
            "%s is present but is not an object" % section)

    added, kept = [], []
    for key, value in entries.items():
        if key in current:
            kept.append(key)
        else:
            current[key] = copy.deepcopy(value)
            added.append(key)
    return added, kept


def merge_claude(doc):
    """Merge the Claude payload into `doc` in place. Returns (added, kept)."""
    added, kept = [], []
    for section, entries in CLAUDE_PAYLOAD.items():
        a, k = _merge_nested(doc, section, entries)
        added.extend("%s.%s" % (section, key) for key in a)
        kept.extend("%s.%s" % (section, key) for key in k)
    return added, kept


def merge_cursor(doc):
    """Merge the Cursor payload into `doc` in place. Returns (added, kept)."""
    added, kept = [], []
    for section, entries in CURSOR_PAYLOAD.items():
        a, k = _merge_nested(doc, section, entries)
        added.extend("%s.%s" % (section, key) for key in a)
        kept.extend("%s.%s" % (section, key) for key in k)
    return added, kept


MERGERS = {"claude": merge_claude, "cursor": merge_cursor}


def read_settings(path):
    """Read a settings file. Returns (doc, existed).

    A missing file yields an empty document. A file that cannot be read, is not
    valid UTF-8, is not valid JSON, or whose top level is not an object raises
    — rule 3. The caller turns that into a reported error and leaves the file
    alone.
    """
    if not os.path.isfile(path):
        return {}, False
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = handle.read()
    except OSError as exc:
        raise PluginConfigError("cannot read: %s" % exc)
    except UnicodeDecodeError as exc:
        # Not an OSError — it is a ValueError. Letting it escape would crash
        # `workspace-plugin-config` out of its JSON envelope, and take every
        # other finding in `workspace-scan` down with it, because one settings
        # file had a stray byte.
        raise PluginConfigError("not valid UTF-8: %s" % exc)
    if not raw.strip():
        return {}, True
    try:
        doc = json.loads(raw)
    except ValueError as exc:
        raise PluginConfigError(
            "not valid JSON (comments and trailing commas are not "
            "supported here): %s" % exc)
    if not isinstance(doc, dict):
        raise PluginConfigError("top level is not an object")
    return doc, True


def render_settings(doc):
    """Serialise a settings document. Two-space indent, one trailing newline."""
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def plan_file(workspace, engine, rel_path):
    """Compute the write for one engine without touching the filesystem.

    Returns a result row. `action` is one of `created`, `updated`,
    `unchanged`, or `error`.

    **A file is rewritten only when a key was actually added.** An existing
    file that already carries our keys is left byte-for-byte alone, even when
    its formatting differs from what `render_settings` would produce. The
    alternative — normalising the whole document to our layout — would put a
    whitespace-only diff through a team's shared settings file on the first
    converge, for no behavioural gain. Rule 1 says touch our own keys; that
    includes not touching the bytes around them.
    """
    path = os.path.join(workspace, rel_path)
    row = {"engine": engine, "path": rel_path, "action": None,
           "added": [], "kept": [], "error": None}
    try:
        doc, existed = read_settings(path)
    except PluginConfigError as exc:
        row["action"] = "error"
        row["error"] = str(exc)
        return row, None

    try:
        added, kept = MERGERS[engine](doc)
    except PluginConfigError as exc:
        row["action"] = "error"
        row["error"] = str(exc)
        return row, None

    row["added"] = added
    row["kept"] = kept
    if not existed:
        row["action"] = "created"
    elif added:
        row["action"] = "updated"
    else:
        row["action"] = "unchanged"
        return row, None
    return row, render_settings(doc)


def write_atomic(path, text):
    """Replace `path` with `text` atomically, or leave it exactly as it was.

    `open(path, "w")` truncates the target the instant it succeeds, *before*
    anything is written. A failure between those two moments — ENOSPC, a quota,
    a killed process, a lost machine — leaves a valid settings file replaced by
    a few bytes of garbage, while the caller reports the same tidy `error` row
    it reports for a refusal that never touched the file at all. That is the
    one outcome this module exists to prevent, so the write goes to a sibling
    temporary file and lands with `os.replace`, which is atomic on POSIX and
    Windows. A failed write leaves only the temp file behind, and we remove it.
    """
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    fd, tmp = tempfile.mkstemp(prefix=".lr-", suffix=".tmp",
                               dir=parent or ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def apply_plugin_config(workspace, dry_run=False):
    """Write both project-scope plugin settings files. Idempotent.

    Never raises for a per-file problem: an unparseable or structurally
    conflicting file becomes an `error` row and the other engine still
    converges. A partial success is a reported result, not an exception.
    """
    rows, errors = [], []
    for engine, rel_path in ENGINE_FILES:
        row, rendered = plan_file(workspace, engine, rel_path)
        if row["action"] == "error":
            errors.append("%s: %s" % (rel_path, row["error"]))
        elif rendered is not None and row["action"] != "unchanged" and not dry_run:
            path = os.path.join(workspace, rel_path)
            try:
                write_atomic(path, rendered)
            except OSError as exc:
                row["action"] = "error"
                row["error"] = "cannot write: %s" % exc
                errors.append("%s: %s" % (rel_path, row["error"]))
        rows.append(row)
    return {"files": rows,
            "unsupported_engines": list(UNSUPPORTED_ENGINES),
            "dry_run": bool(dry_run)}, errors


def check_plugin_config(workspace):
    """Report which project-scope plugin files are missing or unresolvable.

    Pure inspection for `workspace-scan` (finding S18).

    **This asks the merger itself**, on a throwaway copy, rather than
    re-implementing the "is it configured?" test. The two must agree: a file
    the merger refuses but this function calls merely `missing` produces an
    S18 row saying "run workspace-init", forever, on a file workspace-init can
    never converge. Deriving both answers from one code path makes that
    disagreement impossible rather than merely unlikely.

    Three buckets:
      missing      — a key we would add is absent; `workspace-init` fixes it.
      unresolvable — the file cannot be read or cannot be safely merged
                     (bad encoding, invalid JSON, or a key of a conflicting
                     type). Needs a human; `workspace-init` will not touch it.
      disabled     — configured, but explicitly turned off. A deliberate
                     choice, reported as context and never as drift.
    """
    missing, unresolvable, disabled = [], [], []
    for engine, rel_path in ENGINE_FILES:
        path = os.path.join(workspace, rel_path)
        try:
            doc, existed = read_settings(path)
        except PluginConfigError:
            unresolvable.append(rel_path)
            continue
        if not existed:
            missing.append(rel_path)
            continue
        try:
            added, _kept = MERGERS[engine](copy.deepcopy(doc))
        except PluginConfigError:
            unresolvable.append(rel_path)
            continue
        if added:
            missing.append(rel_path)
        elif _is_disabled(engine, doc):
            disabled.append(rel_path)
    return {"missing": missing, "unresolvable": unresolvable,
            "disabled": disabled}


def _is_disabled(engine, doc):
    """True when the plugin is configured but explicitly switched off.

    Only reached for a document the merger found complete, so every lookup
    below is known to be present and of the right type.
    """
    if engine == "claude":
        return doc["enabledPlugins"].get(CLAUDE_PLUGIN_KEY) is False
    entry = doc["plugins"].get(CURSOR_PLUGIN_KEY)
    return isinstance(entry, dict) and entry.get("enabled") is False


def cmd_workspace_plugin_config(args, res):
    """CLI entry point. Resolve `<workspace>`, then delegate to
    `apply_plugin_config` and adapt its `(data, errors)` return onto `res`.

    A per-file problem is `res.fail` — a determinate negative answer, exit 0 —
    not a fatal. The caller can still act on the engine that did converge, and
    a fatal here would send it into the manual fallback for a situation the
    result already describes precisely.
    """
    workspace = os.path.abspath(os.path.expanduser(args.workspace))
    if not os.path.isdir(workspace):
        res.fail("workspace not found: %s" % workspace)
        res.data = {"workspace": workspace, "applicable": False}
        return res

    data, errors = apply_plugin_config(workspace, dry_run=args.dry_run)
    data["workspace"] = workspace
    res.data = data
    for err in errors:
        res.fail(err)
    return res


__all__ = [name for name in globals() if not name.startswith("__")]

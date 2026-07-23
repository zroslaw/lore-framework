#!/usr/bin/env python3
"""lrb — the Being Keeper: CLI + deterministic daemon for Lore Beings.

Part of the lore-framework plugin (`lr`). Pure Python 3 standard library, no
pip install, one file — same sanctioned-exception class as
`scripts/wait-server.py` (see docs/beings.md and the design draft this
implements, `lore-framework-dev/agents/lore-architect/workdir/draft-lore-beings.md`).

A "being" is an ordinary lore agent plus a `being.md` descriptor
(`agents/<name>/being.md`) declaring existential tasks on a cron schedule.
The Keeper is the deterministic supervisor that spawns headless engine
sessions on schedule, enforces budget (daily-USD spawn gate + per-task
wall-clock kill), and tracks state — it never reasons, never judges; that's
the being's job once spawned. See `agent-being-consciousness-substrate-split.md`.

Machine home: $LRB_HOME, default ~/.lore-beings/ (config.json + this script's
installed copy). Workspace state: <workspace>/.lr-beings/ (state.json, outbox/,
logs/) — gitignored, per-workspace.

CLI:
  lrb install                          copy self to $LRB_HOME, write launchd plist
                                        (--launchd to load it)
  lrb status [--json]                  beings, last runs, spend, failures
  lrb validate                         static config/descriptor checks
  lrb logs BEING                       ledger/log pointers for one being
  lrb pause / lrb resume                all-beings scheduling switch (dead-man file)
  lrb stop                             SIGTERM running sessions + pause
  lrb engines add|remove|list          explicit engine configuration (§7 of draft)
  lrb workspaces add|remove|list       workspace registry
  lrb schedule --agent A --at ISO [--timeout-minutes N] "prompt"   outbox one-shot
  lrb daemon [--once]                  run the tick loop (what launchd/testing invoke)

Floor: Python 3.9. No `match`, no `X | Y` annotations.
"""

import argparse
import json
import math
import os
import re
import shutil
import shlex
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, date
from xml.sax.saxutils import escape as xml_escape

if sys.version_info < (3, 9):
    sys.exit("lrb: requires Python 3.9+, found %s" % sys.version.split()[0])

VERSION = "0.1.0"
# Engine kinds — the per-engine invocation + result contract (see docs/beings.md):
#   claude: `CMD -p PROMPT --output-format json --model M` → one JSON object on
#           stdout carrying total_cost_usd/is_error; cost comes from the result.
#   codex:  `CMD exec --json --skip-git-repo-check -m M PROMPT` → JSONL events on
#           stdout ending in turn.completed (usage tokens, NO usd) or turn.failed;
#           cost comes from the engine's configured session-cost-usd flat rate,
#           charged per finished session — without it the daily-usd spawn gate
#           would silently never trip for codex beings (prompt-theater trap).
#   cursor: `CMD -p PROMPT --output-format json --model M --plugin-dir D
#           --workspace W [--force --sandbox disabled]` → one JSON object on
#           stdout (claude-shaped: result/total_cost_usd/is_error/usage); real
#           cursor-agent responses have been observed to omit total_cost_usd
#           entirely (token usage only), so session-cost-usd is REQUIRED for
#           cursor too (same prompt-theater trap as codex) — cost falls back
#           to it whenever total_cost_usd is absent, and to total_cost_usd
#           when a future cursor-agent version does report it. plugin_dir is
#           also required at engines add (Lore skills).
ENGINE_KINDS = ("claude", "codex", "cursor")
LABEL = "com.lore-beings.keeper"
TICK_SECONDS = 30
DEFAULT_CONCURRENCY_CAP = 3
DEFAULT_SCHEDULE_TIMEOUT_MINUTES = 30
MAX_TIMEOUT_MINUTES = 24 * 60
OUTBOX_HORIZON = timedelta(hours=24)
KILL_GRACE_SECONDS = 60
# An entry whose PID identity has been unverifiable (ps blocked/sandboxed —
# see _pid_matches_entry) for longer than this, past its own timeout, is
# force-reaped rather than left running forever: without this, a re-adopted
# entry that can never be identity-confirmed permanently leaks its
# concurrency slot (never billed, never logged, `lrb status` shows it as
# running indefinitely). Set far past MAX_TIMEOUT_MINUTES (24h) + grace so it
# never fires for a session that is genuinely still running normally.
UNVERIFIABLE_REAP_AFTER_HOURS = 48
LATE_THRESHOLD = timedelta(minutes=5)
SAFE_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def lrb_home():
    return os.path.abspath(os.environ.get("LRB_HOME") or os.path.expanduser("~/.lore-beings"))


def launchagents_dir():
    """Overridable via $LRB_LAUNCHAGENTS_DIR so `install` is fully sandboxable
    for tests/dev iteration — never touches the real machine's LaunchAgents
    unless run with the default env, on a real shell."""
    return os.path.abspath(os.environ.get("LRB_LAUNCHAGENTS_DIR") or os.path.expanduser("~/Library/LaunchAgents"))


def die(msg, code=1):
    print("lrb: %s" % msg, file=sys.stderr)
    sys.exit(code)


# ---- atomic file helpers -----------------------------------------------------


def atomic_write_text(path, text):
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.rename(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def atomic_write_json(path, obj):
    atomic_write_text(path, json.dumps(obj, indent=2, sort_keys=True) + "\n")


def read_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


# ---- being.md frontmatter parsing (restricted YAML subset) ------------------
#
# Handles exactly the being.md shape (§3 of the draft): flat scalar keys, plus
# one list-of-mappings for existential-tasks. Not a general YAML parser —
# deliberately bespoke for a fixed 5-key schema, matching the framework's
# "no pip" rule.


def _strip_trailing_comment(s):
    """Strip a trailing ' # comment' from a YAML-ish value/line, respecting
    quotes (a '#' inside a quoted string is not a comment). being.md examples
    in the draft and docs/beings.md use inline comments on value lines, so
    this isn't optional."""
    in_quote = None
    for i, ch in enumerate(s):
        if in_quote:
            if ch == in_quote:
                in_quote = None
        elif ch in ("'", '"'):
            in_quote = ch
        elif ch == "#" and (i == 0 or s[i - 1].isspace()):
            return s[:i].rstrip()
    return s


def _parse_scalar(s):
    s = _strip_trailing_comment(s.strip()).strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def _indent(line):
    return len(line) - len(line.lstrip(" "))


def parse_yaml_frontmatter(text):
    lines = text.split("\n")
    result = {}
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if _indent(line) != 0:
            raise ValueError("unexpected indent at top level: %r" % line)
        if ":" not in line:
            raise ValueError("malformed frontmatter line: %r" % line)
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = _strip_trailing_comment(rest.strip()).strip()
        i += 1
        if rest:
            result[key] = _parse_scalar(rest)
            continue
        # possibly a list-of-mappings follows
        j = i
        while j < n and not lines[j].strip():
            j += 1
        if j < n and _indent(lines[j]) > 0 and lines[j].lstrip().startswith("- "):
            base_indent = _indent(lines[j])
            items = []
            i = j
            while i < n:
                line2 = lines[i]
                if not line2.strip():
                    i += 1
                    continue
                ind2 = _indent(line2)
                if ind2 < base_indent:
                    break
                if not (ind2 == base_indent and line2.lstrip().startswith("- ")):
                    break
                item = {}
                first = line2.lstrip()[2:]
                if ":" in first:
                    k2, _, v2 = first.partition(":")
                    item[k2.strip()] = _parse_scalar(v2.strip())
                item_indent = base_indent + 2
                i += 1
                while i < n:
                    line3 = lines[i]
                    if not line3.strip():
                        i += 1
                        continue
                    ind3 = _indent(line3)
                    if ind3 < item_indent:
                        break
                    if ind3 == base_indent and line3.lstrip().startswith("- "):
                        break
                    if ":" in line3:
                        k3, _, v3 = line3.strip().partition(":")
                        item[k3.strip()] = _parse_scalar(v3.strip())
                    i += 1
                items.append(item)
            result[key] = items
        else:
            result[key] = None
    return result


REQUIRED_BEING_KEYS = ("description", "engine", "model", "daily-usd", "existential-tasks")
REQUIRED_TASK_KEYS = ("name", "schedule", "prompt", "timeout-minutes")


def require_safe_slug(value, label):
    if not isinstance(value, str) or not SAFE_SLUG_RE.match(value):
        raise ValueError("%s must be a safe slug (letters, digits, dot, underscore, hyphen; max 64): %r"
                         % (label, value))
    return value


def require_finite_nonnegative_float(value, label):
    try:
        f = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be a number" % label)
    if not math.isfinite(f) or f < 0:
        raise ValueError("%s must be a finite nonnegative number" % label)
    return f


def require_plugin_dir(path, label="--plugin-dir"):
    """Validate a lore-framework checkout path for cursor-kind engines."""
    if not path or not isinstance(path, str):
        raise ValueError("%s must be a non-empty path" % label)
    abs_path = os.path.abspath(path)
    if not os.path.isdir(abs_path):
        raise ValueError("%s path does not exist: %s" % (label, abs_path))
    if not os.path.isfile(os.path.join(abs_path, "VERSION")):
        raise ValueError("%s path is not a lore-framework root (missing VERSION): %s"
                         % (label, abs_path))
    return abs_path


def require_timeout_minutes(value, label="timeout-minutes"):
    if isinstance(value, bool):
        raise ValueError("%s must be an integer" % label)
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be an integer" % label)
    if str(value).strip() != str(n) and not isinstance(value, int):
        raise ValueError("%s must be an integer" % label)
    if n <= 0 or n > MAX_TIMEOUT_MINUTES:
        raise ValueError("%s must be between 1 and %d" % (label, MAX_TIMEOUT_MINUTES))
    return n


def agent_relative_path(agent_dir, rel_path):
    """Resolve a being-owned path and prove it stays inside the agent dir.
    `being.md` is team-shared config that drives file reads; a prompt path
    must not escape to sibling repos or arbitrary machine files."""
    rel = str(rel_path)
    if os.path.isabs(rel):
        raise ValueError("path must be relative to the agent directory: %r" % rel)
    base = os.path.realpath(agent_dir)
    target = os.path.realpath(os.path.join(base, rel))
    if target != base and not target.startswith(base + os.sep):
        raise ValueError("path escapes the agent directory: %r" % rel)
    return target


def load_being_file(path):
    """Parse a being.md file. Raises ValueError with a human-readable reason
    on any schema violation — callers surface this as a per-being config error,
    never a guess (§6 of the draft)."""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if not text.startswith("---"):
        raise ValueError("being.md missing YAML frontmatter")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("being.md frontmatter not closed")
    fm = parse_yaml_frontmatter(parts[1])
    body = parts[2].lstrip("\n")
    unknown = [k for k in fm if k not in REQUIRED_BEING_KEYS]
    if unknown:
        raise ValueError("being.md has unexpected keys: %s" % ", ".join(sorted(unknown)))
    missing = [k for k in REQUIRED_BEING_KEYS if k not in fm]
    if missing:
        raise ValueError("being.md missing keys: %s" % ", ".join(missing))
    tasks = fm["existential-tasks"]
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("existential-tasks must be a non-empty list")
    for t in tasks:
        if not isinstance(t, dict):
            raise ValueError("existential-tasks entries must be mappings")
        tmissing = [k for k in REQUIRED_TASK_KEYS if k not in t]
        if tmissing:
            raise ValueError("existential task %r missing keys: %s" % (t.get("name"), ", ".join(tmissing)))
        tunknown = [k for k in t if k not in REQUIRED_TASK_KEYS]
        if tunknown:
            raise ValueError("existential task %r has unexpected keys: %s" % (
                t.get("name"), ", ".join(sorted(tunknown))))
        require_safe_slug(t["name"], "existential task name")
        try:
            t["timeout-minutes"] = require_timeout_minutes(t["timeout-minutes"])
        except ValueError as e:
            raise ValueError("existential task %r: %s" % (t.get("name"), e))
        try:
            occurrences = _cron_occurrences_in_day(str(t["schedule"]))
        except ValueError as e:
            raise ValueError("existential task %r: bad schedule %r: %s" % (t.get("name"), t["schedule"], e))
        if occurrences > 1:
            raise ValueError(
                "existential task %r: schedule %r fires %d times/day — existential tasks are "
                "once-daily only (same-day dedup means only the first would ever run); use "
                "separate tasks or self-schedule extra runs via the outbox instead"
                % (t.get("name"), t["schedule"], occurrences)
            )
    daily_usd = require_finite_nonnegative_float(fm["daily-usd"], "daily-usd")
    return {
        "description": str(fm["description"]),
        "engine": str(fm["engine"]),
        "model": str(fm["model"]),
        "daily_usd": daily_usd,
        "existential_tasks": tasks,
        "body": body,
    }


# ---- cron (minute hour day month weekday, machine-local) --------------------


def _cron_field_matches(field, value, lo, hi):
    for part in field.split(","):
        part = part.strip()
        if not part:
            raise ValueError("empty cron field part")
        step = 1
        base = part
        if "/" in part:
            base, step_s = part.split("/", 1)
            step = int(step_s)
            if step <= 0:
                raise ValueError("cron step must be positive: %r" % part)
        if base == "*":
            rng_lo, rng_hi = lo, hi
        elif "-" in base:
            a, b = base.split("-")
            rng_lo, rng_hi = int(a), int(b)
        else:
            rng_lo = rng_hi = int(base)
        if rng_lo < lo or rng_hi > hi:
            raise ValueError("cron value out of range %d..%d: %r" % (lo, hi, part))
        if rng_lo > rng_hi:
            raise ValueError("cron range start greater than end: %r" % part)
        if rng_lo <= value <= rng_hi and (value - rng_lo) % step == 0:
            return True
    return False


def cron_matches(cron_expr, dt):
    """dt: a naive datetime in machine-local time. day-of-month and
    day-of-week are AND'ed (not cron's OR-when-both-restricted nuance) —
    an accepted MVP simplification; every being.md example in the draft uses
    '* *' for both."""
    fields = cron_expr.split()
    if len(fields) != 5:
        raise ValueError("bad cron expression: %r" % cron_expr)
    minute, hour, day, month, weekday = fields
    if not _cron_field_matches(minute, dt.minute, 0, 59):
        return False
    if not _cron_field_matches(hour, dt.hour, 0, 23):
        return False
    if not _cron_field_matches(day, dt.day, 1, 31):
        return False
    if not _cron_field_matches(month, dt.month, 1, 12):
        return False
    cron_wd = (dt.weekday() + 1) % 7  # python Mon=0..Sun=6 -> cron Sun=0..Sat=6
    if not _cron_field_matches(weekday, cron_wd, 0, 6):
        return False
    return True


def next_occurrence_for_date(cron_expr, d):
    """First datetime on date `d` matching cron_expr, or None if it doesn't
    fire that day. O(1440) worst case — trivial at this scale."""
    for minute_of_day in range(24 * 60):
        hh, mm = divmod(minute_of_day, 60)
        candidate = datetime(d.year, d.month, d.day, hh, mm)
        if cron_matches(cron_expr, candidate):
            return candidate
    return None


def _cron_occurrences_in_day(cron_expr):
    """How many times/day cron_expr fires, counting ONLY the minute+hour
    fields — day/month/weekday only gate WHICH days it fires (e.g. "once a
    year on Jan 1"), not how many times within a day it fires on, so they
    must not be checked against a specific sample date (a schedule that
    legitimately never fires today, like an annual cron, is not a config
    error). Still validates all 5 fields' syntax — a bad day/month/weekday
    field must remain a config error even though it doesn't affect the
    count. Raises ValueError on any syntactically bad field."""
    fields = cron_expr.split()
    if len(fields) != 5:
        raise ValueError("bad cron expression: %r" % cron_expr)
    minute, hour, day, month, weekday = fields
    # Probe every value in each field's legal range, not just one sample —
    # _cron_field_matches short-circuits on the first comma-part that
    # matches, so a single-value probe can miss a garbage LATER part (e.g.
    # "1,junk" probed only at value=1 matches "1" and never reaches "junk").
    # Iterating the full range guarantees some value falls through every
    # part that isn't "*" and forces it to actually parse.
    for field, lo, hi in ((day, 1, 31), (month, 1, 12), (weekday, 0, 6)):
        for v in range(lo, hi + 1):
            _cron_field_matches(field, v, lo, hi)
    count = 0
    for hh in range(24):
        for mm in range(60):
            if _cron_field_matches(minute, mm, 0, 59) and _cron_field_matches(hour, hh, 0, 23):
                count += 1
    if count == 0:
        raise ValueError("cron minute/hour fields never fire")
    return count


def parse_naive_iso_datetime(value, label):
    try:
        dt = datetime.fromisoformat(value)
    except Exception:
        raise ValueError("%s must be an ISO datetime, e.g. 2026-07-19T15:00:00" % label)
    if dt.tzinfo is not None and dt.utcoffset() is not None:
        raise ValueError("%s must be machine-local time without a timezone suffix" % label)
    return dt


# ---- config -------------------------------------------------------------


def config_path():
    return os.path.join(lrb_home(), "config.json")


def load_config():
    return read_json(config_path(), {"workspaces": [], "engines": {}})


def save_config(cfg):
    atomic_write_json(config_path(), cfg)


def paused_path():
    return os.path.join(lrb_home(), "paused")


def is_paused():
    return os.path.exists(paused_path())


# ---- being discovery ------------------------------------------------------
#
# Mirrors agent-boot.md's discovery rule: top-level dirs of the workspace
# root containing lore-repo.md; agents/*/being.md within. No nesting.


def discover_beings(workspace):
    """Returns (beings: {being_id: being_dict}, errors: {being_id: str})."""
    beings, errors = {}, {}
    try:
        entries = sorted(os.listdir(workspace))
    except OSError:
        return beings, errors
    for entry in entries:
        repo_dir = os.path.join(workspace, entry)
        if not os.path.isdir(repo_dir) or entry.startswith("."):
            continue
        if not os.path.isfile(os.path.join(repo_dir, "lore-repo.md")):
            continue
        agents_dir = os.path.join(repo_dir, "agents")
        if not os.path.isdir(agents_dir):
            continue
        for agent_name in sorted(os.listdir(agents_dir)):
            being_path = os.path.join(agents_dir, agent_name, "being.md")
            if not os.path.isfile(being_path):
                continue
            being_id = "%s/%s" % (entry, agent_name)
            try:
                being = load_being_file(being_path)
            except Exception as e:
                errors[being_id] = str(e)
                continue
            agent_dir = os.path.join(agents_dir, agent_name)
            try:
                for task in being["existential_tasks"]:
                    agent_relative_path(agent_dir, task["prompt"])
            except ValueError as e:
                errors[being_id] = str(e)
                continue
            being["_repo"] = repo_dir
            being["_agent_dir"] = agent_dir
            being["_agent_name"] = agent_name
            being["_path"] = being_path
            beings[being_id] = being
    return beings, errors


# ---- workspace state (state.json) -----------------------------------------


def ws_dir(workspace):
    return os.path.join(workspace, ".lr-beings")


def state_path(workspace):
    return os.path.join(ws_dir(workspace), "state.json")


def default_state():
    return {"date": date.today().isoformat(), "beings": {}}


def load_state(workspace):
    return read_json(state_path(workspace), default_state())


def save_state(workspace, state):
    atomic_write_json(state_path(workspace), state)


def being_state(state, being_id):
    return state["beings"].setdefault(being_id, {"spent_today_usd": 0.0, "running": [], "last_runs": {}})


def ensure_ws_dirs(workspace):
    for sub in ("outbox", os.path.join("outbox", "accepted"), os.path.join("outbox", "rejected"),
                os.path.join("outbox", "done"), "logs"):
        os.makedirs(os.path.join(ws_dir(workspace), sub), exist_ok=True)


def ledger_path(workspace, being_id):
    safe = being_id.replace("/", "__")
    return os.path.join(ws_dir(workspace), "logs", safe, "ledger.jsonl")


def read_ledger_entries(workspace, being_id):
    p = ledger_path(workspace, being_id)
    try:
        with open(p, "r", encoding="utf-8") as f:
            entries = []
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    entries.append({"outcome": "unparseable-ledger-line", "raw": line})
            return entries
    except OSError:
        return []


def ledger_append(workspace, being_id, entry):
    p = ledger_path(workspace, being_id)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")


def log_path_for(workspace, being_id, task_name, when):
    safe = being_id.replace("/", "__")
    fn = "%s.%s.log" % (require_safe_slug(task_name, "task name"), when.strftime("%Y%m%dT%H%M%S"))
    return os.path.join(ws_dir(workspace), "logs", safe, fn)


# ---- outbox -----------------------------------------------------------------


def outbox_new_dir(workspace):
    return os.path.join(ws_dir(workspace), "outbox")


def outbox_accepted_dir(workspace):
    return os.path.join(ws_dir(workspace), "outbox", "accepted")


def outbox_rejected_dir(workspace):
    return os.path.join(ws_dir(workspace), "outbox", "rejected")


def outbox_done_dir(workspace):
    return os.path.join(ws_dir(workspace), "outbox", "done")


def write_outbox_request(workspace, being_id, at_iso, timeout_minutes, prompt):
    ensure_ws_dirs(workspace)
    req = {
        "being": being_id,
        "at": at_iso,
        "timeout_minutes": timeout_minutes,
        "prompt": prompt,
        "requested_at": datetime.now().isoformat(timespec="seconds"),
    }
    fn = "%s.%d.%s.json" % (being_id.replace("/", "__"), int(time.time()), os.urandom(3).hex())
    atomic_write_json(os.path.join(outbox_new_dir(workspace), fn), req)
    return fn


def process_outbox(workspace, beings, state, now):
    """Validate new outbox requests -> accepted/ or rejected/. New files only
    (accepted/done are handled by the spawn step)."""
    new_dir = outbox_new_dir(workspace)
    try:
        names = sorted(os.listdir(new_dir))
    except OSError:
        return
    for fn in names:
        if fn.startswith(".") or not fn.endswith(".json"):
            continue
        src = os.path.join(new_dir, fn)
        try:
            with open(src, "r", encoding="utf-8") as f:
                req = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(req, dict):
            req = {"rejected_reason": "request must be a JSON object"}
            atomic_write_json(src, req)
            dest = os.path.join(outbox_rejected_dir(workspace), fn)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            try:
                os.rename(src, dest)
            except OSError:
                pass
            continue
        being_id = req.get("being")
        reason = None
        if being_id not in beings:
            reason = "unknown being (or config error): %r" % being_id
        else:
            try:
                at_dt = parse_naive_iso_datetime(req["at"], "'at'")
                timeout_minutes = require_timeout_minutes(
                    req.get("timeout_minutes", DEFAULT_SCHEDULE_TIMEOUT_MINUTES),
                    "timeout_minutes",
                )
                if not isinstance(req.get("prompt"), str) or not req.get("prompt"):
                    raise ValueError("prompt must be a non-empty string")
            except ValueError as e:
                at_dt = None
                reason = str(e)
            if at_dt is None:
                reason = reason or "invalid 'at' timestamp"
            elif at_dt < now - timedelta(minutes=5):
                reason = "'at' is in the past"
            elif at_dt > now + OUTBOX_HORIZON:
                reason = "'at' is beyond the 24h scheduling horizon"
            else:
                bstate = being_state(state, being_id)
                being = beings[being_id]
                if bstate["spent_today_usd"] >= being["daily_usd"]:
                    reason = "daily budget already exhausted"
                else:
                    req["timeout_minutes"] = timeout_minutes
        if reason is None:
            # Persist the normalized timeout_minutes before accepting:
            # accepted/ files ARE the pending schedule (rebuilt-never-stored
            # applies to state.json, not here), so the file must carry the
            # value the spawn will use even when the request omitted it.
            atomic_write_json(src, req)
            dest = os.path.join(outbox_accepted_dir(workspace), fn)
        else:
            req["rejected_reason"] = reason
            atomic_write_json(src, req)
            dest = os.path.join(outbox_rejected_dir(workspace), fn)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        try:
            os.rename(src, dest)
        except OSError:
            pass


# ---- spawning ---------------------------------------------------------------


def _parse_result_json(content):
    """Extract the engine's result JSON from raw stdout content. Tries a
    whole-content parse first (the fast/expected path — exactly one JSON
    object per `--output-format json`), then falls back to the last
    parseable JSON object among the lines, in case anything else still made
    it onto stdout despite stderr now being routed to a sibling file
    (belt-and-braces alongside that separation — see spawn_session)."""
    content = content.strip()
    if not content:
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    for line in reversed(content.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return None


def _descendant_pids(root_pid):
    """All PIDs whose ancestry traces back to root_pid, via a full-system
    ppid-chain walk — NOT process-group membership. Real finding (B3,
    2026-07-20): cursor-agent's sandboxed tool execution runs each shell
    command inside a freshly setsid'd session (a NEW process group), which
    escapes killpg(pgid-of-the-direct-child) entirely — the direct session
    dies on SIGKILL, but its real Bash/tool grandchildren are silently
    orphaned and keep running. Walking by ppid instead of pgid still finds
    them, since a setsid() call changes the process's session/group but
    never its parent. Returns [] (not None) on ps failure/sandbox block —
    callers already have killpg as a first line of defense and must not
    treat "couldn't enumerate descendants" as fatal."""
    try:
        r = subprocess.run(["ps", "-eo", "pid,ppid"], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if r.returncode != 0:
        return []
    children_of = {}
    for line in r.stdout.splitlines()[1:]:
        parts = line.split()
        if len(parts) != 2:
            continue
        try:
            pid, ppid = int(parts[0]), int(parts[1])
        except ValueError:
            continue
        children_of.setdefault(ppid, []).append(pid)
    descendants = []
    frontier = [root_pid]
    while frontier:
        current = frontier.pop()
        for child in children_of.get(current, []):
            descendants.append(child)
            frontier.append(child)
    return descendants


def _ps_field(pid, field):
    """One ps field for one PID. Returns the stripped value, False for a
    dead/invisible PID (nonzero exit or empty output), None when the
    OS/sandbox refuses to run ps at all."""
    try:
        r = subprocess.run(["ps", "-p", str(pid), "-o", field + "="],
                            capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return False
    out = r.stdout.strip()
    return out if out else False


def _pid_identity(pid):
    """Return process identity from ps, False for a dead PID, None when the
    OS/sandbox refuses identity inspection.

    lstart and command are fetched with two SEPARATE ps calls, never one
    call with two -o fields: macOS ps joins multiple -o fields onto one
    line, so a combined query embeds the command line inside "start" — and
    the command string of a live process is NOT stable (macOS framework
    Python re-execs bin/python3.x into Python.app/…/MacOS/Python moments
    after spawn, the same effect _daemon_status documents), which made the
    start-equality check misread a genuinely alive re-adopted session as a
    PID-reuse mismatch and reap it while it was still running. "start" must
    be pure start-time to work as an identity anchor."""
    start = _ps_field(pid, "lstart")
    if start is None or start is False:
        return start
    command = _ps_field(pid, "command")
    if command is None:
        return None
    if command is False:
        return False  # died between the two calls: dead either way
    return {"start": start, "command": command}


def _pid_matches_entry(pid, entry):
    """Best-effort identity check before signaling a PID this run didn't
    spawn itself (re-adopted from state.json after a restart, or read by
    `lrb stop`): after a reboot the OS can and does reuse PIDs, so a bare
    os.kill(pid, 0) 'is it alive' check can say yes for a completely
    unrelated same-user process. Guards SIGTERM/SIGKILL against that.

    Returns True for a confirmed command + process-start match, False for a
    confirmed mismatch/dead PID, and None when identity cannot be checked
    (for example Codex's sandbox blocks `ps` with EPERM, or old state lacks
    the recorded start marker). Unknown is not the same as dead: callers keep
    the entry visible but refuse to signal it.

    NOT used for matching a process against its own `sys.executable` (see
    daemon_info/_daemon_status) — that purely-cosmetic check skips identity
    verification rather than risk a false "not detected"."""
    ident = _pid_identity(pid)
    if ident is None:
        return None
    if ident is False:
        return False
    expected_command = entry.get("command")
    expected_start = entry.get("process_start")
    if not expected_command or not expected_start:
        return None
    if expected_command not in ident["command"]:
        return False
    return expected_start == ident["start"]


def lrb_invocation():
    """The concrete command a spawned being should run to reach this same
    lrb — NOT bare 'lrb', which is never actually placed on PATH by
    `lrb install` (it only copies the script into $LRB_HOME). Derived from
    the currently-running script's own path, so it's correct whether this
    process is the installed copy, a dev worktree copy, or under test."""
    return "%s %s" % (shlex.quote(sys.executable), shlex.quote(os.path.abspath(__file__)))


def build_spawn_prompt(being_id, being, task_name, task_text, spend_so_far, timeout_minutes, being_md_path):
    invocation = lrb_invocation()
    return (
        "You are being spawned by the Being Keeper as scheduled session \"%s\" "
        "for lore being \"%s\".\n\n"
        "Boot as agent \"%s\" from \"%s\" (follow the normal agent-boot.md "
        "procedure: role.md + lore-context.md, auto-pull, version check).\n"
        "Then read your being descriptor at \"%s\" for standing guidance — it is "
        "read at the start of every scheduled session.\n\n"
        "Runtime facts you cannot know yourself: you are running headless, no "
        "user is present. Today's spend so far is $%.4f of your $%.2f daily cap. "
        "This session is killed after %d minutes if still running. To request a "
        "future one-shot session for yourself (e.g. during morning planning), run "
        "(via Bash) exactly this command, substituting the datetime/timeout/prompt — "
        "note it is NOT bare `lrb`, that is not on PATH:\n"
        "`%s schedule --agent %s --at \"<ISO datetime, within 24h, no timezone suffix>\" "
        "--timeout-minutes <N> \"<prompt>\"`\n\n"
        "If that command is denied by your permission settings, do not retry it "
        "silently and do not block waiting for approval — record the denial in "
        "your final summary; that's diagnostic signal for whoever configured this "
        "engine's permission mode.\n\n"
        "End your work with a brief session summary as your final output "
        "message (it is captured as this session's result — not the "
        "sessions/YYYY/MM/ finalization machinery, which stays user-triggered).\n\n"
        "Your task for this session:\n%s\n"
    ) % (
        task_name, being_id, being["_agent_name"], being["_agent_dir"], being_md_path,
        spend_so_far, being["daily_usd"], timeout_minutes, invocation, being_id, task_text,
    )


def spawn_session(workspace, being_id, being, engine_cfg, task_name, prompt_text, timeout_minutes, state, now):
    """Returns the Popen on success. On failure to even launch the engine
    (bad/missing command — e.g. configured at `engines add` time but removed
    or broken since), logs a visible ledger entry and returns None instead
    of raising: one misconfigured being must never crash the Keeper's tick
    loop for every other being/workspace."""
    log_path = log_path_for(workspace, being_id, task_name, now)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    kind = engine_cfg.get("kind", "claude")
    if kind not in ENGINE_KINDS:
        # Hand-edited config with a kind this lrb doesn't know: visible
        # failure, no guessing (same rule as engine-not-configured).
        ledger_append(workspace, being_id, {
            "task": task_name, "outcome": "failed-to-spawn",
            "error": "unknown engine kind %r (known: %s)" % (kind, ", ".join(ENGINE_KINDS)),
            "recorded_at": now.isoformat(timespec="seconds"),
        })
        return None
    if kind == "codex":
        cmd = [engine_cfg["command"], "exec", "--json", "--skip-git-repo-check",
               "-m", being["model"]]
        if engine_cfg.get("permission_mode") == "full":
            cmd.append("--dangerously-bypass-approvals-and-sandbox")
        cmd.append(prompt_text)
    elif kind == "cursor":
        plugin_dir = engine_cfg.get("plugin_dir")
        if not plugin_dir:
            ledger_append(workspace, being_id, {
                "task": task_name, "outcome": "failed-to-spawn",
                "error": "cursor engine missing plugin_dir — re-add with --plugin-dir",
                "recorded_at": now.isoformat(timespec="seconds"),
            })
            return None
        cmd = [
            engine_cfg["command"], "-p", prompt_text,
            "--output-format", "json",
            "--model", being["model"],
            "--plugin-dir", plugin_dir,
            "--workspace", workspace,
            "--trust",
        ]
        if engine_cfg.get("permission_mode") == "full":
            cmd.extend(["--force", "--sandbox", "disabled"])
    else:
        cmd = [engine_cfg["command"], "-p", prompt_text, "--output-format", "json", "--model", being["model"]]
        if engine_cfg.get("permission_mode") == "full":
            cmd.append("--dangerously-skip-permissions")
    # stderr goes to a SIBLING file, not merged into stdout: `claude -p
    # --output-format json` promises exactly one JSON object on stdout, but
    # any stderr noise (a CLI update notice, an MCP warning) merged into the
    # same stream would make the whole-file JSON parse in _finish() fail —
    # silently reading as cost $0.00 and quietly disabling the daily budget
    # cap. Keep them apart so a noisy engine can't defeat the spawn gate.
    log_f = open(log_path, "wb")
    stderr_path = log_path + ".stderr.log"
    stderr_f = open(stderr_path, "wb")
    try:
        proc = subprocess.Popen(
            cmd, stdout=log_f, stderr=stderr_f, stdin=subprocess.DEVNULL, cwd=workspace,
            start_new_session=True,  # own process group, so a kill can take the whole tree (see _kill)
        )
    except OSError as e:
        log_f.close()
        stderr_f.close()
        ledger_append(workspace, being_id, {
            "task": task_name, "outcome": "failed-to-spawn", "error": str(e),
            "recorded_at": now.isoformat(timespec="seconds"),
        })
        return None
    log_f.close()
    stderr_f.close()
    bstate = being_state(state, being_id)
    bstate["running"].append({
        "task": task_name,
        "pid": proc.pid,
        "started": now.isoformat(timespec="seconds"),
        "timeout_minutes": timeout_minutes,
        "log_path": log_path,
        "command": engine_cfg["command"],  # for PID-reuse identity checks — see _pid_matches_entry
        "process_start": (_pid_identity(proc.pid) or {}).get("start"),
        # Recorded at spawn (not looked up at finish) so a mid-flight
        # `engines remove`/re-add can't change how a running session is
        # accounted for.
        "engine_kind": kind,
        "session_cost_usd": engine_cfg.get("session_cost_usd"),
    })
    return proc


# ---- keeper tick loop ---------------------------------------------------


class Keeper(object):
    """Holds this run's live subprocess handles so exited children get
    reaped via proc.poll() rather than lingering as zombies. After a daemon
    restart, re-adopted running entries (no live Popen) fall back to
    os.kill(pid, 0) liveness checks — correct because init/launchd has
    already reparented and can reap them."""

    def __init__(self):
        self.live_procs = {}  # pid -> Popen, this run's own spawns only

    def tick(self, cfg):
        now = datetime.now()
        for workspace in list(cfg.get("workspaces", [])):
            if not os.path.isdir(workspace):
                continue
            try:
                self._tick_workspace(cfg, workspace, now)
            except Exception as e:
                # One workspace's bad state/being must never stop other
                # workspaces from ticking, and must never take the whole
                # daemon process down — that's the single most important
                # substrate invariant (see agent-being-consciousness-
                # substrate-split.md). load_being_file now validates schedule
                # syntax/occurrence-count and timeout-minutes at parse time,
                # so this is a last-resort net for anything still unexpected
                # (e.g. hand-corrupted state.json), not the primary defense.
                print("lrb: tick error in workspace %s: %s" % (workspace, e), file=sys.stderr)

    def _global_running_count(self, cfg, exclude_workspace, exclude_state):
        """Concurrency is a machine-wide cap (§9 of the draft — 'purely so a
        scheduling bug can't fork-bomb the API'), not per-workspace. Recomputed
        fresh at each check point rather than threaded through tick()'s loop:
        `exclude_state` is this workspace's authoritative in-memory state
        (not yet saved to disk this tick); every other workspace's on-disk
        state.json is either not-yet-processed or already-saved this tick,
        so reading it fresh is accurate either way."""
        total = sum(len(b.get("running", [])) for b in exclude_state["beings"].values())
        for w in cfg.get("workspaces", []):
            if w == exclude_workspace:
                continue
            st = read_json(state_path(w), None)
            if st:
                total += sum(len(b.get("running", [])) for b in st.get("beings", {}).values())
        return total

    def _tick_workspace(self, cfg, workspace, now):
        ensure_ws_dirs(workspace)
        state = load_state(workspace)
        beings, _errors = discover_beings(workspace)  # errors surfaced fresh by cmd_status, not persisted
        today = now.date()

        if state.get("date") != today.isoformat():
            prev_date_s = state.get("date")
            if prev_date_s:
                try:
                    prev_date = date.fromisoformat(prev_date_s)
                except ValueError:
                    prev_date = None
                if prev_date:
                    self._check_missed_from_prev_day(workspace, beings, state, prev_date, today)
            for being_id in state["beings"]:
                state["beings"][being_id]["spent_today_usd"] = 0.0
            state["date"] = today.isoformat()

        self._poll_running(workspace, state, now)

        paused = is_paused()
        concurrency = self._global_running_count(cfg, workspace, state)

        if not paused:
            self._fire_existential_tasks(workspace, beings, state, now, concurrency, cfg)
            concurrency = self._global_running_count(cfg, workspace, state)
            process_outbox(workspace, beings, state, now)
            self._spawn_accepted(workspace, beings, state, now, concurrency, cfg)

        save_state(workspace, state)

    def _check_missed_from_prev_day(self, workspace, beings, state, prev_date, today):
        """Walks every day in [prev_date, today) — not just the single most
        recent one — so a multi-day gap (laptop off over a weekend) doesn't
        silently drop the intermediate days from the missed-fire record."""
        d = prev_date
        one_day = timedelta(days=1)
        if today - prev_date > timedelta(days=30):
            # Corrupt/ancient state.json date must degrade mildly, not loop
            # for months of daily cron scans — cap the backfill window.
            d = today - timedelta(days=30)
        while d < today:
            for being_id, being in beings.items():
                bstate = being_state(state, being_id)
                for task in being["existential_tasks"]:
                    try:
                        occ = next_occurrence_for_date(task["schedule"], d)
                    except ValueError:
                        # A schedule that slipped past load_being_file's own
                        # validation (belt-and-braces, not the primary
                        # defense) must not wedge this workspace's rollover
                        # forever — same reasoning as _fire_existential_tasks.
                        continue
                    if occ is None:
                        continue
                    last_run = bstate["last_runs"].get(task["name"])
                    if last_run and last_run[:10] == d.isoformat():
                        continue
                    ledger_append(workspace, being_id, {
                        "task": task["name"], "outcome": "missed",
                        "scheduled_for": occ.isoformat(timespec="seconds"),
                        "recorded_at": datetime.now().isoformat(timespec="seconds"),
                    })
            d = d + one_day

    def _fire_existential_tasks(self, workspace, beings, state, now, concurrency, cfg):
        engines = cfg.get("engines", {})
        for being_id, being in beings.items():
            bstate = being_state(state, being_id)
            engine_cfg = engines.get(being["engine"])
            if engine_cfg is None:
                continue  # config error: engine not configured — never substitute
            for task in being["existential_tasks"]:
                if concurrency >= cfg.get("concurrency_cap", DEFAULT_CONCURRENCY_CAP):
                    return
                name = task["name"]
                try:
                    scheduled = next_occurrence_for_date(task["schedule"], now.date())
                except ValueError:
                    continue
                if scheduled is None or scheduled > now:
                    continue
                if bstate["last_runs"].get(name, "")[:10] == now.date().isoformat():
                    continue
                if bstate["spent_today_usd"] >= being["daily_usd"]:
                    continue
                try:
                    prompt_path = agent_relative_path(being["_agent_dir"], task["prompt"])
                except ValueError as e:
                    print("lrb: %s task %r: bad prompt path: %s" % (being_id, name, e), file=sys.stderr)
                    continue
                try:
                    with open(prompt_path, "r", encoding="utf-8") as f:
                        task_text = f.read()
                except OSError as e:
                    print("lrb: %s task %r: cannot read prompt %s: %s" % (being_id, name, prompt_path, e),
                          file=sys.stderr)
                    continue
                timeout_minutes = int(task["timeout-minutes"])
                spawn_prompt = build_spawn_prompt(
                    being_id, being, name, task_text, bstate["spent_today_usd"],
                    timeout_minutes, being["_path"],
                )
                proc = spawn_session(workspace, being_id, being, engine_cfg, name, spawn_prompt,
                                      timeout_minutes, state, now)
                # Mark last_runs regardless of spawn success: a broken engine
                # command must not retry every 30s all day (retry storm); the
                # failed-to-spawn ledger entry (written by spawn_session) is
                # the visible signal instead.
                bstate["last_runs"][name] = now.isoformat(timespec="seconds")
                if proc is None:
                    continue
                self.live_procs[proc.pid] = proc
                late = (now - scheduled) > LATE_THRESHOLD
                ledger_append(workspace, being_id, {
                    "task": name, "outcome": "spawned-late" if late else "spawned",
                    "pid": proc.pid, "started": now.isoformat(timespec="seconds"),
                })
                concurrency += 1

    def _move_outbox_file(self, src, fn, dest_dir, workspace, being_id, outcome):
        os.makedirs(dest_dir, exist_ok=True)
        try:
            os.rename(src, os.path.join(dest_dir, fn))
        except OSError:
            pass
        if being_id:
            ledger_append(workspace, being_id, {
                "task": "work-session", "outcome": outcome,
                "recorded_at": datetime.now().isoformat(timespec="seconds"),
            })

    def _spawn_accepted(self, workspace, beings, state, now, concurrency, cfg):
        accepted_dir = outbox_accepted_dir(workspace)
        engines = cfg.get("engines", {})
        try:
            names = sorted(os.listdir(accepted_dir))
        except OSError:
            return concurrency
        for fn in names:
            if fn.startswith(".") or not fn.endswith(".json"):
                continue
            if concurrency >= cfg.get("concurrency_cap", DEFAULT_CONCURRENCY_CAP):
                break
            src = os.path.join(accepted_dir, fn)
            try:
                with open(src, "r", encoding="utf-8") as f:
                    req = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(req, dict):
                self._move_outbox_file(src, fn, outbox_done_dir(workspace), workspace, None, "invalid-request")
                continue
            try:
                being_id = req["being"]
                at_dt = parse_naive_iso_datetime(req["at"], "'at'")
                timeout_minutes = require_timeout_minutes(
                    req.get("timeout_minutes", DEFAULT_SCHEDULE_TIMEOUT_MINUTES),
                    "timeout_minutes",
                )
                if not isinstance(req.get("prompt"), str) or not req.get("prompt"):
                    raise ValueError("prompt must be a non-empty string")
            except (KeyError, TypeError, ValueError) as e:
                # Fail safe, not fast: an unparseable 'at' must never be
                # treated as "due now" (that's the wrong failure direction —
                # it'd fire immediately instead of erroring visibly). The
                # same applies to malformed accepted request files generally:
                # move aside visibly rather than wedge this workspace's tick.
                req["invalid_reason"] = str(e)
                try:
                    atomic_write_json(src, req)
                except OSError:
                    pass
                self._move_outbox_file(src, fn, outbox_done_dir(workspace), workspace, req.get("being"),
                                        "invalid-request")
                continue
            if at_dt > now:
                continue
            if at_dt.date() < now.date():
                # Stale: a laptop closed over the request's own day. Spec
                # §6 says missed fires are dropped past midnight, not fired
                # arbitrarily late against the wrong day's prompt/budget —
                # applies to one-shots exactly as it does to existential
                # tasks (_check_missed_from_prev_day covers only the latter).
                self._move_outbox_file(src, fn, outbox_done_dir(workspace), workspace, req.get("being"),
                                        "missed")
                continue
            being = beings.get(being_id)
            if being is None:
                continue  # went to config-error since acceptance; leave file, retry next tick
            bstate = being_state(state, being_id)
            if bstate["spent_today_usd"] >= being["daily_usd"]:
                continue  # budget exhausted since acceptance; leave pending
            engine_cfg = engines.get(being["engine"])
            if engine_cfg is None:
                continue
            spawn_prompt = build_spawn_prompt(
                being_id, being, "work-session", req["prompt"], bstate["spent_today_usd"],
                timeout_minutes, os.path.join(being["_agent_dir"], "being.md"),
            )
            proc = spawn_session(workspace, being_id, being, engine_cfg, "work-session", spawn_prompt,
                                  timeout_minutes, state, now)
            if proc is not None:
                self.live_procs[proc.pid] = proc
                ledger_append(workspace, being_id, {
                    "task": "work-session", "outcome": "spawned", "pid": proc.pid,
                    "started": now.isoformat(timespec="seconds"), "requested_prompt": req["prompt"][:200],
                })
                concurrency += 1
            # Move to done/ either way — spawn_session already logged the
            # failure; retrying a fundamentally broken engine every tick
            # doesn't help (same "no retry storm" reasoning as existential
            # tasks above).
            done_dest = os.path.join(outbox_done_dir(workspace), fn)
            os.makedirs(os.path.dirname(done_dest), exist_ok=True)
            try:
                os.rename(src, done_dest)
            except OSError:
                pass
        return concurrency

    def _poll_running(self, workspace, state, now):
        for being_id, bstate in list(state["beings"].items()):
            still_running = []
            for entry in bstate.get("running", []):
                pid = entry["pid"]
                alive = self._is_alive(pid, entry)
                started = datetime.fromisoformat(entry["started"])
                overdue = now - started > timedelta(minutes=entry["timeout_minutes"])
                if alive and overdue:
                    if self._can_signal(pid, entry):
                        entry.pop("kill_blocked_since", None)
                        self._kill(pid, entry, now)
                        alive = self._is_alive(pid, entry)
                    else:
                        entry["kill_blocked_reason"] = "pid identity check unavailable"
                        entry.setdefault("kill_blocked_since", now.isoformat(timespec="seconds"))
                        blocked_since = datetime.fromisoformat(entry["kill_blocked_since"])
                        if now - blocked_since > timedelta(hours=UNVERIFIABLE_REAP_AFTER_HOURS):
                            print(
                                "lrb: %s: PID %d unverifiable for over %dh past its timeout — "
                                "force-reaping the concurrency slot (identity never confirmed; "
                                "outcome/cost below may be inaccurate)"
                                % (being_id, pid, UNVERIFIABLE_REAP_AFTER_HOURS), file=sys.stderr)
                            entry["force_reaped_unverifiable"] = True
                            alive = False
                if alive:
                    still_running.append(entry)
                    continue
                self._finish(workspace, being_id, bstate, entry, now)
            bstate["running"] = still_running

    def _is_alive(self, pid, entry):
        """entry is used for the PID-reuse identity check on re-adopted
        (not self.live_procs) entries — see _pid_matches_entry."""
        proc = self.live_procs.get(pid)
        if proc is not None:
            return proc.poll() is None
        try:
            os.kill(pid, 0)
        except (ProcessLookupError, PermissionError, OSError):
            return False
        command = entry.get("command")
        if not command:
            return True  # pre-upgrade state entry with no recorded command; best effort liveness
        match = _pid_matches_entry(pid, entry)
        if match is None:
            return True
        return match

    def _can_signal(self, pid, entry):
        """True only when it is safe to signal this PID. For this run's own
        children the Popen handle is authoritative; for re-adopted entries,
        require a confirmed command match. If the identity check is
        unavailable, keep the running entry but do not signal a possibly
        reused PID."""
        if pid in self.live_procs:
            return True
        command = entry.get("command")
        if not command:
            return False  # old state can be observed, but not safely signaled
        return _pid_matches_entry(pid, entry) is True

    def _kill(self, pid, entry, now):
        """Signals the whole process group (spawn_session uses
        start_new_session=True) AND every descendant found by a fresh ppid
        walk (_descendant_pids) — killpg alone misses a descendant that
        called its own setsid (real finding, cursor-agent's sandboxed tool
        execution; see _descendant_pids). Descendants are re-enumerated at
        each escalation step, not just once, since new ones can appear
        between the SIGTERM and the SIGKILL.

        MUST enumerate descendants BEFORE signaling the direct pid/pgid, not
        after: once the direct process dies, the OS reparents any surviving
        child to PID 1, overwriting the very ppid link _descendant_pids
        walks — enumerate-then-kill in the other order can silently miss
        the whole subtree on a fast-dying direct child (caught by
        test_kill_reaches_a_grandchild_that_escaped_into_a_new_session,
        which failed under the original enumerate-after-kill ordering).

        Only ever called on an entry _is_alive already verified (by
        identity, for re-adopted PIDs) as this session's own process."""
        kill_sent_at = entry.get("kill_sent_at")
        try:
            pgid = os.getpgid(pid)
        except OSError:
            pgid = None
        descendants = _descendant_pids(pid)
        if kill_sent_at is None:
            try:
                os.killpg(pgid, signal.SIGTERM) if pgid is not None else os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
            for descendant in descendants:
                try:
                    os.kill(descendant, signal.SIGTERM)
                except OSError:
                    pass
            entry["kill_sent_at"] = now.isoformat(timespec="seconds")
            return
        sent = datetime.fromisoformat(kill_sent_at)
        if (now - sent).total_seconds() > KILL_GRACE_SECONDS:
            try:
                os.killpg(pgid, signal.SIGKILL) if pgid is not None else os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
            for descendant in descendants:
                try:
                    os.kill(descendant, signal.SIGKILL)
                except OSError:
                    pass

    def _finish(self, workspace, being_id, bstate, entry, now):
        self.live_procs.pop(entry["pid"], None)
        log_path = entry.get("log_path")
        result = None
        content = ""
        started = datetime.fromisoformat(entry["started"])
        if log_path and os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read().strip()
                result = _parse_result_json(content)
            except OSError:
                result = None
        killed = "kill_sent_at" in entry
        kind = entry.get("engine_kind", "claude")
        cost = 0.0
        usage = None
        if kind == "codex":
            # Codex reports no USD; charge the engine's configured flat
            # session-cost-usd for EVERY finished session regardless of
            # outcome — over-charging only makes the cap trip earlier (the
            # safe direction; repeated crashes exhausting the budget and
            # stopping further spawns is the desired behavior, not a bug).
            try:
                cost = require_finite_nonnegative_float(
                    entry.get("session_cost_usd") or 0.0, "session_cost_usd")
            except ValueError:
                cost = 0.0
            rtype = result.get("type") if isinstance(result, dict) else None
            if killed:
                outcome = "timeout"
            elif rtype == "turn.completed":
                outcome = "ok"
                usage = result.get("usage")
            elif rtype in ("turn.failed", "error"):
                outcome = "error"
            elif content:
                outcome = "unparseable"  # died mid-stream / non-JSONL output
            else:
                outcome = "crashed"
        elif kind == "cursor":
            usage = None
            if isinstance(result, dict):
                usage = result.get("usage")
                reported = result.get("total_cost_usd")
                if reported is not None:
                    try:
                        cost = require_finite_nonnegative_float(reported, "total_cost_usd")
                        outcome = "timeout" if killed else ("error" if result.get("is_error") else "ok")
                    except ValueError:
                        cost = 0.0
                        outcome = "invalid-cost"
                elif entry.get("session_cost_usd") is not None:
                    try:
                        cost = require_finite_nonnegative_float(
                            entry.get("session_cost_usd"), "session_cost_usd")
                    except ValueError:
                        cost = 0.0
                    outcome = "timeout" if killed else ("error" if result.get("is_error") else "ok")
                else:
                    cost = 0.0
                    outcome = "timeout" if killed else ("error" if result.get("is_error") else "ok")
            elif killed:
                outcome = "timeout"
            elif content:
                outcome = "unparseable"
            else:
                outcome = "crashed"
        elif isinstance(result, dict):
            try:
                cost = require_finite_nonnegative_float(result.get("total_cost_usd") or 0.0, "total_cost_usd")
                outcome = "timeout" if killed else ("error" if result.get("is_error") else "ok")
            except ValueError:
                cost = 0.0
                outcome = "invalid-cost"
        elif killed:
            outcome = "timeout"
        elif content:
            outcome = "unparseable"  # process exited/died and left non-JSON output
        else:
            outcome = "crashed"  # process died leaving no output at all
        if started.date() == now.date():
            bstate["spent_today_usd"] = bstate.get("spent_today_usd", 0.0) + cost
        ledger_entry = {
            "task": entry["task"], "outcome": outcome, "pid": entry["pid"],
            "started": entry["started"], "finished": now.isoformat(timespec="seconds"),
            "duration_s": round((now - started).total_seconds(), 1), "cost_usd": cost,
            "log_path": log_path,
        }
        if usage is not None:
            ledger_entry["usage"] = usage  # tokens recorded too; dollars stay the budget unit
        if entry.get("force_reaped_unverifiable"):
            # See UNVERIFIABLE_REAP_AFTER_HOURS: identity was never confirmed
            # for this entry, so the outcome/cost above are a best-effort
            # read of whatever log content happened to exist, not a
            # confirmed observation of this specific process's exit.
            ledger_entry["force_reaped_unverifiable"] = True
        ledger_append(workspace, being_id, ledger_entry)


# ---- CLI: install / daemon ----------------------------------------------


def cmd_install(args):
    home = lrb_home()
    os.makedirs(home, exist_ok=True)
    src = os.path.abspath(__file__)
    dest = os.path.join(home, "lrb.py")
    if os.path.abspath(src) != os.path.abspath(dest):
        shutil.copy2(src, dest)
    os.chmod(dest, 0o755)
    print("lrb: installed %s (version %s)" % (dest, VERSION))
    if not os.path.exists(config_path()):
        save_config({"workspaces": [], "engines": {}})
    if sys.platform != "darwin":
        print("lrb: launchd install is macOS-only; run `python3 %s daemon` under your "
              "own supervisor (systemd, etc.) on this platform." % dest)
        return
    plist_dir = launchagents_dir()
    os.makedirs(plist_dir, exist_ok=True)
    plist_path = os.path.join(plist_dir, "%s.plist" % LABEL)
    plist = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0"><dict>\n'
        '  <key>Label</key><string>%s</string>\n'
        '  <key>ProgramArguments</key><array>\n'
        '    <string>%s</string>\n'
        '    <string>%s</string>\n'
        '    <string>daemon</string>\n'
        '  </array>\n'
        '  <key>KeepAlive</key><true/>\n'
        '  <key>RunAtLoad</key><true/>\n'
        '  <key>StandardOutPath</key><string>%s/keeper.log</string>\n'
        '  <key>StandardErrorPath</key><string>%s/keeper.log</string>\n'
        '  <key>EnvironmentVariables</key><dict>\n'
        '    <key>LRB_HOME</key><string>%s</string>\n'
        '    <key>PATH</key><string>%s</string>\n'
        '  </dict>\n'
        '</dict></plist>\n'
    ) % tuple(xml_escape(v) for v in (
        LABEL, sys.executable, dest, home, home, home,
        # launchd jobs get a bare PATH (/usr/bin:/bin:...) — capture the
        # installing user's real PATH so an engine with a #!/usr/bin/env
        # shebang (e.g. an npm-installed `claude` needing `node`) resolves
        # under the daemon the same way it did in the terminal that ran
        # `install`. Without this, every real spawn fails silently in
        # production while manual/terminal testing passes (M7 in review).
        os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin"),
    ))  # a PATH/LRB_HOME containing '&' or '<' would otherwise produce an invalid plist
    atomic_write_text(plist_path, plist)
    print("lrb: wrote %s" % plist_path)
    if args.launchd:
        uid = os.getuid()
        subprocess.run(["launchctl", "bootout", "gui/%d/%s" % (uid, LABEL)],
                        capture_output=True)
        r = subprocess.run(["launchctl", "bootstrap", "gui/%d" % uid, plist_path], capture_output=True, text=True)
        if r.returncode != 0:
            die("launchctl bootstrap failed: %s" % (r.stderr or r.stdout).strip())
        print("lrb: Keeper installed and running under launchd (gui/%d/%s)" % (uid, LABEL))
    else:
        print("lrb: plist written but NOT loaded into launchd (pass --launchd to actually "
              "install the persistent background daemon). Run `python3 %s daemon` "
              "directly to run it in the foreground for testing." % dest)


def _acquire_daemon_lock():
    """Refuses to start a second Keeper concurrently — two Keepers ticking
    the same workspace(s) would double-spawn due tasks and race on
    state.json's read-modify-write (last writer wins, orphaning the other's
    'running' entry: that session runs for real, unbilled and untracked).
    fcntl.flock, POSIX-only — matches the current macOS/Linux-only scope
    (no Windows daemon story yet, per the draft's open seams). Returns the
    open lock file; the CALLER must keep a reference alive for the lock's
    lifetime (closing/GC'ing it releases the flock)."""
    import fcntl
    lock_path = os.path.join(lrb_home(), "daemon.lock")
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    # "a+" (never truncates on open) — a refused attempt must not wipe the
    # incumbent daemon's recorded pid before finding out it lost the flock.
    lock_f = open(lock_path, "a+")
    try:
        fcntl.flock(lock_f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock_f.close()
        die("another lrb daemon already holds the lock (%s) — refusing to start a second one" % lock_path)
    lock_f.seek(0)
    lock_f.truncate()
    lock_f.write(str(os.getpid()))
    lock_f.flush()
    return lock_f


def daemon_info_path():
    return os.path.join(lrb_home(), "daemon.info")


def cmd_daemon(args):
    lock = _acquire_daemon_lock()  # held for this process's lifetime; released on exit
    keeper = Keeper()
    if args.once:
        keeper.tick(load_config())
        return
    # §5's "installed version shown in status so drift is visible" only
    # works if status can see the *running* daemon's version, not just the
    # version of whatever copy happens to run the CLI command.
    atomic_write_json(daemon_info_path(), {
        "pid": os.getpid(), "version": VERSION, "script_path": os.path.abspath(__file__),
        "executable": sys.executable,
        "started": datetime.now().isoformat(timespec="seconds"),
    })
    running = [True]

    def _stop(signum, frame):
        running[0] = False

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    while running[0]:
        try:
            keeper.tick(load_config())
        except Exception as e:
            print("lrb: tick error: %s" % e, file=sys.stderr)
        for _ in range(TICK_SECONDS):
            if not running[0]:
                break
            time.sleep(1)


# ---- CLI: status / pause / resume / stop ---------------------------------


def _last_ledger_outcome(workspace, being_id):
    p = ledger_path(workspace, being_id)
    try:
        with open(p, "r", encoding="utf-8") as f:
            last = None
            for line in f:
                line = line.strip()
                if line:
                    last = line
    except OSError:
        return None
    if not last:
        return None
    try:
        return json.loads(last).get("outcome")
    except json.JSONDecodeError:
        return None


def _daemon_status():
    """Purely informational — deliberately skips the identity check
    _pid_matches_entry does for kill paths. Comparing a process against
    its OWN sys.executable is a narrower, less reliable case than matching
    an external engine command: macOS framework Python builds re-exec `bin/
    python3.x` into a differently-named `Python.app` bundle binary, so a
    live daemon's own sys.executable can legitimately not appear in `ps` for
    itself. A theoretical PID-reuse false positive here just misreports
    status text; unlike the kill paths, nothing gets signaled."""
    info = read_json(daemon_info_path(), None)
    if not info:
        return {"running": False}
    pid = info.get("pid")
    alive = False
    if pid:
        try:
            os.kill(pid, 0)
            alive = True
        except OSError:
            alive = False
    info["running"] = alive
    return info


def cmd_status(args):
    cfg = load_config()
    engines = cfg.get("engines", {})
    out = {
        "version": VERSION,
        "paused": is_paused(),
        "daemon": _daemon_status(),
        "engines": sorted(engines.keys()),
        "workspaces": {},
    }
    for workspace in cfg.get("workspaces", []):
        beings, errors = discover_beings(workspace)
        errors = dict(errors)  # don't mutate discover_beings' own dict
        state = load_state(workspace)
        ws_out = {"beings": {}, "config_errors": errors}
        for being_id, being in beings.items():
            if being["engine"] not in engines:
                errors[being_id] = "engine %r not configured (lrb engines add %s ...)" % (
                    being["engine"], being["engine"])
                # Still fall through to list it (with whatever it has
                # running right now) rather than hiding it entirely — the
                # fire loop won't spawn NEW sessions for it, but a session
                # spawned before the engine was removed may still be
                # running, and that must stay visible in status.
            bstate = being_state(state, being_id)
            ws_out["beings"][being_id] = {
                "description": being["description"],
                "engine": being["engine"], "model": being["model"],
                "daily_usd": being["daily_usd"],
                "spent_today_usd": round(bstate["spent_today_usd"], 4),
                "running": bstate["running"],
                "last_runs": bstate["last_runs"],
                "last_outcome": _last_ledger_outcome(workspace, being_id),
                "log_dir": os.path.dirname(ledger_path(workspace, being_id)),
            }
        out["workspaces"][workspace] = ws_out
    if args.json:
        print(json.dumps(out, indent=2, sort_keys=True))
        return
    print("lrb %s%s" % (VERSION, "  [PAUSED]" if out["paused"] else ""))
    d = out["daemon"]
    if d.get("running"):
        drift = "" if d.get("version") == VERSION else "  (CLI is v%s — drift)" % VERSION
        print("daemon: running (pid %s, v%s, since %s)%s" % (d.get("pid"), d.get("version"), d.get("started"), drift))
    else:
        print("daemon: not detected (no running process at the recorded pid)")
    for workspace, ws_out in out["workspaces"].items():
        print("\nworkspace: %s" % workspace)
        for being_id, b in ws_out["beings"].items():
            print("  %-30s $%.4f/$%.2f  running=%d  last=%s  last_outcome=%s" % (
                being_id, b["spent_today_usd"], b["daily_usd"], len(b["running"]),
                b["last_runs"] or "-", b["last_outcome"] or "-"))
            print("      logs: %s" % b["log_dir"])
        for being_id, err in ws_out["config_errors"].items():
            print("  %-30s CONFIG ERROR: %s" % (being_id, err))


def cmd_validate(args):
    cfg = load_config()
    engines = cfg.get("engines", {})
    issues = []
    warnings = []
    workspaces = cfg.get("workspaces", [])
    if not workspaces:
        warnings.append("no registered workspaces (lrb workspaces add <workspace>)")
    if not engines:
        warnings.append("no configured engines (lrb engines add <name> ...)")
    for name, entry in sorted(engines.items()):
        command = entry.get("command")
        if not command:
            issues.append("engine %s: missing command" % name)
        elif os.sep in command or (os.altsep and os.altsep in command):
            if not os.path.exists(command):
                issues.append("engine %s: command does not exist: %s" % (name, command))
        elif not shutil.which(command):
            issues.append("engine %s: command not found on PATH: %s" % (name, command))
        kind = entry.get("kind", "claude")
        if kind not in ENGINE_KINDS:
            issues.append("engine %s: unknown kind %r" % (name, kind))
        if kind in ("codex", "cursor") and entry.get("session_cost_usd") is None:
            issues.append("engine %s: kind %s requires session_cost_usd" % (name, kind))
        if kind == "cursor":
            try:
                require_plugin_dir(entry.get("plugin_dir"), "plugin_dir")
            except ValueError as e:
                issues.append("engine %s: %s" % (name, e))
    total_beings = 0
    for workspace in workspaces:
        if not os.path.isdir(workspace):
            issues.append("workspace missing: %s" % workspace)
            continue
        beings, errors = discover_beings(workspace)
        for being_id, err in sorted(errors.items()):
            issues.append("%s: %s" % (being_id, err))
        total_beings += len(beings)
        for being_id, being in sorted(beings.items()):
            if being["engine"] not in engines:
                issues.append("%s: engine %r not configured" % (being_id, being["engine"]))
            for task in being["existential_tasks"]:
                prompt_path = agent_relative_path(being["_agent_dir"], task["prompt"])
                if not os.path.isfile(prompt_path):
                    issues.append("%s:%s: prompt file missing: %s" % (
                        being_id, task["name"], prompt_path))
    if args.json:
        print(json.dumps({
            "ok": not issues,
            "version": VERSION,
            "workspaces": len(workspaces),
            "engines": sorted(engines.keys()),
            "beings": total_beings,
            "warnings": warnings,
            "issues": issues,
        }, indent=2, sort_keys=True))
        return 0 if not issues else 1
    print("lrb validate: %s" % ("ok" if not issues else "failed"))
    print("  workspaces=%d engines=%d beings=%d" % (
        len(workspaces), len(engines), total_beings))
    for warning in warnings:
        print("  WARNING: %s" % warning)
    for issue in issues:
        print("  ERROR: %s" % issue)
    return 0 if not issues else 1


def cmd_logs(args):
    cfg = load_config()
    matches = []
    for workspace in cfg.get("workspaces", []):
        beings, _errors = discover_beings(workspace)
        if args.being in beings:
            matches.append((workspace, args.being))
    if not matches:
        die("no such being in registered workspaces: %s" % args.being)
    if len(matches) > 1:
        die("being id is ambiguous across registered workspaces: %s" % args.being)
    workspace, being_id = matches[0]
    ledger = ledger_path(workspace, being_id)
    log_dir = os.path.dirname(ledger)
    entries = read_ledger_entries(workspace, being_id)
    if args.json:
        print(json.dumps({
            "workspace": workspace,
            "being": being_id,
            "log_dir": log_dir,
            "ledger": ledger,
            "entries": entries[-args.tail:],
        }, indent=2, sort_keys=True))
        return
    print("being: %s" % being_id)
    print("workspace: %s" % workspace)
    print("logs: %s" % log_dir)
    print("ledger: %s" % ledger)
    if not entries:
        print("ledger: no entries yet")
        return
    print("recent ledger entries:")
    for entry in entries[-args.tail:]:
        bits = [
            entry.get("finished_at") or entry.get("started_at") or entry.get("requested_at") or "-",
            entry.get("task") or entry.get("kind") or "-",
            "outcome=%s" % (entry.get("outcome") or "-"),
        ]
        if entry.get("cost_usd") is not None:
            bits.append("cost=$%.4f" % entry["cost_usd"])
        if entry.get("log_path"):
            bits.append("log=%s" % entry["log_path"])
        print("  " + "  ".join(bits))


def cmd_pause(args):
    atomic_write_text(paused_path(), "")
    print("lrb: paused")


def cmd_resume(args):
    try:
        os.unlink(paused_path())
    except FileNotFoundError:
        pass
    print("lrb: resumed")


def cmd_stop(args):
    cfg = load_config()
    killed = 0
    for workspace in cfg.get("workspaces", []):
        state = load_state(workspace)
        for being_id, bstate in state["beings"].items():
            for entry in bstate.get("running", []):
                pid = entry["pid"]
                command = entry.get("command")
                # PID-reuse guard: this CLI invocation never spawned these
                # processes itself, so unlike the Keeper's own live_procs
                # fast path there is no OS handle to trust — verify identity
                # before signaling anything, same as _is_alive/_kill.
                if not command or _pid_matches_entry(pid, entry) is not True:
                    continue
                try:
                    pgid = os.getpgid(pid)
                    os.killpg(pgid, signal.SIGTERM)
                    killed += 1
                except OSError:
                    pass
    atomic_write_text(paused_path(), "")
    print("lrb: sent SIGTERM to %d running session(s), paused scheduling" % killed)


# ---- CLI: engines / workspaces / schedule --------------------------------


def cmd_engines_add(args):
    cfg = load_config()
    # Kind defaults to the engine NAME when that name is itself a known kind
    # ("claude", "codex", "cursor") — the common case; anything else (a stub,
    # a wrapper script under a custom name) defaults to the claude-shaped
    # contract and can say otherwise with --kind.
    kind = args.kind or (args.name if args.name in ENGINE_KINDS else "claude")
    session_cost_usd = None
    plugin_dir = None
    if kind == "codex":
        if args.session_cost_usd is None:
            die("kind 'codex' reports no USD cost — pass --session-cost-usd <flat USD "
                "charged per session> so the daily-usd spawn gate stays enforceable")
        try:
            session_cost_usd = require_finite_nonnegative_float(
                args.session_cost_usd, "--session-cost-usd")
        except ValueError as e:
            die(str(e))
    elif kind == "cursor":
        if not args.plugin_dir:
            die("kind 'cursor' requires --plugin-dir <lore-framework checkout> "
                "(Lore skills load via cursor-agent --plugin-dir)")
        try:
            plugin_dir = require_plugin_dir(args.plugin_dir)
        except ValueError as e:
            die(str(e))
        if args.session_cost_usd is None:
            die("kind 'cursor' requires --session-cost-usd <flat USD charged per session> — "
                "real cursor-agent responses omit total_cost_usd (token usage only), so "
                "without a flat rate the daily-usd spawn gate never trips")
        try:
            session_cost_usd = require_finite_nonnegative_float(
                args.session_cost_usd, "--session-cost-usd")
        except ValueError as e:
            die(str(e))
    elif args.session_cost_usd is not None:
        die("--session-cost-usd only applies to kind 'codex' or 'cursor' (kind %r is expected "
            "to report its own cost)" % kind)
    if args.plugin_dir and kind != "cursor":
        die("--plugin-dir only applies to kind 'cursor'")
    command = args.command or shutil.which(args.name)
    if not command:
        die("no command found for engine %r; pass --command" % args.name)
    if args.command and (os.sep in args.command or (os.altsep and os.altsep in args.command)):
        command = os.path.abspath(args.command)
    try:
        r = subprocess.run([command, "--version"], capture_output=True, timeout=15, text=True)
    except (OSError, subprocess.TimeoutExpired) as e:
        die("engine probe failed for %r (%s): %s" % (args.name, command, e))
    if r.returncode != 0:
        die("engine probe failed for %r (%s): exit %d" % (args.name, command, r.returncode))
    entry = {"command": command, "permission_mode": args.permission_mode, "kind": kind}
    if session_cost_usd is not None:
        entry["session_cost_usd"] = session_cost_usd
    if plugin_dir is not None:
        entry["plugin_dir"] = plugin_dir
    cfg.setdefault("engines", {})[args.name] = entry
    save_config(cfg)
    print("lrb: engine %r added (%s, kind=%s, permission_mode=%s%s%s)" % (
        args.name, command, kind, args.permission_mode,
        ", session_cost_usd=%s" % session_cost_usd if session_cost_usd is not None else "",
        ", plugin_dir=%s" % plugin_dir if plugin_dir is not None else ""))


def cmd_engines_remove(args):
    cfg = load_config()
    if cfg.get("engines", {}).pop(args.name, None) is None:
        die("no such engine: %r" % args.name)
    save_config(cfg)
    print("lrb: engine %r removed" % args.name)


def cmd_engines_list(args):
    cfg = load_config()
    for name, e in cfg.get("engines", {}).items():
        extra = ""
        if e.get("session_cost_usd") is not None:
            extra = "  session_cost_usd=%s" % e["session_cost_usd"]
        print("%-12s %-40s kind=%-8s permission_mode=%s%s" % (
            name, e["command"], e.get("kind", "claude"), e.get("permission_mode", "default"), extra))


def _ensure_gitignored(path, entry):
    """Best-effort: append `entry` to <path>/.gitignore if `path` is itself a
    git repo and the entry isn't already covered. Never fails registration —
    a workspace that isn't a git repo, or whose .gitignore can't be written,
    just doesn't get this convenience."""
    if not os.path.isdir(os.path.join(path, ".git")):
        return
    gi_path = os.path.join(path, ".gitignore")
    try:
        with open(gi_path, "r", encoding="utf-8") as f:
            existing = f.read()
    except OSError:
        existing = ""
    if entry in existing.splitlines():
        return
    try:
        with open(gi_path, "a", encoding="utf-8") as f:
            if existing and not existing.endswith("\n"):
                f.write("\n")
            f.write(entry + "\n")
    except OSError:
        pass


def cmd_workspaces_add(args):
    path = os.path.realpath(os.path.abspath(args.path))
    if not os.path.isdir(path):
        die("not a directory: %s" % path)
    cfg = load_config()
    ws = cfg.setdefault("workspaces", [])
    if path not in ws:
        ws.append(path)
        save_config(cfg)
    ensure_ws_dirs(path)
    _ensure_gitignored(path, "/.lr-beings/")
    print("lrb: workspace registered: %s" % path)


def cmd_workspaces_remove(args):
    path = os.path.realpath(os.path.abspath(args.path))
    cfg = load_config()
    ws = cfg.get("workspaces", [])
    if path in ws:
        ws.remove(path)
        save_config(cfg)
    print("lrb: workspace removed: %s" % path)


def cmd_workspaces_list(args):
    cfg = load_config()
    for w in cfg.get("workspaces", []):
        print(w)


def cmd_schedule(args):
    workspace = os.path.realpath(os.path.abspath(os.getcwd()))
    cfg = load_config()
    if workspace not in cfg.get("workspaces", []):
        die("cwd %s is not a registered workspace (lrb workspaces add %s)" % (workspace, workspace))
    try:
        parse_naive_iso_datetime(args.at, "--at")
        timeout_minutes = require_timeout_minutes(args.timeout_minutes, "--timeout-minutes")
    except ValueError as e:
        die(str(e))
    fn = write_outbox_request(workspace, args.agent, args.at, timeout_minutes, args.prompt)
    print("lrb: scheduled request %s (pending validation next tick)" % fn)


# ---- argparse wiring ------------------------------------------------------


def build_parser():
    p = argparse.ArgumentParser(prog="lrb", description="Lore Beings — the Being Keeper CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("install", help="copy self to $LRB_HOME and write the launchd plist")
    s.add_argument("--launchd", action="store_true",
                    help="actually bootstrap the launchd job (default: write the plist only)")
    s.set_defaults(func=cmd_install)

    s = sub.add_parser("daemon", help="run the Keeper tick loop (what launchd invokes)")
    s.add_argument("--once", action="store_true", help="run exactly one tick then exit")
    s.set_defaults(func=cmd_daemon)

    s = sub.add_parser("status", help="show beings, spend, and running sessions")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("validate", help="static-check beings, engines, and workspaces")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_validate)

    s = sub.add_parser("logs", help="show ledger/log pointers for one being")
    s.add_argument("being", help="being id, e.g. lore-chronicler/chronicler")
    s.add_argument("--tail", type=int, default=5, help="ledger entries to show (default: 5)")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_logs)

    s = sub.add_parser("pause", help="pause scheduling for all beings")
    s.set_defaults(func=cmd_pause)
    s = sub.add_parser("resume", help="resume scheduling for all beings")
    s.set_defaults(func=cmd_resume)
    s = sub.add_parser("stop", help="SIGTERM running sessions and pause scheduling")
    s.set_defaults(func=cmd_stop)

    eng = sub.add_parser("engines", help="manage configured engines")
    esub = eng.add_subparsers(dest="engines_cmd", required=True)
    s = esub.add_parser("add")
    s.add_argument("name")
    s.add_argument("--command", help="path to the engine binary (default: look up on PATH)")
    s.add_argument("--kind", choices=list(ENGINE_KINDS),
                    help="invocation/result contract (default: the engine name if it is a "
                         "known kind, else 'claude')")
    s.add_argument("--session-cost-usd", dest="session_cost_usd", type=float,
                    help="flat USD charged per session for engines that report no cost "
                         "(required for kind 'codex' and 'cursor')")
    s.add_argument("--plugin-dir", dest="plugin_dir",
                    help="lore-framework checkout path (required for kind 'cursor')")
    s.add_argument("--permission-mode", dest="permission_mode", choices=["default", "full"], default="default")
    s.set_defaults(func=cmd_engines_add)
    s = esub.add_parser("remove")
    s.add_argument("name")
    s.set_defaults(func=cmd_engines_remove)
    s = esub.add_parser("list")
    s.set_defaults(func=cmd_engines_list)

    wsp = sub.add_parser("workspaces", help="manage the workspace registry")
    wsub = wsp.add_subparsers(dest="workspaces_cmd", required=True)
    s = wsub.add_parser("add")
    s.add_argument("path")
    s.set_defaults(func=cmd_workspaces_add)
    s = wsub.add_parser("remove")
    s.add_argument("path")
    s.set_defaults(func=cmd_workspaces_remove)
    s = wsub.add_parser("list")
    s.set_defaults(func=cmd_workspaces_list)

    s = sub.add_parser("schedule", help="request a one-shot future session (outbox)")
    s.add_argument("--agent", required=True, help="being id, e.g. lore-chronicler/chronicler")
    s.add_argument("--at", required=True, help="ISO datetime, within the next 24h")
    s.add_argument("--timeout-minutes", dest="timeout_minutes", type=int, default=DEFAULT_SCHEDULE_TIMEOUT_MINUTES)
    s.add_argument("prompt")
    s.set_defaults(func=cmd_schedule)

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    rc = args.func(args)
    if isinstance(rc, int):
        sys.exit(rc)


if __name__ == "__main__":
    main()

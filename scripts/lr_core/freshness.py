"""Per-repository successful-pull evidence. Check never writes this marker."""
import math
import os
import tempfile
import time

from .common import git, read_text

MAX_AGE = 86400


def stamp_path(repo):
    rc, out, _ = git(repo, ["rev-parse", "--absolute-git-dir"])
    return os.path.join(out.strip(), "lr-last-pull") if rc == 0 and out.strip() else None


def read_stamp(repo):
    path = stamp_path(repo)
    try:
        value = float(read_text(path) or "") if path else None
        return value if value is not None and math.isfinite(value) and value >= 0 else None
    except (TypeError, ValueError):
        return None


def write_stamp(repo):
    """Only call after successful clone/pull. Atomic; return error rather than raise."""
    path = stamp_path(repo)
    if not path:
        return "cannot resolve Git directory"
    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(prefix="lr-last-pull-", dir=os.path.dirname(path))
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write("%d\n" % int(time.time()))
        os.replace(tmp, path)
        return None
    except OSError as exc:
        return str(exc)
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


def repo_freshness(repo, now=None):
    now = time.time() if now is None else now
    stamp = read_stamp(repo)
    age = now - stamp if stamp is not None else None
    status = ("unknown" if age is None or age < 0 else
              "stale" if age > MAX_AGE else "recent")
    return {"repo": repo, "status": status, "last_checked": stamp,
            "age_seconds": age if age is not None and age >= 0 else None,
            "source": "framework-successful-pull"}

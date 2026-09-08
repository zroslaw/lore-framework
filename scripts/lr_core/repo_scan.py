"""Mechanical repo and shortcut checks. No network or writes; meaning stays with AI."""
import os
from datetime import datetime
from pathlib import Path
import re

from .common import git, parse_frontmatter, read_text
from .lore_graph import build_lore_graph, lore_coverage
from .plugin_scan import finding
from .preflight import describe_repo, git_toplevel, compare_versions
from .workspace_scan import frontmatter_unterminated, shortcut_targets


def _good_field(value):
    return isinstance(value, str) and bool(value.strip()) and value.strip().lower() not in ("null", "~")


def _commit_time(repo, relative):
    head_rc, _, _ = git(str(repo), ["rev-parse", "--verify", "HEAD"])
    if head_rc == 128 or head_rc == 1:
        return None, None  # New repositories have no history yet.
    rc, out, err = git(str(repo), ["log", "-1", "--format=%ct", "--", relative])
    return (int(out.strip()) if rc == 0 and out.strip().isdigit() else None,
            err.strip() if rc != 0 else None)


def shortcut_files(workspace):
    root = Path(workspace)
    for path in sorted((root / ".claude/commands").glob("lr-*-agent.md")):
        yield path, "claude", True
    for directory, engine, local in ((root / ".codex/skills", "codex", True),
                                     (root / ".cursor/skills", "cursor", True),
                                     (Path.home() / ".codex/skills", "codex", False)):
        for path in sorted(directory.glob("lr-*-agent/SKILL.md")):
            yield path, engine, local


def bootstrap_template(root, engine):
    """Read the same canonical sentence the registration procedure uses."""
    text = read_text(os.path.join(root, "docs/engines", engine + ".md")) or ""
    section = text.split("## Registered shortcut bootstrap", 1)[-1]
    for line in section.splitlines():
        if line.startswith("Read the `SKILL.md` for the installed") and "boot as agent" in line:
            return line
    raise ValueError("missing canonical %s bootstrap template" % engine)


def normalize_name(value):
    return re.sub(r"[\s-]+", "-", value.strip().casefold())


def check_shortcuts(workspace, framework_root, findings, warnings):
    root = Path(workspace).resolve()
    for path, engine, local in shortcut_files(workspace):
        text = read_text(str(path))
        if text is None:
            warnings.append("Unreadable shortcut: %s" % path)
            continue
        match = re.search(r"boot as agent `([^`]+)` from `([^`]+)`", text)
        target = None
        if match:
            target = Path(os.path.expanduser(match[2]))
            if not target.is_absolute():
                target = (root / target) if local else None
            if target is not None:
                target = target.resolve()
        if not local and (target is None or not target.is_relative_to(root)):
            # A global shortcut from another workspace must never be repaired here.
            continue
        base = {"path": str(path)}
        if target is None or not target.is_dir():
            findings.append(finding("R11", "error", "repos", "shortcuts", **base,
                                    target=str(target) if target else None))
        reasons = []
        body = re.sub(r"\A---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.S).strip()
        if not match:
            reasons.append("missing_boot_target")
        else:
            try:
                expected = bootstrap_template(framework_root, engine)
                for token in ("<agent-dir-rel>", "<agent-dir>"):
                    expected = expected.replace(token, match[2])
                expected = expected.replace("<agent-name>", match[1])
                if body != expected:
                    reasons.append("bootstrap_differs")
            except ValueError as exc:
                warnings.append(str(exc))
            absolute = os.path.isabs(os.path.expanduser(match[2]))
            if local and absolute:
                reasons.append("absolute_workspace_target")
            if not local and not absolute:
                reasons.append("relative_global_target")
            if engine != "claude":
                fm = parse_frontmatter(text)
                if fm.get("name") != "lr-%s-agent" % match[1]:
                    reasons.append("skill_name")
                if not _good_field(fm.get("description")):
                    reasons.append("skill_description")
                if engine == "cursor":
                    if str(fm.get("disable-model-invocation")).lower() != "true":
                        reasons.append("explicit_invocation")
                    if target is not None and target.is_relative_to(root):
                        parts = target.relative_to(root).parts
                        repo = parts[0] if parts else None
                        paths = fm.get("paths", [])
                        if isinstance(paths, str):
                            paths = [paths]
                        if not repo or repo + "/**" not in paths:
                            reasons.append("repo_scope")
        if reasons:
            findings.append(finding("R12", "warn", "repos", "shortcuts", **base, reasons=reasons))
        if target is None or not target.is_dir():
            continue
        role = read_text(str(target / "role.md"))
        heading = re.search(r"^#\s+(.+?)\s*#*\s*$", role or "", re.M)
        if not match or not heading or normalize_name(match[1]) != normalize_name(heading[1]):
            findings.append(finding("R15", "info", "repos", "names", **base,
                                    shortcut_name=match[1] if match else None,
                                    role_heading=heading[1] if heading else None,
                                    reason="different" if match and heading else "unable_to_compare"))
        repo = git_toplevel(str(target))
        if repo:
            stamp, error = _commit_time(repo, os.path.relpath(target / "role.md", repo))
            if error:
                warnings.append("Shortcut age unavailable for %s: %s" % (path, error))
            try:
                if stamp is not None and stamp > path.stat().st_mtime:
                    findings.append(finding("R13", "info", "repos", "shortcuts", **base, role_commit_time=stamp))
            except OSError as exc:
                warnings.append(str(exc))
    for path in sorted((root / ".claude/commands").glob("lr-*.md")):
        if path.name.endswith("-agent.md") or "boot as agent" in (read_text(str(path)) or ""):
            continue
        name = path.stem[3:]
        if (Path(framework_root) / "skills" / name / "SKILL.md").is_file():
            findings.append(finding("R14", "info", "repos", "shortcuts", path=str(path), skill=name))


def changed_repo_paths(repo):
    """Keep both sides of renames: moving a topic out of lore is still a lore change."""
    rc, out, _ = git(str(repo), ["status", "--porcelain=v1", "-z", "--untracked-files=all"])
    if rc != 0:
        return None
    records = out.split("\0")
    paths, i = [], 0
    while i < len(records):
        record = records[i]
        i += 1
        if len(record) < 4:
            continue
        paths.append(record[3:])
        if "R" in record[:2] or "C" in record[:2]:
            if i < len(records):
                paths.append(records[i])
                i += 1
    return sorted(set(paths))


def scan_repos(workspace, framework_root, children, version):
    findings, warnings, repos = [], [], []
    if version is None:
        warnings.append("Repo version comparison unavailable: framework VERSION is unreadable or invalid")
    registered = shortcut_targets(workspace)
    for child in children:
        if not child.get("lore_repo") or child.get("escapes_workspace"):
            continue
        repo = Path(workspace) / child["dirname"]
        info = describe_repo(str(repo))
        info["agents"] = []
        repos.append(info)
        fields = [key for key in ("description", "version") if not _good_field(info.get(key))]
        if frontmatter_unterminated(str(repo / "lore-repo.md")):
            fields.append("frontmatter_unterminated")
        if fields:
            findings.append(finding("R1", "error", "repos", "metadata", repo=info["name"], fields=fields))
        if version is not None and _good_field(info.get("version")) and compare_versions(info["version"], str(version))["verdict"] != "match":
            findings.append(finding("R2", "warn", "repos", "versions", repo=info["name"], actual=info["version"], expected=version))
        own_git = git_toplevel(str(repo)) == str(repo.resolve())
        dirty = []
        if own_git:
            dirty = changed_repo_paths(repo)
            if dirty is None:
                warnings.append("Repo status unavailable for %s" % repo)
                dirty = []
        candidates = sorted((repo / "agents").iterdir()) if (repo / "agents").is_dir() else []
        for agent in candidates:
            if not agent.is_dir() or agent.name.startswith("."):
                continue
            if agent.is_symlink() and not agent.resolve().is_relative_to(repo.resolve()):
                warnings.append("Agent outside repo not scanned: %s" % agent)
                continue
            info["agents"].append(agent.name)
            base = {"repo": info["name"], "agent": agent.name}
            missing = [name for name in ("role.md", "lore", "workdir")
                       if not ((agent / name).is_file() if name.endswith(".md") else (agent / name).is_dir())]
            if missing:
                findings.append(finding("R5", "error", "repos", "files", **base, missing=missing))
            if not (agent / "lore-context.md").exists():
                findings.append(finding("R5", "info", "repos", "files", **base,
                                        missing=["lore-context.md"], reason="optional_context_absent"))
            elif not (agent / "lore-context.md").is_file():
                findings.append(finding("R5", "error", "repos", "files", **base,
                                        missing=["lore-context.md"], reason="context_not_a_file"))
            role = read_text(str(agent / "role.md"))
            fm = parse_frontmatter(role)
            if role is not None:
                if not _good_field(fm.get("description")) or frontmatter_unterminated(str(agent / "role.md")):
                    findings.append(finding("R4", "error", "repos", "metadata", **base, field="description"))
                if "version" in fm:
                    findings.append(finding("R4", "info", "repos", "metadata", **base, field="legacy_version"))
            if str(agent.resolve()) not in registered:
                findings.append(finding("R10", "info", "repos", "shortcuts", **base))
            reflections = agent / "reflections"
            if reflections.is_dir() and any(reflections.iterdir()):
                findings.append(finding("R7", "warn", "repos", "reflections", **base))
            prefix = "agents/%s/" % agent.name
            changed = [p for p in dirty if p in (prefix + "role.md", prefix + "lore-context.md") or p.startswith(prefix + "lore/")]
            if changed:
                findings.append(finding("R8", "warn", "repos", "uncommitted", **base, paths=changed))
            try:
                graph = build_lore_graph(str(agent))
                if graph["git_error"]:
                    warnings.append("Lore history unavailable for %s: %s" % (agent, graph["git_error"]))
                coverage = lore_coverage(graph)
                for kind in ("legacy", "unsupported_version", "invalid_utf8"):
                    count = coverage["uncovered"].get(kind, 0)
                    if count:
                        findings.append(finding("R6", "error" if kind == "invalid_utf8" else "info",
                                                "repos", "lore_coverage", **base,
                                                issue=kind, count=count))
                for issue in graph["findings"]:
                    severity = "info" if (issue["issue"] == "missing_context" or issue["issue"].startswith(("legacy", "unsupported"))) else "warn"
                    if issue["issue"].endswith("error") or "invalid" in issue["issue"]:
                        severity = "error"
                    findings.append(finding("R6", severity, "repos", "lore", **base, **issue))
                for file, node in graph["nodes"].items():
                    for reference in node.get("unresolved_safety", []):
                        findings.append(finding("R6", "info", "repos", "reference_cautions", **base,
                                                file=file, issue="unresolved_legacy_reference", reference=reference))
                # The graph already queried history once for all Lore files.
                context_date = graph["nodes"].get("lore-context.md", {}).get("last_modified_iso")
                newer = [p for p, n in graph["nodes"].items()
                         if p.startswith("lore/") and context_date and n.get("last_modified_iso")
                         and datetime.fromisoformat(n["last_modified_iso"]) > datetime.fromisoformat(context_date)]
                if newer:
                    findings.append(finding("R9", "warn", "repos", "summary_age", **base, topics=newer, context_date=context_date))
                info.setdefault("coverage", {})[agent.name] = coverage
            except (OSError, ValueError) as exc:
                warnings.append("Lore validation incomplete for %s: %s" % (agent, exc))
        if not info["agents"]:
            findings.append(finding("R3", "info", "repos", "agents", repo=info["name"]))
    check_shortcuts(workspace, framework_root, findings, warnings)
    return repos, findings, warnings

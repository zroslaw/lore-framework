"""Unified health scan. Reads state; never repairs, pulls, or changes freshness.

1. Run the existing workspace scan once; keep its public contract unchanged.
2. Derive the three installation states from that result. Context probes only
   inspect descriptor presence, never scan an ancestor's contents.
3. Add plugin, repo, and per-repo freshness findings. S11 is represented by R10.
4. Return exact counts, collapse metadata, and explicit AI/not-run coverage.
"""
from collections import Counter
import os
from pathlib import Path

from .common import resolve_framework_root
from .freshness import repo_freshness
from .plugin_scan import finding, scan_plugin, version_at
from .repo_scan import check_shortcuts, scan_repos
from .workspace_scan import run_workspace_scan

COLLAPSE_UNINITIALIZED = {"S4", "S5", "S10", "S17", "S18"}
S_CATEGORIES = {"S1": "uncommitted", "S2": "publication", "S3": "remotes",
                "S4": "workspace_setup", "S5": "declarations", "S6": "missing_repos",
                "S7": "gitignore", "S8": "branches", "S9": "worktrees",
                "S10": "memory", "S12": "uncommitted", "S13": "repo_conflicts",
                "S14": "behind", "S15": "shortcuts", "S16": "branches",
                "S17": "routing", "S18": "plugin_settings"}


def location_context(workspace):
    # The framework's worktree convention gets first chance, without invoking refresh.
    from .workspace_refresh import resolve_workspace_root
    root = Path(workspace).resolve()
    candidate = resolve_workspace_root(str(root))
    if candidate and candidate != str(root) and (Path(candidate) / "lore-workspace.md").is_file():
        return {"case": "1c", "workspace_root": candidate, "repo": None}
    repo = None
    for path in (root, *root.parents):
        if path != root and (path / "lore-workspace.md").is_file():
            return {"case": "1c", "workspace_root": str(path), "repo": repo}
        if repo is None and (path / "lore-repo.md").is_file():
            repo = str(path)
    if repo:
        return {"case": "1b", "workspace_root": str(Path(repo).parent), "repo": repo}
    below = sorted(str(p) for p in root.iterdir()
                   if p.is_dir() and not p.name.startswith(".") and (p / "lore-workspace.md").is_file())
    return {"case": "1d" if below else "1a", "workspace_roots": below,
            "search_depth": 1, "repo": None, "workspace_root": None}


def summarize(findings):
    result = {}
    for layer in ("plugin", "repos", "workspace"):
        rows = [f for f in findings if f["layer"] == layer]
        result[layer] = {"total": len(rows),
                         "severity": dict(Counter(f["severity"] for f in rows)),
                         "categories": dict(Counter(f["category"] for f in rows))}
    return result


def run_check(workspace, framework_root, engine=None, no_network=False, scope="all", now=None):
    workspace = os.path.realpath(workspace)
    if not os.path.isdir(workspace):
        raise ValueError("workspace directory does not exist: %s" % workspace)
    state_data, warnings = run_workspace_scan(workspace, framework_root, engine)
    state = (1 if not state_data["applicable"] else
             3 if state_data["descriptors"]["lore_workspace"] else 2)
    findings = []
    plugin, repos = None, []
    if scope in ("all", "plugin"):
        plugin, items, notes = scan_plugin(framework_root, state_data["engine"], no_network)
        findings.extend(items)
        warnings.extend(notes)
    children = state_data.get("children", [])
    if scope in ("all", "repos") and state > 1:
        repos, items, notes = scan_repos(workspace, framework_root, children,
                                       (plugin or {}).get("version") or
                                       version_at(framework_root))
        findings.extend(items)
        warnings.extend(notes)
    elif scope in ("all", "repos"):
        # Local shortcuts can outlive the last repo (and workspace descriptor).
        check_shortcuts(workspace, framework_root, findings, warnings)
    freshness = []
    if scope in ("all", "workspace"):
        for row in state_data["findings"]:
            if row["id"] == "S11":
                # Same predicate as R10. Scoped workspace runs still expose it.
                if scope == "workspace":
                    findings.append(dict(row, layer="workspace", category="shortcuts"))
                continue
            findings.append(dict(row, layer="workspace", category=S_CATEGORIES[row["id"]]))
        candidates = []
        root_git = state_data.get("git", {})
        if root_git.get("own_root") and root_git.get("origin"):
            candidates.append(workspace)
        candidates.extend(os.path.join(workspace, c["dirname"]) for c in children
                          if c.get("git") and c.get("origin") and not c.get("escapes_workspace"))
        for repo in sorted(set(os.path.realpath(p) for p in candidates)):
            row = repo_freshness(repo, now)
            freshness.append(row)
            if row["status"] != "recent":
                findings.append(finding("S19", "warn", "workspace", "freshness", **row))
    order = {"error": 0, "warn": 1, "info": 2}
    findings.sort(key=lambda f: (order[f["severity"]], f["id"], str(f["data"])))
    for row in findings:
        # Do not conceal actual malformed files or unsafe enclosing Git state.
        row["collapsed"] = (state < 3 and row["id"] in COLLAPSE_UNINITIALIZED
                            and not (row["id"] == "S4" and row["data"].get("enclosing_root"))
                            and not (row["id"] == "S18" and row["data"].get("unresolvable")))
    visible = [f for f in findings if not f["collapsed"]]
    return {"state": state, "context": location_context(workspace) if state == 1 else None,
            "engine": state_data["engine"], "scope": scope, "plugin": plugin,
            "repos": repos, "workspace": state_data, "freshness": freshness,
            "findings": findings, "summary": summarize(visible),
            "collapsed_count": len(findings) - len(visible),
            "semantic_review": "not_run", "complete": not warnings}, warnings


def cmd_check(args, res):
    data, warnings = run_check(args.workspace, resolve_framework_root(args.framework_root),
                               args.engine, args.no_network, args.scope)
    res.data.update(data)
    res.warnings.extend(warnings)

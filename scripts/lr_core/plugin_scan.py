"""Read-only plugin inventory; the sole remote probe is a bounded tag listing."""
import glob
import json
import os
from pathlib import Path
import re
import runpy

from .common import read_text, run, network_env


def finding(code, severity, layer, category, **data):
    return {"id": code, "severity": severity, "layer": layer,
            "category": category, "data": data}


def version_at(root):
    value = (read_text(os.path.join(str(root), "VERSION")) or "").strip()
    return int(value) if re.fullmatch(r"[0-9]+", value) else None


def installed_trees(engine, home):
    patterns = {
        "claude": [".claude/plugins/cache/*/lr/*/VERSION", ".claude/plugins/marketplaces/*/VERSION"],
        "codex": [".codex/plugins/cache/*/lr/*/VERSION", ".codex/plugins/cache/*/*/VERSION",
                  ".codex/.tmp/marketplaces/*/VERSION"],
        "cursor": [".cursor/plugins/*/*/VERSION", ".cursor/plugins/*/*/*/VERSION",
                   ".cursor/plugins/*/*/*/*/VERSION"],
    }
    roots = set()
    for pattern in patterns.get(engine, []):
        for path in glob.glob(os.path.join(home, pattern)):
            root = os.path.dirname(path)
            # VERSION is not a plugin identity: avoid unrelated plugins with numeric stamps.
            for manifest in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json",
                             ".cursor-plugin/plugin.json"):
                try:
                    if json.loads(read_text(os.path.join(root, manifest)) or "{}").get("name") == "lr":
                        roots.add(os.path.realpath(root))
                except (ValueError, AttributeError):
                    pass
    return sorted(roots)


def migration_issues(text):
    match = re.search(r"^## Write Paths\s*$", text, re.M)
    if not match:
        return ["missing_section"]
    section = re.split(r"^#{2,3} ", text[match.end():], maxsplit=1, flags=re.M)[0]
    block = re.search(r"^```[^\n]*\n(.*?)^```\s*$", section, re.M | re.S)
    if not block:
        return ["missing_fence"]
    bad = []
    for line in block.group(1).splitlines():
        value = line.strip()
        if not value or value.startswith("#") or re.match(r"^\(none\)(?:\s|$)", value):
            continue
        token = re.split(r"\s+#", value, maxsplit=1)[0]
        if not re.fullmatch(r"[A-Za-z0-9._/\-*?\[\]!\\]+", token):
            bad.append(value)
    return bad


def scan_plugin(root, engine, no_network=False, home=None):
    home = os.path.expanduser("~") if home is None else home
    root = Path(root).resolve()
    version = version_at(root)
    findings, warnings = [], []
    data = {"root": str(root), "version": version, "upstream": "unknown",
            "newer_at": [], "latest_version": None}
    if engine == "unknown":
        findings.append(finding("P3", "warn", "plugin", "engine", engine=engine))
    expected = "1.%s.0" % version if version is not None else None
    if expected is None:
        findings.append(finding("P4", "error", "plugin", "versions", path="VERSION", reason="invalid_version"))
    marketplace = {}
    for rel, optional in ((".claude-plugin/plugin.json", False),
                          (".claude-plugin/marketplace.json", True),
                          (".cursor-plugin/plugin.json", False),
                          (".codex-plugin/plugin.json", True)):
        path = root / rel
        if optional and not path.exists():
            continue
        try:
            manifest = json.loads(path.read_text(encoding="utf-8-sig"))
            if rel.endswith("marketplace.json"):
                marketplace = next(p for p in manifest["plugins"] if p["name"] == "lr")
                actual = marketplace["version"]
            else:
                actual = manifest["version"]
            if actual != expected:
                findings.append(finding("P4", "error", "plugin", "versions", path=rel,
                                        actual=actual, expected=expected))
        except (OSError, ValueError, KeyError, TypeError, AttributeError, StopIteration) as exc:
            findings.append(finding("P4", "error", "plugin", "versions", path=rel, reason=str(exc)))
    for tree in installed_trees(engine, home):
        other = version_at(tree)
        if other is not None and version is not None and other > version:
            data["newer_at"].append({"root": tree, "version": other})
        if (engine == "codex" and "/.tmp/marketplaces/" in tree and
                other is not None and version is not None and other < version):
            findings.append(finding("P5", "warn", "plugin", "cache", root=tree, version=other))
    if data["newer_at"]:
        findings.append(finding("P2", "warn", "plugin", "cache", loaded=str(root), newer_at=data["newer_at"]))
    url = marketplace.get("repository") if isinstance(marketplace, dict) else None
    if no_network:
        data["upstream"] = "skipped"
    elif isinstance(url, str) and re.match(r"^(https://|ssh://|git@)", url):
        rc, out, _ = run(["git", "ls-remote", "--tags", "--refs", "--", url, "lr--v1.*"],
                         timeout=15, env_extra=network_env())
        if rc == 0:
            versions = [int(v) for v in re.findall(r"refs/tags/lr--v1\.([0-9]+)\.0$", out, re.M)]
            if versions:
                latest = max(versions)
                data.update(upstream="checked", latest_version=latest)
                if version is not None and latest > version:
                    findings.append(finding("P1", "info", "plugin", "versions", installed=version, latest=latest))
    for path in sorted((root / "migrations").glob("[0-9]*.md")):
        try:
            issues = migration_issues(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError) as exc:
            issues = [str(exc)]
        if issues:
            findings.append(finding("P6", "error", "plugin", "migrations", path=str(path.relative_to(root)), issues=issues))
    # The generator itself defines parity. Importing it does not run main or write files.
    try:
        generator = runpy.run_path(str(root / "scripts/sync-cursor-skills"))
        names = sorted(p.parent.name for p in (root / "skills").glob("*/SKILL.md"))
        expected_paths = generator["expected_wrappers"](names)
        for path, content in expected_paths.items():
            if read_text(str(path)) != content:
                findings.append(finding("P7", "error", "plugin", "skills", path=str(path.relative_to(root)), reason="missing_or_drifted"))
        # Match the generator's directory-level stale checks, including empty remnants.
        cursor = root / ".cursor-skills"
        expected_dirs = {path.parent.name for path in expected_paths}
        if cursor.is_dir():
            for path in sorted(cursor.iterdir()):
                if path.is_dir() and path.name not in expected_dirs:
                    findings.append(finding("P7", "error", "plugin", "skills", path=str(path.relative_to(root)), reason="orphan"))
        legacy = root / "skills/cursor"
        if legacy.exists():
            findings.append(finding("P7", "error", "plugin", "skills", path="skills/cursor", reason="legacy"))
    except (OSError, ValueError, KeyError) as exc:
        warnings.append("Cursor parity could not be checked: %s" % exc)
    return data, findings, warnings

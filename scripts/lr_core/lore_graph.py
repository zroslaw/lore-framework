"""Lore v1 parsing, graph reconstruction, and coverage."""

from .common import *
from .preflight import git_toplevel
from .scan import git_last_modified

def estimate_tokens(text):
    """The documented dependency-free estimate: ceil(Unicode chars / 4)."""
    return (len(text) + 3) // 4


def sha256_bytes(content):
    return hashlib.sha256(content).hexdigest()


def _yaml_scalar(value):
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, float):
        return "%.1f" % value
    if isinstance(value, int):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def _yaml_lines(value, indent=0):
    """Emit the deliberately small, deterministic YAML subset used by Lore."""
    lines = []
    stack = [("value", value, indent)]
    while stack:
        task = stack.pop()
        kind = task[0]
        if kind == "value":
            _, item, level = task
            pad = " " * level
            if isinstance(item, dict):
                if not item:
                    lines.append(pad + "{}")
                else:
                    for key, child in reversed(list(item.items())):
                        stack.append(("dict_item", key, child, level))
            elif isinstance(item, list):
                if not item:
                    lines.append(pad + "[]")
                else:
                    for child in reversed(item):
                        stack.append(("list_item", child, level))
            else:
                lines.append(pad + _yaml_scalar(item))
        elif kind == "dict_item":
            _, key, child, level = task
            prefix = " " * level + str(key) + ":"
            if isinstance(child, dict):
                if child:
                    lines.append(prefix)
                    stack.append(("value", child, level + 2))
                else:
                    lines.append(prefix + " {}")
            elif isinstance(child, list):
                if child:
                    lines.append(prefix)
                    stack.append(("value", child, level + 2))
                else:
                    lines.append(prefix + " []")
            else:
                lines.append(prefix + " " + _yaml_scalar(child))
        elif kind == "list_item":
            _, item, level = task
            pad = " " * level
            if isinstance(item, dict):
                if not item:
                    lines.append(pad + "- {}")
                else:
                    pairs = list(item.items())
                    for index in range(len(pairs) - 1, -1, -1):
                        key, child = pairs[index]
                        stack.append(("list_dict_item", key, child, level,
                                      index == 0))
            elif isinstance(item, list):
                lines.append(pad + "-")
                stack.append(("value", item, level + 2))
            else:
                lines.append(pad + "- " + _yaml_scalar(item))
        else:  # list_dict_item
            _, key, child, level, first = task
            prefix = " " * level + ("- " if first else "  ") + str(key) + ":"
            if isinstance(child, dict):
                if child:
                    lines.append(prefix)
                    stack.append(("value", child, level + 4))
                else:
                    lines.append(prefix + " {}")
            elif isinstance(child, list):
                if child:
                    lines.append(prefix)
                    stack.append(("value", child, level + 4))
                else:
                    lines.append(prefix + " []")
            else:
                lines.append(prefix + " " + _yaml_scalar(child))
    return lines


def yaml_dump(value):
    return "\n".join(_yaml_lines(value)) + "\n"


def emit_yaml_fatal(command, message):
    payload = {
        command.replace("-", "_"): {
            "ok": False,
            "error": message,
        }
    }
    sys.stdout.write(yaml_dump(payload))
    return 2


def _read_lore_text(path):
    """Read canonical Lore input strictly; replacement characters hide damage."""
    with open(path, "rb") as fh:
        return fh.read().decode("utf-8-sig")


def discover_lore_files(agent_dir):
    """Discover the fixed root and regular Markdown below lore/, recursively.

    Hidden directories, hidden files, and symlinks are excluded. Returned keys
    are POSIX agent-root-relative paths, regardless of the host OS.
    """
    agent_dir = os.path.realpath(os.path.abspath(agent_dir))
    if not os.path.isdir(agent_dir):
        raise ValueError("agent directory not found: %s" % agent_dir)
    found = []
    root = os.path.join(agent_dir, "lore-context.md")
    if os.path.isfile(root) and not os.path.islink(root):
        found.append(("lore-context.md", root))
    lore_dir = os.path.join(agent_dir, "lore")
    if os.path.isdir(lore_dir) and not os.path.islink(lore_dir):
        for dirpath, dirnames, filenames in os.walk(lore_dir, topdown=True,
                                                    followlinks=False):
            dirnames[:] = sorted(
                name for name in dirnames
                if not name.startswith(".")
                and not os.path.islink(os.path.join(dirpath, name)))
            for name in sorted(filenames):
                path = os.path.join(dirpath, name)
                if (name.startswith(".") or not name.endswith(".md")
                        or os.path.islink(path) or not os.path.isfile(path)):
                    continue
                rel = os.path.relpath(path, agent_dir).replace(os.sep, "/")
                found.append((rel, path))
    return sorted(found)


def _valid_parent_path(value):
    if not isinstance(value, str) or not LORE_PARENT_RE.match(value):
        return False
    if value.startswith("/") or "\\" in value:
        return False
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        return False
    return value == "lore-context.md" or (
        value.startswith("lore/") and value.endswith(".md"))


def parse_lore_frontmatter(text, rel_path):
    """Parse Lore v1's exact scalar frontmatter without a YAML dependency."""
    if text.startswith("\ufeff"):
        text = text[1:]
    lines = text.splitlines()
    result = {
        "version": None,
        "kind": "legacy",
        "metadata": {},
        "content_start": 0,
        "issues": [],
    }
    if not lines or lines[0] != "---":
        return result

    close = None
    for idx in range(1, len(lines)):
        if lines[idx] == "---":
            close = idx
            break
    body = lines[1:close] if close is not None else lines[1:]
    result["content_start"] = (close + 1) if close is not None else 0

    raw_lore = []
    for line in body:
        match = re.match(r"^lore:\s*(-?\d+)\s*$", line)
        if match:
            raw_lore.append(int(match.group(1)))
    if raw_lore:
        result["version"] = raw_lore[0]
    if result["version"] is None:
        return result
    if result["version"] != LORE_FORMAT_VERSION:
        result["kind"] = "unsupported_version"
        return result

    result["kind"] = "candidate_v1"
    if close is None:
        result["issues"].append(("frontmatter_unclosed", None))
        return result

    allowed = {"lore", "type", "summary", "parent"}
    values = {}
    for line_number, line in enumerate(body, 2):
        match = re.match(r"^([A-Za-z0-9_-]+):(?:\s(.*))?$", line)
        if not match:
            result["issues"].append(("invalid_frontmatter_line", line_number))
            continue
        key = match.group(1)
        value = match.group(2) if match.group(2) is not None else ""
        # Hand-edited scalar lines commonly pick up harmless trailing spaces.
        # Ignore only whitespace outside the value; leading whitespace and
        # whitespace inside a quoted summary remain significant.
        value = value.rstrip(" \t")
        if key not in allowed:
            result["issues"].append(("unknown_frontmatter_key", key))
            continue
        if key in values:
            result["issues"].append(("duplicate_frontmatter_key", key))
            continue
        values[key] = value

    if values.get("lore") != "1":
        result["issues"].append(("invalid_lore_version", values.get("lore")))

    kind = values.get("type")
    if kind not in ("context", "area", "topic"):
        result["issues"].append(("invalid_type", kind))
    else:
        result["metadata"]["type"] = kind

    raw_summary = values.get("summary")
    summary = None
    if raw_summary is None:
        result["issues"].append(("missing_summary", None))
    elif not (len(raw_summary) >= 2 and raw_summary[0] == '"'
              and raw_summary[-1] == '"'):
        result["issues"].append(("invalid_summary", raw_summary))
    else:
        try:
            summary = json.loads(raw_summary)
        except (TypeError, ValueError):
            result["issues"].append(("invalid_summary", raw_summary))
        else:
            if not isinstance(summary, str) or not summary.strip():
                result["issues"].append(("invalid_summary", raw_summary))
            elif any(0xD800 <= ord(char) <= 0xDFFF for char in summary):
                result["issues"].append(("invalid_summary", raw_summary))
            elif len(summary) > SUMMARY_MAX_CHARS:
                result["issues"].append(("summary_too_long", len(summary)))
            elif "\n" in summary or "\r" in summary:
                result["issues"].append(("invalid_summary", raw_summary))
            else:
                result["metadata"]["summary"] = summary

    raw_parent = values.get("parent")
    if kind == "context":
        if rel_path != "lore-context.md":
            result["issues"].append(("context_wrong_path", rel_path))
        if raw_parent is not None:
            result["issues"].append(("context_has_parent", raw_parent))
    elif kind in ("area", "topic"):
        if raw_parent is None:
            result["issues"].append(("missing_parent", None))
        elif not _valid_parent_path(raw_parent):
            result["issues"].append(("invalid_parent_path", raw_parent))
        else:
            result["metadata"]["parent"] = raw_parent
    return result


def _first_h1(text, content_start=0, fallback=None):
    lines = text.splitlines()[content_start:]
    for line in lines:
        match = re.match(r"^#\s+(.+?)\s*$", line)
        if match:
            return match.group(1).strip()[:TITLE_MAX_CHARS]
    return fallback


def _code_filtered_lines(text):
    """Return (formal_text, legacy_text), excluding block code from both.

    Inline code is blanked only in formal_text; its .md references remain in
    legacy_text for conservative destructive-change safety.
    """
    formal, legacy = [], []
    fence = None
    for line in text.splitlines():
        opening = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if fence:
            if re.match(r"^ {0,3}%s{%d,}\s*$" %
                        (re.escape(fence[0]), fence[1]), line):
                fence = None
            formal.append("")
            legacy.append("")
            continue
        if opening:
            marker = opening.group(1)
            fence = (marker[0], len(marker))
            formal.append("")
            legacy.append("")
            continue
        if line.startswith("    ") or line.startswith("\t"):
            formal.append("")
            legacy.append("")
            continue
        legacy.append(line)
        formal.append(re.sub(r"(`+)(.*?)\1", lambda m: " " * len(m.group(0)), line))
    return "\n".join(formal), "\n".join(legacy)


def _resolve_link_target(source, target, discovered):
    """Return (state, path): edge/missing/escape/absolute/ignore."""
    try:
        target = urllib.parse.unquote(target)
    except Exception:
        pass
    target = target.split("#", 1)[0]
    if not target:
        return "ignore", None
    if target.startswith("/") or re.match(r"^[A-Za-z]:[/\\]", target):
        return "absolute", target
    parsed = urllib.parse.urlsplit(target)
    if parsed.scheme or parsed.netloc or target.startswith("//"):
        return "ignore", None
    target = target.replace("\\", "/")
    if target == "lore-context.md" or target.startswith("lore/"):
        candidate = posixpath.normpath(target)
    else:
        candidate = posixpath.normpath(posixpath.join(posixpath.dirname(source), target))
    if candidate == ".." or candidate.startswith("../"):
        return "escape", candidate
    if candidate in discovered:
        return "edge", candidate
    lore_intent = (candidate == "lore-context.md" or candidate.startswith("lore/"))
    if lore_intent and candidate.endswith(".md"):
        return "missing", candidate
    return "ignore", candidate


def _parse_links(source, text, discovered):
    formal_text, legacy_text = _code_filtered_lines(text)
    formal_targets = []
    legacy_tokens = []
    html_targets = []
    findings = []
    occupied = []

    markdown_title = r'(?:"(?:\\.|[^"\n])*"|\'(?:\\.|[^\'\n])*\'|\((?:\\.|[^)\n])*\))'
    definitions = {}
    definition_re = re.compile(
        r"(?m)^ {0,3}\[([^\]]+)\]:\s*(<[^>]+>|\S+)"
        r"(?:\s+" + markdown_title + r")?\s*$")
    for match in definition_re.finditer(formal_text):
        raw = match.group(2)
        definitions.setdefault(
            match.group(1).strip().lower(),
            raw[1:-1] if raw.startswith("<") else raw,
        )
        occupied.append(match.span())

    patterns = [
        re.compile(
            r"(?<!!)\[[^\]\n]+\]\(\s*(<[^>\n]+>|[^\s()<>]+)"
            r"(?:\s+" + markdown_title + r")?\s*\)"),
        # Obsidian embeds (`![[...]]`) are media inclusion, not Lore graph
        # edges. Keep them out of the formal graph; the conservative safety
        # scan below can still notice a Markdown filename inside the embed.
        re.compile(r"(?<!!)\[\[([^\]\n]+)\]\]"),
    ]
    for pattern in patterns:
        for match in pattern.finditer(formal_text):
            raw = match.group(1)
            formal_targets.append(raw[1:-1] if raw.startswith("<") else raw)
            occupied.append(match.span())
    for match in re.finditer(r"(?<!!)\[[^\]\n]+\]\[([^\]\n]+)\]", formal_text):
        ref = match.group(1).strip().lower()
        if ref in definitions:
            formal_targets.append(definitions[ref])
            occupied.append(match.span())

    for match in re.finditer(r"(?i)<a\b[^>]*\bhref\s*=\s*(['\"])(.*?)\1[^>]*>",
                             legacy_text):
        html_targets.append(match.group(2))
        occupied.append(match.span(2))

    mask = list(legacy_text)
    for start, end in occupied:
        for idx in range(max(0, start), min(end, len(mask))):
            if mask[idx] != "\n":
                mask[idx] = " "
    plain = "".join(mask)
    token_re = re.compile(
        r"(?<![A-Za-z0-9._/-])((?:lore/)?[A-Za-z0-9][A-Za-z0-9._/-]*\.md)"
        r"(?![A-Za-z0-9._/-])")
    legacy_tokens.extend(match.group(1) for match in token_re.finditer(plain))

    edges = set()
    safety = set()
    unresolved_safety = []
    for raw in formal_targets:
        state, target = _resolve_link_target(source, raw, discovered)
        if state == "edge":
            edges.add(target)
            safety.add(target)
        elif state in ("missing", "escape", "absolute"):
            findings.append({
                "file": source,
                "issue": "broken_lore_link" if state == "missing" else "unsafe_lore_link",
                "value": target,
            })
    for raw in html_targets:
        state, target = _resolve_link_target(source, raw, discovered)
        if state == "edge":
            safety.add(target)
        elif state in ("missing", "escape", "absolute"):
            findings.append({
                "file": source,
                "issue": "broken_safety_reference" if state == "missing"
                         else "unsafe_safety_reference",
                "value": target,
            })

    by_basename = {}
    for path in discovered:
        by_basename.setdefault(posixpath.basename(path), []).append(path)
    for raw in legacy_tokens:
        if raw == "lore-context.md" or raw.startswith("lore/") or "/" in raw:
            state, target = _resolve_link_target(source, raw, discovered)
            if state == "edge":
                safety.add(target)
            elif state in ("missing", "escape", "absolute"):
                unresolved_safety.append(raw)
            continue
        matches = sorted(by_basename.get(raw, []))
        if len(matches) == 1:
            safety.add(matches[0])
        elif len(matches) > 1:
            findings.append({"file": source, "issue": "ambiguous_legacy_reference",
                             "value": raw})
            unresolved_safety.append(raw)
        else:
            unresolved_safety.append(raw)
    return {
        "outbound": sorted(edges),
        "safety": sorted(safety),
        "unresolved_safety": sorted(set(unresolved_safety)),
        "findings": findings,
    }


def _git_file_state(agent_dir, paths):
    """Return committed dates and uncommitted paths without per-file git calls."""
    repo = _repo_root_for(agent_dir)
    if not repo:
        return {}, set(), None
    top = git_toplevel(repo)
    if not top:
        return {}, set(), None
    agent_rel = os.path.relpath(os.path.realpath(agent_dir), top).replace(os.sep, "/")
    dates, error = git_last_modified(top, agent_rel)
    mapped_dates = {}
    for path in paths:
        repo_rel = posixpath.join(agent_rel, path)
        iso = dates.get(repo_rel)
        mapped_dates[path] = iso

    changed = set()
    rc, out, err = git(top, ["status", "--porcelain=v1", "-z",
                              "--untracked-files=all", "--",
                              agent_rel], timeout=GIT_TIMEOUT_SEC)
    if not git_answered(rc):
        return mapped_dates, changed, (error or err.strip() or "could not run git status")
    if rc != 0:
        return mapped_dates, changed, (error or err.strip() or
                                       "git status exited %d" % rc)
    prefix = agent_rel.rstrip("/") + "/"
    records = out.split("\0")
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if len(record) < 4:
            continue
        status = record[:2]
        raw = record[3:]
        # In porcelain v1 -z form a rename/copy's current path is in the
        # main record and its source path follows as a second NUL field.
        if "R" in status or "C" in status:
            index += 1
        if raw.startswith(prefix):
            rel = raw[len(prefix):]
            if rel in paths:
                changed.add(rel)
    return mapped_dates, changed, error


def _finding(file_path, issue, value=None):
    item = {"file": file_path, "issue": issue}
    if value is not None:
        item["value"] = value
    return item


def build_lore_graph(agent_dir):
    """Build the complete v1 taxonomy and wider reference graph in memory."""
    agent_dir = os.path.realpath(os.path.abspath(agent_dir))
    discovered_pairs = discover_lore_files(agent_dir)
    if not discovered_pairs:
        raise ValueError("no Lore Markdown files found in %s" % agent_dir)
    discovered = {rel: full for rel, full in discovered_pairs}
    texts = {}
    nodes = {}
    findings = []
    for rel, full in discovered_pairs:
        try:
            with open(full, "rb") as handle:
                raw_content = handle.read()
        except (IOError, OSError) as exc:
            raise ValueError("cannot read %s: %s" % (rel, exc))
        invalid_utf8 = False
        try:
            text = raw_content.decode("utf-8-sig")
        except UnicodeError:
            # Keep boot and navigation available when one file is damaged.
            # Replacement text supplies only a rough size estimate; the file
            # is never parsed, mapped, linked, or selected for grooming.
            invalid_utf8 = True
            text = raw_content.decode("utf-8-sig", errors="replace")
        texts[rel] = text
        parsed = ({
            "version": None,
            "kind": "invalid_utf8",
            "metadata": {},
            "content_start": 0,
            "issues": [],
        } if invalid_utf8 else parse_lore_frontmatter(text, rel))
        fallback = posixpath.basename(rel)[:-3] if rel.endswith(".md") else rel
        node = {
            "file": rel,
            "full_path": full,
            "text": text,
            "sha256": sha256_bytes(raw_content),
            "estimated_tokens": estimate_tokens(text),
            "title": _first_h1(text, parsed["content_start"], fallback),
            "version": parsed["version"],
            "parse_kind": parsed["kind"],
            "type": parsed["metadata"].get("type"),
            "summary": parsed["metadata"].get("summary"),
            "parent": parsed["metadata"].get("parent"),
            "invalid_utf8": invalid_utf8,
            "local_invalid": bool(parsed["issues"]),
            "children": [],
            "coverage_reason": None,
        }
        for issue, value in parsed["issues"]:
            findings.append(_finding(rel, issue, value))
        nodes[rel] = node

    # Formal and conservative inbound-reference graphs include every readable
    # file, independent of taxonomy coverage or supported schema version.
    # Invalid UTF-8 is counted separately because its references cannot be
    # scanned reliably.
    inbound = {path: set() for path in nodes}
    safety_inbound = {path: set() for path in nodes}
    for rel in sorted(nodes):
        if nodes[rel]["invalid_utf8"]:
            links = {"outbound": [], "safety": [],
                     "unresolved_safety": [], "findings": []}
        else:
            links = _parse_links(rel, texts[rel], set(nodes))
        nodes[rel]["outbound"] = links["outbound"]
        nodes[rel]["safety_outbound"] = links["safety"]
        nodes[rel]["unresolved_safety"] = links["unresolved_safety"]
        findings.extend(links["findings"])
        for target in links["outbound"]:
            inbound[target].add(rel)
        for target in links["safety"]:
            safety_inbound[target].add(rel)
    for rel, node in nodes.items():
        node["inbound"] = sorted(inbound[rel])
        node["safety_inbound"] = sorted(safety_inbound[rel])

    root = nodes.get("lore-context.md")
    context_claims = sorted(path for path, node in nodes.items()
                            if node["parse_kind"] == "candidate_v1"
                            and node["type"] == "context")
    if len(context_claims) > 1:
        for path in context_claims:
            findings.append(_finding(path, "duplicate_context", len(context_claims)))
    root_is_v1 = bool(root and root["parse_kind"] == "candidate_v1"
                      and not root["local_invalid"] and root["type"] == "context")
    root_is_legacy = bool(root and root["parse_kind"] == "legacy")
    if root is None:
        findings.append(_finding("lore-context.md", "missing_context"))
    elif root["parse_kind"] == "candidate_v1" and root["type"] != "context":
        root["local_invalid"] = True
        findings.append(_finding("lore-context.md", "root_wrong_type", root["type"]))
        root_is_v1 = False
    elif root["parse_kind"] == "unsupported_version":
        findings.append(_finding("lore-context.md", "unsupported_context_version",
                                 root["version"]))
    elif root_is_v1:
        if root["estimated_tokens"] > CONTEXT_ERROR_TOKENS:
            findings.append(_finding("lore-context.md", "context_size_error",
                                     root["estimated_tokens"]))
        elif root["estimated_tokens"] > CONTEXT_WARN_TOKENS:
            findings.append(_finding("lore-context.md", "context_size_warning",
                                     root["estimated_tokens"]))
    elif root_is_legacy and root["estimated_tokens"] > LEGACY_CONTEXT_ERROR_TOKENS:
        findings.append(_finding("lore-context.md", "context_size_error",
                                 root["estimated_tokens"]))

    # Validate each immediate parent relation. A child of the fixed legacy
    # root is the sole compatibility exception: locally valid but unreachable.
    for rel in sorted(nodes):
        node = nodes[rel]
        if node["parse_kind"] != "candidate_v1" or node["local_invalid"]:
            continue
        if node["type"] == "context":
            continue
        parent_path = node["parent"]
        parent = nodes.get(parent_path)
        if parent is None:
            node["local_invalid"] = True
            findings.append(_finding(rel, "missing_parent", parent_path))
            continue
        if parent_path == "lore-context.md" and root_is_legacy:
            parent["children"].append(rel)
            continue
        if (parent["parse_kind"] != "candidate_v1" or parent["local_invalid"]
                or parent["type"] not in ("context", "area")):
            node["local_invalid"] = True
            issue = "parent_is_topic" if parent["type"] == "topic" else "invalid_parent"
            findings.append(_finding(rel, issue, parent_path))
            continue
        parent["children"].append(rel)

    for node in nodes.values():
        node["children"] = sorted(set(node["children"]))

    # Detect cycles among locally valid v1 parent edges. Every cycle member is
    # invalid; descendants remain structurally valid but unreachable.
    visited, cycle_members = set(), set()
    for start_path in sorted(nodes):
        if start_path in visited:
            continue
        chain, positions = [], {}
        path = start_path
        while path in nodes and path != "lore-context.md" and path not in visited:
            node = nodes[path]
            if node["parse_kind"] != "candidate_v1" or node["local_invalid"]:
                break
            if path in positions:
                cycle_members.update(chain[positions[path]:])
                break
            positions[path] = len(chain)
            chain.append(path)
            path = node.get("parent")
        visited.update(chain)
    for rel in sorted(cycle_members):
        nodes[rel]["local_invalid"] = True
        findings.append(_finding(rel, "parent_cycle", nodes[rel].get("parent")))

    # Coverage precedence is a contract. Structural reachability is evaluated
    # only after unsupported, legacy, and local-invalid classifications.
    mapped = set()
    if root_is_v1 and not root["local_invalid"]:
        mapped.add("lore-context.md")
        queue = ["lore-context.md"]
        while queue:
            parent = queue.pop(0)
            for child in nodes[parent]["children"]:
                child_node = nodes[child]
                if (child_node["parse_kind"] == "candidate_v1"
                        and not child_node["local_invalid"]
                        and child not in mapped):
                    mapped.add(child)
                    queue.append(child)

    for rel in sorted(nodes):
        node = nodes[rel]
        if node["parse_kind"] == "invalid_utf8":
            reason = "invalid_utf8"
        elif node["parse_kind"] == "unsupported_version":
            reason = "unsupported_version"
        elif node["parse_kind"] == "legacy":
            reason = "legacy"
        elif node["local_invalid"]:
            reason = "invalid_v1"
        elif rel not in mapped:
            reason = "unreachable_v1"
            findings.append(_finding(rel, "unreachable_v1", node.get("parent")))
        else:
            reason = None
        node["coverage_reason"] = reason

    dates, changed, git_error = _git_file_state(agent_dir, set(nodes))
    for rel, node in nodes.items():
        node["last_modified_iso"] = dates.get(rel)
        node["last_modified"] = dates[rel][:10] if dates.get(rel) else None
        node["uncommitted"] = rel in changed

    # Subtree totals are defined only across mapped taxonomy children.
    if "lore-context.md" in mapped:
        order, queue = [], ["lore-context.md"]
        while queue:
            path = queue.pop(0)
            order.append(path)
            queue.extend(child for child in nodes[path]["children"] if child in mapped)
        for path in reversed(order):
            nodes[path]["subtree_estimated_tokens"] = (
                nodes[path]["estimated_tokens"]
                + sum(nodes[child]["subtree_estimated_tokens"]
                      for child in nodes[path]["children"] if child in mapped)
            )
    for rel, node in nodes.items():
        if "subtree_estimated_tokens" not in node:
            node["subtree_estimated_tokens"] = node["estimated_tokens"]

    findings = sorted(
        findings,
        key=lambda item: (item.get("issue", ""), item.get("file", ""),
                          str(item.get("value", ""))))
    return {
        "agent_dir": agent_dir,
        "nodes": nodes,
        "mapped": mapped,
        "findings": findings,
        "git_error": git_error,
    }


def _percent(part, total):
    return round((100.0 * part / total), 1) if total else 100.0


def lore_coverage(graph):
    nodes = graph["nodes"]
    mapped = graph["mapped"]
    total_files = len(nodes)
    mapped_files = len(mapped)
    total_tokens = sum(node["estimated_tokens"] for node in nodes.values())
    mapped_tokens = sum(nodes[path]["estimated_tokens"] for path in mapped)
    reasons = {name: 0 for name in (
        "invalid_utf8", "legacy", "invalid_v1", "unreachable_v1",
        "unsupported_version")}
    for node in nodes.values():
        if node["coverage_reason"]:
            reasons[node["coverage_reason"]] += 1
    if mapped_files == total_files and total_files:
        status = "complete"
    elif mapped_files == 0:
        status = "legacy"
    else:
        status = "partial"
    guidance = {
        "complete": ("Taxonomy coverage is complete; expand compact entries "
                     "with scoped detailed maps."),
        "partial": "Use the map for mapped areas and search uncovered Lore for comprehensive recall.",
        "legacy": "Use lore-context.md and directory search; no complete declared taxonomy is available.",
    }[status]
    return {
        "status": status,
        "complete": status == "complete",
        "files": {
            "total": total_files,
            "mapped": mapped_files,
            "uncovered": total_files - mapped_files,
            "mapped_percent": _percent(mapped_files, total_files),
        },
        "estimated_tokens": {
            "total": total_tokens,
            "mapped": mapped_tokens,
            "uncovered": total_tokens - mapped_tokens,
            "mapped_percent": _percent(mapped_tokens, total_tokens),
        },
        "uncovered": reasons,
        "guidance": guidance,
    }


def _node_record(graph, path, allowed=None):
    nodes, mapped = graph["nodes"], graph["mapped"]
    order, queue = [], [path]
    while queue:
        current = queue.pop(0)
        order.append(current)
        queue.extend(child for child in nodes[current]["children"]
                     if child in mapped and (allowed is None or child in allowed))
    records = {}
    for current in order:
        node = nodes[current]
        all_children = [child for child in node["children"] if child in mapped]
        records[current] = {
            "file": current,
            "title": node["title"],
            "type": node["type"],
            "summary": node["summary"],
            "parent": node["parent"],
            "estimated_tokens": node["estimated_tokens"],
            "subtree_estimated_tokens": node["subtree_estimated_tokens"],
            "child_count": len(all_children),
            "links": {
                "inbound_count": len(node["inbound"]),
                "outbound_count": len(node["outbound"]),
                "inbound": node["inbound"],
                "outbound": node["outbound"],
            },
            "legacy_references": {
                "inbound": node["safety_inbound"],
                "outbound": node["safety_outbound"],
                "unresolved": node["unresolved_safety"],
            },
            "last_modified": node["last_modified"],
            "uncommitted": node["uncommitted"],
            "children": [],
        }
    for current in order:
        records[current]["children"] = [
            records[child] for child in nodes[current]["children"]
            if child in records
        ]
    return records[path]


def _uncovered_records(graph, allowed=None):
    records = []
    for path in sorted(graph["nodes"]):
        if allowed is not None and path not in allowed:
            continue
        node = graph["nodes"][path]
        if not node["coverage_reason"]:
            continue
        # Invalid UTF-8 is reported as one anonymous coverage count. Exposing
        # every damaged path would needlessly enlarge boot/review context.
        if node["coverage_reason"] == "invalid_utf8":
            continue
        records.append({
            "file": path,
            "reason": node["coverage_reason"],
            "estimated_tokens": node["estimated_tokens"],
            "formal_references": {
                "inbound": node["inbound"],
                "outbound": node["outbound"],
            },
            "legacy_references": {
                "inbound": node["safety_inbound"],
                "outbound": node["safety_outbound"],
                "unresolved": node["unresolved_safety"],
            },
            "last_modified": node["last_modified"],
            "uncommitted": node["uncommitted"],
        })
    return records


def _resolve_scope(graph, raw_scope):
    if raw_scope is None:
        return None
    scope = raw_scope.replace("\\", "/")
    if scope.startswith("./"):
        scope = scope[2:]
    parts = scope.split("/")
    if (not scope or scope.startswith("/") or re.match(r"^[A-Za-z]:/", scope)
            or any(part in ("", ".", "..") for part in parts)):
        raise ValueError("unsafe Lore scope: %s" % raw_scope)
    if scope in graph["nodes"]:
        return scope
    matches = [path for path in graph["nodes"]
               if posixpath.basename(path) == scope]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError("ambiguous Lore scope %s; use an agent-relative path" % raw_scope)
    raise ValueError("Lore scope not found: %s" % raw_scope)


def _scope_paths(graph, scope):
    if scope is None:
        return set(graph["nodes"])
    allowed = {scope}
    node = graph["nodes"][scope]
    # Declared descendants, even if unreachable, remain useful in a scoped
    # diagnostic. Invalid parent edges are deliberately absent from children.
    queue = list(node["children"])
    while queue:
        path = queue.pop(0)
        if path in allowed:
            continue
        allowed.add(path)
        queue.extend(graph["nodes"][path]["children"])
    parent = node.get("parent")
    seen = set()
    while parent in graph["nodes"] and parent not in seen:
        allowed.add(parent)
        seen.add(parent)
        parent = graph["nodes"][parent].get("parent")
    return allowed

__all__ = [name for name in globals() if not name.startswith("__")]

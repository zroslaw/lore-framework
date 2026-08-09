"""Bounded Lore grooming workset selection."""

from .lore_graph import *

def _parse_cursor(agent_dir):
    path = os.path.join(agent_dir, "workdir", "lore-grooming-state.yaml")
    state = {"last_successful_at": None, "last_successful_commit": None,
             "reviewed": {}}
    try:
        text = _read_lore_text(path)
    except (IOError, OSError, UnicodeError):
        return state
    if not re.search(r"(?m)^lore_grooming:\s*1\s*$", text):
        return state
    match = re.search(r'(?m)^last_successful_at:\s*"([^"\n]+)"\s*$', text)
    if match:
        state["last_successful_at"] = match.group(1)
    match = re.search(r'(?m)^last_successful_commit:\s*(?:"([^"\n]+)"|([^\s#]+))\s*$', text)
    if match:
        value = match.group(1) or match.group(2)
        state["last_successful_commit"] = None if value == "null" else value
    for match in re.finditer(
            r'(?m)^\s*-\s*\{file:\s*([^,}]+),\s*at:\s*"([^"\n]+)"\}\s*$', text):
        state["reviewed"][match.group(1).strip().strip('"')] = match.group(2)
    return state


def _iso_timestamp(value):
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.datetime.fromisoformat(normalized)
        # The cursor is disposable derived state. A malformed/naive timestamp
        # must be ignored, not make comparison with Git's zoned timestamps
        # crash the selector.
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(datetime.timezone.utc)
    except (ValueError, AttributeError):
        return None


def _summary_halo_record(graph, path, reason):
    node = graph["nodes"][path]
    record = {
        "file": path,
        "reason": reason,
        "mode": "summary",
        "estimated_tokens": 0,
        "summary": node["summary"],
    }
    if not node["summary"]:
        body = node["text"].splitlines()[parse_lore_frontmatter(
            node["text"], path)["content_start"]:]
        excerpt = " ".join(line.strip() for line in body if line.strip())[:240]
        record["title"] = node["title"]
        record["topic_estimated_tokens"] = node["estimated_tokens"]
        record["excerpt"] = excerpt or None
    current = -1
    while current != record["estimated_tokens"]:
        current = record["estimated_tokens"]
        record["estimated_tokens"] = estimate_tokens(yaml_dump(record))
    return record


def _ancestors(graph, path):
    result, seen = [], set()
    parent = graph["nodes"][path].get("parent")
    while parent in graph["nodes"] and parent not in seen:
        result.append(parent)
        seen.add(parent)
        parent = graph["nodes"][parent].get("parent")
    result.reverse()
    return result


def _area_partitions(graph, scope, budget):
    queue = [scope]
    ordered, seen = [], set()
    while queue:
        path = queue.pop(0)
        if path in seen:
            continue
        seen.add(path)
        ordered.append(path)
        queue.extend(child for child in graph["nodes"][path]["children"]
                     if child in graph["nodes"])
    partitions, current, cost = [], [], 0
    for path in ordered:
        item_cost = graph["nodes"][path]["estimated_tokens"]
        if current and cost + item_cost > budget:
            partitions.append(current)
            current, cost = [], 0
        current.append(path)
        cost += item_cost
        if item_cost > budget:
            partitions.append(current)
            current, cost = [], 0
    if current:
        partitions.append(current)
    return partitions


def _selection_candidates(graph, cursor, scope, budget):
    nodes = graph["nodes"]
    eligible = [path for path in sorted(nodes)
                if nodes[path]["coverage_reason"] not in
                ("unsupported_version", "invalid_utf8")]
    if scope is not None:
        node = nodes[scope]
        if node["coverage_reason"] == "invalid_utf8":
            raise ValueError("Lore scope has invalid UTF-8 and is unreadable: %s" % scope)
        if node["coverage_reason"] == "unsupported_version":
            raise ValueError("unsupported future-version Lore scope is read-only: %s" % scope)
        if node["type"] in ("area", "context") and node["parse_kind"] == "candidate_v1":
            partitions = _area_partitions(graph, scope, budget)
            reviewed = cursor["reviewed"]
            def partition_key(part):
                never = [path for path in part if path not in reviewed]
                if never:
                    return (0, min(never), part[0])
                oldest = min(reviewed.get(path, "") for path in part)
                return (1, oldest, part[0])
            chosen = min(partitions, key=partition_key)
            return [(path, "explicit_scope") for path in chosen]
        return [(scope, "explicit_scope")]

    structural_files = {}
    for item in graph["findings"]:
        path = item.get("file")
        if path not in nodes or path not in eligible:
            continue
        structural_files.setdefault(path, item["issue"])

    last_run = _iso_timestamp(cursor["last_successful_at"])
    recent = []
    for path in eligible:
        node = nodes[path]
        if node["uncommitted"]:
            recent.append((path, True, None))
            continue
        date = _iso_timestamp(node.get("last_modified_iso"))
        if date and (last_run is None or date > last_run):
            recent.append((path, False, date))
    recent.sort(key=lambda item: (0 if item[1] else 1,
                                  -(item[2].timestamp() if item[2] else 0), item[0]))
    tiered = [(path, "recently_changed") for path, _, _ in recent]
    tiered.extend((path, "structural_finding") for path in sorted(
        structural_files, key=lambda path: (structural_files[path], path)))
    oversized = [path for path in eligible
                 if nodes[path]["type"] == "topic"
                 and nodes[path]["estimated_tokens"] > OVERSIZED_TOPIC_TOKENS]
    oversized.sort(key=lambda path: (-nodes[path]["estimated_tokens"], path))
    tiered.extend((path, "oversized_topic") for path in oversized)
    reviewed = cursor["reviewed"]
    rotation = sorted(eligible, key=lambda path: (
        0 if path not in reviewed else 1, reviewed.get(path, ""), path))
    tiered.extend((path, "rotation") for path in rotation)
    seen, result = set(), []
    for path, reason in tiered:
        if path not in seen:
            seen.add(path)
            result.append((path, reason))
    return result


def _halo_tiers(graph, editable):
    nodes = graph["nodes"]
    editable_set = set(editable)
    tiers = [
        ("ancestor", set()),
        ("direct_child", set()),
        ("sibling", set()),
        ("outbound", set()),
        ("inbound", set()),
        ("legacy_reference", set()),
    ]
    tier = {name: paths for name, paths in tiers}
    for path in editable:
        tier["ancestor"].update(_ancestors(graph, path))
        node = nodes[path]
        if node["type"] in ("area", "context"):
            tier["direct_child"].update(node["children"])
        parent = node.get("parent")
        if parent in nodes:
            tier["sibling"].update(nodes[parent]["children"])
        tier["outbound"].update(node["outbound"])
        tier["inbound"].update(node["inbound"])
        tier["legacy_reference"].update(node["safety_outbound"])
        tier["legacy_reference"].update(node["safety_inbound"])
    admitted = set(editable_set)
    result = []
    for name, paths in tiers:
        clean = []
        for path in sorted(paths):
            if path in admitted or path not in nodes:
                continue
            if nodes[path]["coverage_reason"] == "invalid_utf8":
                continue
            admitted.add(path)
            clean.append(path)
        result.append((name, clean))
    return result


def select_lore_workset(graph, scope=None, budget=GROOMING_BUDGET):
    if budget <= 0:
        raise ValueError("budget must be a positive integer")
    scope = _resolve_scope(graph, scope)
    cursor = _parse_cursor(graph["agent_dir"])
    candidates = _selection_candidates(graph, cursor, scope, budget)
    nodes = graph["nodes"]

    editable = []
    editable_cost = 0
    over_budget = False
    for path, reason in candidates:
        cost = nodes[path]["estimated_tokens"]
        if not editable and cost > budget:
            editable.append((path, reason))
            editable_cost = cost
            over_budget = True
            break
        if editable_cost + cost > budget:
            continue
        editable.append((path, reason))
        editable_cost += cost
    if not editable:
        raise ValueError("no Lore files are eligible for grooming")

    # Ancestors are mandatory. If they do not fit, remove the lowest-priority
    # editable entries until they do. The explicit/oversized singleton remains.
    while True:
        halo_tiers = _halo_tiers(graph, [path for path, _ in editable])
        ancestors = [_summary_halo_record(graph, path, "ancestor")
                     for name, paths in halo_tiers if name == "ancestor"
                     for path in paths]
        ancestor_cost = sum(item["estimated_tokens"] for item in ancestors)
        total = editable_cost + ancestor_cost
        if total <= budget or over_budget or len(editable) == 1:
            break
        removed, _ = editable.pop()
        editable_cost -= nodes[removed]["estimated_tokens"]

    if editable_cost + ancestor_cost > budget and not over_budget:
        raise ValueError("selected Lore plus mandatory ancestor summaries exceeds budget")

    halo = []
    omissions = {name: 0 for name, _ in halo_tiers}
    running = editable_cost
    for name, paths in halo_tiers:
        for path in paths:
            record = _summary_halo_record(graph, path, name)
            if name == "ancestor":
                halo.append(record)
                running += record["estimated_tokens"]
                continue
            if running + record["estimated_tokens"] <= budget:
                halo.append(record)
                running += record["estimated_tokens"]
            else:
                omissions[name] += 1

    editable_records = [{"file": path, "reason": reason,
                         "estimated_tokens": nodes[path]["estimated_tokens"]}
                        for path, reason in editable]
    snapshot_paths = sorted(set([item["file"] for item in editable_records]
                                + [item["file"] for item in halo]))
    snapshot = [{"file": path, "sha256": nodes[path]["sha256"]}
                for path in snapshot_paths]
    return {
        "workset": {
            "ok": True,
            "budget": budget,
            "estimated_tokens": running,
            "over_budget": over_budget or running > budget,
            "scope": scope,
            "coverage": lore_coverage(graph),
            "snapshot": snapshot,
            "editable": editable_records,
            "halo": halo,
            "omitted_halo": omissions,
        }
    }
def cmd_lore_workset(args):
    """Read-only deterministic selector for bounded semantic grooming."""
    graph = build_lore_graph(args.agent_dir)
    return select_lore_workset(graph, scope=args.scope, budget=args.budget)

__all__ = [name for name in globals() if not name.startswith("__")]

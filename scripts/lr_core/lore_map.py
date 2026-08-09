"""Detailed and compact Lore map rendering."""

from .lore_graph import *
from .preflight import detect_engine

def detailed_lore_map(graph, scope=None):
    scope = _resolve_scope(graph, scope)
    allowed = _scope_paths(graph, scope)
    root_record = None
    if "lore-context.md" in graph["mapped"] and "lore-context.md" in allowed:
        root_record = _node_record(graph, "lore-context.md", allowed)
    elif "lore-context.md" in graph["nodes"] and "lore-context.md" in allowed:
        node = graph["nodes"]["lore-context.md"]
        root_record = {
            "file": "lore-context.md",
            "title": node["title"],
            "type": node["type"],
            "summary": node["summary"],
            "parent": node["parent"],
            "estimated_tokens": node["estimated_tokens"],
            "subtree_estimated_tokens": node["subtree_estimated_tokens"],
            "child_count": 0,
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
    return {
        "lore_map": 1,
        "view": "detailed",
        "agent_dir": graph["agent_dir"],
        "scope": scope,
        "coverage": lore_coverage(graph),
        "root": root_record,
        "uncovered": _uncovered_records(graph, allowed),
        "validation": [item for item in graph["findings"]
                       if item.get("file") in allowed],
        "git_history_error": graph["git_error"],
    }


def _boot_area_record(graph, path):
    node = graph["nodes"][path]
    return {"file": path, "summary": node["summary"]}


def _with_serialized_estimate(payload, field="estimated_tokens"):
    current = -1
    while current != payload[field]:
        current = payload[field]
        payload[field] = estimate_tokens(yaml_dump(payload))
    return payload


def _boot_system_prompts_estimated_tokens(agent_dir, framework_root, engine):
    """Estimate framework instruction files always loaded during boot."""
    root = os.path.realpath(os.path.abspath(framework_root))
    required_paths = [
        os.path.join(root, "skills", "boot", "SKILL.md"),
        os.path.join(root, "docs", "agent-boot.md"),
        os.path.join(root, "docs", "engines", "%s.md" % engine),
    ]
    total = 0
    for path in required_paths:
        try:
            total += estimate_tokens(_read_lore_text(path))
        except (IOError, OSError, UnicodeError):
            return None
    return total


def _boot_role_estimated_tokens(agent_dir):
    """Estimate the agent role loaded during boot."""
    try:
        return estimate_tokens(
            _read_lore_text(os.path.join(agent_dir, "role.md")))
    except (IOError, OSError, UnicodeError):
        return None


def _with_boot_map_estimates(payload, system_prompt_tokens, role_tokens):
    """Solve map size and its self-referential total boot footprint."""
    while True:
        previous = (
            payload["estimated_tokens"],
            payload["stats"]["boot_footprint_estimated_tokens"],
        )
        payload["estimated_tokens"] = estimate_tokens(yaml_dump(payload))
        payload["stats"]["boot_system_prompts_estimated_tokens"] = (
            system_prompt_tokens)
        payload["stats"]["boot_role_estimated_tokens"] = role_tokens
        context_tokens = (
            payload["stats"]["lore_context_estimated_tokens"] or 0)
        payload["stats"]["boot_footprint_estimated_tokens"] = (
            system_prompt_tokens + role_tokens + context_tokens
            + payload["estimated_tokens"]
            if system_prompt_tokens is not None and role_tokens is not None
            else None
        )
        current = (
            payload["estimated_tokens"],
            payload["stats"]["boot_footprint_estimated_tokens"],
        )
        if current == previous:
            return payload


def boot_lore_map(graph, budget=BOOT_MAP_BUDGET, system_prompt_tokens=None,
                  role_tokens=None):
    coverage = lore_coverage(graph)
    root = graph["nodes"].get("lore-context.md")
    top_areas, direct_topics, subareas = [], [], []
    if "lore-context.md" in graph["mapped"]:
        for child in root["children"]:
            if child not in graph["mapped"]:
                continue
            node = graph["nodes"][child]
            if node["type"] == "area":
                top_areas.append(_boot_area_record(graph, child))
            elif node["type"] == "topic":
                direct_topics.append(_boot_area_record(graph, child))
        for area in [item["file"] for item in top_areas]:
            for child in graph["nodes"][area]["children"]:
                if child in graph["mapped"] and graph["nodes"][child]["type"] == "area":
                    item = _boot_area_record(graph, child)
                    item["parent"] = area
                    subareas.append(item)
    top_areas.sort(key=lambda item: item["file"])
    direct_topics.sort(key=lambda item: item["file"])
    subareas.sort(key=lambda item: item["file"])

    payload = {
        "lore_map": 1,
        "view": "boot",
        "budget": budget,
        "estimated_tokens": 0,
        "over_budget": False,
        "stats": {
            # Every Markdown file below lore/, including area hubs and legacy
            # files. The fixed lore-context.md is measured separately.
            "lore_files": sum(1 for path in graph["nodes"]
                              if path.startswith("lore/")),
            "lore_context_estimated_tokens": (
                root["estimated_tokens"] if root else None),
            "boot_role_estimated_tokens": None,
            "boot_system_prompts_estimated_tokens": None,
            "boot_footprint_estimated_tokens": None,
        },
        "coverage": coverage,
        "root": {
            "file": "lore-context.md",
            "summary": root["summary"] if root and root["coverage_reason"] is None else None,
        },
        "areas": top_areas,
        "direct_topics": [],
        "immediate_subareas": [],
        "omitted": {
            "direct_topics": len(direct_topics),
            "immediate_subareas": len(subareas),
        },
    }
    _with_boot_map_estimates(payload, system_prompt_tokens, role_tokens)
    payload["over_budget"] = payload["estimated_tokens"] > budget
    if not payload["over_budget"]:
        for key, candidates in (("direct_topics", direct_topics),
                                ("immediate_subareas", subareas)):
            for item in candidates:
                payload[key].append(item)
                payload["omitted"][key] -= 1
                _with_boot_map_estimates(
                    payload, system_prompt_tokens, role_tokens)
                if payload["estimated_tokens"] > budget:
                    payload[key].pop()
                    payload["omitted"][key] += 1
                    _with_boot_map_estimates(
                        payload, system_prompt_tokens, role_tokens)
                    break
    _with_boot_map_estimates(payload, system_prompt_tokens, role_tokens)
    payload["over_budget"] = payload["estimated_tokens"] > budget
    _with_boot_map_estimates(payload, system_prompt_tokens, role_tokens)
    return payload
def cmd_lore_map(args):
    """Read-only implementation of Lore v1 map reconstruction.

    Discovery, parsing, graph validation, coverage classification, link
    analysis, metrics, and YAML serialization are all deterministic. This is
    an implementation script rather than a manually reproducible accelerator:
    failure stops map enrichment and callers use their documented fallback.
    """
    graph = build_lore_graph(args.agent_dir)
    if args.view == "boot":
        if args.scope is not None:
            raise ValueError("--scope is supported only with --view detailed")
        framework_root = resolve_framework_root(args.framework_root)
        engine = args.engine or detect_engine(framework_root)["name"]
        system_prompt_tokens = _boot_system_prompts_estimated_tokens(
            graph["agent_dir"], framework_root, engine)
        role_tokens = _boot_role_estimated_tokens(graph["agent_dir"])
        return boot_lore_map(
            graph, system_prompt_tokens=system_prompt_tokens,
            role_tokens=role_tokens)
    return detailed_lore_map(graph, scope=args.scope)

__all__ = [name for name in globals() if not name.startswith("__")]

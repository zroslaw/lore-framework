"""Argument parsing and command dispatch for lr-core."""

from .common import *
from .preflight import cmd_discover, cmd_preflight
from .scan import cmd_scan
from .lore_graph import emit_yaml_fatal, yaml_dump
from .lore_map import cmd_lore_map
from .lore_workset import cmd_lore_workset
from .workspace_scan import cmd_workspace_scan

def build_parser():
    parser = argparse.ArgumentParser(
        prog="lr-core",
        description="Deterministic substrate for the mechanical steps of lore skills.")
    parser.add_argument("--framework-root", default=None,
                        help="Override framework root (default: the script's grandparent, "
                             "i.e. the dir containing VERSION).")
    sub = parser.add_subparsers(dest="command")

    p_disc = sub.add_parser("discover", help="Enumerate lore agent repos and agents.")
    p_disc.add_argument("--workspace", default=".", help="Workspace root (default: cwd).")
    p_disc.set_defaults(func=cmd_discover)

    p_pre = sub.add_parser("preflight", help="Boot/attach preflight for one agent.")
    p_pre.add_argument("--agent", default=None, help="Agent name to resolve.")
    p_pre.add_argument("--agent-dir", default=None,
                       help="Explicit agent directory (skips discovery).")
    p_pre.add_argument("--workspace", default=".", help="Workspace root (default: cwd).")
    p_pre.add_argument("--ttl", type=int, default=DEFAULT_PULL_TTL_SEC,
                       help="Skip the pull if one succeeded within N seconds "
                            "(default: %d; 0 disables the cache)." % DEFAULT_PULL_TTL_SEC)
    p_pre.add_argument("--fresh", action="store_true",
                       help="Bypass the TTL cache and always pull.")
    p_pre.add_argument("--no-pull", action="store_true", help="Skip the pull entirely.")
    p_pre.add_argument("--no-teammate-check", action="store_true",
                       help="Skip the teammate process-ancestry inspection.")
    p_pre.add_argument("--engine", default=None, choices=sorted(set(ENGINE_PROGRAMS.values())),
                       help="Force the engine profile instead of detecting it.")
    p_pre.set_defaults(func=cmd_preflight)

    p_scan = sub.add_parser("scan", help="Manifest of an agent's lore topics.")
    p_scan.add_argument("--agent", default=None, help="Agent name to resolve.")
    p_scan.add_argument("--agent-dir", default=None, help="Explicit agent directory.")
    p_scan.add_argument("--workspace", default=".", help="Workspace root (default: cwd).")
    p_scan.add_argument("--stale-days", type=int, default=DEFAULT_STALE_DAYS,
                        help="Flag topics older than N days (default: %d)."
                             % DEFAULT_STALE_DAYS)
    p_scan.set_defaults(func=cmd_scan)

    p_wscan = sub.add_parser("workspace-scan",
                             help="Workspace git/descriptor/memory state and findings.")
    p_wscan.add_argument("--workspace", default=".", help="Workspace root (default: cwd).")
    p_wscan.add_argument("--engine", default=None,
                         choices=sorted(set(ENGINE_PROGRAMS.values())),
                         help="Force the engine profile instead of detecting it.")
    p_wscan.set_defaults(func=cmd_workspace_scan)

    p_map = sub.add_parser("lore-map", help="Reconstruct and validate Lore v1.")
    p_map.add_argument("--agent-dir", required=True,
                       help="Explicit agent directory.")
    p_map.add_argument("--view", required=True, choices=("boot", "detailed"),
                       help="Compact boot navigation or complete detailed map.")
    p_map.add_argument("--scope", default=None,
                       help="Agent-relative Lore path for a scoped detailed map.")
    p_map.add_argument("--engine", default=None,
                       choices=sorted(set(ENGINE_PROGRAMS.values())),
                       help="Engine profile included in the boot-footprint estimate.")
    p_map.set_defaults(func=cmd_lore_map, output_format="yaml")

    p_workset = sub.add_parser("lore-workset",
                               help="Select a bounded Lore grooming workset.")
    p_workset.add_argument("--agent-dir", required=True,
                           help="Explicit agent directory.")
    p_workset.add_argument("--scope", default=None,
                           help="Optional agent-relative area or topic path.")
    p_workset.add_argument("--budget", type=int, default=GROOMING_BUDGET,
                           help="Estimated-token budget (default: %d)."
                                % GROOMING_BUDGET)
    p_workset.set_defaults(func=cmd_lore_workset, output_format="yaml")

    return parser


def main(argv):
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # argparse prints usage to stderr and exits. `--help` (code 0) keeps its
        # normal behavior; a usage error must still honor the output contract,
        # so a caller parsing stdout sees a well-formed failure rather than
        # nothing at all.
        if exc.code == 0:
            raise
        lore_command = next((name for name in ("lore-map", "lore-workset")
                             if name in argv), None)
        if lore_command:
            return emit_yaml_fatal(lore_command,
                                   "invalid invocation (run with --help for usage)")
        return emit_fatal("invalid invocation (run with --help for usage)")
    if not getattr(args, "command", None):
        parser.print_help(sys.stderr)
        return emit_fatal("no subcommand given (run with --help for usage)")
    if args.command in ("preflight", "scan") and not (args.agent or args.agent_dir):
        return emit_fatal("%s requires --agent or --agent-dir" % args.command)

    if getattr(args, "output_format", None) == "yaml":
        try:
            payload = args.func(args)
        except Exception as exc:  # noqa: BLE001 - deliberate boundary
            return emit_yaml_fatal(args.command, "%s: %s" % (type(exc).__name__, exc))
        sys.stdout.write(yaml_dump(payload))
        return 0

    res = Result()
    try:
        args.func(args, res)
    except Exception as exc:  # noqa: BLE001 - deliberate catch-all
        # Any unexpected failure is exit 2: the caller falls back to the prose
        # procedure rather than proceeding on partial data.
        return emit_fatal("%s: %s" % (type(exc).__name__, exc))
    return res.emit()

__all__ = [name for name in globals() if not name.startswith("__")]

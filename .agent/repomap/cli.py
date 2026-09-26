import argparse
import sys
import json
import logging
from pathlib import Path

# Ensure repository root and agent dir are on sys.path
repo_root = Path(__file__).resolve().parents[2]
agent_dir = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
if str(agent_dir) not in sys.path:
    sys.path.insert(0, str(agent_dir))

from repomap.core.graph import TwoTierGraph
from repomap.core.ranker import CentralityRanker
from repomap.core.packer import MarginalDensityPacker
from repomap.facets.hierarchy import get_symbol_hierarchy
from repomap.facets.schemas import get_schema_registry
from repomap.facets.blast_radius import trace_blast_radius
from repomap.server import RepomapJSONRPCServer


def cmd_index(args):
    mode = "full" if args.full else "dirty" if args.dirty else "full"
    print(f"[repomap] Indexing repository ({mode})...")
    graph = TwoTierGraph(repo_root)
    graph.build_from_repository()
    print(f"[repomap] Indexing complete. Indexed {len(graph.macro_graph)} files.")


def cmd_summary(args):
    focus_files = [f.strip() for f in args.focus.split(",") if f.strip()] if args.focus else None
    graph = TwoTierGraph(repo_root)
    graph.build_from_repository()

    ranker = CentralityRanker(graph)
    symbol_scores = ranker.rank_symbols(focus_files)

    packer = MarginalDensityPacker(repo_root)
    summary_text = packer.pack(symbol_scores, budget_tokens=args.budget)
    print(summary_text)


def cmd_trace(args):
    graph = TwoTierGraph(repo_root)
    graph.build_from_repository()

    blast = trace_blast_radius(args.symbol, direction=args.direction, max_depth=args.depth, graph=graph)
    hierarchy = get_symbol_hierarchy(args.symbol, repo_root)

    output = {
        "symbol": args.symbol,
        "hierarchy": hierarchy,
        "blast_radius": blast,
    }
    print(json.dumps(output, indent=2))


def cmd_schemas(args):
    registry = get_schema_registry(repo_root)
    print(json.dumps(registry, indent=2))


def cmd_cycles(args):
    graph = TwoTierGraph(repo_root)
    graph.build_from_repository()
    cycles = graph.find_cycles()

    output = {
        "cycle_count": len(cycles),
        "cycles": cycles,
    }
    print(json.dumps(output, indent=2))


def cmd_serve(args):
    print("[repomap] Starting JSON-RPC tool server...")
    server = RepomapJSONRPCServer(repo_root)
    server.serve_forever()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="repomap", description="Repomap faceted CLI commands")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # index subcommand
    p_index = subparsers.add_parser("index", help="Index the repository (full or dirty)")
    group = p_index.add_mutually_exclusive_group()
    group.add_argument("--full", action="store_true", help="Force a full re-index")
    group.add_argument("--dirty", action="store_true", help="Index only dirty/changed files")
    p_index.set_defaults(func=cmd_index)

    # summary subcommand
    p_summary = subparsers.add_parser("summary", help="Generate a repository summary within a token budget")
    p_summary.add_argument("--budget", type=int, default=2048, help="Maximum token budget for the summary")
    p_summary.add_argument("--focus", type=str, default="", help="Comma-separated list of files to prioritize")
    p_summary.set_defaults(func=cmd_summary)

    # trace subcommand
    p_trace = subparsers.add_parser("trace", help="Trace type hierarchy and blast radius for a symbol")
    p_trace.add_argument("symbol", type=str, help="Fully qualified symbol name to trace")
    p_trace.add_argument("--direction", choices=["upstream", "downstream", "both"], default="both", help="Traversal direction")
    p_trace.add_argument("--depth", type=int, default=3, help="Maximum depth to explore")
    p_trace.set_defaults(func=cmd_trace)

    # schemas subcommand
    p_schemas = subparsers.add_parser("schemas", help="Print the data-contract/schema registry")
    p_schemas.set_defaults(func=cmd_schemas)

    # cycles subcommand
    p_cycles = subparsers.add_parser("cycles", help="Detect import cycles")
    p_cycles.set_defaults(func=cmd_cycles)

    # serve subcommand
    p_serve = subparsers.add_parser("serve", help="Run the JSON-RPC tool server")
    p_serve.add_argument("--rpc", action="store_true", help="Run in RPC mode")
    p_serve.set_defaults(func=cmd_serve)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()

"""
main.py — CLI entrypoint for the multi-agent SWE orchestration library.

Usage:
    python main.py --project my-gcp-project --goal "Add rate-limiting to /api/v1/ingest"
    python main.py --project my-gcp-project --goal "..." --context repo_context.txt --backend vertex
    python main.py --project my-gcp-project --goal "..." --resume   # resume a prior run
"""

from __future__ import annotations
import argparse
import json
import logging
import sys


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        level=level,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cost-optimized agent orchestration framework (PoC)"
    )
    parser.add_argument("--project",  required=True, help="GCP project ID")
    parser.add_argument("--goal",     required=True, help="High-level task goal")
    parser.add_argument("--context",  default="",    help="Optional extra context (file path or inline string)")
    parser.add_argument("--location", default="us-central1", help="Vertex AI region")
    parser.add_argument("--backend",  default="antigravity",
                        choices=["antigravity", "vertex"],
                        help="Model backend: 'antigravity' (default) or 'vertex'")
    parser.add_argument("--resume",   action="store_true",
                        help="Resume from persisted .orchestrator/state.json")
    parser.add_argument("--repo",     default="",
                        help="Optional path to the repository being modified")
    parser.add_argument("--verbose",  action="store_true",   help="Enable debug logging")
    return parser.parse_args()


def load_context(value: str) -> str:
    """If value is a readable file path, return its contents; otherwise return as-is."""
    if not value:
        return ""
    try:
        with open(value, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return value


def main() -> None:
    args = parse_args()
    setup_logging(args.verbose)
    log = logging.getLogger("main")
    # Initialise the writer queue for SQLite WAL concurrency
    from .db import get_writer_queue
    writer_queue = get_writer_queue()

    context = load_context(args.context)

    # Lazy import so logging is configured first
    from orchestrator import Orchestrator

    orch = Orchestrator(
        project=args.project,
        location=args.location,
        backend=args.backend,
        resume=args.resume,
    )

    log.info("Starting orchestration for goal: %s", args.goal[:100])
    result = orch.run(goal=args.goal, context=context, repository_path=args.repo)

    # --- Pretty-print results ---
    print("\n" + "=" * 60)
    print(f"Task ID : {result.get('task_id', '?')}")
    print(f"Goal    : {result['goal']}")
    print(f"Status  : {result['status']}")
    print(f"Success : {result['success']}")
    print("=" * 60)

    for subtask in result["subtasks"]:
        sid    = subtask.get('id', '?')
        name   = subtask.get('name', '')
        status = subtask.get('status', '?')
        iters  = subtask.get('repair_iterations', '?')
        esc    = subtask.get('escalation_count', 0)
        print(f"\n[{sid}] {name}  status={status}  repairs={iters}  escalations={esc}")

        tr = subtask.get("test_report")
        if tr:
            print(f"  Tests : {tr['status']}  {tr['passed']}/{tr['total']} passed")

        rv = subtask.get("review_verdict")
        if rv:
            print(f"  Review: {rv}")

        diff = subtask.get("diff_preview", "")
        if diff:
            print("  Diff preview:")
            print(textwrap_result(diff))

    # Event log (last 10 entries)
    event_log = result.get("event_log", [])
    if event_log:
        print("\n--- Event Log (last 10) ---")
        for entry in event_log[-10:]:
            print(f"  {entry}")

    print("\n" + result["budget"])

    sys.exit(0 if result["success"] else 1)


def textwrap_result(text: str, width: int = 80, indent: str = "    ") -> str:
    import textwrap
    return "\n".join(
        indent + line
        for line in text.splitlines()
    ) or f"{indent}(empty)"


if __name__ == "__main__":
    main()

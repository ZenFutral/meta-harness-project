#!/usr/bin/env python3
"""
Meta-Harness 1-Click Startup Launcher
=====================================
Initializes all core subsystems:
1. Environment verification & directories setup
2. Repomap AST code intelligence index & SQLite-WAL graph database
3. Multi-agent SWE orchestrator workflow state
4. Zero-dependency Monitoring & Telemetry HTTP server
5. Automatic web browser launch to the dashboard site
"""

import argparse
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Ensure repo root and .agent directories are on sys.path
REPO_ROOT = Path(__file__).resolve().parent
AGENT_DIR = REPO_ROOT / ".agent"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))


def check_environment():
    """Verify python version and required directories."""
    if sys.version_info < (3, 9):
        print(f"[!] Error: Meta-Harness requires Python 3.9+. Current: {sys.version}")
        sys.exit(1)

    dirs_to_ensure = [
        REPO_ROOT / ".agent" / "cache",
        REPO_ROOT / ".agent" / "config",
        REPO_ROOT / ".orchestrator",
        REPO_ROOT / "meta_harness" / "orchestrator" / "sessions",
    ]
    for d in dirs_to_ensure:
        d.mkdir(parents=True, exist_ok=True)


def init_repomap(skip_index: bool = False):
    """Initialize or refresh Repomap symbol index."""
    if skip_index:
        print("[*] Skipping Repomap AST re-indexing.")
        return

    print("[*] Initializing Repomap AST Code Intelligence Graph & SQLite-WAL index...")
    try:
        from repomap.core.graph import TwoTierGraph
        graph = TwoTierGraph(REPO_ROOT)
        graph.build_from_repository()
        print(f"[+] Repomap indexing complete. ({len(graph.macro_graph)} files indexed)")
    except Exception as e:
        print(f"[!] Warning: Repomap indexing encountered a non-fatal warning: {e}")


def init_orchestrator():
    """Ensure multi-agent orchestrator state file is initialized."""
    try:
        from meta_harness.orchestrator.state import load_state, fresh_state
        state = load_state()
        if state is None:
            print("[*] Initializing baseline multi-agent orchestrator workflow state...")
            fresh_state("Meta-Harness SWE Multi-Agent Ecosystem", str(REPO_ROOT))
            print("[+] Orchestrator workflow state initialized (.orchestrator/state.json)")
        else:
            print(f"[+] Orchestrator workflow state loaded (status: {state.status})")
    except Exception as e:
        print(f"[!] Warning: Orchestrator state check warning: {e}")


def launch_browser(url: str, delay: float = 0.6):
    """Launch default browser in a background daemon thread."""
    def _open():
        time.sleep(delay)
        print(f"[*] Opening browser to {url} ...")
        webbrowser.open(url)

    t = threading.Thread(target=_open, daemon=True)
    t.start()


def print_banner(host: str, port: int):
    """Display startup banner."""
    url = f"http://{host}:{port}"
    print(r"""
  __  __      _          _   _                               
 |  \/  | ___| |_ __ _  | | | | __ _ _ __ _ __   ___  ___ ___
 | |\/| |/ _ \ __/ _` | | |_| |/ _` | '__| '_ \ / _ \/ __/ __|
 | |  | |  __/ || (_| | |  _  | (_| | |  | | | |  __/\__ \__ \
 |_|  |_|\___|\__\__,_| |_| |_|\__,_|_|  |_| |_|\___||___/___/
""")
    print("==================================================================")
    print("  Meta-Harness SWE Orchestration & Monitoring Observatory")
    print("==================================================================")
    print(f"  [>] Site URL:             {url}")
    print(f"  [>] GUI Server:           Active on {host}:{port}")
    print(f"  [>] Repomap SQLite-WAL:   Initialized & Ready (.agent/cache/repomap.db)")
    print(f"  [>] SWE Orchestrator:     6-Persona Multi-Agent State Engine Ready")
    print(f"  [>] Multi-Tier Router:    Dual-Engine (Vertex / Antigravity) Ready")
    print(f"  [>] Probes & Telemetry:   Live Gauges & RPC Playground Active")
    print("------------------------------------------------------------------")
    print("  Press Ctrl+C to stop all services cleanly.")
    print("==================================================================\n")


def main():
    parser = argparse.ArgumentParser(description="1-Click Start for Meta-Harness Ecosystem")
    parser.add_argument("--host", default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Port number (default: 8080)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser automatically")
    parser.add_argument("--skip-index", action="store_true", help="Skip Repomap AST re-indexing on start")
    args = parser.parse_args()

    check_environment()
    init_repomap(skip_index=args.skip_index)
    init_orchestrator()

    from meta_harness.gui.server import create_server
    server = create_server(host=args.host, port=args.port)
    url = f"http://{args.host}:{args.port}"

    print_banner(args.host, args.port)

    if not args.no_browser:
        launch_browser(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Shutting down Meta-Harness GUI server & services...")
        server.shutdown()
        server.server_close()
        print("[+] All Meta-Harness functions stopped cleanly.")


if __name__ == "__main__":
    main()

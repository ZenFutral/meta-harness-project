"""
Command-line interface launcher for the System Monitoring GUI.
"""
import argparse
import sys
import webbrowser
import threading
import time
from .server import create_server


def main():
    parser = argparse.ArgumentParser(description="Launch Meta-Harness System Monitoring GUI")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")
    args = parser.parse_args()

    server = create_server(host=args.host, port=args.port)
    url = f"http://{args.host}:{args.port}"
    print(f"\n=======================================================")
    print(f"[+] Meta-Harness System Monitoring GUI running at:")
    print(f"    {url}")
    print(f"    Features: Telemetry HUD, Complete Feature Grid, SQLite-WAL Inspector, RPC Playground")
    print(f"    Press Ctrl+C to terminate.")
    print(f"=======================================================\n")

    if not args.no_browser:
        def open_url():
            time.sleep(0.5)
            webbrowser.open(url)
        threading.Thread(target=open_url, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down GUI server...")
        server.shutdown()
        server.server_close()
        print("Server stopped cleanly.")


if __name__ == "__main__":
    main()

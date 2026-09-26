"""
Lightweight high-performance HTTP Server for the System Monitoring GUI.
Uses Python's standard library ThreadingHTTPServer for zero external dependencies.
"""
import os
import sys
import json
import urllib.parse
from http import HTTPStatus
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Dict, Any, Optional

from .telemetry import get_telemetry_snapshot, get_feature_catalog, get_cache_table_sample
from .probes import probe_router, probe_skeleton, probe_blast_radius, probe_schemas, probe_cycles

STATIC_DIR = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "static")))


class GuiRequestHandler(SimpleHTTPRequestHandler):
    """Custom HTTP request handler with REST API and static file serving."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def _send_json(self, data: Any, status: int = 200) -> None:
        """Helper to send JSON response with CORS headers."""
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        """Handle preflight CORS requests."""
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        """Route GET requests to API or static assets."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        # API Routes
        if path == "/api/telemetry":
            snapshot = get_telemetry_snapshot()
            self._send_json(snapshot.to_dict())
            return

        if path == "/api/features":
            features = [as_dict(f) for f in get_feature_catalog()]
            self._send_json({"features": features, "total": len(features)})
            return

        if path == "/api/cache/tables":
            table_name = query.get("table", ["parse_cache"])[0]
            limit_val = int(query.get("limit", [50])[0])
            result = get_cache_table_sample(table_name, limit_val)
            self._send_json(result)
            return

        if path == "/api/probe/schemas":
            result = probe_schemas()
            self._send_json(result)
            return

        if path == "/api/probe/cycles":
            result = probe_cycles()
            self._send_json(result)
            return

        if path == "/api/vendors":
            from router.vendor_config import load_vendor_config
            self._send_json(load_vendor_config())
            return

        if path == "/api/chat":
            from .chat import get_chat_history
            self._send_json({"messages": get_chat_history()})
            return

        if path == "/api/agent_activity":
            from .telemetry import get_agent_activity_telemetry
            activity = get_agent_activity_telemetry()
            self._send_json(as_dict(activity))
            return

        # Static file mapping
        if path == "/" or path == "":
            self.path = "/index.html"
        elif path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return

        # Delegate static serving to SimpleHTTPRequestHandler
        super().do_GET()

    def do_POST(self) -> None:
        """Handle POST feature probe and vendor configuration requests."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        # Read JSON body
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = {}
        if content_length > 0:
            try:
                raw_body = self.rfile.read(content_length).decode("utf-8")
                post_data = json.loads(raw_body)
            except Exception as e:
                self._send_json({"success": False, "error": f"Invalid JSON body: {str(e)}"}, status=400)
                return

        if path == "/api/chat":
            message = post_data.get("message", "")
            target_persona = post_data.get("persona", "auto")
            context_files = post_data.get("context_files", [])
            backend = post_data.get("backend", "vertex")
            if not message:
                self._send_json({"success": False, "error": "Missing 'message' field"}, status=400)
                return
            from .chat import dispatch_agent_chat
            result = dispatch_agent_chat(
                message=message,
                target_persona=target_persona,
                context_files=context_files,
                backend=backend
            )
            self._send_json(result)
            return

        if path == "/api/chat/clear":
            from .chat import clear_chat_history
            result = clear_chat_history()
            self._send_json(result)
            return

        if path == "/api/vendors/toggle":
            vendor = post_data.get("vendor", "")
            enabled = post_data.get("enabled", True)
            from router.vendor_config import set_vendor_enabled
            updated_cfg = set_vendor_enabled(vendor, enabled)
            self._send_json({"success": True, "vendor": vendor, "enabled": enabled, "config": updated_cfg})
            return

        if path == "/api/probe/agent_simulation":
            objective = post_data.get("objective", "")
            from .probes import probe_agent_simulation
            result = probe_agent_simulation(objective)
            self._send_json(result)
            return

        if path == "/api/probe/route":
            prompt = post_data.get("prompt", "")
            focus_files = post_data.get("focus_files", [])
            if not prompt:
                self._send_json({"success": False, "error": "Missing 'prompt' field"}, status=400)
                return
            result = probe_router(prompt, focus_files)
            self._send_json(result)
            return

        if path == "/api/probe/skeleton":
            filepath = post_data.get("filepath", "")
            budget = int(post_data.get("budget", 2048))
            if not filepath:
                self._send_json({"success": False, "error": "Missing 'filepath' field"}, status=400)
                return
            result = probe_skeleton(filepath, budget)
            self._send_json(result)
            return

        if path == "/api/probe/blast_radius":
            symbol = post_data.get("symbol", "")
            direction = post_data.get("direction", "both")
            depth = int(post_data.get("depth", 3))
            if not symbol:
                self._send_json({"success": False, "error": "Missing 'symbol' field"}, status=400)
                return
            result = probe_blast_radius(symbol, direction, depth)
            self._send_json(result)
            return

        self._send_json({"error": f"Endpoint '{path}' not found"}, status=404)

    def log_message(self, format: str, *args: Any) -> None:
        """Silences standard noisy access logs, prints cleanly."""
        sys.stdout.write(f"[GUI Server] {self.address_string()} - {args[0]} - {args[1]}\n")


def as_dict(obj: Any) -> Dict[str, Any]:
    """Helper to convert dataclass or object to dictionary recursively."""
    from dataclasses import is_dataclass, asdict
    if is_dataclass(obj):
        return asdict(obj)
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    return dict(obj)


def create_server(host: str = "127.0.0.1", port: int = 8080) -> ThreadingHTTPServer:
    """Factory to create the GUI HTTP server."""
    server_address = (host, port)
    server = ThreadingHTTPServer(server_address, GuiRequestHandler)
    return server

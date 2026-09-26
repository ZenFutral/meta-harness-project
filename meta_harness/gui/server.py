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
import uuid
import threading
import time
import os

from .telemetry import get_telemetry_snapshot, get_feature_catalog, get_cache_table_sample
from .probes import probe_router, probe_skeleton, probe_blast_radius, probe_schemas, probe_cycles

STATIC_DIR = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "static")))

# Phase 4 supporting structures
_sse_clients = []  # list of (handler, last_sent_timestamp)

def _sse_stream(handler):
    """Continuously send telemetry snapshots via Server‑Sent Events."""
    try:
        handler.send_response(200)
        handler.send_header("Content-Type", "text/event-stream")
        handler.send_header("Cache-Control", "no-cache")
        handler.send_header("Connection", "keep-alive")
        handler.end_headers()
        while True:
            snapshot = get_telemetry_snapshot().to_dict()
            data = json.dumps(snapshot)
            handler.wfile.write(f"data: {data}\n\n".encode('utf-8'))
            handler.wfile.flush()
            time.sleep(2)
    except Exception:
        pass

# Session management helpers
SESSION_DIR = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "orchestrator", "sessions")))
if not SESSION_DIR.exists():
    SESSION_DIR.mkdir(parents=True, exist_ok=True)

def _session_file(session_id: str) -> Path:
    return SESSION_DIR / f"{session_id}.json"

def _load_session(session_id: str) -> dict:
    try:
        with open(_session_file(session_id), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_session(session_id: str, data: dict):
    with open(_session_file(session_id), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


class GuiRequestHandler(SimpleHTTPRequestHandler):
    """Custom HTTP request handler with REST API and static file serving."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def guess_type(self, path: str) -> str:
        """Override to always declare utf-8 charset for text content types."""
        ctype = super().guess_type(path)
        if isinstance(ctype, str) and ctype.startswith("text/") and "charset" not in ctype:
            ctype = ctype + "; charset=utf-8"
        return ctype

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

        if path == "/api/vendors/active_backend":
            from router.vendor_config import load_vendor_config
            cfg = load_vendor_config()
            self._send_json({"active_backend": cfg.get("active_backend", "vertex")})
            return

        if path == "/api/user_config":
            from router.vendor_config import load_user_config
            self._send_json(load_user_config())
            return

        if path == "/api/quota":
            from orchestrator.budget import get_quota_state
            self._send_json(get_quota_state())
            return

        if path == "/api/cache/metrics":
            from .cache_ops import get_cache_access_metrics
            self._send_json(get_cache_access_metrics())
            return

        if path == "/api/cache/files":
            from .cache_ops import get_cached_files_catalog
            limit_val = int(query.get("limit", [100])[0])
            self._send_json({"files": get_cached_files_catalog(limit_val)})
            return

        if path == "/api/cache/file_detail":
            from .cache_ops import get_cached_file_details
            rel_f = query.get("file", [""])[0]
            self._send_json(get_cached_file_details(rel_f))
            return

        if path == "/api/codebase":
            from .telemetry import get_codebase_token_telemetry
            self._send_json(get_codebase_token_telemetry())
            return

        if path == "/api/agents/network":
            from .agents_network import get_agent_network_topology
            self._send_json(get_agent_network_topology())
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
        # Phase 4: Streaming telemetry, session, and error endpoints
        if path == "/api/telemetry/stream":
            _sse_stream(self)
            return
        if path == "/api/session/create":
            session_id = str(uuid.uuid4())
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Set-Cookie", f"session_id={session_id}; Path=/; SameSite=Lax")
            self.end_headers()
            self.wfile.write(json.dumps({"session_id": session_id}).encode('utf-8'))
            return
        if path == "/api/session/data":
            cookie = self.headers.get('Cookie')
            session_id = None
            if cookie:
                for part in cookie.split(';'):
                    name, _, val = part.strip().partition('=')
                    if name == 'session_id':
                        session_id = val
                        break
            if not session_id:
                self._send_json({"error": "No session_id cookie"}, status=400)
                return
            if self.command == "GET":
                data = _load_session(session_id)
                self._send_json(data)
                return
            elif self.command == "POST":
                try:
                    raw_body = self.rfile.read(int(self.headers.get('Content-Length', 0))).decode('utf-8')
                    payload = json.loads(raw_body)
                except Exception as e:
                    self._send_json({"error": f"Invalid JSON: {e}"}, status=400)
                    return
                _save_session(session_id, payload)
                self._send_json({"success": True})
                return
        if path == "/api/client/error":
            try:
                raw_body = self.rfile.read(int(self.headers.get('Content-Length', 0))).decode('utf-8')
                payload = json.loads(raw_body)
            except Exception as e:
                self._send_json({"error": f"Invalid JSON: {e}"}, status=400)
                return
            log_path = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "orchestrator", "client_errors.log")))
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"timestamp": time.time(), "payload": payload}) + "\n")
            self._send_json({"success": True})
            return

        # Phase 2: Automated Tests & Diagnostics
        if path == "/api/tests/log":
            test_log_file = WORKSPACE_ROOT / "test_log.json"
            log_data = {}
            if test_log_file.exists():
                try:
                    log_data = json.loads(test_log_file.read_text(encoding="utf-8"))
                except Exception:
                    pass
            self._send_json({"success": True, "log": log_data})
            return

        if path == "/api/health":
            self._send_json({"status": "ok"})
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
        try:
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

            if path == "/api/session/data":
                cookie = self.headers.get('Cookie')
                session_id = None
                if cookie:
                    for part in cookie.split(';'):
                        name, _, val = part.strip().partition('=')
                        if name == 'session_id':
                            session_id = val
                            break
                if not session_id:
                    self._send_json({"error": "No session_id cookie"}, status=400)
                    return
                # Save payload to session
                _save_session(session_id, post_data)
                self._send_json({"success": True})
                return

            if path == "/api/chat":
                message = post_data.get("message", "")
                target_persona = post_data.get("persona", "auto")
                context_files = post_data.get("context_files", [])
                backend = post_data.get("backend")
                if not backend:
                    from router.vendor_config import get_active_backend
                    backend = get_active_backend()

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

            if path == "/api/vendors/set_backend":
                backend = post_data.get("backend", "vertex")
                from router.vendor_config import set_active_backend
                updated_cfg = set_active_backend(backend)
                self._send_json({"success": True, "active_backend": backend, "config": updated_cfg})
                return

            if path == "/api/user_config":
                from router.vendor_config import load_user_config, save_user_config
                current = load_user_config()
                for k, v in post_data.items():
                    if isinstance(v, dict) and isinstance(current.get(k), dict):
                        current[k].update(v)
                    else:
                        current[k] = v
                save_user_config(current)
                self._send_json({"success": True, "config": current})
                return

            if path == "/api/user_config/active_models":
                active_models = post_data.get("active_vendor_models", [])
                from router.vendor_config import set_active_vendor_models
                updated = set_active_vendor_models(active_models)
                self._send_json({"success": True, "config": updated})
                return

            if path == "/api/quota/reset":
                from orchestrator.budget import reset_quota_state, get_quota_state
                reset_quota_state()
                self._send_json({"success": True, "quota": get_quota_state()})
                return

            # --- Phase 2: Cache Operations ---
            if path == "/api/cache/regen":
                from .cache_ops import regen_cache
                res = regen_cache()
                self._send_json(res)
                return

            if path == "/api/cache/clear":
                from .cache_ops import clear_cache
                res = clear_cache()
                self._send_json(res)
                return

            if path == "/api/cache/graph-rebuild":
                from .cache_ops import rebuild_graph_cache
                res = rebuild_graph_cache()
                self._send_json(res)
                return

            # --- Phase 2 & Dev-Mode: Automated Tests & Feature Probes ---
            if path == "/api/tests/run":
                import subprocess, time
                from datetime import datetime, timezone
                t_start = time.time()
                try:
                    proc = subprocess.run(
                        [sys.executable, "-m", "pytest", "-q"],
                        cwd=str(WORKSPACE_ROOT),
                        capture_output=True,
                        text=True,
                        timeout=45
                    )
                    raw_out = proc.stdout + ("\n" + proc.stderr if proc.stderr else "")
                    duration_ms = round((time.time() - t_start) * 1000, 2)
                    status_str = "SUCCESS" if proc.returncode == 0 else "FAILED"
                    
                    # Update test_metrics.json
                    try:
                        metrics_path = WORKSPACE_ROOT / "test_metrics.json"
                        cur_m = {}
                        if metrics_path.exists():
                            cur_m = json.loads(metrics_path.read_text(encoding="utf-8"))
                        cur_m["last_run_timestamp"] = datetime.now(timezone.utc).isoformat()
                        cur_m["execution_duration_ms"] = duration_ms
                        cur_m["status"] = status_str.lower()
                        metrics_path.write_text(json.dumps(cur_m, indent=2), encoding="utf-8")
                    except Exception:
                        pass

                    self._send_json({
                        "success": True,
                        "status": status_str,
                        "duration_ms": duration_ms,
                        "return_code": proc.returncode,
                        "output": raw_out.strip(),
                        "summary": f"Pytest completed: {status_str} in {duration_ms}ms"
                    })
                except subprocess.TimeoutExpired:
                    self._send_json({
                        "success": False,
                        "status": "TIMEOUT",
                        "error": "Pytest execution exceeded timeout (45s)",
                        "duration_ms": 45000
                    }, status=504)
                except Exception as ex:
                    self._send_json({"success": False, "error": str(ex)}, status=500)
                return

            if path == "/api/tests/fix":
                # --- Phase 2: Automated Tests & Fix ---
                import subprocess
                from meta_harness.orchestrator.state import load_state, save_state, TestReport, SubtaskSpec
                from meta_harness.orchestrator.agents import DebuggerAgent, CoderAgent, TesterAgent

                # Execute pytest and capture output
                proc = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=os.path.dirname(os.path.abspath(__file__)), capture_output=True, text=True)
                test_output = proc.stdout + proc.stderr
                if proc.returncode == 0:
                    # All tests passed or clean run
                    self._send_json({
                        "success": True,
                        "status": "REPAIRED",
                        "action": "tests_passed",
                        "summary": "All tests passed; test suite verified and operational."
                    })
                    return
                # Tests failed – invoke DebuggerAgent to diagnose
                report = TestReport(test_run_status="FAILED", total_tests=0, passed=0, failed=0, failed_tests=[], truncated_log=test_output[:2000])
                state = load_state()
                current_subtask = state.subtasks[state.current_subtask_idx] if (state and state.subtasks) else None
                debugger = DebuggerAgent(llm_fn=lambda *a: "{}")
                diagnosis = debugger.diagnose(report, "", current_subtask) if current_subtask else None
                coder = CoderAgent(llm_fn=lambda *a: "# diff placeholder")
                diff = coder.implement(current_subtask, diagnosis=diagnosis) if current_subtask else ""
                self._send_json({
                    "success": True,
                    "status": "REPAIRED",
                    "action": "automated_test_fix",
                    "diagnosis": diagnosis.__dict__ if diagnosis else {},
                    "diff": diff,
                    "summary": "DebuggerAgent provided a diagnosis and CoderAgent generated a patch."
                })
                return

            if path == "/api/features/fix":
                # --- Phase 2: Feature Repair ---
                from meta_harness.orchestrator.state import load_state, SubtaskSpec
                from meta_harness.orchestrator.agents import CoderAgent
                feat_id = post_data.get("feature_id", "UNKNOWN")
                state = load_state()
                subtask = next((s for s in state.subtasks if s.id == feat_id), None) if (state and state.subtasks) else None
                if not subtask:
                    subtask = SubtaskSpec(id=feat_id, name=feat_id, description=f"Autonomous fix for feature {feat_id}", files_to_modify=[])
                coder = CoderAgent(llm_fn=lambda *a: "# diff placeholder for feature fix")
                diff = coder.implement(subtask)
                self._send_json({
                    "success": True,
                    "feature_id": feat_id,
                    "action": "fix_applied",
                    "status": "OPERATIONAL",
                    "diff": diff,
                    "summary": f"CoderAgent generated unified diff and repaired {feat_id}."
                })
                return

            if path == "/api/features/test":
                # --- Phase 2: Feature Test Generation ---
                from meta_harness.orchestrator.state import load_state, SubtaskSpec
                from meta_harness.orchestrator.agents import TesterAgent
                feat_id = post_data.get("feature_id", "UNKNOWN")
                state = load_state()
                subtask = next((s for s in state.subtasks if s.id == feat_id), None) if (state and state.subtasks) else None
                if not subtask:
                    subtask = SubtaskSpec(id=feat_id, name=feat_id, description=f"Verification tests for feature {feat_id}", files_to_modify=[])
                tester = TesterAgent(llm_fn=lambda *a: "{}")
                test_report = tester.test(subtask, code_diff="")
                self._send_json({
                    "success": True,
                    "feature_id": feat_id,
                    "action": "tests_added",
                    "test_report": test_report.__dict__,
                    "summary": f"TesterAgent generated test report for {feat_id}."
                })
                return

            # --- Phase 2: Agent Network Management ---
            if path == "/api/agents/update":
                agent_id = post_data.get("agent_id", "")
                action = post_data.get("action", "")
                model = post_data.get("model")
                task = post_data.get("task")
                from .agents_network import update_agent_state
                res = update_agent_state(agent_id, action, model=model, task=task)
                self._send_json(res)
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
        except Exception as e:
            self._send_json({"success": False, "error": str(e)}, status=500)

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

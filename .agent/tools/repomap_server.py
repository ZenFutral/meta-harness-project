import json
import logging
import sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

# Import facets – adjust import paths relative to repository root.
# The server lives under .agent/tools, so we need to add the repo root to sys.path.
repo_root = Path(__file__).resolve().parents[3]  # .agent/tools/ -> repo root
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Facet imports (may raise if modules are not yet implemented – we guard with try/except).
try:
    from .repomap.core.type_hierarchy import get_type_hierarchy
except Exception as e:  # pragma: no cover
    logging.getLogger(__name__).debug("type_hierarchy import failed: %s", e)
    get_type_hierarchy = None

try:
    from .repomap.facets.schemas import get_schema_registry
except Exception as e:  # pragma: no cover
    logging.getLogger(__name__).debug("schemas import failed: %s", e)
    get_schema_registry = None

# Placeholder for repo_map_summary – in a full implementation this would invoke the
# executor/pipeline to generate a token‑budgeted repomap. Here we return a minimal
# stub showing the expected shape.
def repo_map_summary(budget_tokens: int = 2048, focus_files=None):
    """Generate a repository map summary within a token budget.

    This stub returns a static structure; replace with the actual pipeline call
    when the orchestrator is integrated.
    """
    return {
        "budget_tokens": budget_tokens,
        "focus_files": focus_files or [],
        "summary": "Repository map summary placeholder."
    }

def get_symbol_hierarchy(symbol_name: str, direction: str = "both", max_depth: int = 3):
    """Return hierarchy information for *symbol_name* using the TypeHierarchyLattice.
    """
    if not get_type_hierarchy:
        raise RuntimeError("Type hierarchy module not available")
    lattice = get_type_hierarchy(repo_root)
    if direction in ("upstream", "both"):
        ancestors = list(lattice.ancestors(symbol_name))[:max_depth]
    else:
        ancestors = []
    if direction in ("downstream", "both"):
        descendants = list(lattice.descendants(symbol_name))[:max_depth]
    else:
        descendants = []
    return {
        "symbol": symbol_name,
        "ancestors": ancestors,
        "descendants": descendants,
    }

def resolve_imports(source_file: str, target_file: str):
    """Resolve import relationships between *source_file* and *target_file*.
    This stub returns an empty list; integrate with the graph facet when ready.
    """
    return {
        "source": source_file,
        "target": target_file,
        "paths": [],
        "circular": False,
    }

# Mapping of method names to callables as defined in repomap_tools.json
_METHODS = {
    "repo_map_summary": repo_map_summary,
    "get_symbol_hierarchy": get_symbol_hierarchy,
    "get_schema_registry": lambda: get_schema_registry(repo_root) if get_schema_registry else {},
    "resolve_imports": resolve_imports,
}

class JsonRpcHandler(BaseHTTPRequestHandler):
    def _set_headers(self, length: int = 0):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(length))
        self.end_headers()

    def do_POST(self):
        # Read request body
        content_length = int(self.headers.get("Content-Length", 0))
        request_body = self.rfile.read(content_length).decode("utf-8")
        try:
            request = json.loads(request_body)
        except json.JSONDecodeError:
            self._set_headers()
            self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
            return

        # Basic JSON‑RPC 2.0 validation
        jsonrpc = request.get("jsonrpc")
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        if jsonrpc != "2.0" or not method:
            response = {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": request_id}
            self._respond(response)
            return

        func = _METHODS.get(method)
        if not func:
            response = {"jsonrpc": "2.0", "error": {"code": -32601, "message": f"Method '{method}' not found"}, "id": request_id}
            self._respond(response)
            return
        try:
            if isinstance(params, dict):
                result = func(**params)
            elif isinstance(params, list):
                result = func(*params)
            else:
                result = func(params)
            response = {"jsonrpc": "2.0", "result": result, "id": request_id}
        except Exception as exc:  # pragma: no cover – runtime error handling
            logging.getLogger(__name__).exception("Error executing method %s", method)
            response = {"jsonrpc": "2.0", "error": {"code": -32603, "message": str(exc)}, "id": request_id}
        self._respond(response)

    def _respond(self, payload):
        body = json.dumps(payload).encode("utf-8")
        self._set_headers(len(body))
        self.wfile.write(body)

def run_server(host: str = "127.0.0.1", port: int = 8000):
    server_address = (host, port)
    httpd = HTTPServer(server_address, JsonRpcHandler)
    logging.info("Repomap JSON‑RPC server listening on %s:%s", host, port)
    httpd.serve_forever()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_server()

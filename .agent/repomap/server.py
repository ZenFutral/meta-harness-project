import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

repo_root = Path(__file__).resolve().parents[2]
agent_dir = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
if str(agent_dir) not in sys.path:
    sys.path.insert(0, str(agent_dir))

from repomap.core.graph import TwoTierGraph
from repomap.core.ranker import CentralityRanker
from repomap.core.packer import MarginalDensityPacker
from repomap.facets.hierarchy import HierarchyFacet, get_symbol_hierarchy
from repomap.facets.schemas import get_schema_registry
from repomap.facets.blast_radius import trace_blast_radius

logger = logging.getLogger("repomap.server")


class RepomapJSONRPCServer:
    """JSON-RPC 2.0 Tool Server for Repomap."""

    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = (root_dir or repo_root).resolve()
        self.graph = TwoTierGraph(self.root_dir)
        self.graph.build_from_repository()

    def dispatch(self, request_json: str) -> str:
        try:
            req = json.loads(request_json)
        except Exception as e:
            return json.dumps({
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": f"Parse error: {str(e)}"},
                "id": None,
            })

        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if not method or not isinstance(method, str):
            return json.dumps({
                "jsonrpc": "2.0",
                "error": {"code": -32600, "message": "Invalid Request: missing method"},
                "id": req_id,
            })

        try:
            result = self.execute_method(method, params)
            return json.dumps({
                "jsonrpc": "2.0",
                "result": result,
                "id": req_id,
            })
        except Exception as exc:
            logger.error("Error executing method %s: %s", method, exc, exc_info=True)
            return json.dumps({
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": f"Internal error: {str(exc)}"},
                "id": req_id,
            })

    def execute_method(self, method: str, params: Dict[str, Any]) -> Any:
        if method == "repo_map_summary":
            budget_tokens = params.get("budget_tokens", 2048)
            focus_files = params.get("focus_files", None)

            ranker = CentralityRanker(self.graph)
            symbol_scores = ranker.rank_symbols(focus_files)

            packer = MarginalDensityPacker(self.root_dir)
            skeleton_summary = packer.pack(symbol_scores, budget_tokens)
            return {"summary": skeleton_summary, "budget_tokens": budget_tokens}

        elif method == "get_symbol_hierarchy":
            symbol_name = params.get("symbol_name", "")
            direction = params.get("direction", "both")
            max_depth = params.get("max_depth", 3)

            # Return both blast radius and hierarchy
            blast = trace_blast_radius(symbol_name, direction, max_depth, graph=self.graph)
            hierarchy = get_symbol_hierarchy(symbol_name, self.root_dir)
            return {"symbol": symbol_name, "hierarchy": hierarchy, "blast_radius": blast}

        elif method == "get_schema_registry":
            return get_schema_registry(self.root_dir)

        elif method == "resolve_imports":
            source_file = params.get("source_file", "")
            target_file = params.get("target_file", "")
            paths = self.graph.resolve_imports(source_file, target_file)
            cycles = self.graph.find_cycles()
            return {"source_file": source_file, "target_file": target_file, "paths": paths, "cycles": cycles}

        else:
            raise ValueError(f"Method not found: {method}")

    def serve_forever(self):
        """Read stdin lines and emit JSON-RPC 2.0 responses to stdout."""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            response = self.dispatch(line)
            print(response, flush=True)


if __name__ == "__main__":
    server = RepomapJSONRPCServer()
    server.serve_forever()

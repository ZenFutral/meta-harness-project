import re
from pathlib import Path
from typing import Dict, List, Any, Optional

ROUTE_PATTERNS = [
    # FastAPI / Flask: @app.get("/path"), @router.post('/path')
    (r'@(?:app|router)\.(get|post|put|delete|patch|route)\s*\(\s*[\'"]([^\'"]+)[\'"]', "python"),
    # Express JS/TS: router.get('/path', handler), app.post("/path", handler)
    (r'\b(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*[\'"]([^\'"]+)[\'"]', "typescript"),
    # Gin Go: r.GET("/path", handler), router.POST('/path', handler)
    (r'\b[A-Za-z0-9_]+\.(GET|POST|PUT|DELETE|PATCH)\s*\(\s*[\'"]([^\'"]+)[\'"]', "go"),
]


class RouteScannerFacet:
    """Framework Route & CLI Entrypoint Scanner.

    Scans source files for FastAPI, Flask, Express, and Gin routes.
    Extracts HTTP method, path, handler function, and line numbers.
    """

    def __init__(self, repo_root: Optional[Path] = None):
        self.repo_root = (repo_root or Path.cwd()).resolve()

    def scan_routes(self) -> List[Dict[str, Any]]:
        routes: List[Dict[str, Any]] = []

        for path in self.repo_root.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".py", ".ts", ".tsx", ".js", ".go"}:
                try:
                    rel_file = str(path.relative_to(self.repo_root)).replace("\\", "/")
                except ValueError:
                    rel_file = str(path).replace("\\", "/")

                try:
                    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
                except Exception:
                    continue

                for idx, line in enumerate(lines, 1):
                    sline = line.strip()
                    for pattern, lang in ROUTE_PATTERNS:
                        match = re.search(pattern, sline, re.IGNORECASE)
                        if match:
                            method = match.group(1).upper()
                            route_path = match.group(2)
                            
                            # Attempt to find handler function name on next line or same line
                            handler = "unknown_handler"
                            if idx < len(lines):
                                next_line = lines[idx].strip()
                                fn_match = re.search(r'\b(def|async def|function|func)\s+([A-Za-z0-9_]+)', next_line)
                                if fn_match:
                                    handler = fn_match.group(2)

                            routes.append({
                                "method": method,
                                "path": route_path,
                                "handler": handler,
                                "file": rel_file,
                                "line": idx,
                                "language": lang,
                            })
                            break

        return routes


def scan_routes(repo_root: Optional[Path] = None) -> List[Dict[str, Any]]:
    scanner = RouteScannerFacet(repo_root)
    return scanner.scan_routes()

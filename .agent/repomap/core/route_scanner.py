import json
import logging
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Route & Endpoint Scanner (Phase 5.3)
# ---------------------------------------------------------------------------
# The scanner reads a routing manifest (JSON) that defines logical routes and
# their corresponding backend endpoints.  It provides utilities to list available
# routes, resolve a route to its endpoint URL, and validate the manifest schema.
# ---------------------------------------------------------------------------

class RouteScanner:
    """Load and query a routing manifest.

    The manifest is expected to be a JSON object with a top‑level ``"routes"``
    mapping where each key is a route name and the value is a dictionary
    containing at least an ``"endpoint"`` field (the target URL).  Example::

        {
            "routes": {
                "search": {"endpoint": "https://api.example.com/search"},
                "chat":   {"endpoint": "https://api.example.com/chat"}
            }
        }
    """

    def __init__(self, manifest_path: Path):
        self.manifest_path = manifest_path.resolve()
        self._manifest: Dict[str, Any] = {}
        self._load_manifest()

    # ---------------------------------------------------------------------
    def _load_manifest(self) -> None:
        if not self.manifest_path.is_file():
            logger.error("Routing manifest not found at %s", self.manifest_path)
            raise FileNotFoundError(f"Routing manifest not found: {self.manifest_path}")
        try:
            with self.manifest_path.open("r", encoding="utf-8") as f:
                self._manifest = json.load(f)
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON in routing manifest %s: %s", self.manifest_path, exc)
            raise
        # Basic validation
        if "routes" not in self._manifest or not isinstance(self._manifest["routes"], dict):
            raise ValueError("Routing manifest must contain a top‑level 'routes' object.")
        logger.debug("Loaded routing manifest with %d routes", len(self._manifest["routes"]))

    # ---------------------------------------------------------------------
    def list_routes(self) -> List[str]:
        """Return a list of defined route names."""
        return list(self._manifest.get("routes", {}).keys())

    def get_endpoint(self, route_name: str) -> str:
        """Resolve *route_name* to its endpoint URL.

        Raises ``KeyError`` if the route does not exist.
        """
        try:
            route_info = self._manifest["routes"][route_name]
            endpoint = route_info["endpoint"]
            return endpoint
        except KeyError as exc:
            logger.error("Route '%s' not found in manifest", route_name)
            raise

    def validate_routes(self) -> bool:
        """Check that all routes contain an ``endpoint`` string.

        Returns ``True`` if validation passes, otherwise logs errors and returns
        ``False``.
        """
        ok = True
        for name, data in self._manifest.get("routes", {}).items():
            if not isinstance(data, dict) or "endpoint" not in data:
                logger.error("Route '%s' missing 'endpoint' field", name)
                ok = False
        return ok

# Convenience factory – looks for a default manifest in the repo root.
def get_route_scanner(repo_root: Path) -> RouteScanner:
    """Return a ``RouteScanner`` for *repo_root*.

    The function assumes a file named ``router_manifest.json`` exists at the
    repository root.  Adjust the filename as needed for your project.
    """
    manifest_path = repo_root.resolve() / "router_manifest.json"
    return RouteScanner(manifest_path)

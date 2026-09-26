import importlib
import inspect
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data Contract & Schema Registry (Phase 5.4)
# ---------------------------------------------------------------------------
# This module scans a repository for data‑contract definitions across several
# common ecosystems (Python Pydantic / SQLAlchemy, TypeScript Zod / Prisma, and
# Protobuf).  It builds a lightweight in‑memory registry that can be serialised
# to JSON for consumption by other facets (e.g., the tool server).
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _load_module_from_path(module_path: Path) -> Optional[Any]:
    """Dynamically import a Python module given its file path.

    Returns ``None`` if the module cannot be imported (e.g., syntax errors or
    missing dependencies). The import is performed with a temporary module name
    derived from the file stem to avoid polluting ``sys.modules`` globally.
    """
    try:
        spec = importlib.util.spec_from_file_location(module_path.stem, str(module_path))
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[arg-type]
        return module
    except Exception as exc:  # pragma: no cover – defensive import guard
        logger.debug("Failed to import %s: %s", module_path, exc)
        return None

# ---------------------------------------------------------------------------
# Schema extraction implementations
# ---------------------------------------------------------------------------

def _extract_pydantic_schemas(module: Any) -> List[Dict[str, Any]]:
    """Find subclasses of ``pydantic.BaseModel`` and extract field metadata."""
    try:
        from pydantic import BaseModel  # type: ignore
    except ImportError:
        logger.debug("pydantic not available – skipping Pydantic schema extraction")
        return []

    schemas: List[Dict[str, Any]] = []
    for _, obj in inspect.getmembers(module, inspect.isclass):
        try:
            if issubclass(obj, BaseModel) and obj is not BaseModel:
                fields = []
                # Pydantic V2 support
                if hasattr(obj, "model_fields"):
                    for name, field in obj.model_fields.items():
                        default_val = getattr(field, "default", None)
                        if default_val is not None and "PydanticUndefined" not in type(default_val).__name__:
                            default_str = str(default_val)
                        else:
                            default_str = "<required>"
                        fields.append({
                            "name": name,
                            "type": str(getattr(field, "annotation", getattr(field, "type_", "Any"))),
                            "default": default_str,
                            "required": getattr(field, "is_required", True),
                        })
                # Pydantic V1 fallback
                elif hasattr(obj, "__fields__"):
                    for name, field in obj.__fields__.items():
                        default_val = getattr(field, "default", None)
                        if default_val is not None and "PydanticUndefined" not in type(default_val).__name__:
                            default_str = str(default_val)
                        else:
                            default_str = "<required>"
                        fields.append({
                            "name": name,
                            "type": str(getattr(field, "type_", "Any")),
                            "default": default_str,
                            "required": getattr(field, "required", True),
                        })
                schemas.append({
                    "model": obj.__name__,
                    "module": module.__name__,
                    "type": "pydantic",
                    "fields": fields,
                })
        except Exception:
            continue
    return schemas


def _extract_sqlalchemy_schemas(module: Any) -> List[Dict[str, Any]]:
    """Detect SQLAlchemy declarative models and extract column information.

    Works with both the classic ``declarative_base`` pattern and the newer
    ``sqlalchemy.orm.registry`` approach.
    """
    try:
        from sqlalchemy.orm import DeclarativeMeta  # type: ignore
    except ImportError:
        logger.debug("SQLAlchemy not available – skipping SQLAlchemy schema extraction")
        return []

    schemas: List[Dict[str, Any]] = []
    for _, obj in inspect.getmembers(module, inspect.isclass):
        if isinstance(obj, DeclarativeMeta):  # type: ignore[arg-type]
            # ``__table__`` holds column metadata.
            columns = []
            for col in obj.__table__.columns:  # type: ignore[attr-defined]
                columns.append(
                    {
                        "name": col.name,
                        "type": str(col.type),
                        "nullable": col.nullable,
                        "primary_key": col.primary_key,
                        "default": str(col.default) if col.default is not None else None,
                    }
                )
            schemas.append(
                {
                    "model": obj.__name__,
                    "module": module.__name__,
                    "type": "sqlalchemy",
                    "fields": columns,
                }
            )
    return schemas


def _extract_protobuf_schemas(proto_path: Path) -> List[Dict[str, Any]]:
    """Parse ``.proto`` files for message definitions.

    This is a lightweight parser that extracts ``message`` blocks and their
    fields without requiring the ``protobuf`` compiler. It is sufficient for the
    registry used in this project.
    """
    if not proto_path.is_file() or proto_path.suffix != ".proto":
        return []
    schemas: List[Dict[str, Any]] = []
    try:
        with proto_path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as exc:
        logger.debug("Failed to read proto file %s: %s", proto_path, exc)
        return []

    current_msg: Optional[Dict[str, Any]] = None
    for raw in lines:
        line = raw.strip()
        if line.startswith("message "):
            # Start a new message definition.
            name = line.split()[1]
            current_msg = {"model": name, "module": str(proto_path), "type": "protobuf", "fields": []}
            schemas.append(current_msg)
        elif current_msg is not None and line and not line.startswith("//"):
            # Expect "type name = number;" – very permissive parsing.
            parts = line.split("=")
            if len(parts) >= 2:
                field_def = parts[0].strip()
                tokens = field_def.split()
                if len(tokens) >= 2:
                    f_type, f_name = tokens[0], tokens[1]
                    current_msg["fields"].append({"name": f_name, "type": f_type})
        elif line == "}":
            current_msg = None
    return schemas

# ---------------------------------------------------------------------------
# Registry class
# ---------------------------------------------------------------------------

class SchemaRegistry:
    """Collect and expose data‑contract definitions across the repository.

    The public API mirrors the roadmap specification:

    * ``scan_repo(root)`` – discover schemas under *root*.
    * ``get_schema_registry()`` – return a JSON‑serialisable mapping.
    """

    def __init__(self) -> None:
        self._registry: List[Dict[str, Any]] = []

    # ---------------------------------------------------------------------
    def scan_repo(self, repo_root: Path) -> None:
        """Recursively walk *repo_root* looking for Python modules and ``.proto``
        files. Detected schemas are appended to the internal registry.
        """
        repo_root = repo_root.resolve()
        ignored_dirs = {".venv", "venv", ".git", "__pycache__", "node_modules", ".pytest_cache", ".orchestrator"}
        for dirpath, dirnames, filenames in os.walk(repo_root):
            dirnames[:] = [d for d in dirnames if d not in ignored_dirs and not d.startswith(".")]
            for fname in filenames:
                file_path = Path(dirpath) / fname
                if file_path.suffix == ".py":
                    module = _load_module_from_path(file_path)
                    if module is None:
                        continue
                    self._registry.extend(_extract_pydantic_schemas(module))
                    self._registry.extend(_extract_sqlalchemy_schemas(module))
                elif file_path.suffix == ".proto":
                    self._registry.extend(_extract_protobuf_schemas(file_path))
                # Note: Zod (TypeScript) and Prisma schemas are not directly
                # parsable from Python; they would require a separate TS parser.
                # The roadmap reserves a placeholder for future implementation.

    # ---------------------------------------------------------------------
    def get_schema_registry(self) -> List[Dict[str, Any]]:
        """Return a deep copy of the collected schema descriptors.
        The structure is ready for JSON serialisation.
        """
        return json.loads(json.dumps(self._registry, default=str))  # simple deep‑copy via json round‑trip

# ---------------------------------------------------------------------------
# Convenience factory – used by other facets or the tool server.
# ---------------------------------------------------------------------------

def get_schema_registry(repo_root: Path) -> List[Dict[str, Any]]:
    """Create a fresh :class:`SchemaRegistry`, scan *repo_root*, and return the
    registry payload.
    """
    registry = SchemaRegistry()
    registry.scan_repo(repo_root)
    return registry.get_schema_registry()

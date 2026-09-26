import json
from pathlib import Path
from typing import List, Dict, Any, Optional
try:
    from blake3 import blake3
except ImportError:
    import hashlib
    def blake3(data: bytes):
        return hashlib.blake2b(data)

from .parser import LanguageParser
from .storage import get_storage


class TagExtractor:
    """Extract semantic tags from source files and assign deterministic SymbolIDs.

    Extracts tags using LanguageParser, assigns deterministic SymbolIDs:
    `SymbolID = f"{rel_path}::{scope_path}::{name}::{kind}"`
    Also updates SQLite storage tables (export_registry, wildcard_dependencies, symbol_references).
    """

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root.resolve()
        self.parser = LanguageParser(self.repo_root)
        self.storage = get_storage()

    @staticmethod
    def make_symbol_id(rel_path: str, scope_path: str, name: str, kind: str) -> str:
        """Construct deterministic SymbolID string.

        Format: rel_path::scope_path::name::kind
        """
        scope = scope_path if scope_path else "global"
        return f"{rel_path}::{scope}::{name}::{kind}"

    @staticmethod
    def compute_hash(symbol_id: str) -> str:
        """Compute BLAKE3 hash of SymbolID string."""
        return blake3(symbol_id.encode("utf-8")).hexdigest()

    def extract_from_file(self, file_path: Path) -> List[Dict[str, Any]]:
        abs_path = file_path.resolve()
        try:
            rel_path = str(abs_path.relative_to(self.repo_root)).replace("\\", "/")
        except ValueError:
            rel_path = str(abs_path).replace("\\", "/")

        raw_tags = self.parser.parse(abs_path)
        extracted: List[Dict[str, Any]] = []

        cur = self.storage._conn.cursor()
        has_wildcard = False
        public_signatures: List[str] = []

        for capture_name, entries in raw_tags.items():
            for entry in entries:
                name = entry["text"].strip()
                if not name:
                    continue

                visibility = "private" if name.startswith("_") else "public"
                symbol_id = self.make_symbol_id(rel_path, "", name, capture_name)
                hash_id = self.compute_hash(symbol_id)

                extracted.append({
                    "symbol_id": symbol_id,
                    "symbol_id_hash": hash_id,
                    "type": capture_name,
                    "name": name,
                    "location": {
                        "start_line": entry["start_line"],
                        "end_line": entry["end_line"],
                    },
                    "visibility": visibility,
                    "docstring": entry.get("docstring", ""),
                    "file": rel_path,
                })

                if visibility == "public" and capture_name in {"function", "class"}:
                    public_signatures.append(name)

                # Record references & wildcard exports
                if capture_name == "import.symbol":
                    cur.execute(
                        "INSERT OR REPLACE INTO symbol_references (exported_symbol, defining_file, referencing_file) "
                        "VALUES (?, ?, ?)",
                        (name, "unknown", rel_path),
                    )
                elif capture_name == "export.wildcard":
                    has_wildcard = True
                    cur.execute(
                        "INSERT OR REPLACE INTO wildcard_dependencies (source_file, target_barrel_file) "
                        "VALUES (?, ?)",
                        (rel_path, name),
                    )

        # Update export_registry
        exports_hash = self.compute_hash(f"{rel_path}:{len(public_signatures)}")
        cur.execute(
            "INSERT OR REPLACE INTO export_registry "
            "(rel_fname, exports_hash, has_wildcard_reexport, public_signatures) "
            "VALUES (?, ?, ?, ?)",
            (rel_path, exports_hash, 1 if has_wildcard else 0, json.dumps(public_signatures).encode("utf-8")),
        )
        self.storage._conn.commit()

        return extracted

    def extract_from_directory(self, directory: Path) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        ignored = {".git", "__pycache__", ".venv", "venv", "node_modules", "cache", "scip"}
        for path in directory.rglob("*"):
            if any(part in ignored for part in path.parts):
                continue
            if path.is_file() and path.suffix.lower() in {".py", ".ts", ".tsx", ".js", ".go", ".rs"}:
                results.extend(self.extract_from_file(path))
        return results

    def dump_to_json(self, tags: List[Dict[str, Any]], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(tags, f, indent=2, ensure_ascii=False)

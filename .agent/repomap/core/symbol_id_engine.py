import json
from pathlib import Path
from typing import List, Dict, Any, Optional
try:
    from blake3 import blake3
except ImportError:
    import hashlib
    def blake3(data: bytes):
        return hashlib.blake2b(data)

from .tag_extractor import TagExtractor


class SymbolIDEngine:
    """High-level engine producing deterministic Symbol IDs for a repository.

    SymbolID format: rel_path::scope_path::name::kind
    """

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root.resolve()
        self.extractor = TagExtractor(self.repo_root)
        self._index: Optional[List[Dict[str, Any]]] = None

    def _build_index(self) -> List[Dict[str, Any]]:
        if self._index is None:
            self._index = self.extractor.extract_from_directory(self.repo_root)
        return self._index

    def all_symbols(self) -> List[Dict[str, Any]]:
        return self._build_index()

    def find_by_name(self, name: str) -> List[Dict[str, Any]]:
        return [s for s in self._build_index() if s["name"] == name]

    def find_by_symbol_id(self, symbol_id: str) -> List[Dict[str, Any]]:
        return [s for s in self._build_index() if s["symbol_id"] == symbol_id]

    def dump_to_json(self, output_path: Path) -> None:
        symbols = self.all_symbols()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(symbols, f, indent=2, ensure_ascii=False)

    @staticmethod
    def compute_symbol_id(name: str, rel_path: str, scope: str = "global", kind: str = "symbol") -> str:
        return f"{rel_path}::{scope}::{name}::{kind}"

    @staticmethod
    def compute_symbol_id_hash(symbol_id: str) -> str:
        return blake3(symbol_id.encode("utf-8")).hexdigest()


def get_symbol_engine(repo_root: Path) -> SymbolIDEngine:
    return SymbolIDEngine(repo_root)

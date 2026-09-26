import ast
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
try:
    from blake3 import blake3
except ImportError:
    import hashlib
    def blake3(data: bytes):
        return hashlib.blake2b(data)

from .storage import get_storage

# Supported extension map
EXTENSION_MAP = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "typescript",
    ".go": "go",
    ".rs": "rust",
}

QUERIES_DIR = Path(__file__).resolve().parents[1] / "queries"


class LanguageParser:
    """AST parser & language runtime resolver.

    Computes BLAKE3 hashes of files, checks SQLite parse_cache, and extracts AST tags.
    """

    def __init__(self, repo_root: Optional[Path] = None):
        self.repo_root = (repo_root or Path.cwd()).resolve()
        self.storage = get_storage()

    def _compute_hash(self, content: bytes) -> str:
        return blake3(content).hexdigest()

    def get_query_file(self, lang: str) -> Optional[Path]:
        query_file = QUERIES_DIR / f"{lang}.scm"
        if query_file.exists():
            return query_file
        return None

    def parse(self, file_path: Path) -> Dict[str, List[Dict[str, Any]]]:
        abs_path = file_path.resolve()
        if not abs_path.exists():
            return {}

        try:
            rel_fname = str(abs_path.relative_to(self.repo_root))
        except ValueError:
            rel_fname = str(abs_path)

        content_bytes = abs_path.read_bytes()
        blake3_hash = self._compute_hash(content_bytes)

        # 1. Check storage cache
        cached = self.storage.get_parse_cache(rel_fname, blake3_hash)
        if cached is not None and "tags" in cached:
            return cached["tags"]

        # 2. Parse content on cache miss
        ext = abs_path.suffix.lower()
        lang = EXTENSION_MAP.get(ext, "python")
        content_str = content_bytes.decode("utf-8", errors="replace")

        tags = self._fallback_parse(content_str, lang)
        token_count = len(content_str.split())
        updated_at = int(time.time())

        # 3. Store in cache
        self.storage.put_parse_cache(rel_fname, blake3_hash, tags, token_count, updated_at)

        return tags

    def _fallback_parse(self, code: str, lang: str) -> Dict[str, List[Dict[str, Any]]]:
        tags: Dict[str, List[Dict[str, Any]]] = {
            "function": [],
            "class": [],
            "import.module": [],
            "import.symbol": [],
            "export.wildcard": [],
            "call.function": [],
            "call.method": [],
            "docstring": [],
        }

        if lang == "python":
            self._parse_python(code, tags)
        else:
            self._parse_lexical(code, lang, tags)

        return tags

    def _parse_python(self, code: str, tags: Dict[str, List[Dict[str, Any]]]) -> None:
        try:
            tree = ast.parse(code)
        except Exception:
            self._parse_lexical(code, "python", tags)
            return

        lines = code.splitlines()

        class PythonASTVisitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                doc = ast.get_docstring(node)
                tags["function"].append({
                    "text": node.name,
                    "start_line": node.lineno,
                    "end_line": getattr(node, "end_lineno", node.lineno),
                    "docstring": doc or "",
                })
                if doc:
                    tags["docstring"].append({
                        "text": doc,
                        "start_line": node.lineno,
                        "end_line": node.lineno,
                    })
                self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                doc = ast.get_docstring(node)
                tags["function"].append({
                    "text": node.name,
                    "start_line": node.lineno,
                    "end_line": getattr(node, "end_lineno", node.lineno),
                    "docstring": doc or "",
                })
                self.generic_visit(node)

            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                doc = ast.get_docstring(node)
                supers = [ast.unparse(b) for b in node.bases]
                tags["class"].append({
                    "text": node.name,
                    "start_line": node.lineno,
                    "end_line": getattr(node, "end_lineno", node.lineno),
                    "super_classes": supers,
                    "docstring": doc or "",
                })
                self.generic_visit(node)

            def visit_Import(self, node: ast.Import) -> None:
                for alias in node.names:
                    tags["import.module"].append({
                        "text": alias.name,
                        "start_line": node.lineno,
                        "end_line": node.lineno,
                    })

            def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
                mod = node.module or ""
                for alias in node.names:
                    if alias.name == "*":
                        tags["export.wildcard"].append({
                            "text": mod,
                            "start_line": node.lineno,
                            "end_line": node.lineno,
                        })
                    else:
                        tags["import.symbol"].append({
                            "text": f"{mod}.{alias.name}" if mod else alias.name,
                            "start_line": node.lineno,
                            "end_line": node.lineno,
                        })

            def visit_Call(self, node: ast.Call) -> None:
                if isinstance(node.func, ast.Name):
                    tags["call.function"].append({
                        "text": node.func.id,
                        "start_line": node.lineno,
                        "end_line": node.lineno,
                    })
                elif isinstance(node.func, ast.Attribute):
                    tags["call.method"].append({
                        "text": node.func.attr,
                        "start_line": node.lineno,
                        "end_line": node.lineno,
                    })
                self.generic_visit(node)

        visitor = PythonASTVisitor()
        visitor.visit(tree)

    def _parse_lexical(self, code: str, lang: str, tags: Dict[str, List[Dict[str, Any]]]) -> None:
        lines = code.splitlines()
        for idx, line in enumerate(lines, 1):
            sline = line.strip()
            # Regex for function signatures
            fn_match = re.search(r'\b(def|function|fn|func)\s+([A-Za-z_][A-Za-z0-9_]*)', sline)
            if fn_match:
                tags["function"].append({
                    "text": fn_match.group(2),
                    "start_line": idx,
                    "end_line": idx,
                })

            # Regex for class/struct/interface
            class_match = re.search(r'\b(class|interface|struct|trait|type)\s+([A-Za-z_][A-Za-z0-9_]*)', sline)
            if class_match:
                tags["class"].append({
                    "text": class_match.group(2),
                    "start_line": idx,
                    "end_line": idx,
                })

            # Regex for imports
            imp_match = re.search(r'\b(import|require|use)\s+[\'"]?([A-Za-z0-9_\./\:-]+)', sline)
            if imp_match:
                tags["import.module"].append({
                    "text": imp_match.group(2),
                    "start_line": idx,
                    "end_line": idx,
                })

            # Wildcard export / import *
            if "*" in sline and ("export" in sline or "import" in sline or "use" in sline):
                tags["export.wildcard"].append({
                    "text": sline,
                    "start_line": idx,
                    "end_line": idx,
                })

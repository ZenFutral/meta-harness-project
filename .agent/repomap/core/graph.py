import math
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any

from .tag_extractor import TagExtractor
from .storage import get_storage


class TwoTierGraph:
    """Two-Tier Hierarchical Graph (Macro File Graph & Micro Symbol Graph).

    - Macro Graph: Directed file-to-file graph with IDF edge penalties.
    - Micro Graph: Directed symbol-to-symbol graph linked via explicit import bindings.
    - Tarjan SCC: Detects circular dependencies and condenses macro cycles.
    - Barrel Unfolding: Resolves transitive re-exports up to 16 hops.
    """

    def __init__(self, repo_root: Optional[Path] = None):
        self.repo_root = (repo_root or Path.cwd()).resolve()
        self.macro_graph: Dict[str, Dict[str, float]] = {}  # src_file -> target_file -> weight
        self.micro_graph: Dict[str, Dict[str, float]] = {}  # src_symbol -> target_symbol -> weight
        self.file_symbols: Dict[str, List[Dict[str, Any]]] = {}  # rel_file -> list of tags
        self.storage = get_storage()

    def build_from_repository(self) -> None:
        extractor = TagExtractor(self.repo_root)
        all_tags = extractor.extract_from_directory(self.repo_root)

        # 1. Group symbols by file and register macro nodes
        for tag in all_tags:
            f = tag["file"]
            if f not in self.macro_graph:
                self.macro_graph[f] = {}
            if f not in self.file_symbols:
                self.file_symbols[f] = []
            self.file_symbols[f].append(tag)

            sym_id = tag["symbol_id"]
            if sym_id not in self.micro_graph:
                self.micro_graph[sym_id] = {}

        # 2. Build Macro and Micro edges from import tags
        for f, tags in self.file_symbols.items():
            for tag in tags:
                tag_type = tag["type"]
                target = tag["name"]

                if tag_type in {"import.module", "export.wildcard"}:
                    # Find potential matching target file
                    for candidate_file in self.macro_graph:
                        if candidate_file != f and (target in candidate_file or candidate_file.startswith(target)):
                            self.macro_graph[f][candidate_file] = 1.0

                elif tag_type == "import.symbol":
                    # Restrict micro edge strictly to explicitly imported symbols
                    for cand_file, cand_tags in self.file_symbols.items():
                        if cand_file == f:
                            continue
                        for cand_tag in cand_tags:
                            if cand_tag["name"] == target or cand_tag["name"].endswith(f".{target}"):
                                self.macro_graph[f][cand_file] = 1.0
                                src_sym = tag["symbol_id"]
                                tgt_sym = cand_tag["symbol_id"]
                                self.micro_graph[src_sym][tgt_sym] = 1.0

        # 3. Apply IDF edge penalties: weight(u, v) = 1.0 / log(1 + fanout(u))
        for u in list(self.macro_graph.keys()):
            fanout = len(self.macro_graph[u])
            if fanout > 0:
                idf_weight = 1.0 / math.log(1 + fanout)
                for v in self.macro_graph[u]:
                    self.macro_graph[u][v] = idf_weight

        for u in list(self.micro_graph.keys()):
            fanout = len(self.micro_graph[u])
            if fanout > 0:
                idf_weight = 1.0 / math.log(1 + fanout)
                for v in self.micro_graph[u]:
                    self.micro_graph[u][v] = idf_weight

    def find_cycles(self) -> List[List[str]]:
        """Tarjan's Strongly Connected Components (SCC) algorithm on Macro Graph."""
        index = 0
        indices: Dict[str, int] = {}
        lowlink: Dict[str, int] = {}
        stack: List[str] = []
        on_stack: Set[str] = set()
        sccs: List[List[str]] = []

        def strongconnect(node: str) -> None:
            nonlocal index
            indices[node] = index
            lowlink[node] = index
            index += 1
            stack.append(node)
            on_stack.add(node)

            for neighbor in self.macro_graph.get(node, {}):
                if neighbor not in indices:
                    strongconnect(neighbor)
                    lowlink[node] = min(lowlink[node], lowlink[neighbor])
                elif neighbor in on_stack:
                    lowlink[node] = min(lowlink[node], indices[neighbor])

            if lowlink[node] == indices[node]:
                scc: List[str] = []
                while True:
                    w = stack.pop()
                    on_stack.remove(w)
                    scc.append(w)
                    if w == node:
                        break
                if len(scc) > 1 or (len(scc) == 1 and node in self.macro_graph.get(node, {})):
                    sccs.append(scc)

        for node in list(self.macro_graph.keys()):
            if node not in indices:
                strongconnect(node)

        return sccs

    def condense_cycles(self) -> Dict[str, Dict[str, float]]:
        """Condense SCC cycles into macro meta-nodes while preserving intra-cycle micro edges."""
        sccs = self.find_cycles()
        node_to_meta: Dict[str, str] = {}
        for idx, scc in enumerate(sccs):
            meta_name = f"SCC_META_{idx}"
            for f in scc:
                node_to_meta[f] = meta_name

        condensed: Dict[str, Dict[str, float]] = {}
        for u, neighbors in self.macro_graph.items():
            src_node = node_to_meta.get(u, u)
            if src_node not in condensed:
                condensed[src_node] = {}
            for v, w in neighbors.items():
                tgt_node = node_to_meta.get(v, v)
                if src_node != tgt_node:
                    condensed[src_node][tgt_node] = max(condensed[src_node].get(tgt_node, 0.0), w)

        return condensed

    def resolve_imports(self, source_file: str, target_file: str, max_depth: int = 16) -> List[List[str]]:
        """Find circular or transitive import paths between source_file and target_file up to max_depth."""
        paths: List[List[str]] = []

        def dfs(current: str, target: str, visited: List[str], depth: int) -> None:
            if depth > max_depth:
                return
            if current == target and len(visited) > 1:
                paths.append(list(visited))
                return

            for neighbor in self.macro_graph.get(current, {}):
                if neighbor not in visited or (neighbor == target and len(visited) > 1):
                    visited.append(neighbor)
                    dfs(neighbor, target, visited, depth + 1)
                    visited.pop()

        dfs(source_file, target_file, [source_file], 0)
        return paths

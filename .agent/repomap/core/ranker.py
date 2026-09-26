import math
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from .graph import TwoTierGraph

KIND_WEIGHTS = {
    "class": 2.5,
    "function": 2.0,
    "import.module": 1.0,
    "import.symbol": 1.0,
    "export.wildcard": 1.0,
}

ENTRYPOINT_NAMES = {
    "main.py", "app.py", "index.py", "server.py",
    "main.ts", "index.ts", "app.ts", "server.ts",
    "main.go", "main.rs", "cli.py"
}


class CentralityRanker:
    """Multi-Factor Centrality Ranking & Personalized PageRank.

    1. Computes Personalized PageRank (PPR) over macro file graph (alpha = 0.85).
    2. Personalizes vector p on focus_files if provided, or uniform for cold indexing.
    3. Boosts entry points (1.5x - 2.0x).
    4. Projects file rank to symbols:
       Score(s) = PPR(file(s)) * (weight_kind(s) + in_degree(s)) / (1 + fanout(s))
    """

    def __init__(self, graph: TwoTierGraph, alpha: float = 0.85, max_iter: int = 100, tol: float = 1e-6):
        self.graph = graph
        self.alpha = alpha
        self.max_iter = max_iter
        self.tol = tol

    def compute_file_pagerank(self, focus_files: Optional[List[str]] = None) -> Dict[str, float]:
        macro = self.graph.macro_graph
        nodes = list(macro.keys())
        n = len(nodes)
        if n == 0:
            return {}

        # Personalization vector p
        p: Dict[str, float] = {}
        if focus_files:
            valid_focus = [f for f in focus_files if f in nodes]
            if valid_focus:
                p_val = 1.0 / len(valid_focus)
                for node in nodes:
                    p[node] = p_val if node in valid_focus else 0.0
            else:
                p_val = 1.0 / n
                for node in nodes:
                    p[node] = p_val
        else:
            p_val = 1.0 / n
            for node in nodes:
                p[node] = p_val

        # Initial rank distribution
        rank: Dict[str, float] = {node: 1.0 / n for node in nodes}

        # Power iteration
        for _ in range(self.max_iter):
            next_rank: Dict[str, float] = {node: (1.0 - self.alpha) * p[node] for node in nodes}

            dangling_sum = sum(rank[u] for u in nodes if len(macro[u]) == 0)
            dangling_contribution = self.alpha * dangling_sum / n

            for u in nodes:
                neighbors = macro[u]
                fanout = len(neighbors)
                if fanout > 0:
                    share = self.alpha * rank[u] / fanout
                    for v in neighbors:
                        if v in next_rank:
                            next_rank[v] += share

            for node in nodes:
                next_rank[node] += dangling_contribution * (p[node] * n)

            # Check convergence
            diff = sum(abs(next_rank[node] - rank[node]) for node in nodes)
            rank = next_rank
            if diff < self.tol:
                break

        # Entry point boosting (1.5x - 2.0x)
        for node in nodes:
            filename = Path(node).name.lower()
            if filename in ENTRYPOINT_NAMES or filename.startswith("main") or filename.startswith("app"):
                rank[node] *= 1.8

        return rank

    def rank_symbols(self, focus_files: Optional[List[str]] = None) -> List[Dict[str, float]]:
        file_ppr = self.compute_file_pagerank(focus_files)
        symbol_scores: List[Dict[str, Any]] = []

        for f, tags in self.graph.file_symbols.items():
            ppr_f = file_ppr.get(f, 0.0)
            for tag in tags:
                sym_id = tag["symbol_id"]
                kind = tag["type"]
                weight_kind = KIND_WEIGHTS.get(kind, 1.0)

                micro_edges = self.graph.micro_graph.get(sym_id, {})
                fanout = len(micro_edges)

                # In-degree computation
                in_degree = sum(1 for src, tgts in self.graph.micro_graph.items() if sym_id in tgts)

                score = ppr_f * (weight_kind + in_degree) / (1.0 + fanout)
                symbol_scores.append({
                    "symbol_id": sym_id,
                    "name": tag["name"],
                    "file": f,
                    "kind": kind,
                    "score": score,
                    "location": tag["location"],
                    "visibility": tag.get("visibility", "public"),
                })

        # Sort descending by score
        symbol_scores.sort(key=lambda x: x["score"], reverse=True)
        return symbol_scores

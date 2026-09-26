from pathlib import Path
from typing import Dict, List, Set, Any, Optional

from ..core.graph import TwoTierGraph


class BlastRadiusTracer:
    """Directed Blast Radius & Impact Analysis.

    Traverses symbol and file graphs to determine downstream callees/references
    and upstream callers/dependents. Terminated when depth > max_depth or fanout > max_fanout.
    """

    def __init__(self, graph: Optional[TwoTierGraph] = None):
        self.graph = graph or TwoTierGraph()

    def trace_blast_radius(
        self,
        symbol_name: str,
        direction: str = "both",
        max_depth: int = 3,
        max_fanout: int = 10,
    ) -> Dict[str, Any]:
        """Trace symbol dependencies up to max_depth and max_fanout."""
        upstream_impact: List[Dict[str, Any]] = []
        downstream_impact: List[Dict[str, Any]] = []

        visited_nodes: Set[str] = set()

        # Find matching symbol IDs in graph
        matching_symbols = [
            sym_id for sym_id in self.graph.micro_graph
            if symbol_name in sym_id
        ]

        if not matching_symbols:
            matching_symbols = [symbol_name]

        def dfs(node: str, current_depth: int, is_upstream: bool) -> None:
            if current_depth >= max_depth or node in visited_nodes:
                return
            visited_nodes.add(node)

            if is_upstream:
                # Find callers (incoming edges)
                incoming = [
                    src for src, tgts in self.graph.micro_graph.items()
                    if node in tgts
                ]
                for idx, src in enumerate(incoming):
                    if idx >= max_fanout:
                        break
                    upstream_impact.append({
                        "symbol_id": src,
                        "depth": current_depth + 1,
                        "relationship": "caller",
                    })
                    dfs(src, current_depth + 1, is_upstream=True)
            else:
                # Find callees (outgoing edges)
                outgoing = self.graph.micro_graph.get(node, {})
                for idx, tgt in enumerate(outgoing.keys()):
                    if idx >= max_fanout:
                        break
                    downstream_impact.append({
                        "symbol_id": tgt,
                        "depth": current_depth + 1,
                        "relationship": "callee",
                    })
                    dfs(tgt, current_depth + 1, is_upstream=False)

        for sym in matching_symbols:
            if direction in {"upstream", "both"}:
                visited_nodes.clear()
                dfs(sym, 0, is_upstream=True)
            if direction in {"downstream", "both"}:
                visited_nodes.clear()
                dfs(sym, 0, is_upstream=False)

        risk_score = min(10.0, (len(upstream_impact) * 1.5) + (len(downstream_impact) * 1.0))

        return {
            "target_symbol": symbol_name,
            "direction": direction,
            "max_depth": max_depth,
            "risk_score": risk_score,
            "upstream": upstream_impact,
            "downstream": downstream_impact,
        }


def trace_blast_radius(
    symbol_name: str,
    direction: str = "both",
    max_depth: int = 3,
    max_fanout: int = 10,
    graph: Optional[TwoTierGraph] = None,
) -> Dict[str, Any]:
    tracer = BlastRadiusTracer(graph)
    return tracer.trace_blast_radius(symbol_name, direction, max_depth, max_fanout)

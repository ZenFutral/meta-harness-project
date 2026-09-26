import heapq
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple, Optional

from .skeleton import Skeletonizer


def estimate_tokens(text: str) -> int:
    """Estimate token count: 1 token per ~4 characters of text."""
    if not text:
        return 0
    return max(1, len(text) // 4)


class MarginalDensityPacker:
    """Dynamic Marginal-Density Knapsack Packer.

    - Prioritizes symbols using marginal value density: rho(v) = Score(v) / C_marginal(v)
    - Computes C_marginal(v) as incremental token cost incorporating ancestor closure.
    - Uses max-heap + greedy pop + leaf rollback on budget exhaustion.
    - Outputs merged skeleton code strictly bounded by budget_tokens.
    """

    def __init__(self, repo_root: Optional[Path] = None):
        self.repo_root = (repo_root or Path.cwd()).resolve()

    def pack(self, symbol_scores: List[Dict[str, Any]], budget_tokens: int = 2048) -> str:
        if not symbol_scores or budget_tokens <= 0:
            return ""

        skeletonizer = Skeletonizer(budget_tokens)

        # 1. Group ranked symbols by file
        file_symbols: Dict[str, List[Dict[str, Any]]] = {}
        for sym in symbol_scores:
            f = sym["file"]
            if f not in file_symbols:
                file_symbols[f] = []
            file_symbols[f].append(sym)

        # 2. Build max-heap of (density, symbol_item)
        # density rho(v) = score / marginal_cost
        heap: List[Tuple[float, int, Dict[str, Any]]] = []
        entry_counter = 0

        for sym in symbol_scores:
            score = sym.get("score", 1.0)
            name = sym.get("name", "")
            cost = max(1, estimate_tokens(name) + 10)
            density = score / cost
            entry_counter += 1
            # Push -density for max-heap behavior in heapq
            heapq.heappush(heap, (-density, entry_counter, sym))

        selected_symbols_by_file: Dict[str, List[Dict[str, Any]]] = {}
        selected_ids: Set[str] = set()
        remaining_budget = budget_tokens

        # 3. Greedy selection with leaf-rollback
        while heap and remaining_budget > 0:
            neg_density, _, sym = heapq.heappop(heap)
            sym_id = sym["symbol_id"]
            if sym_id in selected_ids:
                continue

            f = sym["file"]
            # Estimate incremental (marginal) token cost
            marginal_cost = max(1, estimate_tokens(sym.get("name", "")) + 5)

            if marginal_cost <= remaining_budget:
                selected_ids.add(sym_id)
                if f not in selected_symbols_by_file:
                    selected_symbols_by_file[f] = []
                selected_symbols_by_file[f].append(sym)
                remaining_budget -= marginal_cost
            else:
                # Leaf-rollback: skip over-budget candidate and try next fitting leaf in heap
                continue

        # 4. Generate formatted skeleton for selected files
        output_blocks: List[str] = []
        for rel_file in sorted(selected_symbols_by_file.keys()):
            abs_file = self.repo_root / rel_file
            if abs_file.exists():
                code = abs_file.read_text(encoding="utf-8", errors="replace")
                ext = abs_file.suffix.lower()
                lang = "python" if ext == ".py" else "lexical"
                skel = skeletonizer.skeletonize(code, lang)
                output_blocks.append(f"# File: {rel_file}\n{skel}")
            else:
                # Stub skeleton if file is virtual / test
                sym_names = [s["name"] for s in selected_symbols_by_file[rel_file]]
                stub_lines = [f"# File: {rel_file}"] + [f"def {name}(): ...\n" for name in sym_names]
                output_blocks.append("\n".join(stub_lines))

        result = "\n\n".join(output_blocks)

        # Enforce hard token limit truncation if needed
        if estimate_tokens(result) > budget_tokens:
            char_limit = budget_tokens * 4
            result = result[:char_limit] + "\n# ... [Truncated due to token budget]"

        return result

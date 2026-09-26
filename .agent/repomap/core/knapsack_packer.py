import heapq
from pathlib import Path
from typing import List, Tuple, Dict, Any

# ---------------------------------------------------------------------------
# Marginal‑Density Knapsack Packer (Phase 4.2)
# ---------------------------------------------------------------------------
# The packer selects a subset of candidate files such that the total token
# count does not exceed ``max_tokens`` while maximising the summed ``priority``.
# We employ a greedy algorithm based on *value‑per‑token* density, which is
# sufficient for the "marginal‑density" heuristic described in the roadmap.
# ---------------------------------------------------------------------------

Item = Tuple[Path, int, float]  # (file_path, token_count, priority)

class MarginalDensityKnapsack:
    """Select files for inclusion in the context window.

    Parameters
    ----------
    candidates:
        Iterable of ``(Path, token_count, priority)`` tuples.
    max_tokens:
        Upper bound on the total token budget for the selected set.

    The algorithm sorts items by ``priority / token_count`` (density) in
    descending order and greedily picks items while the budget permits.
    """

    def __init__(self, candidates: List[Item], max_tokens: int):
        self.candidates = candidates
        self.max_tokens = max_tokens

    def pack(self) -> List[Item]:
        """Return the list of selected items.

        The returned list preserves the original order of selection (high‑
        density first).  Items that would exceed the remaining budget are skipped.
        """
        # Compute density and build a max‑heap (negative density for heapq).
        heap: List[Tuple[float, Item]] = []
        for item in self.candidates:
            path, token_cnt, priority = item
            if token_cnt <= 0:
                continue  # ignore empty/invalid entries
            density = priority / token_cnt
            heapq.heappush(heap, (-density, item))

        selected: List[Item] = []
        remaining = self.max_tokens
        while heap and remaining > 0:
            _, (path, token_cnt, priority) = heapq.heappop(heap)
            if token_cnt <= remaining:
                selected.append((path, token_cnt, priority))
                remaining -= token_cnt
        return selected

    @staticmethod
    def from_file_metadata(file_meta: List[Dict[str, Any]], max_tokens: int) -> "MarginalDensityKnapsack":
        """Convenience constructor.

        ``file_meta`` is expected to be a list of dictionaries with keys:
        ``"path"`` (str or Path), ``"tokens"`` (int), and ``"priority"`` (float).
        """
        items: List[Item] = []
        for meta in file_meta:
            path = Path(meta["path"]).resolve()
            token_cnt = int(meta.get("tokens", 0))
            priority = float(meta.get("priority", 1.0))
            items.append((path, token_cnt, priority))
        return MarginalDensityKnapsack(items, max_tokens)

# ---------------------------------------------------------------------------
# Helper for token estimation (used elsewhere in the repo)
# ---------------------------------------------------------------------------
def estimate_tokens_for_path(path: Path) -> int:
    """Very rough token estimate: 1 token per 5 characters of file size.

    This mirrors the heuristic used in the pipeline implementation.  The
    function is public so other modules (e.g., the executor) can reuse the
    calculation without duplication.
    """
    try:
        size = path.stat().st_size
        return max(1, size // 5)
    except Exception:
        return 1

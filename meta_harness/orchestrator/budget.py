from __future__ import annotations

import dataclasses
import logging
import json
import time
from pathlib import Path

try:
    from .config import COST_PER_1K, BUDGET
except ImportError:
    try:
        from meta_harness.orchestrator.config import COST_PER_1K, BUDGET
    except ImportError:
        from config import COST_PER_1K, BUDGET

log = logging.getLogger(__name__)


class BudgetExceeded(RuntimeError):
    """Raised when a hard-stop budget limit is breached."""


@dataclasses.dataclass
class CallRecord:
    tier: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


class BudgetTracker:
    def __init__(self) -> None:
        self._session_records: list[CallRecord] = []
        self._task_records: list[CallRecord] = []   # reset per task

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------
    def record(self, tier: str, input_tokens: int, output_tokens: int) -> float:
        """Record a single API call and return its cost in USD."""
        rates = COST_PER_1K[tier]
        cost = (input_tokens / 1_000 * rates["input"]) + (output_tokens / 1_000 * rates["output"])
        rec = CallRecord(tier=tier, input_tokens=input_tokens, output_tokens=output_tokens, cost_usd=cost)
        self._session_records.append(rec)
        self._task_records.append(rec)
        log.debug("Recorded call: tier=%s in=%d out=%d cost=$%.6f", tier, input_tokens, output_tokens, cost)
        return cost

    def reset_task(self) -> None:
        """Call at the start of each new task to reset per-task accounting."""
        self._task_records = []

    # ------------------------------------------------------------------
    # Guard checks (raise BudgetExceeded on violation)
    # ------------------------------------------------------------------
    def check_session(self) -> None:
        total = self.session_cost
        if total >= BUDGET["session_hard_stop_usd"]:
            raise BudgetExceeded(
                f"Session hard-stop reached: ${total:.4f} >= ${BUDGET['session_hard_stop_usd']:.2f}"
            )
        if total >= BUDGET["session_warn_usd"]:
            log.warning("Budget warning: session spend $%.4f / $%.2f", total, BUDGET["session_hard_stop_usd"])

    def check_task(self) -> None:
        total = self.task_cost
        if total >= BUDGET["task_hard_stop_usd"]:
            raise BudgetExceeded(
                f"Per-task hard-stop reached: ${total:.4f} >= ${BUDGET['task_hard_stop_usd']:.2f}"
            )

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    @property
    def session_cost(self) -> float:
        return sum(r.cost_usd for r in self._session_records)

    @property
    def task_cost(self) -> float:
        return sum(r.cost_usd for r in self._task_records)

    @property
    def session_tokens(self) -> dict[str, int]:
        return {
            "input":  sum(r.input_tokens  for r in self._session_records),
            "output": sum(r.output_tokens for r in self._session_records),
        }

    def summary(self) -> str:
        toks = self.session_tokens
        lines = [
            "=== Budget Summary ===",
            f"  Session cost : ${self.session_cost:.6f}",
            f"  Input tokens : {toks['input']:,}",
            f"  Output tokens: {toks['output']:,}",
            f"  Calls        : {len(self._session_records)}",
        ]
        # Per-tier breakdown
        tiers: dict[str, dict] = {}
        for r in self._session_records:
            t = tiers.setdefault(r.tier, {"calls": 0, "cost": 0.0})
            t["calls"] += 1
            t["cost"]  += r.cost_usd
        for tier, data in tiers.items():
            lines.append(f"  [{tier}] calls={data['calls']} cost=${data['cost']:.6f}")
        return "\n".join(lines)

# ---------------------------------------------------------------------------
# Daily quota‑tracking circuit‑breaker (Phase 1 – 1.3)
# ---------------------------------------------------------------------------
QUOTA_FILE = Path(__file__).resolve().parents[2] / ".agent" / "cache" / "quota.json"
DAILY_COST_CAP = 0.33  # USD – $0.33 per day as specified in the plan
INPUT_COST_PER_M = 0.075  # Gemini‑2.0 Flash input cost ($/1M tokens)

def get_quota_file_path() -> Path:
    return QUOTA_FILE

def check_and_update_budget(input_tokens: int = 0) -> bool:
    """Update the daily quota file and enforce the $0.33/day hard cap.

    Returns ``True`` if the projected cost is still under the cap, otherwise
    ``False`` (caller should fall back to a local or HF endpoint).
    """
    today = time.strftime("%Y-%m-%d")
    if QUOTA_FILE.exists():
        try:
            state = json.loads(QUOTA_FILE.read_text())
        except Exception:
            state = {"date": today, "tokens": 0, "cost": 0.0}
    else:
        state = {"date": today, "tokens": 0, "cost": 0.0}

    if state.get("date") != today:
        state = {"date": today, "tokens": 0, "cost": 0.0}

    projected_cost = state["cost"] + (input_tokens / 1_000_000) * INPUT_COST_PER_M
    if projected_cost >= DAILY_COST_CAP:
        return False

    state["tokens"] = state.get("tokens", 0) + input_tokens
    state["cost"] = projected_cost
    QUOTA_FILE.parent.mkdir(parents=True, exist_ok=True)
    QUOTA_FILE.write_text(json.dumps(state, indent=2))
    return True

def get_quota_state() -> dict:
    """Return the current quota state (for diagnostics)."""
    if not QUOTA_FILE.exists():
        return {"date": "", "tokens": 0, "cost": 0.0}
    try:
        return json.loads(QUOTA_FILE.read_text())
    except Exception:
        return {"date": "", "tokens": 0, "cost": 0.0}

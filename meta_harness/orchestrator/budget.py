from __future__ import annotations

import dataclasses
import logging
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

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
        rates = COST_PER_1K.get(tier, {"input": 0.000075, "output": 0.0003})
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
# Daily quota‑tracking & multi-model concurrent circuit‑breaker
# ---------------------------------------------------------------------------
QUOTA_FILE = Path(__file__).resolve().parents[2] / ".agent" / "cache" / "quota.json"
DAILY_COST_CAP = 0.33  # Base USD per model/tier daily cap
INPUT_COST_PER_M = 0.075  # Gemini‑2.0 Flash input cost ($/1M tokens)

# In-memory sliding rate limit tracker: {qualified_model: [timestamp_1, timestamp_2, ...]}
_RATE_LIMIT_TIMESTAMPS: Dict[str, List[float]] = {}


def get_quota_file_path() -> Path:
    return QUOTA_FILE


def calculate_concurrent_daily_ceiling(active_models: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Computes aggregated concurrent daily ceilings across active models and vendors.
    Sums daily token quotas and calculates combined daily cost ceilings.
    """
    try:
        from router.vendor_config import get_all_active_models, load_user_config, get_model_spec
    except ImportError:
        try:
            from meta_harness.router.vendor_config import get_all_active_models, load_user_config, get_model_spec
        except ImportError:
            return {
                "aggregate_daily_quota": 2000,
                "aggregate_daily_cost_cap": DAILY_COST_CAP,
                "model_ceilings": {},
                "active_count": 1
            }

    if active_models is not None:
        models_data = []
        for m in active_models:
            v = m.split("/")[0] if "/" in m else "default"
            m_id = m.split("/")[1] if "/" in m else m
            models_data.append({
                "vendor": v,
                "model": m_id,
                "qualified": m,
                "spec": get_model_spec(v, m_id)
            })
    else:
        models_data = get_all_active_models()

    total_tokens_quota = 0
    unique_vendors = set()
    model_ceilings = {}

    for item in models_data:
        spec = item.get("spec", {})
        q_name = item.get("qualified", item.get("model", "unknown"))
        vendor = item.get("vendor", "default")
        unique_vendors.add(vendor)

        m_quota = int(spec.get("daily_quota", 1000))
        total_tokens_quota += m_quota
        model_ceilings[q_name] = {
            "daily_quota": m_quota,
            "rate_limit": int(spec.get("rate_limit", 100)),
            "max_output_tokens": int(spec.get("max_output_tokens", 64000)),
            "max_thinking_tokens": int(spec.get("max_thinking_tokens", 8000)),
            "vendor": vendor
        }

    # Aggregate daily cost ceiling accounts for concurrent providers (scaling by active vendor count)
    active_vendor_count = max(1, len(unique_vendors))
    aggregate_cost_cap = round(DAILY_COST_CAP * active_vendor_count, 4)

    return {
        "aggregate_daily_quota": total_tokens_quota if total_tokens_quota > 0 else 2000,
        "aggregate_daily_cost_cap": aggregate_cost_cap,
        "model_ceilings": model_ceilings,
        "active_count": len(models_data)
    }


def check_rate_limit(model_id: str, max_requests_per_minute: int = 100) -> bool:
    """
    Sliding window rate limit checker (requests per 60 seconds).
    Returns True if allowed, False if rate limited.
    """
    now = time.time()
    timestamps = _RATE_LIMIT_TIMESTAMPS.setdefault(model_id, [])
    # Prune timestamps older than 60s
    _RATE_LIMIT_TIMESTAMPS[model_id] = [t for t in timestamps if now - t < 60.0]
    if len(_RATE_LIMIT_TIMESTAMPS[model_id]) >= max_requests_per_minute:
        return False
    _RATE_LIMIT_TIMESTAMPS[model_id].append(now)
    return True


def check_and_update_budget(
    *args,
    input_tokens: int = 0,
    output_tokens: int = 0,
    model: Optional[str] = None,
    vendor: Optional[str] = None,
    **kwargs
) -> bool:
    """
    Update daily quota tracking and enforce per-model and concurrent daily ceilings.
    
    Supports:
      - check_and_update_budget(100)
      - check_and_update_budget(input_tokens=100)
      - check_and_update_budget("orchestrator", 50, 50)
      - check_and_update_budget(input_tokens=100, model="antigravity/gemini-3-pro-preview")
    """
    # Parse flexible positional arguments
    if args:
        if isinstance(args[0], (int, float)):
            input_tokens = int(args[0])
        elif isinstance(args[0], str):
            if not model:
                model = args[0]
            if len(args) > 1 and isinstance(args[1], (int, float)):
                input_tokens = int(args[1])
            if len(args) > 2 and isinstance(args[2], (int, float)):
                output_tokens = int(args[2])

    # Resolve active model if not specified
    if not model:
        try:
            from router.vendor_config import get_active_backend
            model = get_active_backend()
        except Exception:
            model = "default/gemini-2.0-flash"

    # Identify qualified model name and vendor
    if "/" in model:
        v_name, m_name = model.split("/", 1)
    else:
        v_name = vendor or "default"
        m_name = model
    qualified_model = f"{v_name}/{m_name}" if v_name != "default" else m_name

    # Calculate concurrent daily ceilings
    ceiling_info = calculate_concurrent_daily_ceiling()
    daily_cost_cap = ceiling_info.get("aggregate_daily_cost_cap", DAILY_COST_CAP)
    model_spec = ceiling_info.get("model_ceilings", {}).get(qualified_model, {})
    model_daily_quota = model_spec.get("daily_quota", 1000)
    model_rate_limit = model_spec.get("rate_limit", 100)

    # Rate limit check
    if not check_rate_limit(qualified_model, model_rate_limit):
        log.warning("Rate limit exceeded for model %s (%d req/min cap)", qualified_model, model_rate_limit)
        return False

    today = time.strftime("%Y-%m-%d")
    state: Dict[str, Any] = {"date": today, "tokens": 0, "cost": 0.0, "models": {}}

    if QUOTA_FILE.exists():
        try:
            loaded = json.loads(QUOTA_FILE.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                state = loaded
        except Exception:
            state = {"date": today, "tokens": 0, "cost": 0.0, "models": {}}

    # Handle day rollover: reset counters when date changes
    if state.get("date") != today:
        state = {"date": today, "tokens": 0, "cost": 0.0, "models": {}}

    if "models" not in state or not isinstance(state["models"], dict):
        state["models"] = {}

    m_state = state["models"].setdefault(qualified_model, {
        "tokens": 0,
        "calls": 0,
        "cost": 0.0,
        "tripped": False
    })

    projected_cost = float(state.get("cost", 0.0)) + (input_tokens / 1_000_000) * INPUT_COST_PER_M
    projected_model_tokens = int(m_state.get("tokens", 0)) + input_tokens + output_tokens

    # Hard-stop circuit breaker: check base cap ($0.33), aggregate cap, and model token quota
    cost_tripped = (projected_cost >= DAILY_COST_CAP) or (projected_cost >= daily_cost_cap)
    model_quota_tripped = (model_daily_quota > 0) and (projected_model_tokens > model_daily_quota * 1000)

    if cost_tripped or model_quota_tripped:
        m_state["tripped"] = True
        state["circuit_breaker_tripped"] = True
        QUOTA_FILE.parent.mkdir(parents=True, exist_ok=True)
        QUOTA_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
        return False

    # Update state
    state["tokens"] = int(state.get("tokens", 0)) + input_tokens + output_tokens
    state["cost"] = round(projected_cost, 6)
    state["daily_cap"] = daily_cost_cap
    state["aggregate_quota"] = ceiling_info.get("aggregate_daily_quota", 2000)
    state["circuit_breaker_tripped"] = False

    m_state["tokens"] = projected_model_tokens
    m_state["calls"] = int(m_state.get("calls", 0)) + 1
    m_state["cost"] = round(float(m_state.get("cost", 0.0)) + (input_tokens / 1_000_000) * INPUT_COST_PER_M, 6)
    m_state["daily_quota"] = model_daily_quota
    m_state["rate_limit"] = model_rate_limit
    m_state["tripped"] = False

    QUOTA_FILE.parent.mkdir(parents=True, exist_ok=True)
    QUOTA_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return True


def get_quota_state() -> dict:
    """Return the current quota state including per-model breakdown (for diagnostics)."""
    if not QUOTA_FILE.exists():
        today = time.strftime("%Y-%m-%d")
        ceiling = calculate_concurrent_daily_ceiling()
        return {
            "date": today,
            "tokens": 0,
            "cost": 0.0,
            "daily_cap": ceiling.get("aggregate_daily_cost_cap", DAILY_COST_CAP),
            "aggregate_quota": ceiling.get("aggregate_daily_quota", 2000),
            "models": {}
        }
    try:
        data = json.loads(QUOTA_FILE.read_text(encoding="utf-8"))
        if "daily_cap" not in data:
            ceiling = calculate_concurrent_daily_ceiling()
            data["daily_cap"] = ceiling.get("aggregate_daily_cost_cap", DAILY_COST_CAP)
        return data
    except Exception:
        return {"date": "", "tokens": 0, "cost": 0.0, "models": {}}


def get_model_quota_status(model_id: str) -> dict:
    """Returns quota usage and ceiling metrics for a designated model."""
    state = get_quota_state()
    models = state.get("models", {})
    if model_id in models:
        return dict(models[model_id])
    # Search by partial match (e.g. "gemini-3-pro-preview")
    for k, v in models.items():
        if k.endswith(f"/{model_id}") or k == model_id:
            return dict(v)
    ceiling = calculate_concurrent_daily_ceiling()
    spec = ceiling.get("model_ceilings", {}).get(model_id, {})
    return {
        "tokens": 0,
        "calls": 0,
        "cost": 0.0,
        "daily_quota": spec.get("daily_quota", 1000),
        "rate_limit": spec.get("rate_limit", 100),
        "tripped": False
    }


def reset_quota_state() -> None:
    """Resets the quota file for today."""
    today = time.strftime("%Y-%m-%d")
    ceiling = calculate_concurrent_daily_ceiling()
    state = {
        "date": today,
        "tokens": 0,
        "cost": 0.0,
        "daily_cap": ceiling.get("aggregate_daily_cost_cap", DAILY_COST_CAP),
        "aggregate_quota": ceiling.get("aggregate_daily_quota", 2000),
        "models": {}
    }
    QUOTA_FILE.parent.mkdir(parents=True, exist_ok=True)
    QUOTA_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")

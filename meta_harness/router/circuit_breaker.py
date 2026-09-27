import os
import json
import threading
import time
from datetime import datetime
from pathlib import Path
from collections import deque
from typing import Dict, Any

# Path to quota cache file
_QUOTA_PATH = Path(__file__).resolve().parents[3] / ".agent" / "cache" / "quota.json"
_QUOTA_PATH.parent.mkdir(parents=True, exist_ok=True)

_QUOTA_LOCK = threading.Lock()

def _load_quota() -> Dict[str, Any]:
    """Load quota data from JSON file, returning defaults if missing or corrupted."""
    with _QUOTA_LOCK:
        if not _QUOTA_PATH.is_file():
            return {
                "vertex_month_spend": 0.0,
                "vertex_budget_ceiling": 9.5,
                "last_updated_timestamp": 0,
                "antigravity_swarm_rpm": 0,
                "antigravity_warning_active": False,
            }
        try:
            with open(_QUOTA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
        data.setdefault("vertex_month_spend", 0.0)
        data.setdefault("vertex_budget_ceiling", 9.5)
        data.setdefault("last_updated_timestamp", 0)
        data.setdefault("antigravity_swarm_rpm", 0)
        data.setdefault("antigravity_warning_active", False)
        return data

def _save_quota(data: Dict[str, Any]) -> None:
    """Atomically write quota data to the JSON cache file.
    Writes to a temporary file first and then replaces the target.
    """
    with _QUOTA_LOCK:
        tmp_path = _QUOTA_PATH.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, _QUOTA_PATH)

class VertexMonthlyBudgetBreaker:
    """Tracks Vertex AI spend for the current calendar month and trips when a ceiling is reached.

    The budget ceiling is $9.50 per month. The implementation records a spend value that callers provide
    (e.g., token‑based cost) and accumulates it. The month rolls over automatically on the first day of
    each month.
    """

    def __init__(self):
        self._data = _load_quota()
        self._budget_ceiling = float(self._data.get("vertex_budget_ceiling", 9.5))
        self._current_month = datetime.utcnow().month

    def _reset_if_new_month(self) -> None:
        now_month = datetime.utcnow().month
        if now_month != self._current_month:
            self._data["vertex_month_spend"] = 0.0
            self._current_month = now_month
            self._data["last_updated_timestamp"] = int(time.time())
            _save_quota(self._data)

    def record_spend(self, amount: float) -> None:
        """Add *amount* (in USD) to the monthly spend.
        Thread‑safe and persists the updated state.
        """
        self._reset_if_new_month()
        self._data["vertex_month_spend"] = self._data.get("vertex_month_spend", 0.0) + amount
        self._data["last_updated_timestamp"] = int(time.time())
        _save_quota(self._data)

    def should_trip(self) -> bool:
        """Return ``True`` if the accumulated spend exceeds the ceiling."""
        self._reset_if_new_month()
        return float(self._data.get("vertex_month_spend", 0.0)) >= self._budget_ceiling

    def get_status(self) -> Dict[str, Any]:
        """Return a snapshot of the current budget state."""
        self._reset_if_new_month()
        return {
            "vertex_month_spend": float(self._data.get("vertex_month_spend", 0.0)),
            "vertex_budget_ceiling": self._budget_ceiling,
            "budget_tripped": self.should_trip(),
        }

class AntigravitySwarmRateMonitor:
    """Monitors Antigravity CLI invocations in a sliding 60‑second window.

    Records timestamps for each invocation, computes the current requests‑per‑minute (RPM), and raises a
    warning flag when the projected usage would exhaust the five‑hour Pro credit window. A default
    warning threshold of 300 RPM (≈5 000 requests over five hours) is used.
    """

    def __init__(self, rpm_warning_threshold: int = 300):
        self._timestamps = deque()
        self._lock = threading.Lock()
        self._warning_threshold = rpm_warning_threshold
        self._warning_active = False
        self._load_state()

    def _prune(self) -> None:
        cutoff = time.time() - 60
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()

    def record_invocation(self) -> None:
        with self._lock:
            now = time.time()
            self._timestamps.append(now)
            self._prune()
            self._warning_active = len(self._timestamps) >= self._warning_threshold
            self._persist_state()

    def current_rpm(self) -> int:
        with self._lock:
            self._prune()
            return len(self._timestamps)

    def warning_active(self) -> bool:
        with self._lock:
            self._prune()
            return self._warning_active

    def _state_path(self) -> Path:
        return _QUOTA_PATH.parent / "swarm_rate.json"

    def _persist_state(self) -> None:
        path = self._state_path()
        data = {
            "timestamps": list(self._timestamps),
            "warning_active": self._warning_active,
        }
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, path)

    def _load_state(self) -> None:
        path = self._state_path()
        if not path.is_file():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            timestamps = data.get("timestamps", [])
            with self._lock:
                self._timestamps = deque(timestamps)
                self._warning_active = data.get("warning_active", False)
        except Exception:
            pass

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            self._prune()
            return {
                "antigravity_swarm_rpm": len(self._timestamps),
                "antigravity_warning_active": self._warning_active,
            }

# Shared singletons used throughout the codebase
_vertex_budget_breaker = VertexMonthlyBudgetBreaker()
_swarm_rate_monitor = AntigravitySwarmRateMonitor()

def get_vertex_monthly_budget_breaker() -> VertexMonthlyBudgetBreaker:
    """Return the shared ``VertexMonthlyBudgetBreaker`` instance."""
    return _vertex_budget_breaker

def get_swarm_rate_monitor() -> AntigravitySwarmRateMonitor:
    """Return the shared ``AntigravitySwarmRateMonitor`` instance."""
    return _swarm_rate_monitor

__all__ = [
    "VertexMonthlyBudgetBreaker",
    "AntigravitySwarmRateMonitor",
    "get_vertex_monthly_budget_breaker",
    "get_swarm_rate_monitor",
]

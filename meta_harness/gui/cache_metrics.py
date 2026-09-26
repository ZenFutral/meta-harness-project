import json
import os
import time
import threading
from pathlib import Path
from typing import Dict, Any

# Directory where cache files live (same as cache_ops uses)
CACHE_DIR = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".agent", "cache")))
if not CACHE_DIR.exists():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

# In‑memory per‑key metrics
_METRICS: Dict[str, Dict[str, Any]] = {}

# Persistence file (placed under orchestrator state)
STATE_DIR = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "orchestrator")))
STATE_DIR.mkdir(parents=True, exist_ok=True)
_STATE_FILE = STATE_DIR / "cache_metrics.json"

_STATE_LOCK = threading.Lock()

def _load_state() -> None:
    """Load persisted metrics from disk into _METRICS (called at import time)."""
    if _STATE_FILE.exists():
        try:
            with open(_STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    _METRICS.update(data)
        except Exception:
            # If the file is corrupt we start fresh – log later via GUI logger
            pass

def _save_state() -> None:
    """Atomically write the current metrics to disk."""
    tmp_path = _STATE_FILE.with_suffix(".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(_METRICS, f, indent=2)
        os.replace(tmp_path, _STATE_FILE)
    except Exception:
        # Silently ignore save errors – they will be logged by the caller if needed
        pass

# Load on module import
_load_state()

def record_access(key: str, *, hit: bool = True, bytes_written: int = 0, latency: float = 0.0) -> None:
    """Update metrics for a specific cache *key*.

    Args:
        key: Identifier for the cached entry (e.g., file path or hash).
        hit: Whether this access was a cache hit.
        bytes_written: Number of bytes written to the cache (0 for reads).
        latency: Time in seconds the operation took.
    """
    met = _METRICS.setdefault(key, {
        "reads": 0,
        "writes": 0,
        "hits": 0,
        "misses": 0,
        "bytes": 0,
        "total_latency": 0.0,
        "last_access": time.time(),
    })
    met["reads"] += 1
    if hit:
        met["hits"] += 1
    else:
        met["misses"] += 1
    met["bytes"] += bytes_written
    met["total_latency"] += latency
    met["last_access"] = time.time()

def record_write(key: str, *, bytes_written: int, latency: float = 0.0) -> None:
    """Record a cache write operation (e.g., when regen_cache stores a file)."""
    met = _METRICS.setdefault(key, {
        "reads": 0,
        "writes": 0,
        "hits": 0,
        "misses": 0,
        "bytes": 0,
        "total_latency": 0.0,
        "last_access": time.time(),
    })
    met["writes"] += 1
    met["bytes"] += bytes_written
    met["total_latency"] += latency
    met["last_access"] = time.time()

def snapshot() -> Dict[str, Any]:
    """Return a deep‑copy of the current metrics suitable for JSON API response."""
    result: Dict[str, Any] = {}
    for k, v in _METRICS.items():
        reads = v.get("reads", 0)
        avg_latency = (v.get("total_latency", 0.0) / reads) if reads > 0 else 0.0
        result[k] = {
            "reads": reads,
            "writes": v.get("writes", 0),
            "hits": v.get("hits", 0),
            "misses": v.get("misses", 0),
            "bytes": v.get("bytes", 0),
            "avg_latency_ms": round(avg_latency * 1000, 3),
            "last_access": v.get("last_access", 0),
        }
    return result

def persist_periodically(interval: int = 60) -> threading.Thread:
    """Start a daemon thread that flushes metrics to disk every *interval* seconds."""
    def _run():
        while True:
            time.sleep(interval)
            with _STATE_LOCK:
                _save_state()
    t = threading.Thread(target=_run, daemon=True, name="cache-metrics-persist")
    t.start()
    return t

# Auto‑start persistence thread on import
persist_periodically()

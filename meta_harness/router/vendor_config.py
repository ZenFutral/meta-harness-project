"""
Vendor configuration store for Hugging Face, Vertex AI, and Antigravity model providers.
Persists settings to .agent/config/vendors.json.
"""
import os
import json
from pathlib import Path
from typing import Dict, Any

WORKSPACE_ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
AGENT_CONFIG_DIR = WORKSPACE_ROOT / ".agent" / "config"
VENDORS_FILE = AGENT_CONFIG_DIR / "vendors.json"

DEFAULT_VENDOR_CONFIG: Dict[str, Any] = {
    "vendors": {
        "huggingface": {
            "name": "Hugging Face Serverless",
            "enabled": True,
            "primary_model": "facebook/bart-large-mnli",
            "role": "Tier 0 Zero-Shot Intent Classification",
            "tier": "Tier 0 Triage"
        },
        "vertex": {
            "name": "Vertex AI (Gemini Flash)",
            "enabled": True,
            "primary_model": "gemini-2.0-flash",
            "role": "Tier 1 Router & Manifest Synthesizer ($0.33/day Cap)",
            "tier": "Tier 1 Router"
        },
        "antigravity": {
            "name": "Google Antigravity CLI",
            "enabled": True,
            "primary_model": "antigravity-default",
            "role": "Tier 2 Deep Agentic Execution & Pro Subscription",
            "tier": "Tier 2 Execution"
        }
    },
    "active_backend": "vertex"
}


def load_vendor_config() -> Dict[str, Any]:
    """Loads current vendor configuration from disk or returns defaults."""
    if VENDORS_FILE.exists():
        try:
            data = json.loads(VENDORS_FILE.read_text(encoding="utf-8"))
            # Ensure missing vendor keys inherit defaults
            cfg = DEFAULT_VENDOR_CONFIG.copy()
            cfg["active_backend"] = data.get("active_backend", "vertex")
            if "vendors" in data:
                for k, v in data["vendors"].items():
                    if k in cfg["vendors"]:
                        cfg["vendors"][k].update(v)
            return cfg
        except Exception:
            pass

    return DEFAULT_VENDOR_CONFIG.copy()


def save_vendor_config(config: Dict[str, Any]) -> None:
    """Persists configuration to .agent/config/vendors.json."""
    AGENT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    VENDORS_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")


def set_vendor_enabled(vendor_id: str, enabled: bool) -> Dict[str, Any]:
    """Toggles a vendor ON or OFF."""
    cfg = load_vendor_config()
    if vendor_id in cfg["vendors"]:
        cfg["vendors"][vendor_id]["enabled"] = bool(enabled)
        save_vendor_config(cfg)
    return cfg


def set_active_backend(backend_id: str) -> Dict[str, Any]:
    """Sets active default execution backend (vertex vs antigravity)."""
    cfg = load_vendor_config()
    if backend_id in ["vertex", "antigravity", "huggingface"]:
        cfg["active_backend"] = backend_id
        save_vendor_config(cfg)
    return cfg


def is_vendor_enabled(vendor_id: str) -> bool:
    """Checks if a vendor is currently enabled."""
    cfg = load_vendor_config()
    return cfg.get("vendors", {}).get(vendor_id, {}).get("enabled", True)

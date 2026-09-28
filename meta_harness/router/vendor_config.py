"""
Vendor and Model configuration store supporting multi-vendor providers
(Antigravity, OpenAI, Vertex AI, Hugging Face) and user_config.json persistence.
"""
from __future__ import annotations

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

log = logging.getLogger(__name__)

WORKSPACE_ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
AGENT_CONFIG_DIR = WORKSPACE_ROOT / ".agent" / "config"
VENDORS_FILE = AGENT_CONFIG_DIR / "vendors.json"
USER_CONFIG_FILE = AGENT_CONFIG_DIR / "user_config.json"
WORKSPACE_USER_CONFIG = WORKSPACE_ROOT / "user_config.json"

DEFAULT_VENDOR_CONFIG: Dict[str, Any] = {
    "vendors": {
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
            "primary_model": "gemini-3-pro-preview",
            "role": "Tier 2 Deep Agentic Execution & Pro Subscription",
            "tier": "Tier 2 Execution"
        }
    },
    "active_backend": "antigravity/gemini-3-pro-preview"
}

DEFAULT_USER_CONFIG: Dict[str, Any] = {
    "active_vendor_models": [
        "antigravity/gemini-3-pro-preview",
        "antigravity/antigravity-default",
        "antigravity",
        "openai",
        "vertex",
        "huggingface"
    ],
    "active_backend": "antigravity/gemini-3-pro-preview",
    "antigravity": {
        "api_keys": ["", ""],
        "models": {
            "gemini-3-pro-preview": {
                "daily_quota": 1000,
                "max_output_tokens": 100000,
                "max_thinking_tokens": 10000,
                "rate_limit": 100
            },
            "antigravity-default": {
                "daily_quota": 5000,
                "max_output_tokens": 128000,
                "max_thinking_tokens": 8000,
                "rate_limit": 120
            }
        }
    },
    "openai": {
        "api_keys": ["", ""],
        "models": {
            "gpt-5.1": {
                "daily_quota": 1000,
                "max_output_tokens": 100000,
                "max_thinking_tokens": 10000,
                "rate_limit": 100
            },
            "gpt-4o": {
                "daily_quota": 2000,
                "max_output_tokens": 16384,
                "max_thinking_tokens": 0,
                "rate_limit": 200
            }
        }
    },
    "vertex": {
        "api_keys": [""],
        "models": {
            "gemini-2.0-flash": {
                "daily_quota": 1500,
                "max_output_tokens": 64000,
                "max_thinking_tokens": 8000,
                "rate_limit": 150
            },
            "gemini-2.5-flash": {
                "daily_quota": 1000,
                "max_output_tokens": 64000,
                "max_thinking_tokens": 8000,
                "rate_limit": 100
            }
        }
    },
    "huggingface": {
        "api_keys": [""],
        "models": {
            "facebook/bart-large-mnli": {
                "daily_quota": 5000,
                "max_output_tokens": 4096,
                "max_thinking_tokens": 0,
                "rate_limit": 300
            }
        }
    }
}


def _deep_merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merges override dictionary into base copy."""
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge_dict(result[k], v)
        else:
            result[k] = v
    return result


def load_user_config() -> Dict[str, Any]:
    """Loads user_config.json from .agent/config/ or workspace root, returning defaults if missing."""
    target_path = None
    if USER_CONFIG_FILE.exists():
        target_path = USER_CONFIG_FILE
    elif WORKSPACE_USER_CONFIG.exists():
        target_path = WORKSPACE_USER_CONFIG

    if target_path and target_path.exists():
        try:
            data = json.loads(target_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return _deep_merge_dict(DEFAULT_USER_CONFIG, data)
        except Exception as e:
            log.warning("Failed to parse %s: %s; falling back to default user_config", target_path, e)

    return json.loads(json.dumps(DEFAULT_USER_CONFIG))


def save_user_config(config: Dict[str, Any]) -> None:
    """Persists configuration to .agent/config/user_config.json."""
    AGENT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    USER_CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")


def get_active_vendor_models() -> List[str]:
    """Returns list of active vendor/model entries from user_config.json."""
    cfg = load_user_config()
    return cfg.get("active_vendor_models", [])


def set_active_vendor_models(active_list: List[str]) -> Dict[str, Any]:
    """Updates and persists active_vendor_models in user_config.json."""
    cfg = load_user_config()
    cfg["active_vendor_models"] = list(active_list)
    save_user_config(cfg)
    return cfg


def is_model_active(identifier: str, model_id: Optional[str] = None) -> bool:
    """
    Checks if a model or vendor is active according to active_vendor_models.
    
    Supports:
      - Exact match: "antigravity/gemini-3-pro-preview"
      - Wildcard vendor match: "openai" activates all models under "openai"
      - Vendor query: "openai" -> True if "openai" or any "openai/*" is active
      - Model query with vendor: ("openai", "gpt-5.1")
    """
    active_list = get_active_vendor_models()
    if not active_list:
        # Fallback to checking vendor enabled in legacy config
        return is_vendor_enabled(identifier)

    target = identifier.strip()
    if model_id:
        target = f"{identifier.strip()}/{model_id.strip()}"

    # 1. Exact match
    if target in active_list:
        return True

    # 2. If target has a slash (vendor/model)
    if "/" in target:
        vendor, model = target.split("/", 1)
        # Whole-vendor wildcard matches this model
        if vendor in active_list:
            return True
        return False

    # 3. Target is vendor name without slash (e.g. "openai" or "antigravity")
    if target in active_list:
        return True
    for item in active_list:
        if item.startswith(f"{target}/"):
            return True

    return False


def get_active_backend() -> str:
    """Returns the default active backend/model identifier from user_config or vendors.json."""
    user_cfg = load_user_config()
    if "active_backend" in user_cfg and user_cfg["active_backend"]:
        return user_cfg["active_backend"]

    vendor_cfg = load_vendor_config()
    return vendor_cfg.get("active_backend", "antigravity/gemini-3-pro-preview")


def set_active_backend(backend_id: str) -> Dict[str, Any]:
    """Sets active default execution backend across user_config and vendors.json."""
    user_cfg = load_user_config()
    user_cfg["active_backend"] = backend_id
    # Ensure active backend is present in active_vendor_models
    active_list = user_cfg.get("active_vendor_models", [])
    if backend_id not in active_list:
        active_list.append(backend_id)
        user_cfg["active_vendor_models"] = active_list
    save_user_config(user_cfg)

    vendor_cfg = load_vendor_config()
    simple_backend = backend_id.split("/")[0] if "/" in backend_id else backend_id
    if simple_backend in vendor_cfg.get("vendors", {}):
        vendor_cfg["active_backend"] = simple_backend
        save_vendor_config(vendor_cfg)

    return user_cfg


def get_model_spec(vendor_or_qualified: str, model_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieves model specifications (daily_quota, max_output_tokens, max_thinking_tokens, rate_limit)
    from user_config.json, with robust fallbacks.
    """
    user_cfg = load_user_config()
    if "/" in vendor_or_qualified and not model_id:
        vendor, model = vendor_or_qualified.split("/", 1)
    else:
        vendor = vendor_or_qualified
        model = model_id or ""

    vendor_data = user_cfg.get(vendor, {})
    models_dict = vendor_data.get("models", {})
    if model in models_dict:
        return dict(models_dict[model])

    # Check first available model for vendor
    if models_dict:
        first_key = next(iter(models_dict))
        return dict(models_dict[first_key])

    # Safe defaults
    return {
        "daily_quota": 1000,
        "max_output_tokens": 64000,
        "max_thinking_tokens": 8000,
        "rate_limit": 100
    }


def get_all_active_models() -> List[Dict[str, Any]]:
    """
    Returns a unified list of all currently active models with vendor, model_id,
    qualified name, and specs.
    """
    user_cfg = load_user_config()
    active_list = user_cfg.get("active_vendor_models", [])
    result = []
    seen = set()

    for item in active_list:
        if "/" in item:
            vendor, model = item.split("/", 1)
            qualified = item
            if qualified not in seen:
                seen.add(qualified)
                spec = get_model_spec(vendor, model)
                result.append({
                    "vendor": vendor,
                    "model": model,
                    "qualified": qualified,
                    "spec": spec
                })
        else:
            vendor = item
            vendor_data = user_cfg.get(vendor, {})
            models_dict = vendor_data.get("models", {})
            for m_id, m_spec in models_dict.items():
                qualified = f"{vendor}/{m_id}"
                if qualified not in seen:
                    seen.add(qualified)
                    result.append({
                        "vendor": vendor,
                        "model": m_id,
                        "qualified": qualified,
                        "spec": dict(m_spec)
                    })

    # If active_vendor_models is empty, provide default active backend
    if not result:
        default_backend = get_active_backend()
        v = default_backend.split("/")[0] if "/" in default_backend else default_backend
        m = default_backend.split("/")[1] if "/" in default_backend else "default"
        result.append({
            "vendor": v,
            "model": m,
            "qualified": default_backend,
            "spec": get_model_spec(v, m)
        })

    return result


# ---------------------------------------------------------------------------
# Backward-compatible vendor API
# ---------------------------------------------------------------------------

def load_vendor_config() -> Dict[str, Any]:
    """Loads current vendor configuration merged with user_config."""
    cfg = DEFAULT_VENDOR_CONFIG.copy()
    if VENDORS_FILE.exists():
        try:
            data = json.loads(VENDORS_FILE.read_text(encoding="utf-8"))
            cfg["active_backend"] = data.get("active_backend", "antigravity/gemini-3-pro-preview")
            if "vendors" in data:
                for k, v in data["vendors"].items():
                    if k in cfg["vendors"]:
                        cfg["vendors"][k].update(v)
                    else:
                        cfg["vendors"][k] = v
        except Exception:
            pass

    # Enrich with user_config state
    user_cfg = load_user_config()
    cfg["active_vendor_models"] = user_cfg.get("active_vendor_models", [])
    cfg["user_config"] = user_cfg
    if "active_backend" in user_cfg:
        cfg["active_model_backend"] = user_cfg["active_backend"]

    return cfg


def save_vendor_config(config: Dict[str, Any]) -> None:
    """Persists configuration to .agent/config/vendors.json."""
    AGENT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    # Strip heavy user_config sub-keys when saving to vendors.json
    to_save = {
        "vendors": config.get("vendors", DEFAULT_VENDOR_CONFIG["vendors"]),
        "active_backend": config.get("active_backend", "antigravity/gemini-3-pro-preview")
    }
    VENDORS_FILE.write_text(json.dumps(to_save, indent=2), encoding="utf-8")


def set_vendor_enabled(vendor_id: str, enabled: bool) -> Dict[str, Any]:
    """Toggles a vendor ON or OFF in vendors.json and updates active_vendor_models."""
    cfg = load_vendor_config()
    if vendor_id in cfg["vendors"]:
        cfg["vendors"][vendor_id]["enabled"] = bool(enabled)
        save_vendor_config(cfg)

    # Sync with user_config active_vendor_models
    user_cfg = load_user_config()
    active_list = user_cfg.get("active_vendor_models", [])
    if enabled:
        if not is_model_active(vendor_id):
            active_list.append(vendor_id)
            user_cfg["active_vendor_models"] = active_list
            save_user_config(user_cfg)
    else:
        # Remove vendor and its specific models
        active_list = [
            item for item in active_list
            if item != vendor_id and not item.startswith(f"{vendor_id}/")
        ]
        user_cfg["active_vendor_models"] = active_list
        save_user_config(user_cfg)

    return load_vendor_config()
def toggle_vendor(vendor_id: str, enabled: bool) -> dict:
    """Toggle a vendor's enabled state via the existing set_vendor_enabled helper.

    Returns a dict compatible with the API endpoint expectations.
    """
    set_vendor_enabled(vendor_id, enabled)
    return {"success": True, "enabled": enabled}



def is_vendor_enabled(vendor_id: str) -> bool:
    """Checks if a vendor is currently enabled via vendors.json or active_vendor_models."""
    cfg = load_vendor_config()
    vendor_entry = cfg.get("vendors", {}).get(vendor_id, {})
    if "enabled" in vendor_entry:
        return bool(vendor_entry["enabled"])
    return is_model_active(vendor_id)

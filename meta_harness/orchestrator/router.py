"""Deprecated location for router.py.
Router logic has been migrated to the `router` package (`meta-harness/router/router.py`).
Re-exporting for backward compatibility.
"""

def __getattr__(name):
    if name in ("ModelRouter", "BaseRouter"):
        import router.router as router_mod
        return getattr(router_mod, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ["ModelRouter", "BaseRouter"]

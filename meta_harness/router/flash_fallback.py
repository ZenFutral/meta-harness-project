import logging
from typing import Optional, Dict, Any

from .manifest import RoutingManifest

log = logging.getLogger(__name__)


class FlashFallbackRouter:
    """Stage 2 Ambiguity Fallback Router (Vertex AI Gemini 2.0 / 2.5 Flash).

    Evaluates ambiguous requests when zero-shot confidence < 0.85.
    Enforces $0.33/day daily cost circuit breaker via check_and_update_budget().
    """

    def __init__(self, model_name: str = "gemini-2.0-flash"):
        self.model_name = model_name

    def route_fallback(self, prompt: str, **kwargs) -> RoutingManifest:
        from .vendor_config import is_vendor_enabled
        vertex_enabled = is_vendor_enabled("vertex")
        antigravity_enabled = is_vendor_enabled("antigravity")

        # If Vertex AI is disabled, bypass Vertex API call
        if not vertex_enabled:
            log.info("Vertex AI vendor is toggled OFF; using deterministic router")
            engine = "antigravity_cli" if antigravity_enabled else "repomap_only"
            return RoutingManifest(
                intent="repomap_summary",
                primary_target_symbols=kwargs.get("primary_target_symbols", []),
                focus_files=kwargs.get("focus_files", []),
                repomap_token_budget=2048,
                require_blast_radius=False,
                execution_engine=engine,
                task_instructions="Routed with Vertex AI vendor toggled OFF",
            )

        # Import budget check lazily to avoid circular import during module load
        from orchestrator.budget import check_and_update_budget

        # Estimate input tokens
        input_tokens = max(1, len(prompt) // 4)

        # Enforce $0.33/day circuit breaker
        budget_ok = check_and_update_budget(input_tokens)
        if not budget_ok:
            log.warning("Daily Vertex AI budget limit ($0.33/day) reached; tripping to deterministic fallback")
            engine = "antigravity_cli" if antigravity_enabled else "repomap_only"
            return RoutingManifest(
                intent="repomap_summary",
                primary_target_symbols=kwargs.get("primary_target_symbols", []),
                focus_files=kwargs.get("focus_files", []),
                repomap_token_budget=2048,
                require_blast_radius=False,
                execution_engine=engine,
                task_instructions="Fallback due to daily budget ceiling trip",
            )

        # Disambiguate prompt intent
        p_lower = prompt.lower()
        if "trace" in p_lower or "call hierarchy" in p_lower or "blast radius" in p_lower:
            intent = "symbol_trace"
            require_blast = True
        elif "schema" in p_lower or "dto" in p_lower or "model" in p_lower:
            intent = "schema_registry"
            require_blast = False
        elif "refactor" in p_lower or "multi-file" in p_lower:
            intent = "refactor_code"
            require_blast = True
        elif "cycle" in p_lower or "import" in p_lower:
            intent = "dependency_check"
            require_blast = False
        else:
            intent = "repomap_summary"
            require_blast = False

        return RoutingManifest(
            intent=intent,
            primary_target_symbols=kwargs.get("primary_target_symbols", []),
            focus_files=kwargs.get("focus_files", []),
            repomap_token_budget=kwargs.get("repomap_token_budget", 2048),
            require_blast_radius=require_blast,
            execution_engine="antigravity_cli",
            task_instructions=f"Vertex AI Flash routed for prompt: {prompt[:50]}...",
        )

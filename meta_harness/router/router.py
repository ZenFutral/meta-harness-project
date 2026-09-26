"""Router module for Repomap.

Provides BaseRouter and ModelRouter constructing RoutingManifest instances via multi-tier routing:
Stage 1: Hugging Face Zero-Shot Intent Classifier
Stage 2: Vertex AI Flash Ambiguity Fallback (with $0.33/day budget circuit breaker)
"""

from __future__ import annotations

import logging
from typing import List, Literal, Optional

from .manifest import RoutingManifest
from .zero_shot import ZeroShotIntentClassifier
from .flash_fallback import FlashFallbackRouter

log = logging.getLogger(__name__)


def _get_config():
    import orchestrator.config as cfg
    return cfg


class BaseRouter:
    """Abstract router interface."""

    def route(
        self,
        intent: Literal[
            "repomap_summary",
            "symbol_trace",
            "schema_registry",
            "refactor_code",
            "dependency_check",
        ],
        primary_target_symbols: Optional[List[str]] = None,
        focus_files: Optional[List[str]] = None,
        repomap_token_budget: int = 2048,
        require_blast_radius: bool = False,
        execution_engine: Literal["antigravity_cli", "repomap_only"] = "repomap_only",
        task_instructions: str = "",
    ) -> RoutingManifest:
        raise NotImplementedError


class ModelRouter(BaseRouter):
    """Multi-tier router for SWE orchestration and Repomap."""

    def __init__(self, backend: str = "vertex") -> None:
        cfg = _get_config()
        self._backend = backend
        self._model_map = cfg.MODELS_ANTIGRAVITY if backend == "antigravity" else cfg.MODELS
        self._tier_order = ["flash", "pro"]
        self.zero_shot = ZeroShotIntentClassifier()
        self.flash_fallback = FlashFallbackRouter()

    def model_id_for_persona(self, persona: str) -> str:
        cfg = _get_config()
        if persona not in cfg.PERSONAS:
            log.warning("Router: unknown persona %r; falling back to flash", persona)
            return self._model_map.get("flash", cfg.MODELS["flash"])
        model = self._model_map.get(persona)
        if model is None:
            log.warning("Router: no model configured for persona %r; falling back", persona)
            return self._model_map.get("flash", cfg.MODELS["flash"])
        log.debug("Router: persona=%s → model=%s", persona, model)
        return model

    def select(self, prompt: str, prompt_token_estimate: int = 0) -> str:
        cfg = _get_config()
        text_lower = prompt.lower()
        keywords = cfg.COMPLEXITY_THRESHOLDS["reasoning_keywords"]
        max_flash_tokens = cfg.COMPLEXITY_THRESHOLDS["max_prompt_tokens_for_flash"]
        if prompt_token_estimate > max_flash_tokens:
            log.info("Router: escalating to pro (token count %d > %d)", prompt_token_estimate, max_flash_tokens)
            return "pro"
        for kw in keywords:
            if kw in text_lower:
                log.info("Router: escalating to pro (keyword %r found)", kw)
                return "pro"
        log.info("Router: using flash (low complexity)")
        return "flash"

    def escalate(self, current_tier: str) -> str:
        idx = self._tier_order.index(current_tier)
        next_idx = min(idx + 1, len(self._tier_order) - 1)
        new_tier = self._tier_order[next_idx]
        if new_tier != current_tier:
            log.info("Router: escalated %s -> %s", current_tier, new_tier)
        return new_tier

    def downgrade(self, current_tier: str) -> str:
        idx = self._tier_order.index(current_tier)
        prev_idx = max(idx - 1, 0)
        new_tier = self._tier_order[prev_idx]
        if new_tier != current_tier:
            log.info("Router: downgraded %s -> %s", current_tier, new_tier)
        return new_tier

    def route(
        self,
        intent: Literal[
            "repomap_summary",
            "symbol_trace",
            "schema_registry",
            "refactor_code",
            "dependency_check",
        ],
        primary_target_symbols: Optional[List[str]] = None,
        focus_files: Optional[List[str]] = None,
        repomap_token_budget: int = 2048,
        require_blast_radius: bool = False,
        execution_engine: Literal["antigravity_cli", "repomap_only"] = "repomap_only",
        task_instructions: str = "",
    ) -> RoutingManifest:
        manifest = RoutingManifest(
            intent=intent,
            primary_target_symbols=primary_target_symbols or [],
            focus_files=focus_files or [],
            repomap_token_budget=repomap_token_budget,
            require_blast_radius=require_blast_radius,
            execution_engine=execution_engine,
            task_instructions=task_instructions,
        )
        log.debug("Router: constructed manifest %s", manifest.json())
        return manifest

    def route_with_fallback(self, prompt: str, **kwargs) -> RoutingManifest:
        # Stage 1: Fast-path Zero-shot intent classification
        fast_manifest = self.zero_shot.route_fast_path(prompt, **kwargs)
        if fast_manifest is not None:
            return fast_manifest

        # Stage 2: Vertex AI Flash ambiguity fallback with budget circuit breaker
        return self.flash_fallback.route_fallback(prompt, **kwargs)

    @staticmethod
    def model_id(tier: str) -> str:
        cfg = _get_config()
        return cfg.MODELS[tier]

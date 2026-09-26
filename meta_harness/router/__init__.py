"""Router package for Repomap.
Provides routing manifest schemas, zero-shot classifier, flash fallback, and multi-tier routing logic.
"""

from .manifest import RoutingManifest
from .router import BaseRouter, ModelRouter
from .zero_shot import ZeroShotIntentClassifier
from .flash_fallback import FlashFallbackRouter

__all__ = [
    "RoutingManifest",
    "BaseRouter",
    "ModelRouter",
    "ZeroShotIntentClassifier",
    "FlashFallbackRouter",
]

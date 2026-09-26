import os
import json
import logging
import urllib.request
from typing import Optional, Tuple, Dict, Any

from .manifest import RoutingManifest

log = logging.getLogger(__name__)

CANDIDATE_LABELS = [
    "schema_inspection",
    "architecture_navigation",
    "targeted_code_edit",
    "multi_file_refactoring",
    "dependency_cycle_resolution",
]

LABEL_TO_INTENT: Dict[str, str] = {
    "schema_inspection": "schema_registry",
    "architecture_navigation": "repomap_summary",
    "targeted_code_edit": "refactor_code",
    "multi_file_refactoring": "refactor_code",
    "dependency_cycle_resolution": "dependency_check",
}


class ZeroShotIntentClassifier:
    """Stage 1 Hugging Face Zero-Shot Intent Classifier (facebook/bart-large-mnli).

    Fast-path triage: bypasses Vertex AI if classification confidence >= 0.85.
    """

    def __init__(self, api_url: Optional[str] = None):
        self.api_url = api_url or "https://api-inference.huggingface.co/models/facebook/bart-large-mnli"

    def classify(self, prompt: str) -> Optional[Tuple[str, float]]:
        headers = {"Content-Type": "application/json"}
        token = os.getenv("HF_API_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        payload = {
            "inputs": prompt,
            "parameters": {"candidate_labels": CANDIDATE_LABELS},
        }

        try:
            req = urllib.request.Request(
                self.api_url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    if isinstance(data, dict) and "labels" in data and "scores" in data:
                        best_label = data["labels"][0]
                        best_score = float(data["scores"][0])
                        return best_label, best_score
        except Exception as exc:
            log.debug("HF inference request failed: %s", exc)

        # Fallback heuristic rule matcher
        return self._rule_fallback(prompt)

    def _rule_fallback(self, prompt: str) -> Optional[Tuple[str, float]]:
        p_lower = prompt.lower()
        if any(w in p_lower for w in ["schema", "orm", "dto", "model", "pydantic", "proto"]):
            return "schema_inspection", 0.90
        elif any(w in p_lower for w in ["map", "summary", "structure", "overview", "skeleton"]):
            return "architecture_navigation", 0.90
        elif any(w in p_lower for w in ["cycle", "circular", "import loop"]):
            return "dependency_cycle_resolution", 0.90
        elif any(w in p_lower for w in ["refactor", "rename", "rewrite", "multi-file"]):
            return "multi_file_refactoring", 0.88
        elif any(w in p_lower for w in ["edit", "fix", "patch", "bug"]):
            return "targeted_code_edit", 0.86

        return None

    def route_fast_path(self, prompt: str, **kwargs) -> Optional[RoutingManifest]:
        from .vendor_config import is_vendor_enabled
        if not is_vendor_enabled("huggingface"):
            log.info("Hugging Face vendor is toggled OFF; bypassing fast-path")
            return None

        res = self.classify(prompt)
        if not res:
            return None

        label, score = res
        if score < 0.85:
            log.info("Zero-shot confidence %.2f < 0.85 threshold; delegating to Stage 2", score)
            return None

        intent = LABEL_TO_INTENT.get(label, "repomap_summary")
        budget = 4096 if intent == "refactor_code" else 2048

        return RoutingManifest(
            intent=intent,
            primary_target_symbols=kwargs.get("primary_target_symbols", []),
            focus_files=kwargs.get("focus_files", []),
            repomap_token_budget=budget,
            require_blast_radius=kwargs.get("require_blast_radius", False),
            execution_engine=kwargs.get("execution_engine", "repomap_only"),
            task_instructions=f"Fast-path zero-shot routed for {label} (confidence: {score:.2f})",
        )

"""Stage 2: Provider Cascade Executor.

This module defines a minimal implementation of the provider cascade as described
in the implementation plan. It uses only the Python standard library –
`urllib.request` for HTTP calls and `subprocess` for invoking local executables.
The executor attempts to run the prompt through a series of tiers, falling back
if a tier fails or exceeds context limits.
"""

from __future__ import annotations

import json
import logging
import subprocess
import urllib.request
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)

# Simple configuration placeholder – in a real project this would be loaded from
# orchestrator.config or a similar settings module.
class Config:
    # Example model endpoints / commands for each tier
    GEMMA_LOCAL_CMD = ["python", "-m", "gemma_server", "--prompt"]
    AGY_CLI_CMD = ["agy", "run"]
    VERTEX_AI_ENDPOINT = "https://vertexai.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION/publishModels/MODEL_ID:predict"
    OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
    # Token limits per tier (illustrative values)
    TIER_TOKEN_LIMITS = {
        "gemma": 8192,
        "agy": 16384,
        "vertex": 32768,
        "openrouter": 65536,
    }

def _run_subprocess(command: list[str], input_text: str) -> Optional[Dict[str, Any]]:
    """Run a subprocess command with *input_text* as stdin.

    Returns parsed JSON output if the command succeeds, otherwise ``None``.
    """
    try:
        result = subprocess.run(
            command,
            input=input_text.encode("utf-8"),
            capture_output=True,
            check=True,
            timeout=30,
        )
        return json.loads(result.stdout.decode("utf-8"))
    except Exception as exc:
        log.debug("Subprocess %s failed: %s", command, exc)
        return None

def _http_post(url: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """POST *payload* as JSON to *url* and return parsed JSON response.
    """
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        log.debug("HTTP request to %s failed: %s", url, exc)
    return None

class ProviderCascadeExecutor:
    """Attempt to satisfy a prompt using a cascade of providers.

    The cascade order is:
        1. Local Gemma E4B (subprocess)
        2. Antigravity CLI (subprocess)
        3. Vertex AI (REST)
        4. OpenRouter (REST)
    """

    def __init__(self, config: Optional[Config] = None):
        self.cfg = config or Config()

    def execute(self, prompt: str, token_budget: int) -> Optional[Dict[str, Any]]:
        """Run *prompt* through the cascade respecting *token_budget*.

        The function checks the budget against each tier's limit and falls back
        when the tier cannot handle the request or returns an error.
        """
        # Tier 1 – Gemma local binary
        if token_budget <= self.cfg.TIER_TOKEN_LIMITS["gemma"]:
            log.info("Attempting Gemma local execution")
            result = _run_subprocess(self.cfg.GEMMA_LOCAL_CMD, prompt)
            if result:
                return result
        # Tier 2 – Antigravity CLI
        if token_budget <= self.cfg.TIER_TOKEN_LIMITS["agy"]:
            log.info("Falling back to Antigravity CLI")
            result = _run_subprocess(self.cfg.AGY_CLI_CMD, prompt)
            if result:
                return result
        # Tier 3 – Vertex AI REST
        if token_budget <= self.cfg.TIER_TOKEN_LIMITS["vertex"]:
            log.info("Falling back to Vertex AI")
            payload = {"instances": [{"prompt": prompt}], "parameters": {"max_output_tokens": token_budget}}
            result = _http_post(self.cfg.VERTEX_AI_ENDPOINT, payload)
            if result:
                return result
        # Tier 4 – OpenRouter REST
        if token_budget <= self.cfg.TIER_TOKEN_LIMITS["openrouter"]:
            log.info("Falling back to OpenRouter")
            payload = {"model": "openrouter-model", "messages": [{"role": "user", "content": prompt}], "max_tokens": token_budget}
            result = _http_post(self.cfg.OPENROUTER_ENDPOINT, payload)
            if result:
                return result
        log.warning("All provider tiers failed for prompt")
        return None

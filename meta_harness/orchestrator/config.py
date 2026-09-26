"""
config.py — Central configuration for the multi-agent SWE orchestration library.

Model Selection follows the specification's 3-tier cost-to-performance matrix:
  - Tier 0: Local Repomap & Hugging Face Serverless (BART Large MNLI)
  - Tier 1: Vertex AI (Gemini 2.0 Flash / Flash-Lite)
  - Tier 2: Google Antigravity CLI (Deep Reasoning & Antigravity Harness)
"""

# ---------------------------------------------------------------------------
# Agent Persona identifiers
# ---------------------------------------------------------------------------
PERSONAS = ["orchestrator", "planner", "coder", "tester", "reviewer", "debugger"]

# ---------------------------------------------------------------------------
# Model tiers mapped to Vertex AI (primary) model IDs
# Per spec §2 "Multi-Tier Agent Library Matrix"
# ---------------------------------------------------------------------------
MODELS: dict[str, str] = {
    # Vertex AI choices (primary — cost-optimised)
    "orchestrator": "gemini-2.0-flash-lite",       # High-freq JSON routing at $0.0375/1M
    "planner":      "gemini-2.5-flash",            # CoT DAG planning at $0.15/1M
    "coder":        "gemini-2.0-flash",            # Code synthesis & FIM
    "tester":       "gemini-2.0-flash",            # Verbose test suites
    "reviewer":     "gemini-2.5-flash",            # Deep review & security check
    "debugger":     "gemini-2.5-flash",            # Traceback & root cause analysis

    # Legacy two-tier aliases
    "flash": "gemini-2.0-flash",
    "pro":   "gemini-2.5-flash",
}

# Antigravity subscription-tier alternatives (used when BACKEND="antigravity")
MODELS_ANTIGRAVITY: dict[str, str] = {
    "orchestrator": "antigravity-default",
    "planner":      "gemini-2.5-pro",
    "coder":        "antigravity-default",
    "tester":       "antigravity-default",
    "reviewer":     "deepseek-r1",
    "debugger":     "deepseek-r1",
}

# ---------------------------------------------------------------------------
# Cost per 1 000 tokens (input / output) in USD — aligned with billing matrix
# ---------------------------------------------------------------------------
COST_PER_1K: dict[str, dict[str, float]] = {
    "orchestrator": {"input": 0.000_0375, "output": 0.000_150},
    "planner":      {"input": 0.000_1500, "output": 0.000_600},
    "coder":        {"input": 0.000_0750, "output": 0.000_300},
    "tester":       {"input": 0.000_0750, "output": 0.000_300},
    "reviewer":     {"input": 0.000_1500, "output": 0.000_600},
    "debugger":     {"input": 0.000_1500, "output": 0.000_600},

    # Legacy two-tier
    "flash": {"input": 0.000_0750, "output": 0.000_300},
    "pro":   {"input": 0.001_2500, "output": 0.005_000},
}

# ---------------------------------------------------------------------------
# Budget / quota guardrails
# ---------------------------------------------------------------------------
BUDGET: dict[str, float] = {
    "session_hard_stop_usd": 1.00,   # Abort whole session above this
    "session_warn_usd":      0.75,   # Log warning above this
    "task_hard_stop_usd":    0.25,   # Abort a single subtask above this
    "daily_quota_usd":       0.33,   # Hard daily Vertex AI spending ceiling
    "subtask_token_budget":  100_000,
}

# ---------------------------------------------------------------------------
# Execution / Loop-guard limits (spec §4 "Safety & Loop Guards")
# ---------------------------------------------------------------------------
MAX_REFINEMENT_ITERATIONS = 3    # Max Coder->Tester->Debugger->Coder repair loops
MAX_ESCALATION_RETRIES    = 3    # Times an agent may fail before Planner re-engages

# ---------------------------------------------------------------------------
# Task-complexity heuristics (used by legacy ModelRouter)
# ---------------------------------------------------------------------------
COMPLEXITY_THRESHOLDS: dict[str, object] = {
    "max_prompt_tokens_for_flash": 4_000,
    "reasoning_keywords": [
        "architect", "design", "refactor", "debug", "explain why",
        "root cause", "tradeoff", "compare", "optimize",
    ],
}

# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------
STATE_DIR  = ".orchestrator"
STATE_FILE = ".orchestrator/state.json"

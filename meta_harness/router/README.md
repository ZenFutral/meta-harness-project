# Router Module

Multi-tier request routing, zero-shot intent classification, and manifest generation for Meta-Harness and Repomap.

---

## Overview

The `router` package decouples intent parsing and model selection from agent execution. It provides a multi-tier routing architecture that classifies incoming user objectives into structured `RoutingManifest` instances, balancing cost, speed, and accuracy:

```
                         Incoming User Prompt
                                  │
                                  ▼
                ┌───────────────────────────────────┐
                │ Stage 1: Zero-Shot Classifier     │
                │ (BART Large MNLI / Rule Heuristic)│
                └─────────────────┬─────────────────┘
                                  │
                  ┌───────────────┴───────────────┐
                  ▼                               ▼
          Confidence >= 0.85              Confidence < 0.85
                  │                               │
                  ▼                               ▼
       Fast-Path Manifest            ┌───────────────────────────┐
       (repomap_summary / refactor)  │ Stage 2: Fallback Router  │
                                     │ (Gemini 2.0 / 2.5 Flash)  │
                                     └─────────────┬─────────────┘
                                                   │
                                                   ▼
                                       ┌───────────────────────┐
                                       │ Circuit Breaker Guard │
                                       │ (Daily $0.33 Cap)     │
                                       └───────────┬───────────┘
                                                   │
                                                   ▼
                                       Disambiguated Manifest
```

---

## Subsystems

1. **`ZeroShotIntentClassifier` (`zero_shot.py`)**:
   - Primary tier (Tier 0).
   - Queries Hugging Face Inference API (`facebook/bart-large-mnli`) or utilizes offline rule-based fallback heuristics.
   - Fast-paths high-confidence matches (>= 0.85) without incurring LLM charges.
2. **`FlashFallbackRouter` (`flash_fallback.py`)**:
   - Secondary tier (Tier 1).
   - Engages when Stage 1 confidence is below threshold or when deep prompt disambiguation is necessary.
   - Enforces the **$0.33/day circuit breaker** (`check_and_update_budget()`), tripping to deterministic local fallback if daily budget limit is breached.
3. **`RoutingManifest` (`manifest.py`)**:
   - Pydantic v2 (with dataclass fallback) schema standardizing routing parameters:
     - `intent`: `repomap_summary`, `symbol_trace`, `schema_registry`, `refactor_code`, or `dependency_check`.
     - `primary_target_symbols`: Target functions/classes to focus on.
     - `focus_files`: Priority file list for contextualization.
     - `repomap_token_budget`: Allocated tokens (512–8192).
     - `require_blast_radius`: Flag indicating dependency blast-radius calculation.
     - `execution_engine`: `antigravity_cli` or `repomap_only`.
4. **`ModelRouter` (`router.py`)**:
   - Maps persona roles (`orchestrator`, `planner`, `coder`, `tester`, `reviewer`, `debugger`) to exact model identifiers based on backend (`vertex` vs `antigravity`).
5. **`vendor_config.py`**:
   - Manages model vendor toggles (`huggingface`, `vertex`, `antigravity`) with configuration stored at `.agent/config/vendors.json`.

---

## Usage

### Generating a Routing Manifest

```python
from router.zero_shot import ZeroShotIntentClassifier
from router.flash_fallback import FlashFallbackRouter

prompt = "Refactor database schema for user profiles"

# 1. Fast-path triage
classifier = ZeroShotIntentClassifier()
manifest = classifier.route_fast_path(prompt)

if not manifest:
    # 2. Stage 2 fallback
    fallback_router = FlashFallbackRouter()
    manifest = fallback_router.route_fallback(prompt)

print(f"Routed intent: {manifest.intent}")
print(f"Token budget: {manifest.repomap_token_budget}")
```

### Model Selection by Persona

```python
from router.router import ModelRouter

router = ModelRouter(backend="vertex")
coder_model = router.model_id_for_persona("coder")       # gemini-2.0-flash
planner_model = router.model_id_for_persona("planner")   # gemini-2.5-flash
```

---

## Testing

Run unit tests for the router package:

```bash
pytest meta-harness/router/tests/test_phase7.py
```

"""Persona scoring and precedence rules for deterministic routing.

This module defines static scoring matrices that map high‑level task goals to the
six software‑engineering personas used throughout the harness:
    Planner, Coder, Tester, Reviewer, Debugger, Orchestrator.
The ``get_persona_for_goal`` helper applies a simple precedence order based on
action verbs found in the task description.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

# Scoring matrix: persona -> list of associated keywords (lower‑case)
PERSONA_KEYWORDS: Dict[str, List[str]] = {
    "Planner": ["plan", "design", "architecture", "roadmap", "spec"],
    "Coder": ["implement", "code", "write", "develop", "feature"],
    "Tester": ["test", "verify", "validate", "coverage", "unit test"],
    "Reviewer": ["review", "audit", "critique", "feedback"],
    "Debugger": ["debug", "diagnose", "trace", "stacktrace", "bug"],
    "Orchestrator": ["orchestrate", "coordinate", "pipeline", "workflow", "manage"],
}

# Action‑verb precedence: first match wins
VERB_PRECEDENCE: List[Tuple[str, str]] = [
    ("test", "Tester"),
    ("diagnose", "Debugger"),
    ("debug", "Debugger"),
    ("review", "Reviewer"),
    ("plan", "Planner"),
    ("design", "Planner"),
    ("implement", "Coder"),
    ("code", "Coder"),
    ("orchestrate", "Orchestrator"),
]

def get_persona_for_goal(goal: str) -> str:
    """Return the most appropriate persona for a free‑form *goal* string.

    The function first applies the verb precedence list; if no verb matches, it
    falls back to a keyword‑frequency scoring using ``PERSONA_KEYWORDS``.
    """
    lower = goal.lower()
    for verb, persona in VERB_PRECEDENCE:
        if re.search(r"\\b" + re.escape(verb) + r"\\b", lower):
            return persona
    # Frequency‑based fallback
    scores: Dict[str, int] = {p: 0 for p in PERSONA_KEYWORDS}
    for persona, keywords in PERSONA_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                scores[persona] += 1
    # Choose persona with highest score, deterministic tie‑break by order in dict
    best = max(scores.items(), key=lambda item: (item[1], list(PERSONA_KEYWORDS).index(item[0])))
    return best[0]

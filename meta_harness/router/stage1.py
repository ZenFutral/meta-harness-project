import re
import logging
from typing import List, Dict, Optional

log = logging.getLogger(__name__)

# Keyword patterns for each intent
INTENT_PATTERNS: Dict[str, List[str]] = {
    "refactor_code": [r"\\brefactor\\b", r"\\brename\\b", r"\\brewrite\\b", r"\\boptimize\\b"],
    "dependency_check": [r"\\bdependency\\b", r"\\brequirements\\b", r"\\binstall\\b", r"\\bpackage\\b"],
    "schema_registry": [r"\\bschema\\b", r"\\bmodel\\b", r"\\borm\\b", r"\\bproto\\b"],
    "repomap_summary": [r"\\bsummary\\b", r"\\boverview\\b", r"\\bstructure\\b", r"\\bskeleton\\b"],
    "symbol_trace": [r"\\bsymbol\\b", r"\\btrace\\b", r"\\bcallgraph\\b"],
}

DEFAULT_INTENT = "repomap_summary"


class DeterministicIntentRouter:
    """Stage‑1 deterministic intent router.

    Uses only the Python standard library (regular expressions) to map a free‑form
    prompt to one of the supported Repomap intents defined in ``INTENT_PATTERNS``.
    The router scans intents in the order they appear in the dictionary and
    returns the first matching intent. If nothing matches, ``DEFAULT_INTENT`` is
    returned.
    """

    def __init__(self, intent_patterns: Optional[Dict[str, List[str]]] = None):
        self.intent_patterns = intent_patterns or INTENT_PATTERNS
        # Pre‑compile regexes for efficiency
        self._compiled: Dict[str, List[re.Pattern]] = {
            intent: [re.compile(p, re.IGNORECASE) for p in patterns]
            for intent, patterns in self.intent_patterns.items()
        }
        log.debug("DeterministicIntentRouter initialised with intents: %s", list(self._compiled.keys()))

    def route(self, prompt: str) -> str:
        """Return the best‑fit intent for *prompt*.

        The method iterates over intents deterministically. As soon as a pattern
        matches, the associated intent is returned.
        """
        if not isinstance(prompt, str):
            raise TypeError("prompt must be a string")
        for intent, regexes in self._compiled.items():
            for regex in regexes:
                if regex.search(prompt):
                    log.info("DeterministicIntentRouter matched intent %s for prompt %r", intent, prompt)
                    return intent
        log.info("DeterministicIntentRouter fell back to default intent %s for prompt %r", DEFAULT_INTENT, prompt)
        return DEFAULT_INTENT

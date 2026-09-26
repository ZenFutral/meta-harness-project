import sys
import json
import unittest
import tempfile
from pathlib import Path

META_HARNESS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = META_HARNESS_DIR.parent
AGENT_DIR = REPO_ROOT / ".agent"

for path in [str(META_HARNESS_DIR), str(REPO_ROOT), str(AGENT_DIR)]:
    if path not in sys.path:
        sys.path.insert(0, path)

from router.zero_shot import ZeroShotIntentClassifier
from contextualize.src.engine import Engine as ContextEngine
from orchestrator.orchestrator import Orchestrator
from orchestrator.budget import check_and_update_budget, get_quota_file_path


class TestEndToEndPipeline(unittest.TestCase):

    def test_e2e_refactor_schema_query(self):
        user_query = "Refactor database schema for user profiles"

        # 1. Intent Classification & Routing Manifest Generation
        classifier = ZeroShotIntentClassifier()
        manifest = classifier.route_fast_path(user_query)
        self.assertIsNotNone(manifest)
        self.assertEqual(manifest.intent, "schema_registry")
        self.assertGreaterEqual(manifest.repomap_token_budget, 512)

        # 2. Contextualizer Integration
        config = {
            "sources": {
                "system": {"enabled": False},
                "git": {"enabled": False},
                "filesystem": {"enabled": False},
                "repomap": {"enabled": True, "budget_tokens": manifest.repomap_token_budget}
            },
            "token_budget": {
                "max_tokens": 8000,
                "reserved_completion_tokens": 1000
            },
            "paths": {
                "output_bundle": "./output/test_e2e_bundle.json",
                "metrics_file": "./test_e2e_metrics.json",
                "log_file": "./test_e2e_log.json"
            }
        }
        context_engine = ContextEngine(config)
        context_bundle = context_engine.run(dry_run=True)
        self.assertIn("repomap", context_bundle)
        self.assertIn("markdown_context", context_bundle)

        # 3. Quota & Budget Enforcement
        allowed = check_and_update_budget(input_tokens=100)
        self.assertTrue(allowed, "Budget check should pass for standard execution")

        quota_file = get_quota_file_path()
        self.assertTrue(quota_file.exists(), "Quota file should exist and record spend")

        # 4. Orchestrator Dispatch
        orch = Orchestrator()
        self.assertIsNotNone(orch)
        self.assertIsNotNone(orch.router)


if __name__ == "__main__":
    unittest.main()

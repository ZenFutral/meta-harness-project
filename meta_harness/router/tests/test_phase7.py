import sys
import unittest
import tempfile
from pathlib import Path

META_HARNESS_DIR = Path(__file__).resolve().parents[2]
if str(META_HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(META_HARNESS_DIR))

from router.manifest import RoutingManifest
from router.router import ModelRouter
from router.zero_shot import ZeroShotIntentClassifier
from router.flash_fallback import FlashFallbackRouter
import orchestrator.budget as budget_mod


class Phase7Tests(unittest.TestCase):
    def test_step_7_1_routing_manifest_validation(self):
        manifest = RoutingManifest(
            intent="repomap_summary",
            primary_target_symbols=["main.py::global::run::function"],
            focus_files=["main.py"],
            repomap_token_budget=2048,
            require_blast_radius=False,
            execution_engine="repomap_only",
            task_instructions="Generate summary",
        )
        self.assertEqual(manifest.intent, "repomap_summary")
        self.assertEqual(manifest.repomap_token_budget, 2048)

        # Invalid budget < 512 raises ValueError
        with self.assertRaises((ValueError, Exception)):
            RoutingManifest(
                intent="repomap_summary",
                repomap_token_budget=100,  # ge=512 constraint
                execution_engine="repomap_only",
                task_instructions="Invalid budget",
            )

    def test_step_7_2_router_migration_and_decoupling(self):
        router = ModelRouter(backend="vertex")
        self.assertEqual(router.model_id_for_persona("coder"), "gemini-2.0-flash")

        # Test import from legacy orchestrator location re-export
        from orchestrator.router import ModelRouter as LegacyRouter
        leg_router = LegacyRouter()
        self.assertEqual(leg_router.model_id_for_persona("coder"), "gemini-2.0-flash")

    def test_step_7_3_zero_shot_fast_path(self):
        classifier = ZeroShotIntentClassifier()
        # Rule fallback test
        res = classifier.classify("Show me the ORM schema registry models")
        self.assertIsNotNone(res)
        label, score = res
        self.assertEqual(label, "schema_inspection")
        self.assertGreaterEqual(score, 0.85)

        manifest = classifier.route_fast_path("Show me the ORM schema registry models")
        self.assertIsNotNone(manifest)
        self.assertEqual(manifest.intent, "schema_registry")

    def test_step_7_4_flash_fallback_and_budget_trip(self):
        fallback = FlashFallbackRouter()
        manifest = fallback.route_fallback("Trace blast radius for function foo")
        self.assertEqual(manifest.intent, "symbol_trace")
        self.assertTrue(manifest.require_blast_radius)

        # Simulate budget trip
        tmp_dir = tempfile.TemporaryDirectory()
        quota_file = Path(tmp_dir.name) / "quota.json"
        quota_file.write_text('{"date": "2026-09-25", "tokens": 10000000, "cost": 0.50}')
        orig_quota = budget_mod.QUOTA_FILE
        budget_mod.QUOTA_FILE = quota_file

        try:
            tripped_manifest = fallback.route_fallback("Any prompt")
            self.assertIn("Fallback due to daily budget ceiling trip", tripped_manifest.task_instructions)
        finally:
            budget_mod.QUOTA_FILE = orig_quota
            tmp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()

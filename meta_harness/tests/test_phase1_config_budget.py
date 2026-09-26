"""
Unit tests for Phase 1: Unified Provider/Model Configuration and Concurrent Quota Engine.
"""
import sys
import json
import unittest
import tempfile
from pathlib import Path

META_HARNESS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = META_HARNESS_DIR.parent
if str(META_HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(META_HARNESS_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import router.vendor_config as vc
import orchestrator.budget as budget_mod


class TestPhase1ConfigAndBudget(unittest.TestCase):
    def setUp(self):
        # Save original paths and active settings
        self.orig_active = vc.get_active_vendor_models()
        self.orig_backend = vc.get_active_backend()
        self.orig_quota_file = budget_mod.QUOTA_FILE

    def tearDown(self):
        # Restore original state
        vc.set_active_vendor_models(self.orig_active)
        vc.set_active_backend(self.orig_backend)
        budget_mod.QUOTA_FILE = self.orig_quota_file

    def test_user_config_loading_and_structure(self):
        cfg = vc.load_user_config()
        self.assertIn("active_vendor_models", cfg)
        self.assertIn("antigravity", cfg)
        self.assertIn("openai", cfg)
        self.assertIn("models", cfg["antigravity"])
        self.assertIn("models", cfg["openai"])

        # Check antigravity gemini-3-pro-preview specs
        model_spec = cfg["antigravity"]["models"]["gemini-3-pro-preview"]
        self.assertEqual(model_spec["daily_quota"], 1000)
        self.assertEqual(model_spec["max_output_tokens"], 100000)
        self.assertEqual(model_spec["max_thinking_tokens"], 10000)
        self.assertEqual(model_spec["rate_limit"], 100)

    def test_wildcard_and_specific_model_matching(self):
        # Test exact model vs wildcard
        vc.set_active_vendor_models(["antigravity/gemini-3-pro-preview", "openai"])

        # 1. Exact model match
        self.assertTrue(vc.is_model_active("antigravity/gemini-3-pro-preview"))
        self.assertTrue(vc.is_model_active("antigravity", "gemini-3-pro-preview"))

        # 2. Antigravity model not in active list
        self.assertFalse(vc.is_model_active("antigravity/unregistered-model"))

        # 3. Whole vendor wildcard (openai)
        self.assertTrue(vc.is_model_active("openai"))
        self.assertTrue(vc.is_model_active("openai/gpt-5.1"))
        self.assertTrue(vc.is_model_active("openai", "gpt-4o"))

        # 4. Vendor level queries
        self.assertTrue(vc.is_model_active("antigravity"))

    def test_get_model_spec(self):
        spec = vc.get_model_spec("antigravity/gemini-3-pro-preview")
        self.assertEqual(spec["daily_quota"], 1000)
        self.assertEqual(spec["rate_limit"], 100)

        spec_openai = vc.get_model_spec("openai", "gpt-5.1")
        self.assertEqual(spec_openai["daily_quota"], 1000)

    def test_concurrent_daily_ceiling_calculation(self):
        vc.set_active_vendor_models(["antigravity/gemini-3-pro-preview", "openai"])
        ceiling = budget_mod.calculate_concurrent_daily_ceiling()

        self.assertGreater(ceiling["aggregate_daily_quota"], 0)
        self.assertGreaterEqual(ceiling["aggregate_daily_cost_cap"], 0.33)
        self.assertIn("antigravity/gemini-3-pro-preview", ceiling["model_ceilings"])
        self.assertIn("openai/gpt-5.1", ceiling["model_ceilings"])

    def test_check_and_update_budget_per_model_tracking(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_quota = Path(tmpdir) / "quota.json"
            budget_mod.QUOTA_FILE = tmp_quota

            # Call with model identifier
            allowed = budget_mod.check_and_update_budget(
                input_tokens=150,
                model="antigravity/gemini-3-pro-preview"
            )
            self.assertTrue(allowed)
            self.assertTrue(tmp_quota.exists())

            state = budget_mod.get_quota_state()
            self.assertEqual(state["tokens"], 150)
            self.assertIn("models", state)
            self.assertIn("antigravity/gemini-3-pro-preview", state["models"])
            m_info = state["models"]["antigravity/gemini-3-pro-preview"]
            self.assertEqual(m_info["tokens"], 150)
            self.assertEqual(m_info["calls"], 1)

            # Test flexible positional call (persona/model, in_tok, out_tok)
            allowed_pos = budget_mod.check_and_update_budget("openai/gpt-5.1", 100, 50)
            self.assertTrue(allowed_pos)

            state2 = budget_mod.get_quota_state()
            self.assertIn("openai/gpt-5.1", state2["models"])
            self.assertEqual(state2["models"]["openai/gpt-5.1"]["tokens"], 150)

    def test_model_quota_status_helper(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_quota = Path(tmpdir) / "quota.json"
            budget_mod.QUOTA_FILE = tmp_quota

            budget_mod.check_and_update_budget(100, model="antigravity/gemini-3-pro-preview")
            status = budget_mod.get_model_quota_status("gemini-3-pro-preview")
            self.assertEqual(status["tokens"], 100)
            self.assertEqual(status["calls"], 1)
            self.assertFalse(status["tripped"])

    def test_rate_limit_checker(self):
        test_model = "test-provider/test-model"
        # Reset tracker for test model
        budget_mod._RATE_LIMIT_TIMESTAMPS[test_model] = []

        self.assertTrue(budget_mod.check_rate_limit(test_model, max_requests_per_minute=2))
        self.assertTrue(budget_mod.check_rate_limit(test_model, max_requests_per_minute=2))
        # 3rd request within 60s exceeds 2 req/min
        self.assertFalse(budget_mod.check_rate_limit(test_model, max_requests_per_minute=2))

    def test_set_active_backend_sync(self):
        res = vc.set_active_backend("openai/gpt-5.1")
        self.assertEqual(vc.get_active_backend(), "openai/gpt-5.1")
        self.assertIn("openai/gpt-5.1", vc.get_active_vendor_models())


if __name__ == "__main__":
    unittest.main()

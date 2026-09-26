import sys
import unittest
import tempfile
from pathlib import Path

META_HARNESS_DIR = Path(__file__).resolve().parents[2]
if str(META_HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(META_HARNESS_DIR))

import orchestrator.config as config
from orchestrator.orchestrator import Orchestrator
from router.router import ModelRouter
import orchestrator.budget as budget_mod


class Phase8Tests(unittest.TestCase):
    def test_step_8_1_config_model_matrix_alignment(self):
        # Verify aligned models in config.py
        self.assertEqual(config.MODELS["orchestrator"], "gemini-2.0-flash-lite")
        self.assertEqual(config.MODELS["planner"], "gemini-2.5-flash")
        self.assertEqual(config.MODELS["coder"], "gemini-2.0-flash")

        # Verify antigravity models do not use invalid identifiers like gemini-3.8-flash
        self.assertEqual(config.MODELS_ANTIGRAVITY["orchestrator"], "antigravity-default")

    def test_step_8_2_orchestrator_router_decoupling(self):
        router = ModelRouter(backend="vertex")
        self.assertEqual(router.model_id_for_persona("orchestrator"), "gemini-2.0-flash-lite")

    def test_step_8_3_llm_call_daily_quota_circuit_breaker(self):
        import time
        today = time.strftime("%Y-%m-%d")
        tmp_dir = tempfile.TemporaryDirectory()
        quota_file = Path(tmp_dir.name) / "quota.json"
        # Set cost above $0.33/day cap
        quota_file.write_text(f'{{"date": "{today}", "tokens": 10000000, "cost": 0.50}}')

        orig_quota = budget_mod.QUOTA_FILE
        budget_mod.QUOTA_FILE = quota_file

        try:
            orch = Orchestrator.__new__(Orchestrator)
            orch.router = ModelRouter()
            orch._persona_model_map = {p: orch.router.model_id_for_persona(p) for p in config.PERSONAS}

            resp = orch._llm_call("coder", "system prompt", "user prompt")
            self.assertIn("[LOCAL_FALLBACK]", resp)
            self.assertIn("Daily budget cap ($0.33) reached", resp)
        finally:
            budget_mod.QUOTA_FILE = orig_quota
            tmp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()

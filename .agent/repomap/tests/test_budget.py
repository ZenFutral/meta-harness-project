import sys
import unittest
import tempfile
import json
from pathlib import Path

META_HARNESS_DIR = Path(__file__).resolve().parents[3] / "meta-harness"
if str(META_HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(META_HARNESS_DIR))

import orchestrator.budget as budget_mod
from orchestrator.budget import check_and_update_budget, get_quota_state, DAILY_COST_CAP, INPUT_COST_PER_M


class BudgetQuotaTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.quota_file = Path(self.tmp_dir.name) / "quota.json"
        
        self.orig_quota_file = budget_mod.QUOTA_FILE
        budget_mod.QUOTA_FILE = self.quota_file

    def tearDown(self):
        budget_mod.QUOTA_FILE = self.orig_quota_file
        self.tmp_dir.cleanup()

    def test_quota_accumulation_and_circuit_breaker(self):
        # Under cap call (e.g. 100k tokens = $0.0075)
        res = check_and_update_budget(100_000)
        self.assertTrue(res)
        
        state = get_quota_state()
        self.assertEqual(state["tokens"], 100_000)
        self.assertAlmostEqual(state["cost"], 0.0075, places=5)

        # Exceed cap (e.g. 5M tokens = $0.375 + $0.0075 > $0.33)
        res_exceeded = check_and_update_budget(5_000_000)
        self.assertFalse(res_exceeded)

    def test_day_rollover_resets_quota(self):
        # Write an expired quota entry for yesterday
        yesterday_state = {"date": "2020-01-01", "tokens": 1000000, "cost": 0.50}
        self.quota_file.parent.mkdir(parents=True, exist_ok=True)
        self.quota_file.write_text(json.dumps(yesterday_state))

        # Check budget for 100k tokens today -> should reset and succeed
        res = check_and_update_budget(100_000)
        self.assertTrue(res)
        state = get_quota_state()
        self.assertEqual(state["tokens"], 100_000)


if __name__ == "__main__":
    unittest.main()

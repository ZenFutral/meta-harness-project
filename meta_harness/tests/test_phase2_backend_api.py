"""
Unit and integration tests for Phase 2: Backend Services, Cache Operations,
Codebase Token Telemetry, and Agent Network Management APIs.
"""
import sys
import json
import time
import threading
import urllib.request
import urllib.error
import unittest
from pathlib import Path

META_HARNESS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = META_HARNESS_DIR.parent
if str(META_HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(META_HARNESS_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from meta_harness.gui.cache_ops import (
    clear_cache,
    regen_cache,
    rebuild_graph_cache,
    get_cache_access_metrics,
    get_cached_files_catalog,
    get_cached_file_details
)
from meta_harness.gui.agents_network import (
    get_agent_network_topology,
    update_agent_state
)
from meta_harness.gui.telemetry import (
    get_codebase_token_telemetry,
    get_cache_telemetry,
    get_telemetry_snapshot
)
from meta_harness.gui.server import create_server


class TestPhase2BackendServices(unittest.TestCase):
    def test_codebase_token_telemetry(self):
        metrics = get_codebase_token_telemetry()
        self.assertIn("root_directory_name", metrics)
        self.assertIn("workspace_folder_name", metrics)
        self.assertIn("total_files", metrics)
        self.assertIn("total_tokens", metrics)
        self.assertIn("token_packing_efficiency_pct", metrics)

        self.assertGreater(metrics["total_files"], 0)
        self.assertGreater(metrics["total_tokens"], 0)
        self.assertGreaterEqual(metrics["token_packing_efficiency_pct"], 0.0)

    def test_cache_operations(self):
        # 1. Access metrics
        acc = get_cache_access_metrics()
        self.assertIn("access_count", acc)
        self.assertIn("hit_rate_pct", acc)

        # 2. Regen cache
        regen_res = regen_cache()
        self.assertTrue(regen_res["success"])
        self.assertIn("indexed_files", regen_res)

        # 3. Rebuild graph cache
        graph_res = rebuild_graph_cache()
        self.assertTrue(graph_res["success"])
        self.assertIn("macro_nodes", graph_res)
        self.assertIn("micro_nodes", graph_res)

        # 4. Catalog inspection
        catalog = get_cached_files_catalog(limit=10)
        self.assertIsInstance(catalog, list)

        # 5. Clear cache
        clear_res = clear_cache()
        self.assertTrue(clear_res["success"])

        # Re-index to leave clean state
        regen_cache()

    def test_agent_network_topology(self):
        topo = get_agent_network_topology()
        self.assertTrue(topo["success"])
        self.assertEqual(topo["total_agent_count"], 6)

        node_ids = {n["id"] for n in topo["nodes"]}
        expected_workers = {"orchestrator", "planner", "coder", "tester", "reviewer", "debugger"}
        self.assertEqual(node_ids, expected_workers)
        # Verify router agent is excluded
        self.assertNotIn("router", node_ids)

        # Check edge structure
        self.assertGreater(len(topo["edges"]), 0)
        for e in topo["edges"]:
            self.assertIn("source", e)
            self.assertIn("target", e)
            self.assertIn("flow_type", e)

        # Check unified event log
        self.assertIsInstance(topo["unified_event_log"], list)
        self.assertGreater(len(topo["unified_event_log"]), 0)

    def test_agent_state_mutation(self):
        # 1. Set model
        res_model = update_agent_state("coder", "set_model", model="antigravity/gemini-3-pro-preview")
        self.assertTrue(res_model["success"])
        self.assertEqual(res_model["agent"]["model"], "antigravity/gemini-3-pro-preview")

        # 2. Edit task
        res_task = update_agent_state("coder", "edit_task", task="Synthesize AST repair for tests")
        self.assertTrue(res_task["success"])
        self.assertEqual(res_task["agent"]["current_task"], "Synthesize AST repair for tests")

        # 3. Rerun
        res_rerun = update_agent_state("tester", "rerun")
        self.assertTrue(res_rerun["success"])

        # 4. Cancel
        res_cancel = update_agent_state("planner", "cancel")
        self.assertTrue(res_cancel["success"])
        self.assertEqual(res_cancel["agent"]["status"], "STANDBY")

        # Verify mutation was recorded in unified event log
        topo = get_agent_network_topology()
        recent_msgs = [evt["message"] for evt in topo["unified_event_log"]]
        self.assertTrue(any("antigravity/gemini-3-pro-preview" in m for m in recent_msgs))

    def test_telemetry_snapshot_enrichment(self):
        snapshot = get_telemetry_snapshot()
        snap_dict = snapshot.to_dict()
        self.assertIn("codebase", snap_dict)
        self.assertIn("agent_network", snap_dict)
        self.assertIn("cache", snap_dict)
        self.assertIn("access_count", snap_dict["cache"])


class TestPhase2ServerEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start server on dynamic port
        cls.server = create_server("127.0.0.1", 8089)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.base_url = "http://127.0.0.1:8089"
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _get(self, path: str) -> dict:
        req = urllib.request.Request(f"{self.base_url}{path}")
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            self.assertEqual(resp.status, 200)
            return json.loads(resp.read().decode("utf-8"))

    def _post(self, path: str, payload: dict) -> dict:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            self.assertEqual(resp.status, 200)
            return json.loads(resp.read().decode("utf-8"))

    def test_get_codebase_endpoint(self):
        data = self._get("/api/codebase")
        self.assertIn("total_files", data)
        self.assertIn("total_tokens", data)

    def test_get_cache_endpoints(self):
        metrics = self._get("/api/cache/metrics")
        self.assertIn("access_count", metrics)

        files = self._get("/api/cache/files")
        self.assertIn("files", files)

    def test_get_agents_network_endpoint(self):
        data = self._get("/api/agents/network")
        self.assertTrue(data["success"])
        self.assertEqual(len(data["nodes"]), 6)
        self.assertIn("unified_event_log", data)

    def test_post_cache_actions(self):
        regen = self._post("/api/cache/regen", {})
        self.assertTrue(regen["success"])

        graph = self._post("/api/cache/graph-rebuild", {})
        self.assertTrue(graph["success"])

        clear = self._post("/api/cache/clear", {})
        self.assertTrue(clear["success"])

        # Restore cache
        self._post("/api/cache/regen", {})

    def test_post_automated_fix_and_test(self):
        # Automated test fix
        test_fix = self._post("/api/tests/fix", {})
        self.assertTrue(test_fix["success"])
        self.assertEqual(test_fix["status"], "REPAIRED")

        # Feature fix
        feat_fix = self._post("/api/features/fix", {"feature_id": "ORCH-01"})
        self.assertTrue(feat_fix["success"])
        self.assertEqual(feat_fix["feature_id"], "ORCH-01")

        # Feature test generation
        feat_test = self._post("/api/features/test", {"feature_id": "ROUT-01"})
        self.assertTrue(feat_test["success"])
        self.assertEqual(feat_test["feature_id"], "ROUT-01")

    def test_post_agent_update(self):
        update_res = self._post("/api/agents/update", {
            "agent_id": "tester",
            "action": "set_model",
            "model": "antigravity/gemini-3-pro-preview"
        })
        self.assertTrue(update_res["success"])
        self.assertEqual(update_res["agent"]["model"], "antigravity/gemini-3-pro-preview")


if __name__ == "__main__":
    unittest.main()

import sys
import json
import unittest
import tempfile
import subprocess
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from repomap.server import RepomapJSONRPCServer
from repomap.cli import main as cli_main


class Phase6Tests(unittest.TestCase):
    def test_step_6_1_repomap_tools_json_schema(self):
        tools_path = AGENT_DIR / "tools" / "repomap_tools.json"
        self.assertTrue(tools_path.exists(), "repomap_tools.json missing")

        data = json.loads(tools_path.read_text(encoding="utf-8"))
        self.assertIn("tools", data)
        tools = data["tools"]
        expected_tools = ["repo_map_summary", "get_symbol_hierarchy", "get_schema_registry", "resolve_imports"]
        for t in expected_tools:
            self.assertIn(t, tools, f"Tool spec {t} missing")

    def test_step_6_2_json_rpc_server_dispatch(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        repo_root = Path(self.tmp_dir.name)

        # Create sample file for indexing
        app_file = repo_root / "app.py"
        app_file.write_text("def run():\n    pass\n")

        server = RepomapJSONRPCServer(repo_root)

        # Test repo_map_summary RPC call
        req_summary = json.dumps({
            "jsonrpc": "2.0",
            "method": "repo_map_summary",
            "params": {"budget_tokens": 512},
            "id": 1
        })
        resp_raw = server.dispatch(req_summary)
        resp = json.loads(resp_raw)
        self.assertEqual(resp["jsonrpc"], "2.0")
        self.assertEqual(resp["id"], 1)
        self.assertIn("result", resp)
        self.assertIn("summary", resp["result"])

        # Test resolve_imports RPC call
        req_imports = json.dumps({
            "jsonrpc": "2.0",
            "method": "resolve_imports",
            "params": {"source_file": "app.py", "target_file": "utils.py"},
            "id": 2
        })
        resp_imports = json.loads(server.dispatch(req_imports))
        self.assertEqual(resp_imports["id"], 2)

        # Test invalid method RPC error
        req_invalid = json.dumps({
            "jsonrpc": "2.0",
            "method": "invalid_method",
            "params": {},
            "id": 3
        })
        resp_invalid = json.loads(server.dispatch(req_invalid))
        self.assertIn("error", resp_invalid)

        self.tmp_dir.cleanup()

    def test_step_6_3_cli_executable_launcher(self):
        launcher = AGENT_DIR / "bin" / "repomap"
        self.assertTrue(launcher.exists(), ".agent/bin/repomap missing")

        res = subprocess.run(
            [sys.executable, str(launcher), "summary", "--budget", "1024"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 0)


if __name__ == "__main__":
    unittest.main()

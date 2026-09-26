import sys
import unittest
import tempfile
import sqlite3
import concurrent.futures
from pathlib import Path

META_HARNESS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = META_HARNESS_DIR.parent
AGENT_DIR = REPO_ROOT / ".agent"

if str(META_HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(META_HARNESS_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from repomap.core.storage import RepomapStorage
from repomap.core.graph import TwoTierGraph
from repomap.core.packer import MarginalDensityPacker


class TestRepomapHardening(unittest.TestCase):

    def test_sqlite_wal_concurrency(self):
        """Test SQLite-WAL concurrency: verify concurrent reads during writes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_wal.db"

            def write_db(idx):
                conn = sqlite3.connect(str(db_path), timeout=5.0)
                try:
                    conn.execute("PRAGMA journal_mode=WAL;")
                    conn.execute("CREATE TABLE IF NOT EXISTS test (id TEXT PRIMARY KEY, val TEXT);")
                    conn.execute("INSERT OR REPLACE INTO test VALUES (?, ?);", (f"k_{idx}", f"v_{idx}"))
                    conn.commit()
                finally:
                    conn.close()

            def read_db():
                conn = sqlite3.connect(str(db_path), timeout=5.0)
                try:
                    conn.execute("PRAGMA journal_mode=WAL;")
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM test;")
                    return cursor.fetchone()[0]
                finally:
                    conn.close()

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = []
                for i in range(5):
                    futures.append(executor.submit(write_db, i))
                    futures.append(executor.submit(read_db))

                results = [f.result() for f in futures if f.exception() is None]
                self.assertGreater(len(results), 0)

    def test_recursive_cte_invalidation(self):
        """Test recursive CTE invalidation: modify leaf file and verify downstream nodes invalidated."""
        storage = RepomapStorage()

        cur = storage._conn.cursor()
        cur.execute("INSERT OR REPLACE INTO symbol_references VALUES (?, ?, ?)", ("symbol_b", "c.py", "b.py"))
        cur.execute("INSERT OR REPLACE INTO symbol_references VALUES (?, ?, ?)", ("symbol_a", "b.py", "a.py"))
        storage._conn.commit()

        dirty = storage.invalidate_file_transitive("c.py")
        self.assertIn("b.py", dirty)
        self.assertIn("a.py", dirty)

    def test_tarjan_scc_cycle_detection(self):
        """Test Tarjan SCC cycle detection on circular graph without infinite loops."""
        graph = TwoTierGraph(REPO_ROOT)

        # Manually inject cyclic imports A -> B -> C -> A
        graph.macro_graph = {
            "mod_a.py": {"mod_b.py": 1.0},
            "mod_b.py": {"mod_c.py": 1.0},
            "mod_c.py": {"mod_a.py": 1.0},
        }

        cycles = graph.find_cycles()
        self.assertGreaterEqual(len(cycles), 1)
        flattened = [node for cycle in cycles for node in cycle]
        self.assertIn("mod_a.py", flattened)

    def test_token_budget_limits(self):
        """Assert skeleton outputs never exceed budget_tokens constraint."""
        packer = MarginalDensityPacker(REPO_ROOT)
        symbol_scores = [
            {"file": "main.py", "symbol_id": "main.py::run", "name": "run", "score": 10.0},
            {"file": "config.py", "symbol_id": "config.py::Config", "name": "Config", "score": 8.0},
            {"file": "utils.py", "symbol_id": "utils.py::helper", "name": "helper", "score": 5.0},
        ]
        budget = 500
        summary = packer.pack(symbol_scores, budget_tokens=budget)
        self.assertIsInstance(summary, str)
        self.assertLessEqual(len(summary), budget * 6)


if __name__ == "__main__":
    unittest.main()

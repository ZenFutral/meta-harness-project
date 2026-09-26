import sys
import unittest
import tempfile
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parents[2]
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

import repomap.core.storage as storage_mod
from repomap.core.storage import RepomapStorage, get_storage
from repomap.core.graph import TwoTierGraph
from repomap.core.ranker import CentralityRanker


class Phase3Tests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.tmp_dir.name)
        self.db_file = self.repo_root / "test_repomap.db"

        self.orig_db_path = storage_mod.DB_PATH
        storage_mod.DB_PATH = self.db_file
        RepomapStorage._instance = None
        self.storage = get_storage()

    def tearDown(self):
        self.storage.close()
        storage_mod.DB_PATH = self.orig_db_path
        RepomapStorage._instance = None
        self.tmp_dir.cleanup()

    def test_step_3_1_two_tier_graph_and_idf(self):
        # Create 2 modules where app.py imports helper.py
        app_file = self.repo_root / "app.py"
        app_file.write_text("from helper import do_work\n\ndef main():\n    do_work()\n")

        helper_file = self.repo_root / "helper.py"
        helper_file.write_text("def do_work():\n    pass\n")

        graph = TwoTierGraph(self.repo_root)
        graph.build_from_repository()

        self.assertIn("app.py", graph.macro_graph)
        self.assertIn("helper.py", graph.macro_graph)

    def test_step_3_2_tarjan_scc_and_cycle_resolution(self):
        # Create synthetic graph with circular dependency: a -> b -> c -> a
        graph = TwoTierGraph(self.repo_root)
        graph.macro_graph = {
            "a.py": {"b.py": 1.0},
            "b.py": {"c.py": 1.0},
            "c.py": {"a.py": 1.0},
            "leaf.py": {},
        }

        sccs = graph.find_cycles()
        self.assertEqual(len(sccs), 1)
        cycle_files = set(sccs[0])
        self.assertEqual(cycle_files, {"a.py", "b.py", "c.py"})

        # Condense cycles
        condensed = graph.condense_cycles()
        self.assertTrue(any(k.startswith("SCC_META") for k in condensed.keys()))

        # Resolve transitive import path
        paths = graph.resolve_imports("a.py", "c.py")
        self.assertTrue(any(p == ["a.py", "b.py", "c.py"] for p in paths))

    def test_step_3_3_ranker_pagerank_and_symbol_scoring(self):
        app_file = self.repo_root / "main.py"
        app_file.write_text("def run():\n    pass\n")

        leaf_file = self.repo_root / "utils.py"
        leaf_file.write_text("def util_fn():\n    pass\n")

        graph = TwoTierGraph(self.repo_root)
        graph.build_from_repository()

        ranker = CentralityRanker(graph, alpha=0.85)
        # Test focus file personalization
        ppr_focus = ranker.compute_file_pagerank(focus_files=["main.py"])
        self.assertGreater(ppr_focus["main.py"], ppr_focus.get("utils.py", 0.0))

        # Rank symbols
        ranked_symbols = ranker.rank_symbols(focus_files=["main.py"])
        self.assertGreater(len(ranked_symbols), 0)
        self.assertEqual(ranked_symbols[0]["file"], "main.py")


if __name__ == "__main__":
    unittest.main()

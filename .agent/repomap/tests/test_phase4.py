import ast
import sys
import unittest
import tempfile
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parents[2]
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from repomap.core.skeleton import Skeletonizer
from repomap.core.packer import MarginalDensityPacker, estimate_tokens


class Phase4Tests(unittest.TestCase):
    def test_step_4_1_skeletonizer_signatures_and_docstring_pruning(self):
        sample_code = '''
class ComplexService(BaseService):
    """
    Detailed multi-line docstring explaining the complex service.
    Line 2 of docstring.
    Line 3 of docstring.
    """

    def process_data(self, item_id: int, options: dict = None) -> bool:
        """Process data for given item ID."""
        data = self.fetch_data(item_id)
        if not data:
            return False
        return self.save_data(data, options)

    def fetch_data(self, item_id: int) -> dict:
        return {"id": item_id, "status": "active"}
'''
        # 1. Low budget <= 2048: Elide docstrings
        skel_low = Skeletonizer(budget_tokens=1024).skeletonize(sample_code, "python")
        self.assertNotIn("Detailed multi-line docstring", skel_low)
        self.assertNotIn("Process data for given item ID", skel_low)
        self.assertIn("class ComplexService(BaseService):", skel_low)
        self.assertIn("def process_data(self, item_id: int, options: dict=None) -> bool:", skel_low)
        # Verify valid Python syntax
        parsed_low = ast.parse(skel_low)
        self.assertIsNotNone(parsed_low)

        # 2. Medium budget 3000: Retain first line of docstring
        skel_med = Skeletonizer(budget_tokens=3000).skeletonize(sample_code, "python")
        self.assertIn('"""Detailed multi-line docstring explaining the complex service."""', skel_med)
        self.assertNotIn("Line 2 of docstring", skel_med)

        # 3. High budget 5000: Retain full docstring
        skel_high = Skeletonizer(budget_tokens=5000).skeletonize(sample_code, "python")
        self.assertIn("Line 2 of docstring", skel_high)

    def test_step_4_2_marginal_density_packer_budget_constraint(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        repo_root = Path(self.tmp_dir.name)

        # Create sample files
        f1 = repo_root / "core.py"
        f1.write_text("class CoreRunner:\n    def run(self):\n        pass\n")

        f2 = repo_root / "utils.py"
        f2.write_text("def helper():\n    pass\n")

        symbol_scores = [
            {
                "symbol_id": "core.py::global::CoreRunner::class",
                "name": "CoreRunner",
                "file": "core.py",
                "kind": "class",
                "score": 10.0,
            },
            {
                "symbol_id": "utils.py::global::helper::function",
                "name": "helper",
                "file": "utils.py",
                "kind": "function",
                "score": 2.0,
            },
        ]

        packer = MarginalDensityPacker(repo_root)
        output_skel = packer.pack(symbol_scores, budget_tokens=512)

        self.assertIn("# File: core.py", output_skel)
        self.assertIn("class CoreRunner:", output_skel)

        # Verify token count constraint
        tok_cnt = estimate_tokens(output_skel)
        self.assertLessEqual(tok_cnt, 512)

        self.tmp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()

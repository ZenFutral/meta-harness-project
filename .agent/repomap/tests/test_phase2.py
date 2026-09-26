import sys
import unittest
import tempfile
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parents[2]
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

import repomap.core.storage as storage_mod
from repomap.core.storage import RepomapStorage, get_storage
from repomap.core.parser import LanguageParser, QUERIES_DIR
from repomap.core.tag_extractor import TagExtractor
from repomap.core.symbol_id_engine import SymbolIDEngine
from repomap.core.extractor import TagExtractor as ExtractorAlias


class Phase2Tests(unittest.TestCase):
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

    def test_step_2_1_scm_queries_exist(self):
        expected_queries = ["python.scm", "typescript.scm", "go.scm", "rust.scm"]
        for q in expected_queries:
            path = QUERIES_DIR / q
            self.assertTrue(path.exists(), f"Query file {q} missing")
            content = path.read_text(encoding="utf-8")
            self.assertGreater(len(content), 20, f"Query file {q} appears empty")

    def test_step_2_2_parser_cache_hit_and_miss(self):
        py_file = self.repo_root / "sample.py"
        py_code = 'def foo():\n    """Docstring foo"""\n    pass\n'
        py_file.write_text(py_code, encoding="utf-8")

        parser = LanguageParser(self.repo_root)

        # Parse 1: Cache Miss -> Populates storage cache
        tags1 = parser.parse(py_file)
        self.assertIn("function", tags1)
        self.assertEqual(len(tags1["function"]), 1)
        self.assertEqual(tags1["function"][0]["text"], "foo")

        # Parse 2: Cache Hit -> Returns cached result from SQLite
        tags2 = parser.parse(py_file)
        self.assertEqual(tags1, tags2)

    def test_step_2_3_tag_extractor_and_symbol_id(self):
        # Create a sample Python module and barrel export
        mod_file = self.repo_root / "mod.py"
        mod_code = (
            'class MyClass:\n'
            '    """Class doc"""\n'
            '    def method_one(self):\n'
            '        pass\n\n'
            'def _private_helper():\n'
            '    pass\n'
        )
        mod_file.write_text(mod_code, encoding="utf-8")

        barrel_file = self.repo_root / "index.py"
        barrel_code = "from mod import *"
        barrel_file.write_text(barrel_code, encoding="utf-8")

        extractor = TagExtractor(self.repo_root)
        extracted = extractor.extract_from_file(mod_file)

        # Assert symbol ID format: rel_path::scope::name::kind
        sym_ids = [t["symbol_id"] for t in extracted]
        self.assertTrue(any("mod.py::global::MyClass::class" in s for s in sym_ids))

        # Assert visibility
        privates = [t for t in extracted if t["visibility"] == "private"]
        publics = [t for t in extracted if t["visibility"] == "public"]
        self.assertTrue(any(p["name"] == "_private_helper" for p in privates))
        self.assertTrue(any(p["name"] == "MyClass" for p in publics))

        # Extract barrel export and verify SQLite export_registry & wildcard_dependencies
        extractor.extract_from_file(barrel_file)
        cur = self.storage._conn.cursor()
        cur.execute("SELECT * FROM wildcard_dependencies WHERE source_file='index.py'")
        row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["target_barrel_file"], "mod")

        cur.execute("SELECT * FROM export_registry WHERE rel_fname='mod.py'")
        exp_row = cur.fetchone()
        self.assertIsNotNone(exp_row)

    def test_extractor_alias_and_symbol_engine(self):
        engine = SymbolIDEngine(self.repo_root)
        sym_id = engine.compute_symbol_id("my_func", "foo.py", "global", "function")
        self.assertEqual(sym_id, "foo.py::global::my_func::function")


if __name__ == "__main__":
    unittest.main()

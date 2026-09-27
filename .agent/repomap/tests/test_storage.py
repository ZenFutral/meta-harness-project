import sys
import unittest
import tempfile
import os
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parents[2]
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

import repomap.db as db_mod
import repomap.core.storage as storage_mod
from repomap.core.storage import RepomapStorage, get_storage


class StorageTests(unittest.TestCase):
    def setUp(self):
        # Create a temporary database for isolated testing
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_file = Path(self.tmp_dir.name) / "test_repomap.db"
        
        # Override DB_PATH in storage module and db module and reset singleton instances
        self.orig_db_path = storage_mod.DB_PATH
        storage_mod.DB_PATH = self.db_file
        db_mod.DB_PATH = self.db_file
        if db_mod._writer_queue is not None:
            db_mod._writer_queue.shutdown()
            db_mod._writer_queue = None
        RepomapStorage._instance = None
        
        self.storage = get_storage()

    def tearDown(self):
        self.storage.close()
        if db_mod._writer_queue is not None:
            db_mod._writer_queue.shutdown()
            db_mod._writer_queue = None
        storage_mod.DB_PATH = self.orig_db_path
        db_mod.DB_PATH = self.orig_db_path
        RepomapStorage._instance = None
        self.tmp_dir.cleanup()

    def test_pragmas_and_wal(self):
        cur = self.storage._conn.cursor()
        cur.execute("PRAGMA journal_mode;")
        mode = cur.fetchone()[0]
        self.assertEqual(mode.lower(), "wal")

    def test_schema_tables_and_indexes(self):
        cur = self.storage._conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cur.fetchall()}
        expected_tables = {"parse_cache", "export_registry", "symbol_references", "wildcard_dependencies"}
        self.assertTrue(expected_tables.issubset(tables))

        cur.execute("SELECT name FROM sqlite_master WHERE type='index';")
        indexes = {row[0] for row in cur.fetchall()}
        expected_indexes = {"idx_sym_ref_def", "idx_sym_ref_target", "idx_wildcard_src"}
        self.assertTrue(expected_indexes.issubset(indexes))

    def test_parse_cache_crud(self):
        fname = "foo/bar.py"
        hash_val = "blake3_sample_hash_123"
        tags = {"symbols": [{"name": "my_func", "kind": "function"}]}
        token_cnt = 42
        updated_at = 1600000000

        # Cache miss initially
        self.assertIsNone(self.storage.get_parse_cache(fname, hash_val))

        # Put cache
        self.storage.put_parse_cache(fname, hash_val, tags, token_cnt, updated_at)

        # Cache hit
        cached = self.storage.get_parse_cache(fname, hash_val)
        self.assertIsNotNone(cached)
        self.assertEqual(cached["tags"], tags)
        self.assertEqual(cached["token_count"], token_cnt)
        self.assertEqual(cached["updated_at"], updated_at)

    def test_transitive_invalidation_cte(self):
        cur = self.storage._conn.cursor()
        # Setup symbol references: a.py defines sym1 which b.py references. b.py defines sym2 which c.py references.
        cur.execute("INSERT INTO symbol_references VALUES ('sym1', 'a.py', 'b.py')")
        cur.execute("INSERT INTO symbol_references VALUES ('sym2', 'b.py', 'c.py')")
        # Setup wildcard dependency: c.py is source, target barrel is d.py
        cur.execute("INSERT INTO wildcard_dependencies VALUES ('c.py', 'd.py')")
        self.storage._conn.commit()

        invalidated = self.storage.invalidate_file_transitive("a.py")
        self.assertIn("b.py", invalidated)
        self.assertIn("c.py", invalidated)
        self.assertIn("d.py", invalidated)


if __name__ == "__main__":
    unittest.main()

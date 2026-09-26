import sqlite3
import json
from pathlib import Path
from typing import Optional, Dict, List

# Path to the SQLite WAL database (will be created on first use)
DB_PATH = Path(__file__).resolve().parents[3] / ".agent" / "cache" / "repomap.db"

# Ensure the parent directory exists
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


class RepomapStorage:
    """Thin wrapper around a SQLite database using WAL mode.

    Provides helper methods for the core Repomap cache tables:
    - parse_cache
    - export_registry
    - symbol_references
    - wildcard_dependencies
    """

    _instance: Optional["RepomapStorage"] = None

    def __new__(cls) -> "RepomapStorage":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        # Initialise only once
        if getattr(self, "_conn", None):
            return
        self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._setup_pragmas()
        self._ensure_schema()

    # ---------------------------------------------------------------------
    # PRAGMA configuration (WAL, performance tuning)
    # ---------------------------------------------------------------------
    def _setup_pragmas(self) -> None:
        cur = self._conn.cursor()
        pragmas = {
            "journal_mode": "WAL",
            "synchronous": "NORMAL",
            "mmap_size": 268435456,  # 256 MiB
            "cache_size": -64000,     # negative = KB units, ~64 MiB
        }
        for name, value in pragmas.items():
            cur.execute(f"PRAGMA {name} = {value};")
        self._conn.commit()

    # ---------------------------------------------------------------------
    # Schema creation – idempotent; safe to run on each start
    # ---------------------------------------------------------------------
    def _ensure_schema(self) -> None:
        cur = self._conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS parse_cache (
                rel_fname TEXT NOT NULL,
                blake3_hash TEXT NOT NULL,
                tags_json BLOB NOT NULL,
                token_count INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY (rel_fname, blake3_hash)
            );

            CREATE TABLE IF NOT EXISTS export_registry (
                rel_fname TEXT PRIMARY KEY,
                exports_hash TEXT NOT NULL,
                has_wildcard_reexport BOOLEAN NOT NULL DEFAULT 0,
                public_signatures BLOB NOT NULL
            );

            CREATE TABLE IF NOT EXISTS symbol_references (
                exported_symbol TEXT NOT NULL,
                defining_file TEXT NOT NULL,
                referencing_file TEXT NOT NULL,
                PRIMARY KEY (exported_symbol, defining_file, referencing_file)
            );

            CREATE TABLE IF NOT EXISTS wildcard_dependencies (
                source_file TEXT NOT NULL,
                target_barrel_file TEXT NOT NULL,
                PRIMARY KEY (source_file, target_barrel_file)
            );

            CREATE INDEX IF NOT EXISTS idx_sym_ref_def ON symbol_references(defining_file);
            CREATE INDEX IF NOT EXISTS idx_sym_ref_target ON symbol_references(referencing_file);
            CREATE INDEX IF NOT EXISTS idx_wildcard_src ON wildcard_dependencies(source_file);
            """
        )
        self._conn.commit()

    # ---------------------------------------------------------------------
    # Public helper methods for the parse_cache table
    # ---------------------------------------------------------------------
    def get_parse_cache(self, rel_fname: str, blake3_hash: str) -> Optional[Dict]:
        """Retrieve cached tags for a file if present.

        Returns a dict with keys ``tags_json``, ``token_count`` and ``updated_at``
        or ``None`` when the entry does not exist.
        """
        cur = self._conn.cursor()
        cur.execute(
            "SELECT tags_json, token_count, updated_at FROM parse_cache "
            "WHERE rel_fname = ? AND blake3_hash = ?",
            (rel_fname, blake3_hash),
        )
        row = cur.fetchone()
        if row is None:
            return None
        tags = json.loads(row["tags_json"].decode("utf-8"))
        return {
            "tags": tags,
            "token_count": row["token_count"],
            "updated_at": row["updated_at"],
        }

    def put_parse_cache(
        self,
        rel_fname: str,
        blake3_hash: str,
        tags: Dict,
        token_count: int,
        updated_at: int,
    ) -> None:
        """Insert or replace a parse‑cache entry.

        ``tags`` is a Python ``dict`` which will be JSON‑encoded before storage.
        """
        cur = self._conn.cursor()
        tags_blob = json.dumps(tags).encode("utf-8")
        cur.execute(
            "INSERT OR REPLACE INTO parse_cache "
            "(rel_fname, blake3_hash, tags_json, token_count, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (rel_fname, blake3_hash, tags_blob, token_count, updated_at),
        )
        self._conn.commit()

    # ---------------------------------------------------------------------
    # Invalidation helper – walks transitive dependencies up to 16 hops
    # ---------------------------------------------------------------------
    def invalidate_file_transitive(self, rel_fname: str) -> List[str]:
        """Return a list of files whose cache entries should be invalidated.

        The implementation uses a *recursive CTE* that traverses both
        ``symbol_references`` and ``wildcard_dependencies`` up to a depth of 16.
        Caller is expected to delete the corresponding rows from ``parse_cache``.
        """
        cur = self._conn.cursor()
        cur.execute(
            """
            WITH RECURSIVE deps(file, depth) AS (
                SELECT ?, 0
                UNION ALL
                SELECT sr.referencing_file, depth + 1
                FROM symbol_references sr
                JOIN deps d ON sr.defining_file = d.file
                WHERE depth < 16
                UNION ALL
                SELECT wd.target_barrel_file, depth + 1
                FROM wildcard_dependencies wd
                JOIN deps d ON wd.source_file = d.file
                WHERE depth < 16
            )
            SELECT DISTINCT file FROM deps WHERE file != ?;
            """,
            (rel_fname, rel_fname),
        )
        rows = cur.fetchall()
        return [row["file"] for row in rows]

    # ---------------------------------------------------------------------
    # Convenience cleanup (close connection on interpreter exit)
    # ---------------------------------------------------------------------
    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None


def get_storage() -> RepomapStorage:
    """Return the shared :class:`RepomapStorage` singleton."""
    return RepomapStorage()

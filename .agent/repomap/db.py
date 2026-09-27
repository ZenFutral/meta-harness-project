import sqlite3
import threading
import queue
import atexit
import signal
from pathlib import Path
from typing import Tuple, Any

# ---------------------------------------------------------------------------
# Configuration – database location and PRAGMAs (WAL, performance tuning)
# ---------------------------------------------------------------------------
DB_PATH = Path(__file__).resolve().parents[2] / ".agent" / "cache" / "repomap.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

_PRAGMAS = {
    "journal_mode": "WAL",
    "synchronous": "NORMAL",
    "busy_timeout": 5000,          # ms
    "cache_size": -64000,          # ~64 MiB (negative = KB units)
    "mmap_size": 268435456,        # 256 MiB
}

def _init_connection() -> sqlite3.Connection:
    """Create a DB connection and apply WAL pragmas."""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    for name, value in _PRAGMAS.items():
        cur.execute(f"PRAGMA {name} = {value};")
    cur.executescript("""
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
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sym_ref_def ON symbol_references(defining_file);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sym_ref_target ON symbol_references(referencing_file);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_wildcard_src ON wildcard_dependencies(source_file);")
    conn.commit()
    return conn

# ---------------------------------------------------------------------------
# Writer queue daemon – serialises all mutating statements
# ---------------------------------------------------------------------------
class DatabaseWriterQueue:
    """Background thread that consumes SQL write statements from a queue.

    Public API:
        submit(sql: str, params: Tuple[Any, ...] = ()) -> None
        checkpoint() -> None  # force WAL checkpoint
        shutdown() -> None    # clean termination
    """

    def __init__(self) -> None:
        self._queue: queue.Queue[Tuple[str, Tuple[Any, ...]]] = queue.Queue()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._worker,
            name="DatabaseWriterQueue",
            daemon=False,
        )
        self._conn = _init_connection()
        self._thread.start()

    # ---------------------------------------------------------------------
    # Public methods
    # ---------------------------------------------------------------------
    def submit(self, sql: str, params: Tuple[Any, ...] = ()) -> None:
        """Enqueue a mutating statement for execution.
        The call returns immediately; the worker will execute it sequentially.
        """
        self._queue.put((sql, params))

    def checkpoint(self) -> None:
        """Force a WAL checkpoint – useful after bulk writes."""
        self._queue.put(("PRAGMA wal_checkpoint(FULL);", ()))

    def shutdown(self) -> None:
        """Gracefully stop the writer thread, draining pending writes."""
        self._stop_event.set()
        # Sentinel to unblock the worker if it is waiting on the queue.
        self._queue.put(("", ()))
        self._thread.join()
        self._conn.close()
        self._conn = None

    # ---------------------------------------------------------------------
    # Worker loop
    # ---------------------------------------------------------------------
    def _worker(self) -> None:
        while True:
            sql, params = self._queue.get()
            if self._stop_event.is_set() and not sql:
                break
            if sql:
                try:
                    cur = self._conn.cursor()
                    cur.execute(sql, params)
                    self._conn.commit()
                except Exception as exc:
                    raise RuntimeError(f"DB write failed: {exc}") from exc
            self._queue.task_done()

# ---------------------------------------------------------------------------
# Helper – obtain a read‑only connection (WAL allows concurrent reads)
# ---------------------------------------------------------------------------
def get_read_connection() -> sqlite3.Connection:
    """Return a new read‑only connection respecting WAL mode."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# ---------------------------------------------------------------------------
# Global singleton accessor
# ---------------------------------------------------------------------------
_writer_queue: DatabaseWriterQueue | None = None

def get_writer_queue() -> DatabaseWriterQueue:
    global _writer_queue
    if _writer_queue is None or (_writer_queue._conn is not None and str(DB_PATH) not in str(_writer_queue._conn)):
        if _writer_queue is not None:
            _writer_queue.shutdown()
        _writer_queue = DatabaseWriterQueue()
    return _writer_queue

# ---------------------------------------------------------------------------
# Register graceful shutdown hooks (atexit + SIGINT/SIGTERM)
# ---------------------------------------------------------------------------
def _register_shutdown_hooks() -> None:
    def _on_exit() -> None:
        if _writer_queue is not None:
            _writer_queue.shutdown()
    atexit.register(_on_exit)
    def _handle_signal(signum, frame):  # pragma: no cover
        _on_exit()
        signal.default_int_handler(signum, frame)
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _handle_signal)

_register_shutdown_hooks()

import logging
from pathlib import Path
from typing import List, Set

from .storage import get_storage

logger = logging.getLogger(__name__)

class BlastRadiusTracer:
    """Utility to compute the *blast radius* – all files that may be impacted
    by a change to a given source file.

    The implementation delegates to the ``RepomapStorage.invalidate_file_transitive``
    method, which performs a recursive CTE over ``symbol_references`` and
    ``wildcard_dependencies`` up to a depth of 16 hops (see ``storage.py``).
    """

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root.resolve()
        self.storage = get_storage()

    def trace_by_file(self, file_path: Path) -> List[str]:
        """Return a list of repository‑relative file paths that should be
        re‑indexed when *file_path* changes.
        """
        rel_path = str(file_path.resolve().relative_to(self.repo_root))
        logger.debug("Tracing blast radius for %s", rel_path)
        # ``invalidate_file_transitive`` returns a list of dependent file paths.
        dependent_files = self.storage.invalidate_file_transitive(rel_path)
        return dependent_files

    def trace_by_files(self, file_paths: List[Path]) -> Set[str]:
        """Aggregate the blast radius for multiple files.
        Returns a set of unique relative paths.
        """
        all_deps: Set[str] = set()
        for p in file_paths:
            all_deps.update(self.trace_by_file(p))
        return all_deps

# Convenience factory
def get_blast_tracer(repo_root: Path) -> BlastRadiusTracer:
    """Return a :class:`BlastRadiusTracer` bound to *repo_root*."""
    return BlastRadiusTracer(repo_root)

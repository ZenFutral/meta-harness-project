from pathlib import Path
from typing import Dict, List, Any, Optional

from ..core.type_hierarchy import TypeHierarchyLattice, get_type_hierarchy


class HierarchyFacet:
    """Type & Inheritance Lattice Facet.

    Provides ancestry trees, base types, and derived sub-types for symbols.
    """

    def __init__(self, lattice: Optional[TypeHierarchyLattice] = None):
        self.lattice = lattice or TypeHierarchyLattice()

    def get_symbol_hierarchy(self, symbol_name: str) -> Dict[str, Any]:
        ancestors = list(self.lattice.ancestors(symbol_name))
        descendants = list(self.lattice.descendants(symbol_name))

        return {
            "symbol_name": symbol_name,
            "ancestors": ancestors,
            "descendants": descendants,
            "is_root": len(ancestors) == 0,
            "is_leaf": len(descendants) == 0,
        }


def get_symbol_hierarchy(symbol_name: str, repo_root: Optional[Path] = None) -> Dict[str, Any]:
    root = repo_root or Path.cwd()
    lattice = get_type_hierarchy(root)
    facet = HierarchyFacet(lattice)
    return facet.get_symbol_hierarchy(symbol_name)

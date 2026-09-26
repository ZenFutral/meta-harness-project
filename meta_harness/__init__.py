"""Meta-Harness package initialization."""
import os, sys

_pkg_dir = os.path.abspath(os.path.dirname(__file__))
_root_dir = os.path.abspath(os.path.join(_pkg_dir, ".."))
_agent_dir = os.path.abspath(os.path.join(_root_dir, ".agent"))

for _p in [_root_dir, _pkg_dir, _agent_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

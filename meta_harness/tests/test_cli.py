# test_cli.py – headless Rich HUD test
"""Ensures the HUD can be constructed without a live terminal.
The test builds a dummy metrics dict, invokes the internal
`_make_dashboard` helper and checks that a `Panel` instance is
returned. This verifies that the Rich rendering pipeline does not
raise exceptions when run in a non‑interactive environment.
"""

import pytest
from meta_harness.cli.hud import _make_dashboard

def test_dashboard_renders() -> None:
    dummy_metrics = {
        "total_symbols": 0,
        "top_pr": [],
        "scc_cycles": 0,
    }
    panel = _make_dashboard(dummy_metrics)
    assert panel.title == "Meta-Harness HUD"

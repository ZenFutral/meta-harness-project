"""
Unit and integration test suite for the System Monitoring GUI backend and API server.
"""
import os
import sys
import json
import time
import threading
import urllib.request
import urllib.error
import pytest
from pathlib import Path

# Setup paths
WORKSPACE_ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
META_HARNESS_DIR = WORKSPACE_ROOT / "meta-harness"

for p in [str(WORKSPACE_ROOT), str(META_HARNESS_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from gui.models import FeatureItem, QuotaTelemetry, CacheTelemetry, TelemetrySnapshot
from gui.telemetry import (
    get_quota_telemetry,
    get_cache_telemetry,
    get_test_metrics_telemetry,
    get_feature_catalog,
    get_telemetry_snapshot,
    get_cache_table_sample
)
from gui.probes import probe_router, probe_skeleton, probe_blast_radius
from gui.server import create_server


def test_quota_telemetry():
    quota = get_quota_telemetry()
    assert isinstance(quota, QuotaTelemetry)
    assert quota.daily_cap == 0.33
    assert quota.cost >= 0.0
    assert isinstance(quota.circuit_breaker_tripped, bool)


def test_cache_telemetry():
    cache = get_cache_telemetry()
    assert isinstance(cache, CacheTelemetry)
    assert cache.db_exists is True
    assert cache.db_size_bytes > 0
    assert cache.wal_enabled is True
    assert cache.parse_cache_count >= 0


def test_test_metrics_telemetry():
    metrics = get_test_metrics_telemetry()
    assert metrics.status in ["SUCCESS", "IDLE", "FAILURE"]
    assert metrics.budget_limit > 0


def test_feature_catalog():
    from router.vendor_config import set_vendor_enabled
    # Ensure vendors are enabled for baseline feature check
    set_vendor_enabled("huggingface", True)
    set_vendor_enabled("vertex", True)
    set_vendor_enabled("antigravity", True)

    features = get_feature_catalog()
    assert len(features) >= 23
    subsystems = {f.subsystem for f in features}
    assert {"Orchestrator", "Router", "Contextualize", "Repomap"}.issubset(subsystems)
    for f in features:
        assert f.id.startswith(("ORCH-", "ROUT-", "CTX-", "REPO-"))
        assert f.status in ["OPERATIONAL", "STANDBY", "DEGRADED", "TRIPPED", "DISABLED (VENDOR OFF)"]


def test_telemetry_snapshot():
    snapshot = get_telemetry_snapshot()
    assert isinstance(snapshot, TelemetrySnapshot)
    data = snapshot.to_dict()
    assert "quota" in data
    assert "cache" in data
    assert "features" in data
    assert "agent_activity" in data
    assert len(data["features"]) >= 23


def test_agent_activity_telemetry():
    from gui.telemetry import get_agent_activity_telemetry
    activity = get_agent_activity_telemetry()
    assert activity.task_id != ""
    assert len(activity.personas) == 6
    assert isinstance(activity.event_log, list)


def test_cache_table_sample():
    sample = get_cache_table_sample("parse_cache", limit=5)
    assert "columns" in sample
    assert "rows" in sample
    assert "rel_fname" in sample["columns"]


def test_probe_router():
    res = probe_router("Refactor user database models")
    assert res["success"] is True
    assert "manifest" in res
    assert "intent" in res["manifest"]


def test_probe_skeleton():
    res = probe_skeleton("meta-harness/orchestrator/budget.py", budget=2048)
    assert res["success"] is True
    assert res["skeleton_lines"] > 0
    assert "def check_and_update_budget" in res["skeleton"]


def test_probe_blast_radius():
    res = probe_blast_radius("check_and_update_budget", direction="both", max_depth=2)
    assert res["success"] is True
    assert "result" in res


def test_gui_server_http_lifecycle():
    port = 8791
    server = create_server(host="127.0.0.1", port=port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.3)

    base_url = f"http://127.0.0.1:{port}"

    try:
        # Test index.html
        req = urllib.request.Request(f"{base_url}/")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            html = resp.read().decode("utf-8")
            assert "META-HARNESS" in html
            assert "SYSTEM OBSERVATORY" in html

        # Test app.css
        with urllib.request.urlopen(f"{base_url}/app.css") as resp:
            assert resp.status == 200
            css = resp.read().decode("utf-8")
            assert "--accent-cyan" in css

        # Test app.js
        with urllib.request.urlopen(f"{base_url}/app.js") as resp:
            assert resp.status == 200
            js = resp.read().decode("utf-8")
            assert "fetchTelemetry" in js

        # Test /api/telemetry
        with urllib.request.urlopen(f"{base_url}/api/telemetry") as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert "quota" in data
            assert len(data["features"]) >= 23

        # Test /api/features
        with urllib.request.urlopen(f"{base_url}/api/features") as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["total"] >= 23

        # Test /api/cache/tables
        with urllib.request.urlopen(f"{base_url}/api/cache/tables?table=parse_cache&limit=5") as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert "columns" in data

        # Test POST /api/probe/route
        post_data = json.dumps({"prompt": "inspect schema models", "focus_files": []}).encode("utf-8")
        req = urllib.request.Request(f"{base_url}/api/probe/route", data=post_data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            res = json.loads(resp.read().decode("utf-8"))
            assert res["success"] is True

        # Test POST /api/probe/skeleton
        post_data = json.dumps({"filepath": "meta-harness/orchestrator/budget.py", "budget": 1024}).encode("utf-8")
        req = urllib.request.Request(f"{base_url}/api/probe/skeleton", data=post_data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            res = json.loads(resp.read().decode("utf-8"))
            assert res["success"] is True

        # Test /api/vendors
        with urllib.request.urlopen(f"{base_url}/api/vendors") as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert "vendors" in data
            assert "huggingface" in data["vendors"]

        # Test POST /api/vendors/toggle
        post_data = json.dumps({"vendor": "huggingface", "enabled": False}).encode("utf-8")
        req = urllib.request.Request(f"{base_url}/api/vendors/toggle", data=post_data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            res = json.loads(resp.read().decode("utf-8"))
            assert res["success"] is True
            assert res["enabled"] is False

        # Verify probe_router bypasses HF fast-path when disabled
        probe_res = probe_router("Refactor user database models")
        assert probe_res["success"] is True
        assert "Stage 2" in probe_res["tier_selected"]

        # Test /api/agent_activity
        with urllib.request.urlopen(f"{base_url}/api/agent_activity") as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert "task_id" in data
            assert len(data["personas"]) == 6

        # Test POST /api/probe/agent_simulation
        post_data = json.dumps({"objective": "Test workflow simulation"}).encode("utf-8")
        req = urllib.request.Request(f"{base_url}/api/probe/agent_simulation", data=post_data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            res = json.loads(resp.read().decode("utf-8"))
            assert res["success"] is True

        # Test /api/chat GET
        with urllib.request.urlopen(f"{base_url}/api/chat") as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert "messages" in data
            assert len(data["messages"]) >= 1

        # Test POST /api/chat
        post_data = json.dumps({
            "message": "Plan an endpoint for real-time log ingestion",
            "persona": "planner",
            "context_files": ["meta_harness/orchestrator/config.py"]
        }).encode("utf-8")
        req = urllib.request.Request(f"{base_url}/api/chat", data=post_data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            res = json.loads(resp.read().decode("utf-8"))
            assert res["success"] is True
            assert res["persona"] == "planner"
            assert "message" in res

        # Test POST /api/chat/clear
        req = urllib.request.Request(f"{base_url}/api/chat/clear", data=b"{}", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            res = json.loads(resp.read().decode("utf-8"))
            assert res["success"] is True

        # Re-enable huggingface vendor
        post_data = json.dumps({"vendor": "huggingface", "enabled": True}).encode("utf-8")
        req = urllib.request.Request(f"{base_url}/api/vendors/toggle", data=post_data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200

    finally:
        from router.vendor_config import set_vendor_enabled
        set_vendor_enabled("huggingface", True)
        set_vendor_enabled("vertex", True)
        set_vendor_enabled("antigravity", True)
        server.shutdown()
        server.server_close()

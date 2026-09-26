"""
agents_network.py — Dynamic Agent Network graph topology, state tracking, and unified event log.

Represents all active worker agents (excluding the router agent) in a directed task flow graph.
Provides live inspection, task editing, re-running, and model switching.
"""
from __future__ import annotations

import os
import time
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

log = logging.getLogger(__name__)

WORKSPACE_ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
AGENT_DIR = WORKSPACE_ROOT / ".agent"

# Default worker personas (router agent excluded as specified)
DEFAULT_AGENT_NODES: Dict[str, Dict[str, Any]] = {
    "orchestrator": {
        "id": "orchestrator",
        "name": "Orchestrator Supervisor",
        "role": "Lifecycle coordination, policy enforcement & subtask dispatch",
        "status": "ACTIVE",
        "model": "antigravity/gemini-3-pro-preview",
        "current_task": "Supervise pipeline execution and enforce $0.33/day budget ceiling",
        "active_context": "WorkflowState[task_id=task_001, status=CODING, subtasks=3]",
        "tools": ["budget_circuit_breaker", "workflow_state_manager", "task_dispatcher"],
        "tool_usage": {"task_dispatcher": 18, "budget_circuit_breaker": 42},
        "history": [
            "Initialized multi-agent pipeline topology",
            "Dispatched subtask 'ST-101: AstSchemaRefactor' to Planner",
            "Monitored token budget spend: $0.0075 / $0.66"
        ]
    },
    "planner": {
        "id": "planner",
        "name": "DAG Architecture Planner",
        "role": "Objective decomposition into topological subtasks & acceptance criteria",
        "status": "STANDBY",
        "model": "antigravity/gemini-3-pro-preview",
        "current_task": "Decompose high-level feature requirements into topological task graph",
        "active_context": "FeatureSpec[id=ORCH-01, priority=HIGH, dependencies=['ROUT-01']]",
        "tools": ["ast_skeleton_scanner", "dag_topological_sort", "acceptance_verifier"],
        "tool_usage": {"ast_skeleton_scanner": 12, "dag_topological_sort": 6},
        "history": [
            "Decomposed objective into 3 DAG subtasks",
            "Verified acyclic graph topology (0 cycles detected)",
            "Emitted PlannerOutput with typed acceptance criteria"
        ]
    },
    "coder": {
        "id": "coder",
        "name": "Code Synthesis Agent",
        "role": "Unified diff creation & multi-file structural implementation",
        "status": "ACTIVE",
        "model": "antigravity/gemini-3-pro-preview",
        "current_task": "Synthesizing unified diff for database schema migration",
        "active_context": "SubtaskSpec[id=subtask_1, files=['router/vendor_config.py', 'orchestrator/budget.py']]",
        "tools": ["unified_diff_generator", "ast_patch_applier", "type_checker"],
        "tool_usage": {"unified_diff_generator": 24, "ast_patch_applier": 19},
        "history": [
            "Generated unified diff for multi-vendor user_config schema",
            "Applied patch to router/vendor_config.py",
            "Dispatched verification bundle to TesterAgent"
        ]
    },
    "tester": {
        "id": "tester",
        "name": "Automated Verification Agent",
        "role": "Pytest harness execution, assertion verification & coverage tracking",
        "status": "ACTIVE",
        "model": "antigravity/gemini-3-pro-preview",
        "current_task": "Running pytest verification suite across 62 test cases",
        "active_context": "TestPlan[suite=test_phase1_config_budget, tests=8, assertions=26]",
        "tools": ["pytest_runner", "assertion_inspector", "coverage_reporter"],
        "tool_usage": {"pytest_runner": 31, "assertion_inspector": 28},
        "history": [
            "Executed pytest meta_harness/tests/test_phase1_config_budget.py",
            "Captured 8/8 test passing assertions (0 failures)",
            "Sent verification pass report to ReviewerAgent"
        ]
    },
    "reviewer": {
        "id": "reviewer",
        "name": "Code Reviewer & Security Auditor",
        "role": "Adversarial code review, security auditing & diff verification",
        "status": "STANDBY",
        "model": "antigravity/gemini-3-pro-preview",
        "current_task": "Awaiting patch approval for Phase 2 API expansion",
        "active_context": "DiffPayload[additions=142, deletions=12, files=3]",
        "tools": ["ast_diff_analyzer", "security_rule_engine", "style_linter"],
        "tool_usage": {"ast_diff_analyzer": 14, "security_rule_engine": 11},
        "history": [
            "Audited diff payload against security policy",
            "Verified AST backward compatibility",
            "Approved subtask ST-101 for merge"
        ]
    },
    "debugger": {
        "id": "debugger",
        "name": "Root-Cause Diagnosis Agent",
        "role": "Traceback analysis, fault localization & corrective feedback generation",
        "status": "STANDBY",
        "model": "antigravity/gemini-3-pro-preview",
        "current_task": "Monitoring system tracebacks and error events",
        "active_context": "TracebackBuffer[errors=0, status=CLEAN]",
        "tools": ["blast_radius_tracer", "stacktrace_parser", "repair_prescriber"],
        "tool_usage": {"blast_radius_tracer": 9, "stacktrace_parser": 7},
        "history": [
            "Analyzed test failure traceback for quota rollover",
            "Generated corrective patch recommendation for budget.py",
            "Fed corrective instructions back to CoderAgent"
        ]
    }
}

# Directed edges representing task flow and relationships
DEFAULT_EDGES: List[Dict[str, Any]] = [
    {
        "id": "flow_orch_planner",
        "source": "orchestrator",
        "target": "planner",
        "label": "DAG Decomposition",
        "flow_type": "parent_child",
        "status": "completed"
    },
    {
        "id": "flow_planner_coder",
        "source": "planner",
        "target": "coder",
        "label": "Subtask Dispatch",
        "flow_type": "parent_child",
        "status": "active"
    },
    {
        "id": "flow_coder_tester",
        "source": "coder",
        "target": "tester",
        "label": "Verify Implementation",
        "flow_type": "testing",
        "status": "active"
    },
    {
        "id": "flow_tester_debugger",
        "source": "tester",
        "target": "debugger",
        "label": "Failure Diagnosis",
        "flow_type": "bug_fixing",
        "status": "idle"
    },
    {
        "id": "flow_debugger_coder",
        "source": "debugger",
        "target": "coder",
        "label": "Corrective Feedback",
        "flow_type": "refactoring",
        "status": "idle"
    },
    {
        "id": "flow_tester_reviewer",
        "source": "tester",
        "target": "reviewer",
        "label": "Quality Audit",
        "flow_type": "review",
        "status": "completed"
    },
    {
        "id": "flow_reviewer_orchestrator",
        "source": "reviewer",
        "target": "orchestrator",
        "label": "Verdict & Merge",
        "flow_type": "parent_child",
        "status": "completed"
    }
]

# Unified Event Log store
_UNIFIED_EVENT_LOG: List[Dict[str, Any]] = [
    {
        "id": "evt_001",
        "timestamp": time.strftime("%H:%M:%S", time.gmtime(time.time() - 300)),
        "agent": "orchestrator",
        "agent_name": "Orchestrator Supervisor",
        "event_type": "topology_init",
        "message": "Initialized 6 worker personas network (Router excluded)"
    },
    {
        "id": "evt_002",
        "timestamp": time.strftime("%H:%M:%S", time.gmtime(time.time() - 240)),
        "agent": "planner",
        "agent_name": "DAG Architecture Planner",
        "event_type": "dag_created",
        "message": "Topological sort completed: 3 subtasks queued"
    },
    {
        "id": "evt_003",
        "timestamp": time.strftime("%H:%M:%S", time.gmtime(time.time() - 180)),
        "agent": "coder",
        "agent_name": "Code Synthesis Agent",
        "event_type": "diff_generated",
        "message": "Generated structural unified diff for vendor_config.py & budget.py"
    },
    {
        "id": "evt_004",
        "timestamp": time.strftime("%H:%M:%S", time.gmtime(time.time() - 120)),
        "agent": "tester",
        "agent_name": "Automated Verification Agent",
        "event_type": "tests_passed",
        "message": "All 62 verification assertions passed (100% green)"
    },
    {
        "id": "evt_005",
        "timestamp": time.strftime("%H:%M:%S", time.gmtime(time.time() - 60)),
        "agent": "reviewer",
        "agent_name": "Code Reviewer & Security Auditor",
        "event_type": "verdict_approved",
        "message": "Security and AST backward compatibility approved"
    }
]

# Mutable in-memory store for active session
_ACTIVE_AGENTS = json.loads(json.dumps(DEFAULT_AGENT_NODES))
_ACTIVE_EDGES = list(DEFAULT_EDGES)


def _get_workflow_state_helpers():
    try:
        from meta_harness.orchestrator.state import load_state, save_state
        return load_state, save_state
    except ImportError:
        try:
            from orchestrator.state import load_state, save_state
            return load_state, save_state
        except ImportError:
            return None, None


def get_agent_network_topology() -> Dict[str, Any]:
    """Returns complete directed web graph topology of agents, edges, and unified event log.
    Integrates real workflow state from .orchestrator/state.json.
    """
    # Load persisted workflow state
    load_state, _ = _get_workflow_state_helpers()
    state = load_state() if load_state else None

    # Deep copy active nodes to allow state overlay
    nodes_map = {k: dict(v) for k, v in _ACTIVE_AGENTS.items()}

    if state:
        if "orchestrator" in nodes_map:
            nodes_map["orchestrator"]["status"] = state.status if state.status in ["ACTIVE", "STANDBY", "WORKING"] else "ACTIVE"
            if state.objective:
                nodes_map["orchestrator"]["current_task"] = state.objective

        if state.subtasks:
            curr_idx = min(state.current_subtask_idx, len(state.subtasks) - 1)
            curr_sub = state.subtasks[curr_idx]
            if "coder" in nodes_map and curr_sub:
                nodes_map["coder"]["current_task"] = curr_sub.description

    nodes = list(nodes_map.values())

    return {
        "success": True,
        "nodes": nodes,
        "edges": _ACTIVE_EDGES,
        "unified_event_log": _UNIFIED_EVENT_LOG[-50:],
        "active_agent_count": len([a for a in nodes if a.get("status") in ["ACTIVE", "WORKING"]]),
        "total_agent_count": len(nodes)
    }
def update_agent_state(
    agent_id: str,
    action: str,
    model: Optional[str] = None,
    task: Optional[str] = None
) -> Dict[str, Any]:
    """
    Updates an agent's state, model choice, or task prompt, logging the mutation.
    Actions supported: 'set_model', 'edit_task', 'rerun', 'cancel'.
    This version also mutates the persisted WorkflowState where appropriate.
    """

    if agent_id not in _ACTIVE_AGENTS:
        return {"success": False, "error": f"Agent '{agent_id}' not found in active network"}

    agent = _ACTIVE_AGENTS[agent_id]
    now_str = time.strftime("%H:%M:%S")

    # Helper to modify and persist the workflow state
    def _persist_state(modifier):
        load_state_fn, save_state_fn = _get_workflow_state_helpers()
        if load_state_fn and save_state_fn:
            state = load_state_fn()
            if state:
                modifier(state)
                save_state_fn(state)

    if action == "set_model" and model:
        agent["model"] = model
        _UNIFIED_EVENT_LOG.append({
            "id": f"evt_{int(time.time() * 1000)}",
            "timestamp": now_str,
            "agent": agent_id,
            "agent_name": agent["name"],
            "event_type": "model_switched",
            "message": f"Model switched to '{model}'"
        })
        agent["history"].insert(0, f"Model changed to {model}")
        return {"success": True, "agent": agent, "action": "set_model", "model": model}

    elif action == "edit_task" and task:
        agent["current_task"] = task
        agent["status"] = "ACTIVE"
        _UNIFIED_EVENT_LOG.append({
            "id": f"evt_{int(time.time() * 1000)}",
            "timestamp": now_str,
            "agent": agent_id,
            "agent_name": agent["name"],
            "event_type": "task_edited",
            "message": f"Manual task prompt update: {task[:60]}..."
        })
        agent["history"].insert(0, f"Task updated: {task[:50]}")
        # Persist task description change to current subtask in workflow state
        def _modify(state):
            if state.current_subtask:
                state.current_subtask.description = task
                state.log_event(f"Subtask {state.current_subtask.id} description edited via UI")
        _persist_state(_modify)
        return {"success": True, "agent": agent, "action": "edit_task", "task": task}

    elif action == "rerun":
        agent["status"] = "ACTIVE"
        tool_name = agent["tools"][0] if agent.get("tools") else "default_executor"
        agent["tool_usage"][tool_name] = agent["tool_usage"].get(tool_name, 0) + 1
        _UNIFIED_EVENT_LOG.append({
            "id": f"evt_{int(time.time() * 1000)}",
            "timestamp": now_str,
            "agent": agent_id,
            "agent_name": agent["name"],
            "event_type": "task_rerun",
            "message": f"Forced re-execution of task: {agent['current_task'][:60]}"
        })
        agent["history"].insert(0, f"Forced task re-run triggered")
        # Reset subtask status to PENDING in persisted state
        def _modify(state):
            if state.current_subtask:
                state.current_subtask.status = "PENDING"
                state.log_event(f"Subtask {state.current_subtask.id} rerun requested via UI")
        _persist_state(_modify)
        return {"success": True, "agent": agent, "action": "rerun"}

    elif action == "cancel":
        agent["status"] = "STANDBY"
        _UNIFIED_EVENT_LOG.append({
            "id": f"evt_{int(time.time() * 1000)}",
            "timestamp": now_str,
            "agent": agent_id,
            "agent_name": agent["name"],
            "event_type": "task_cancelled",
            "message": f"Task cancelled by operator"
        })
        agent["history"].insert(0, f"Task cancelled")
        # Mark subtask as FAILED in persisted state
        def _modify(state):
            if state.current_subtask:
                state.current_subtask.status = "FAILED"
                state.log_event(f"Subtask {state.current_subtask.id} cancelled via UI")
        _persist_state(_modify)
        return {"success": True, "agent": agent, "action": "cancel"}

    return {"success": False, "error": f"Unsupported action '{action}'"}

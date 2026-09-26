"""
Interactive feature testing bridge for System Monitoring GUI.
Allows developers and users to probe routing, skeletonization, blast radius,
and schemas in real-time.
"""
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

WORKSPACE_ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
AGENT_DIR = WORKSPACE_ROOT / ".agent"

# Ensure workspace and packages are in path
for p in [str(WORKSPACE_ROOT), str(WORKSPACE_ROOT / "meta-harness"), str(AGENT_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)


def probe_router(prompt: str, focus_files: Optional[List[str]] = None) -> Dict[str, Any]:
    """Tests the multi-tier router against an arbitrary prompt."""
    try:
        from router.router import ModelRouter
        router = ModelRouter()
        safe_focus = focus_files if focus_files is not None else []
        
        # Test Fast Path
        fast_manifest = router.zero_shot.route_fast_path(prompt, focus_files=safe_focus)
        tier_used = "Stage 1: Hugging Face Zero-Shot (Fast-Path)" if fast_manifest else "Stage 2: Vertex AI Flash (Fallback)"
        
        manifest = router.route_with_fallback(prompt, focus_files=safe_focus)
        return {
            "success": True,
            "tier_selected": tier_used,
            "manifest": {
                "intent": manifest.intent,
                "primary_target_symbols": manifest.primary_target_symbols,
                "focus_files": manifest.focus_files,
                "repomap_token_budget": manifest.repomap_token_budget,
                "require_blast_radius": manifest.require_blast_radius,
                "execution_engine": manifest.execution_engine,
                "task_instructions": manifest.task_instructions,
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def probe_skeleton(rel_filepath: str, budget: int = 2048) -> Dict[str, Any]:
    """Generates an AST skeleton for a workspace file with budget-aware docstring pruning."""
    target_path = WORKSPACE_ROOT / rel_filepath
    if not (target_path.exists() and target_path.is_file()):
        # Handle legacy or alternate meta-harness / meta_harness prefix
        if rel_filepath.startswith("meta-harness/"):
            alt_path = WORKSPACE_ROOT / rel_filepath.replace("meta-harness/", "meta_harness/", 1)
            if alt_path.exists() and alt_path.is_file():
                target_path = alt_path
        elif rel_filepath.startswith("meta_harness/"):
            alt_path = WORKSPACE_ROOT / rel_filepath.replace("meta_harness/", "meta-harness/", 1)
            if alt_path.exists() and alt_path.is_file():
                target_path = alt_path

    if not target_path.exists() or not target_path.is_file():
        return {"success": False, "error": f"File '{rel_filepath}' not found or is a directory"}

    try:
        from repomap.core.skeleton import Skeletonizer
        code = target_path.read_text(encoding="utf-8", errors="replace")
        ext = target_path.suffix.lower()
        lang = "python" if ext in [".py"] else "generic"

        skeletonizer = Skeletonizer(budget_tokens=budget)
        skeleton_code = skeletonizer.skeletonize(code, lang=lang)
        token_estimate = len(skeleton_code) // 4  # rough heuristic: 1 token ~ 4 chars

        pruning_mode = "Full docstrings elided (budget <= 2048)" if budget <= 2048 else (
            "First line of docstrings retained (2049 <= budget <= 4096)" if budget <= 4096 else "Full docstrings preserved (budget >= 4097)"
        )

        return {
            "success": True,
            "filepath": rel_filepath,
            "original_lines": len(code.splitlines()),
            "skeleton_lines": len(skeleton_code.splitlines()),
            "budget_tokens": budget,
            "estimated_tokens": token_estimate,
            "pruning_mode": pruning_mode,
            "skeleton": skeleton_code
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def probe_blast_radius(symbol_name: str, direction: str = "both", max_depth: int = 3) -> Dict[str, Any]:
    """Traces caller/callee blast radius for a given symbol."""
    try:
        from repomap.facets.blast_radius import BlastRadiusTracer
        from repomap.core.graph import TwoTierGraph

        # Build graph from cache or storage
        tracer = BlastRadiusTracer()
        result = tracer.trace_blast_radius(symbol_name=symbol_name, direction=direction, max_depth=max_depth)
        return {
            "success": True,
            "symbol": symbol_name,
            "direction": direction,
            "max_depth": max_depth,
            "upstream_count": len(result.get("upstream_impact", [])),
            "downstream_count": len(result.get("downstream_impact", [])),
            "result": result
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def probe_schemas() -> Dict[str, Any]:
    """Discovers schema definitions in the repository."""
    try:
        from repomap.facets.schemas import SchemaRegistry
        registry = SchemaRegistry()
        schemas = registry.get_schema_registry()
        return {
            "success": True,
            "total_schemas": len(schemas),
            "schemas": schemas
        }
    except Exception as e:
        # Fallback inspection if SchemaRegistry raises
        return {"success": False, "error": str(e)}


def probe_cycles() -> Dict[str, Any]:
    """Discovers circular dependencies using Tarjan SCC."""
    try:
        from repomap.core.graph import TwoTierGraph
        graph = TwoTierGraph()
        cycles = graph.find_cycles() if hasattr(graph, "find_cycles") else []
        return {
            "success": True,
            "cycles_count": len(cycles),
            "cycles": cycles
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def probe_agent_simulation(objective: str = "") -> Dict[str, Any]:
    """Simulates or advances a multi-agent workflow state transition."""
    try:
        from orchestrator.state import load_state, save_state, WorkflowState, WorkflowStatus, SubtaskSpec, SubtaskStatus
        
        state = load_state()
        if not state or not objective or state.status == WorkflowStatus.COMPLETE:
            # Create a fresh workflow simulation
            obj_text = objective or "Refactor database storage layer and verify circuit breaker telemetry"
            state = WorkflowState(objective=obj_text, repository_path=str(WORKSPACE_ROOT))
            state.status = WorkflowStatus.PLANNING
            state.next_agent = "planner"
            state.subtasks = [
                SubtaskSpec(
                    id="SUB-01",
                    name="AST Parsing & SQLite-WAL Storage Indexing",
                    description="Index repository tags and populate export registry",
                    files_to_modify=["meta-harness/orchestrator/storage.py"],
                    status=SubtaskStatus.RUNNING
                ),
                SubtaskSpec(
                    id="SUB-02",
                    name="Multi-Tier Router Manifest Validation",
                    description="Validate RoutingManifest schemas across HF and Vertex AI",
                    files_to_modify=["meta-harness/router/manifest.py"],
                    status=SubtaskStatus.PENDING
                ),
                SubtaskSpec(
                    id="SUB-03",
                    name="Circuit Breaker Quota Enforcement",
                    description="Enforce $0.33/day ceiling check in budget.py",
                    files_to_modify=["meta-harness/orchestrator/budget.py"],
                    status=SubtaskStatus.PENDING
                )
            ]
            state.log_event(f"Workflow dispatched for objective: {obj_text}")
            state.log_event("Planner agent engaged -> Generated 3 subtasks")
        else:
            # Advance existing workflow state
            if state.status == WorkflowStatus.PLANNING:
                state.status = WorkflowStatus.CODING
                state.next_agent = "coder"
                if state.subtasks:
                    state.subtasks[0].status = SubtaskStatus.RUNNING
                state.log_event("Coder agent engaged -> Synthesizing AST diff for SUB-01")
            elif state.status == WorkflowStatus.CODING:
                state.status = WorkflowStatus.TESTING
                state.next_agent = "tester"
                if state.subtasks:
                    state.subtasks[0].status = SubtaskStatus.PASSED
                    if len(state.subtasks) > 1:
                        state.subtasks[1].status = SubtaskStatus.RUNNING
                state.log_event("Tester agent engaged -> Running verification test suite")
            elif state.status == WorkflowStatus.TESTING:
                state.status = WorkflowStatus.REVIEWING
                state.next_agent = "reviewer"
                state.log_event("Reviewer agent engaged -> Performing security & structural audit")
            elif state.status == WorkflowStatus.REVIEWING:
                state.status = WorkflowStatus.COMPLETE
                state.next_agent = "orchestrator"
                for st in state.subtasks:
                    st.status = SubtaskStatus.COMPLETE
                state.log_event("All subtasks completed successfully. Workflow status -> COMPLETE")

        save_state(state)
        return {
            "success": True,
            "task_id": state.task_id,
            "status": str(state.status),
            "next_agent": state.next_agent,
            "event_log_latest": state.event_log[-1] if state.event_log else ""
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

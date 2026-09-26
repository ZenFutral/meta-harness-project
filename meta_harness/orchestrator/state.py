"""
state.py — Artifact-driven state machine for the multi-agent orchestration pipeline.

Implements spec §1 "Context Hygiene & State Isolation Principles":
  - State persists in .orchestrator/state.json (not LLM memory).
  - Agents communicate only through typed artifacts.
  - Supports the full lifecycle: INTAKE → PLANNING → CODING → TESTING →
    REVIEWING → DEBUGGING → COMPLETE / FAILED.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

try:
    from .config import STATE_DIR, STATE_FILE
except ImportError:
    try:
        from orchestrator.config import STATE_DIR, STATE_FILE
    except ImportError:
        from config import STATE_DIR, STATE_FILE

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifecycle states (spec §4 "Execution Lifecycle & State Machine")
# ---------------------------------------------------------------------------

class WorkflowStatus(str, Enum):
    INTAKE     = "INTAKE"
    PLANNING   = "PLANNING"
    CODING     = "CODING"
    TESTING    = "TESTING"
    REVIEWING  = "REVIEWING"
    DEBUGGING  = "DEBUGGING"
    COMPLETE   = "COMPLETE"
    FAILED     = "FAILED"
    IN_PROGRESS = "IN_PROGRESS"


class SubtaskStatus(str, Enum):
    PENDING   = "PENDING"
    RUNNING   = "RUNNING"
    PASSED    = "PASSED"
    FAILED    = "FAILED"
    REJECTED  = "REJECTED"
    COMPLETE  = "COMPLETE"


# ---------------------------------------------------------------------------
# Typed artifact dataclasses (spec §3 agent I/O schemas)
# ---------------------------------------------------------------------------

@dataclass
class SubtaskSpec:
    """A single unit of work emitted by the Planner."""
    id: str
    name: str
    description: str
    files_to_modify: list[str] = field(default_factory=list)
    acceptance_criteria: str = ""
    dependencies: list[str] = field(default_factory=list)
    status: str = SubtaskStatus.PENDING
    repair_iterations: int = 0          # Coder→Tester→Debugger loops so far
    escalation_count: int = 0           # How many times Planner was re-engaged


@dataclass
class TestReport:
    """Tester output artifact (spec §3.4)."""
    test_run_status: str           # "PASSED" | "FAILED"
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    failed_tests: list[dict] = field(default_factory=list)
    truncated_log: str = ""


@dataclass
class DebugDiagnosis:
    """Debugger output artifact (spec §3.6)."""
    fault_location: dict[str, Any] = field(default_factory=dict)  # {file, line_number}
    root_cause: str = ""
    suggested_fix: str = ""


@dataclass
class ReviewVerdict:
    """Reviewer output artifact (spec §3.5)."""
    verdict: str = "COMMENT"     # "APPROVE" | "COMMENT" | "REJECT"
    feedback: list[str] = field(default_factory=list)
    line_specific: list[dict] = field(default_factory=list)


@dataclass
class PlannerOutput:
    """Planner output artifact (spec §3.2)."""
    architecture_summary: str = ""
    tasks: list[SubtaskSpec] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Global workflow state
# ---------------------------------------------------------------------------

@dataclass
class WorkflowState:
    """
    Version-controlled state stored in .orchestrator/state.json.

    This is the single source of truth for the pipeline — never rely on
    conversational context across agent boundaries.
    """
    task_id: str = field(default_factory=lambda: f"TASK-{uuid.uuid4().hex[:8].upper()}")
    objective: str = ""
    repository_path: str = ""

    status: str = WorkflowStatus.INTAKE
    active_step_id: str = ""
    next_agent: str = ""

    # Populated by the Planner
    architecture_summary: str = ""
    subtasks: list[SubtaskSpec] = field(default_factory=list)

    # Current subtask index
    current_subtask_idx: int = 0

    # Accumulated artifacts keyed by subtask id
    code_diffs: dict[str, str] = field(default_factory=dict)
    test_reports: dict[str, TestReport] = field(default_factory=dict)
    debug_diagnoses: dict[str, DebugDiagnosis] = field(default_factory=dict)
    review_verdicts: dict[str, ReviewVerdict] = field(default_factory=dict)

    # Token + cost tracking
    budget_tokens_remaining: int = 500_000
    total_tokens_used: int = 0

    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Human-readable event log
    event_log: list[str] = field(default_factory=list)

    def log_event(self, msg: str) -> None:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        entry = f"[{ts}] {msg}"
        self.event_log.append(entry)
        log.info(entry)

    @property
    def current_subtask(self) -> SubtaskSpec | None:
        if 0 <= self.current_subtask_idx < len(self.subtasks):
            return self.subtasks[self.current_subtask_idx]
        return None


# ---------------------------------------------------------------------------
# State persistence helpers
# ---------------------------------------------------------------------------

def _ensure_state_dir() -> None:
    os.makedirs(STATE_DIR, exist_ok=True)


def _subtask_to_dict(st: SubtaskSpec) -> dict:
    return asdict(st)


def _subtask_from_dict(d: dict) -> SubtaskSpec:
    return SubtaskSpec(**{k: v for k, v in d.items() if k in SubtaskSpec.__dataclass_fields__})


def _test_report_from_dict(d: dict) -> TestReport:
    return TestReport(**{k: v for k, v in d.items() if k in TestReport.__dataclass_fields__})


def _debug_diagnosis_from_dict(d: dict) -> DebugDiagnosis:
    return DebugDiagnosis(**{k: v for k, v in d.items() if k in DebugDiagnosis.__dataclass_fields__})


def _review_verdict_from_dict(d: dict) -> ReviewVerdict:
    return ReviewVerdict(**{k: v for k, v in d.items() if k in ReviewVerdict.__dataclass_fields__})


def save_state(state: WorkflowState) -> None:
    """Persist state to .orchestrator/state.json."""
    _ensure_state_dir()
    state.updated_at = datetime.now(timezone.utc).isoformat()

    raw: dict[str, Any] = {
        "task_id":              state.task_id,
        "objective":            state.objective,
        "repository_path":      state.repository_path,
        "status":               state.status,
        "active_step_id":       state.active_step_id,
        "next_agent":           state.next_agent,
        "architecture_summary": state.architecture_summary,
        "subtasks":             [_subtask_to_dict(s) for s in state.subtasks],
        "current_subtask_idx":  state.current_subtask_idx,
        "code_diffs":           state.code_diffs,
        "test_reports":         {k: asdict(v) for k, v in state.test_reports.items()},
        "debug_diagnoses":      {k: asdict(v) for k, v in state.debug_diagnoses.items()},
        "review_verdicts":      {k: asdict(v) for k, v in state.review_verdicts.items()},
        "budget_tokens_remaining": state.budget_tokens_remaining,
        "total_tokens_used":    state.total_tokens_used,
        "created_at":           state.created_at,
        "updated_at":           state.updated_at,
        "event_log":            state.event_log,
    }
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2)
    log.debug("State saved → %s", STATE_FILE)


def load_state() -> WorkflowState | None:
    """Load persisted state, or return None if no state file exists."""
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE, encoding="utf-8") as f:
        raw = json.load(f)

    state = WorkflowState(
        task_id              = raw.get("task_id", ""),
        objective            = raw.get("objective", ""),
        repository_path      = raw.get("repository_path", ""),
        status               = raw.get("status", WorkflowStatus.INTAKE),
        active_step_id       = raw.get("active_step_id", ""),
        next_agent           = raw.get("next_agent", ""),
        architecture_summary = raw.get("architecture_summary", ""),
        subtasks             = [_subtask_from_dict(s) for s in raw.get("subtasks", [])],
        current_subtask_idx  = raw.get("current_subtask_idx", 0),
        code_diffs           = raw.get("code_diffs", {}),
        test_reports         = {k: _test_report_from_dict(v) for k, v in raw.get("test_reports", {}).items()},
        debug_diagnoses      = {k: _debug_diagnosis_from_dict(v) for k, v in raw.get("debug_diagnoses", {}).items()},
        review_verdicts      = {k: _review_verdict_from_dict(v) for k, v in raw.get("review_verdicts", {}).items()},
        budget_tokens_remaining = raw.get("budget_tokens_remaining", 500_000),
        total_tokens_used    = raw.get("total_tokens_used", 0),
        created_at           = raw.get("created_at", ""),
        updated_at           = raw.get("updated_at", ""),
        event_log            = raw.get("event_log", []),
    )
    log.debug("State loaded ← %s (status=%s)", STATE_FILE, state.status)
    return state


def fresh_state(objective: str, repository_path: str = "") -> WorkflowState:
    """Create a brand-new workflow state."""
    state = WorkflowState(objective=objective, repository_path=repository_path)
    save_state(state)
    return state

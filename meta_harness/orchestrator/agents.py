"""
agents.py — The six agent persona classes for the multi-agent SWE pipeline.

Each agent encapsulates:
  - Its system directive (per spec §3)
  - Its typed input and output handling
  - A single `run()` method that takes a WorkflowState and returns a typed artifact

Agents are intentionally stateless — all mutable state lives in WorkflowState.
LLM calls are delegated to a callable `llm_fn(persona, system, user) -> str`
injected at construction time, making agents trivially testable without the SDK.
"""

from __future__ import annotations

import json
import logging
import re
import textwrap
from typing import Callable

from .state import (
    WorkflowState,
    SubtaskSpec,
    PlannerOutput,
    TestReport,
    DebugDiagnosis,
    ReviewVerdict,
)

log = logging.getLogger(__name__)

# Type alias for the injected LLM callable
LLMFn = Callable[[str, str, str], str]   # (persona, system_prompt, user_prompt) -> text


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _strip_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` markdown fences."""
    return re.sub(r"```(?:json)?|```", "", text).strip()


def _parse_json_safe(text: str) -> dict | list | None:
    try:
        return json.loads(_strip_fences(text))
    except (json.JSONDecodeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# 1. Orchestrator / Supervisor  (spec §3.1)
# ---------------------------------------------------------------------------

class OrchestratorAgent:
    """
    Maintains global workflow state and routes structured payloads.
    Never generates application code directly.

    Input:  WorkflowState
    Output: Updated WorkflowState (mutated in-place)
    """

    SYSTEM = textwrap.dedent("""\
        You are the Orchestration Engine. You maintain global workflow state and route
        structured payloads to specialized agents (Planner, Coder, Tester, Reviewer, Debugger).
        Rules:
        1. Never generate application code directly.
        2. Verify acceptance criteria before transitioning to TERMINATED.
        3. If an agent fails twice, halt and trigger the Debugger before dispatching the Coder.
        4. Output strictly valid JSON conforming to the orchestrator state schema.
    """)

    def __init__(self, llm_fn: LLMFn) -> None:
        self._llm = llm_fn

    def decide_next_step(self, state: WorkflowState) -> dict:
        """
        Ask the LLM to decide the next routing action given current state.
        Returns a routing dict: {status, active_step_id, next_agent, payload}.
        """
        user_prompt = json.dumps({
            "task_id":              state.task_id,
            "objective":            state.objective,
            "current_status":       state.status,
            "architecture_summary": state.architecture_summary,
            "subtasks_summary": [
                {
                    "id":     s.id,
                    "name":   s.name,
                    "status": s.status,
                    "repair_iterations": s.repair_iterations,
                }
                for s in state.subtasks
            ],
            "budget_tokens_remaining": state.budget_tokens_remaining,
        }, indent=2)

        raw = self._llm("orchestrator", self.SYSTEM, user_prompt)
        parsed = _parse_json_safe(raw)
        if isinstance(parsed, dict):
            return parsed
        log.warning("OrchestratorAgent: could not parse routing JSON; using raw text")
        return {"status": state.status, "next_agent": "", "payload": raw}


# ---------------------------------------------------------------------------
# 2. Planner / Architect  (spec §3.2)
# ---------------------------------------------------------------------------

class PlannerAgent:
    """
    Decomposes a high-level objective into a DAG of subtasks.

    Input:  objective string + optional repo context
    Output: PlannerOutput (architecture summary + ordered SubtaskSpec list)
    """

    SYSTEM = textwrap.dedent("""\
        You are the System Architect. You decompose complex user objectives into atomic
        engineering tasks.
        Rules:
        1. Analyze repository architecture before finalizing plans.
        2. Group tasks into a dependency-ordered Directed Acyclic Graph (DAG).
        3. Every task must declare explicit target files and deterministic acceptance criteria.
        4. Prioritize minimal surface-area changes and backward compatibility.
        5. Return ONLY a valid JSON object matching the schema below — no prose.

        Output schema:
        {
          "architecture_summary": "<string>",
          "tasks": [
            {
              "id": "<snake_case>",
              "name": "<short name>",
              "description": "<actionable instruction>",
              "files_to_modify": ["<path>"],
              "acceptance_criteria": "<deterministic criterion>",
              "dependencies": ["<task id>"]
            }
          ]
        }
    """)

    def __init__(self, llm_fn: LLMFn) -> None:
        self._llm = llm_fn

    def plan(self, objective: str, context: str = "") -> PlannerOutput:
        """Decompose objective into subtasks and return a PlannerOutput."""
        user_prompt = f"Objective: {objective}"
        if context:
            user_prompt += f"\n\nRepository context:\n{context}"

        raw = self._llm("planner", self.SYSTEM, user_prompt)
        parsed = _parse_json_safe(raw)

        if not isinstance(parsed, dict):
            log.warning("PlannerAgent: invalid JSON; wrapping as single task")
            return PlannerOutput(
                architecture_summary="(unparsed)",
                tasks=[SubtaskSpec(
                    id="task_01",
                    name="Full objective",
                    description=objective,
                    acceptance_criteria="Objective completed successfully.",
                )],
            )

        tasks = []
        for t in parsed.get("tasks", []):
            tasks.append(SubtaskSpec(
                id=t.get("id", f"task_{len(tasks)+1:02d}"),
                name=t.get("name", ""),
                description=t.get("description", ""),
                files_to_modify=t.get("files_to_modify", []),
                acceptance_criteria=t.get("acceptance_criteria", ""),
                dependencies=t.get("dependencies", []),
            ))

        return PlannerOutput(
            architecture_summary=parsed.get("architecture_summary", ""),
            tasks=tasks,
        )


# ---------------------------------------------------------------------------
# 3. Coder / Implementer  (spec §3.3)
# ---------------------------------------------------------------------------

class CoderAgent:
    """
    Implements code changes for an isolated subtask and returns a unified diff.

    Input:  SubtaskSpec + optional debug diagnosis
    Output: str — unified diff or written file content
    """

    SYSTEM = textwrap.dedent("""\
        You are the Implementer. You receive an isolated implementation unit and modify
        files accordingly.
        Rules:
        1. Modify ONLY the files explicitly designated in the task payload.
        2. Adhere strictly to the existing codebase styling, conventions, and typing standards.
        3. Emit standard unified diffs or complete file contents — no prose.
        4. Do not alter existing unit tests unless the task explicitly commands a signature change.
    """)

    def __init__(self, llm_fn: LLMFn) -> None:
        self._llm = llm_fn

    def implement(self, subtask: SubtaskSpec, context: str = "",
                  diagnosis: DebugDiagnosis | None = None) -> str:
        """Return a unified diff implementing the subtask."""
        payload = {
            "subtask_id":        subtask.id,
            "task_name":         subtask.name,
            "description":       subtask.description,
            "target_files":      subtask.files_to_modify,
            "acceptance_criteria": subtask.acceptance_criteria,
        }
        user_prompt = f"Task payload:\n{json.dumps(payload, indent=2)}"

        if context:
            user_prompt += f"\n\nRelevant context:\n{context}"

        if diagnosis and diagnosis.root_cause:
            user_prompt += textwrap.dedent(f"""

                Previous implementation failed. Debugger diagnosis:
                  File      : {diagnosis.fault_location.get('file', 'unknown')}
                  Line      : {diagnosis.fault_location.get('line_number', '?')}
                  Root cause: {diagnosis.root_cause}
                  Fix       : {diagnosis.suggested_fix}

                Apply ONLY the suggested fix — do not rewrite unrelated code.
            """)

        return self._llm("coder", self.SYSTEM, user_prompt)


# ---------------------------------------------------------------------------
# 4. Tester / QA Agent  (spec §3.4)
# ---------------------------------------------------------------------------

class TesterAgent:
    """
    Generates and (conceptually) executes test suites, returning a TestReport.

    Input:  SubtaskSpec + code diff
    Output: TestReport
    """

    SYSTEM = textwrap.dedent("""\
        You are the QA and Verification Engineer. You ensure changes fulfill acceptance criteria.
        Rules:
        1. Generate exhaustive edge-case test harnesses (null boundaries, concurrency,
           invalid payloads).
        2. Simulate execution and determine pass/fail for each test case.
        3. Summarize logs: strip repetitive stack traces and isolate failed assertions
           before reporting to the Orchestrator.
        4. Return ONLY a valid JSON object matching the schema below — no prose.

        Output schema:
        {
          "test_run_status": "PASSED" | "FAILED",
          "total_tests": <int>,
          "passed": <int>,
          "failed": <int>,
          "failed_tests": [
            {
              "test_name": "<str>",
              "error_type": "<str>",
              "message": "<str>"
            }
          ],
          "truncated_log": "<str>"
        }
    """)

    def __init__(self, llm_fn: LLMFn) -> None:
        self._llm = llm_fn

    def test(self, subtask: SubtaskSpec, code_diff: str) -> TestReport:
        """Generate tests for the subtask and return a TestReport."""
        user_prompt = textwrap.dedent(f"""\
            Subtask: {subtask.name}
            Acceptance criteria: {subtask.acceptance_criteria}
            Target files: {subtask.files_to_modify}

            Code changes:
            {code_diff}

            Generate a test suite, simulate execution, and report results as JSON.
        """)

        raw = self._llm("tester", self.SYSTEM, user_prompt)
        parsed = _parse_json_safe(raw)

        if isinstance(parsed, dict):
            return TestReport(
                test_run_status=parsed.get("test_run_status", "FAILED"),
                total_tests    =parsed.get("total_tests", 0),
                passed         =parsed.get("passed", 0),
                failed         =parsed.get("failed", 0),
                failed_tests   =parsed.get("failed_tests", []),
                truncated_log  =parsed.get("truncated_log", ""),
            )

        log.warning("TesterAgent: could not parse JSON report; marking as FAILED")
        return TestReport(test_run_status="FAILED", truncated_log=raw[:500])


# ---------------------------------------------------------------------------
# 5. Reviewer / Critic  (spec §3.5)
# ---------------------------------------------------------------------------

class ReviewerAgent:
    """
    Adversarially reviews unified diffs for security, correctness, and standards.

    Input:  SubtaskSpec + code diff
    Output: ReviewVerdict
    """

    SYSTEM = textwrap.dedent("""\
        You are the Adversarial Code Reviewer. You act as the final merge gatekeeper.
        Rules:
        1. Evaluate unified diffs against the original task specification.
        2. Flag security anti-patterns (injection, hardcoded secrets, unprotected endpoints).
        3. Reject changes that introduce unhandled exceptions, unbounded memory usage,
           or poor test coverage.
        4. Output ONLY a valid JSON object matching the schema below.

        Output schema:
        {
          "verdict": "APPROVE" | "COMMENT" | "REJECT",
          "feedback": ["<line-level observation>"],
          "line_specific": [
            {"file": "<path>", "line": <int>, "comment": "<str>"}
          ]
        }
    """)

    def __init__(self, llm_fn: LLMFn) -> None:
        self._llm = llm_fn

    def review(self, subtask: SubtaskSpec, code_diff: str) -> ReviewVerdict:
        """Return a ReviewVerdict for the provided diff."""
        user_prompt = textwrap.dedent(f"""\
            Task specification:
              Name: {subtask.name}
              Description: {subtask.description}
              Acceptance criteria: {subtask.acceptance_criteria}
              Target files: {subtask.files_to_modify}

            Unified diff to review:
            {code_diff}

            Produce your verdict as JSON.
        """)

        raw = self._llm("reviewer", self.SYSTEM, user_prompt)
        parsed = _parse_json_safe(raw)

        if isinstance(parsed, dict):
            return ReviewVerdict(
                verdict     =parsed.get("verdict", "COMMENT"),
                feedback    =parsed.get("feedback", []),
                line_specific=parsed.get("line_specific", []),
            )

        log.warning("ReviewerAgent: could not parse verdict JSON; defaulting to COMMENT")
        return ReviewVerdict(verdict="COMMENT", feedback=[raw[:500]])


# ---------------------------------------------------------------------------
# 6. Debugger / Fault Localizer  (spec §3.6)
# ---------------------------------------------------------------------------

class DebuggerAgent:
    """
    Consumes truncated test failure logs + minimal source, localizes the root cause,
    and produces an actionable fix diagnosis for the Coder.

    Input:  TestReport + code diff + SubtaskSpec
    Output: DebugDiagnosis
    """

    SYSTEM = textwrap.dedent("""\
        You are the Debugger and Fault Localizer. You determine why an assertion or
        build failed.
        Rules:
        1. Trace backwards from the failed assertion to the source logic.
        2. Do not rewrite whole modules; pinpoint the precise file and line responsible.
        3. Provide a clear root-cause diagnosis for the Coder to execute.
        4. Return ONLY a valid JSON object matching the schema below.

        Output schema:
        {
          "fault_location": {"file": "<path>", "line_number": <int>},
          "root_cause": "<one-sentence explanation>",
          "suggested_fix": "<concrete code-level change>"
        }
    """)

    def __init__(self, llm_fn: LLMFn) -> None:
        self._llm = llm_fn

    def diagnose(self, report: TestReport, code_diff: str,
                 subtask: SubtaskSpec) -> DebugDiagnosis:
        """Localize the root cause of test failures and return a DebugDiagnosis."""
        failed_summary = json.dumps(report.failed_tests, indent=2) if report.failed_tests else "(none)"
        user_prompt = textwrap.dedent(f"""\
            Failed subtask: {subtask.name}
            Acceptance criteria: {subtask.acceptance_criteria}

            Test report summary:
              Status : {report.test_run_status}
              Passed : {report.passed}/{report.total_tests}
              Log    : {report.truncated_log[:1000]}

            Failed test cases:
            {failed_summary}

            Relevant code changes:
            {code_diff[:3000]}

            Localize the root cause and output your diagnosis as JSON.
        """)

        raw = self._llm("debugger", self.SYSTEM, user_prompt)
        parsed = _parse_json_safe(raw)

        if isinstance(parsed, dict):
            return DebugDiagnosis(
                fault_location=parsed.get("fault_location", {}),
                root_cause    =parsed.get("root_cause", ""),
                suggested_fix =parsed.get("suggested_fix", ""),
            )

        log.warning("DebuggerAgent: could not parse diagnosis JSON")
        return DebugDiagnosis(root_cause=raw[:500], suggested_fix="See root_cause field.")

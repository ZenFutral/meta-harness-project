"""
orchestrator.py — Full hierarchical multi-agent SWE orchestration pipeline.

Implements the spec's Hub-and-Spoke Topology (§1) and State Machine (§4):

  INTAKE → PLANNING → CODING → TESTING
                                  |
                         FAILED → DEBUGGING → CODING (loop, max 3x)
                                  |
                         PASSED → REVIEWING
                                  |
                         REJECTED → PLANNING (escalation on architectural failure)
                                  |
                         APPROVED → COMPLETE

Safety & Loop Guards (§4):
  - Max 3 Coder→Tester→Debugger→Coder repair loops per subtask.
  - After 3 failures the Planner is re-engaged (escalation_count tracked).
  - Token budget circuit breaker: BudgetExceeded halts the entire session.

Context Hygiene (§1):
  - Raw outputs are never passed raw across agent boundaries; only typed artifacts.
  - State persists in .orchestrator/state.json, not in LLM memory.
"""

from __future__ import annotations

import json
import logging
import re
import textwrap
from typing import Any

from .budget import BudgetTracker, BudgetExceeded, check_and_update_budget
try:
    from router.router import ModelRouter
except ImportError:
    from .router import ModelRouter
from .state import (
    WorkflowState, WorkflowStatus, SubtaskStatus,
    PlannerOutput, TestReport, DebugDiagnosis, ReviewVerdict,
    SubtaskSpec, fresh_state, save_state, load_state,
)
from .agents import (
    OrchestratorAgent, PlannerAgent, CoderAgent,
    TesterAgent, ReviewerAgent, DebuggerAgent,
)
from .config import MAX_REFINEMENT_ITERATIONS, MAX_ESCALATION_RETRIES, BUDGET

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Token estimation helper (unchanged from original)
# ---------------------------------------------------------------------------

def _estimate_tokens(text: str) -> int:
    """Rough approximation: ~4 chars per token."""
    return max(1, len(text) // 4)


# ---------------------------------------------------------------------------
# Legacy subtask parser (kept for backward compat with simple decompose path)
# ---------------------------------------------------------------------------

def _parse_subtasks(raw: str) -> list[dict[str, str]]:
    """
    Parse the decomposition response. Expects JSON array of objects with
    keys 'id', 'description', 'input_contract', 'output_contract'.
    Falls back to a single-item list if parsing fails.
    """
    cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()
    try:
        tasks = json.loads(cleaned)
        if isinstance(tasks, list):
            return tasks
    except json.JSONDecodeError:
        pass
    log.warning("Could not parse subtasks as JSON; wrapping raw text as one task.")
    return [{"id": "task_1", "description": raw, "input_contract": "", "output_contract": ""}]


# ---------------------------------------------------------------------------
# Core Orchestrator
# ---------------------------------------------------------------------------

class Orchestrator:
    """
    Hierarchical Hub-and-Spoke Orchestrator.

    Drives the full agentic lifecycle per the specification:
      1. Intake the goal and initialise state.
      2. Dispatch the Planner to produce a task DAG.
      3. For each subtask, run the Coding → Testing loop (with Debugger on failures).
      4. Gate each subtask through the Reviewer.
      5. Re-engage the Planner on repeated architectural failures.
      6. Enforce token-budget circuit breakers at every step.

    Args:
        project:  GCP project ID.
        location: Vertex AI region (default: us-central1).
        backend:  "vertex" (default) or "antigravity".
        resume:   If True, attempt to resume from persisted state.
    """

    def __init__(
        self,
        project: str = "meta-harness",
        location: str = "us-central1",
        backend: str = "vertex",
        resume: bool = False,
    ) -> None:
        """Initialize the Orchestrator with project, location, backend, and resume flag.

        Sets up the router, budget tracker, and agent instances. Also builds a mapping
        from each persona to its configured model ID based on the backend.
        """
        import vertexai as _vertexai
        _vertexai.init(project=project, location=location)

        self.router   = ModelRouter(backend=backend)
        self.budget   = BudgetTracker()
        self._project  = project
        self._location = location

        # Wire up the six agent personas
        self._orchestrator_agent = OrchestratorAgent(self._llm_call)
        self._planner            = PlannerAgent(self._llm_call)
        self._coder              = CoderAgent(self._llm_call)
        self._tester             = TesterAgent(self._llm_call)
        self._reviewer           = ReviewerAgent(self._llm_call)
        self._debugger           = DebuggerAgent(self._llm_call)

        self._resume = resume

        # Build a dict mapping each persona to its model ID for quick lookup
        self._persona_model_map: dict[str, str] = {
            persona: self.router.model_id_for_persona(persona)
            for persona in [
                "orchestrator",
                "planner",
                "coder",
                "tester",
                "reviewer",
                "debugger",
            ]
        }

        import vertexai as _vertexai
        _vertexai.init(project=project, location=location)

        self.router   = ModelRouter(backend=backend)
        self.budget   = BudgetTracker()
        self._project  = project
        self._location = location

        # Wire up the six agent personas
        self._orchestrator_agent = OrchestratorAgent(self._llm_call)
        self._planner            = PlannerAgent(self._llm_call)
        self._coder              = CoderAgent(self._llm_call)
        self._tester             = TesterAgent(self._llm_call)
        self._reviewer           = ReviewerAgent(self._llm_call)
        self._debugger           = DebuggerAgent(self._llm_call)

        self._resume = resume

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, goal: str, context: str = "", repository_path: str = "") -> dict[str, Any]:
        """
        Execute the full orchestration pipeline for a user goal.

        Returns:
            {
                "task_id":  str,
                "goal":     str,
                "status":   str,
                "subtasks": [...],
                "budget":   str,
                "success":  bool,
                "event_log": [...],
            }
        """
        log.info("Orchestrator.run() — goal: %s", goal[:120])

        # Initialise or resume state
        if self._resume:
            state = load_state()
            if state:
                log.info("Resuming workflow %s (status=%s)", state.task_id, state.status)
            else:
                log.info("No prior state found; starting fresh.")
                state = fresh_state(goal, repository_path)
        else:
            state = fresh_state(goal, repository_path)

        state.objective = goal

        try:
            self._run_pipeline(state, context)
        except BudgetExceeded as exc:
            log.error("Budget exceeded: %s", exc)
            state.status = WorkflowStatus.FAILED
            state.log_event(f"BUDGET EXCEEDED: {exc}")
            save_state(state)

        return self._build_result(state)

    # ------------------------------------------------------------------
    # Pipeline driver
    # ------------------------------------------------------------------

    def _run_pipeline(self, state: WorkflowState, context: str) -> None:
        """
        Drive the state machine until COMPLETE or FAILED.
        """
        # --- INTAKE → PLANNING ---
        if state.status in (WorkflowStatus.INTAKE, WorkflowStatus.PLANNING):
            state.status = WorkflowStatus.PLANNING
            state.log_event("Phase: PLANNING — dispatching Planner agent")
            save_state(state)
            self._phase_planning(state, context)

        # --- Process subtasks ---
        while state.current_subtask_idx < len(state.subtasks):
            subtask = state.subtasks[state.current_subtask_idx]

            if subtask.status in (SubtaskStatus.COMPLETE,):
                state.current_subtask_idx += 1
                save_state(state)
                continue

            # Check escalation guard
            if subtask.escalation_count >= MAX_ESCALATION_RETRIES:
                state.log_event(
                    f"Subtask {subtask.id}: escalation_count={subtask.escalation_count} "
                    f"exceeded MAX_ESCALATION_RETRIES={MAX_ESCALATION_RETRIES}. "
                    "Alerting human operator — halting."
                )
                state.status = WorkflowStatus.FAILED
                save_state(state)
                return

            state.log_event(f"Processing subtask [{subtask.id}]: {subtask.name}")

            # --- CODING ---
            state.status = WorkflowStatus.CODING
            save_state(state)
            code_diff = self._phase_coding(state, subtask, context)
            state.code_diffs[subtask.id] = code_diff

            # --- Repair loop: TESTING → DEBUGGING → CODING ---
            repair_ok = self._repair_loop(state, subtask, code_diff, context)

            if not repair_ok:
                # Re-engage Planner (escalation)
                subtask.escalation_count += 1
                state.log_event(
                    f"Subtask {subtask.id}: repair loop exhausted "
                    f"(escalation #{subtask.escalation_count}). Re-engaging Planner."
                )
                state.status = WorkflowStatus.PLANNING
                save_state(state)
                self._phase_planning(state, context)   # replanned subtasks
                continue   # restart while loop with updated subtasks

            # --- REVIEWING ---
            state.status = WorkflowStatus.REVIEWING
            save_state(state)
            approved = self._phase_reviewing(state, subtask, state.code_diffs[subtask.id])

            if not approved:
                # Reviewer rejected — re-engage Planner (architectural failure path)
                subtask.escalation_count += 1
                state.log_event(
                    f"Subtask {subtask.id}: REJECTED by Reviewer "
                    f"(escalation #{subtask.escalation_count}). Re-engaging Planner."
                )
                state.status = WorkflowStatus.PLANNING
                save_state(state)
                self._phase_planning(state, context)
                continue

            subtask.status = SubtaskStatus.COMPLETE
            state.current_subtask_idx += 1
            state.log_event(f"Subtask [{subtask.id}] COMPLETE ✓")
            save_state(state)

            # Budget guards between subtasks
            self.budget.check_session()

        # All subtasks done
        state.status = WorkflowStatus.COMPLETE
        state.log_event("All subtasks complete — workflow COMPLETE ✓")
        save_state(state)

    # ------------------------------------------------------------------
    # Phase: Planning
    # ------------------------------------------------------------------

    def _phase_planning(self, state: WorkflowState, context: str) -> None:
        """Dispatch the Planner and populate state.subtasks."""
        self.budget.reset_task()
        plan: PlannerOutput = self._planner.plan(state.objective, context)

        state.architecture_summary = plan.architecture_summary
        # Preserve statuses of already-completed subtasks on re-plan
        completed_ids = {s.id for s in state.subtasks if s.status == SubtaskStatus.COMPLETE}
        new_tasks = [t for t in plan.tasks if t.id not in completed_ids]

        if state.subtasks:
            # Re-plan: keep completed, replace rest
            state.subtasks = [s for s in state.subtasks if s.status == SubtaskStatus.COMPLETE] + new_tasks
            state.current_subtask_idx = sum(
                1 for s in state.subtasks if s.status == SubtaskStatus.COMPLETE
            )
        else:
            state.subtasks = plan.tasks
            state.current_subtask_idx = 0

        state.log_event(
            f"Planner produced {len(plan.tasks)} task(s): "
            + ", ".join(t.id for t in plan.tasks)
        )
        save_state(state)

    # ------------------------------------------------------------------
    # Phase: Coding
    # ------------------------------------------------------------------

    def _phase_coding(self, state: WorkflowState, subtask: SubtaskSpec,
                      context: str) -> str:
        """Dispatch the Coder for the subtask. Returns unified diff."""
        self.budget.reset_task()
        subtask.status = SubtaskStatus.RUNNING

        # Attach last debug diagnosis if available
        diagnosis = state.debug_diagnoses.get(subtask.id)
        diff = self._coder.implement(subtask, context=context, diagnosis=diagnosis)

        state.log_event(f"Coder produced diff for [{subtask.id}] ({len(diff)} chars)")
        self.budget.check_task()
        self.budget.check_session()
        return diff

    # ------------------------------------------------------------------
    # Phase: Testing + Debug repair loop
    # ------------------------------------------------------------------

    def _repair_loop(self, state: WorkflowState, subtask: SubtaskSpec,
                     initial_diff: str, context: str) -> bool:
        """
        Runs the Coder → Tester → Debugger → Coder cycle up to
        MAX_REFINEMENT_ITERATIONS times.

        Returns True if tests pass within the budget, False otherwise.
        """
        code_diff = initial_diff

        for iteration in range(1, MAX_REFINEMENT_ITERATIONS + 1):
            # --- Testing ---
            state.status = WorkflowStatus.TESTING
            save_state(state)
            state.log_event(f"[{subtask.id}] Tester iteration {iteration}")

            report: TestReport = self._tester.test(subtask, code_diff)
            state.test_reports[subtask.id] = report
            save_state(state)

            if report.test_run_status == "PASSED":
                subtask.repair_iterations = iteration
                state.log_event(f"[{subtask.id}] Tests PASSED on iteration {iteration}")
                return True

            state.log_event(
                f"[{subtask.id}] Tests FAILED ({report.failed}/{report.total_tests}) "
                f"on iteration {iteration}"
            )

            if iteration == MAX_REFINEMENT_ITERATIONS:
                break  # Exhausted — bubble up to escalation

            # --- Debugging ---
            state.status = WorkflowStatus.DEBUGGING
            save_state(state)
            state.log_event(f"[{subtask.id}] Dispatching Debugger (iteration {iteration})")

            diagnosis: DebugDiagnosis = self._debugger.diagnose(report, code_diff, subtask)
            state.debug_diagnoses[subtask.id] = diagnosis
            save_state(state)

            state.log_event(
                f"[{subtask.id}] Debugger root cause: {diagnosis.root_cause[:120]}"
            )

            # --- Re-code with diagnosis ---
            state.status = WorkflowStatus.CODING
            save_state(state)
            code_diff = self._coder.implement(subtask, context=context, diagnosis=diagnosis)
            state.code_diffs[subtask.id] = code_diff

            self.budget.check_task()
            self.budget.check_session()

        subtask.repair_iterations = MAX_REFINEMENT_ITERATIONS
        state.log_event(
            f"[{subtask.id}] Repair loop exhausted after {MAX_REFINEMENT_ITERATIONS} iterations"
        )
        return False

    # ------------------------------------------------------------------
    # Phase: Reviewing
    # ------------------------------------------------------------------

    def _phase_reviewing(self, state: WorkflowState, subtask: SubtaskSpec,
                         code_diff: str) -> bool:
        """
        Dispatch the Reviewer. Returns True if APPROVE, False if REJECT/COMMENT.
        """
        self.budget.reset_task()
        verdict: ReviewVerdict = self._reviewer.review(subtask, code_diff)
        state.review_verdicts[subtask.id] = verdict
        save_state(state)

        state.log_event(
            f"[{subtask.id}] Reviewer verdict: {verdict.verdict} | "
            + "; ".join(verdict.feedback[:2])
        )

        self.budget.check_task()
        self.budget.check_session()
        return verdict.verdict == "APPROVE"

    # ------------------------------------------------------------------
    # LLM call (Vertex AI Generative Models)
    # ------------------------------------------------------------------

    def _llm_call(self, persona: str, system: str, user: str) -> str:
        """
        Dispatch a single LLM call for the given persona.

        Uses the persona-specific model ID from the router, records token usage,
        and enforces budget circuit breakers.
        """
        input_est = max(1, len(user) // 4)
        if not check_and_update_budget(input_est):
            log.warning("Daily quota cap ($0.33/day) reached before LLM call for persona %s. Tripping circuit breaker.", persona)
            return f"[LOCAL_FALLBACK] Daily budget cap ($0.33) reached for persona {persona}."

        import vertexai  # noqa: F401
        from vertexai.generative_models import GenerativeModel, GenerationConfig

        # Use the pre-computed persona->model map for consistency and avoid repeated look-ups
        model_id = self._persona_model_map.get(persona, self.router.model_id_for_persona(persona))
        log.debug("LLM call: persona=%s model=%s", persona, model_id)

        model = GenerativeModel(
            model_name=model_id,
            system_instruction=system,
        )
        response = model.generate_content(
            contents=user,
            generation_config=GenerationConfig(temperature=0.2),
        )

        usage = response.usage_metadata
        cost  = self.budget.record(
            tier=persona,
            input_tokens=usage.prompt_token_count,
            output_tokens=usage.candidates_token_count,
        )
        log.debug(
            "Usage: persona=%s in=%d out=%d cost=$%.6f",
            persona, usage.prompt_token_count, usage.candidates_token_count, cost,
        )

        self.budget.check_session()
        self.budget.check_task()

        return response.text

    # ------------------------------------------------------------------
    # Result builder
    # ------------------------------------------------------------------

    def _build_result(self, state: WorkflowState) -> dict[str, Any]:
        """Construct the final result dict for the orchestrator run.

        Includes a snapshot of the model configuration used for each persona.
        """
        # Include model config snapshot for debugging / audit
        state.model_config = getattr(self, "_persona_model_map", {persona: self.router.model_id_for_persona(persona) for persona in ["orchestrator", "planner", "coder", "tester", "reviewer", "debugger"]})
        subtask_summaries = []
        subtask_summaries = []
        for st in state.subtasks:
            entry: dict[str, Any] = {
                "id":                st.id,
                "name":              st.name,
                "status":            st.status,
                "repair_iterations": st.repair_iterations,
                "escalation_count":  st.escalation_count,
            }
            # Attach diff (truncated)
            diff = state.code_diffs.get(st.id, "")
            entry["diff_preview"] = diff[:500] + ("…" if len(diff) > 500 else "")

            # Attach test report if present
            report = state.test_reports.get(st.id)
            if report:
                entry["test_report"] = {
                    "status":  report.test_run_status,
                    "passed":  report.passed,
                    "failed":  report.failed,
                    "total":   report.total_tests,
                }

            # Attach review verdict if present
            verdict = state.review_verdicts.get(st.id)
            if verdict:
                entry["review_verdict"] = verdict.verdict

            subtask_summaries.append(entry)

        return {
            "task_id":   state.task_id,
            "goal":      state.objective,
            "status":    state.status,
            "subtasks":  subtask_summaries,
            "budget":    self.budget.summary(),
            "success":   state.status == WorkflowStatus.COMPLETE,
            "event_log": state.event_log,
        }

    # ------------------------------------------------------------------
    # Legacy simple-orchestrator helpers (kept for backward compat / tests)
    # ------------------------------------------------------------------

    def _decompose(self, goal: str, context: str) -> list[dict]:
        """Legacy decompose path (used only by tests that bypass the new pipeline)."""
        system_prompt = textwrap.dedent("""\
            You are an expert task decomposer.
            Break the user's goal into discrete, single-purpose subtasks.
            Return ONLY a JSON array. Each element must have:
              - "id":               unique short identifier (snake_case)
              - "description":      clear, actionable instruction for one agent
              - "input_contract":   what inputs the subtask requires
              - "output_contract":  exact format/schema of the expected output
            Keep subtasks minimal — combine where possible to reduce API calls.
        """)
        prompt = f"Goal: {goal}"
        if context:
            prompt += f"\n\nAdditional context:\n{context}"

        tier = self.router.select(prompt, _estimate_tokens(prompt))
        raw  = self._llm_call(tier=tier, system=system_prompt, user=prompt)
        return _parse_subtasks(raw)

    def _validate(self, output: str, contract: str) -> str:
        """
        Lightweight deterministic validation (kept for legacy tests).
        Returns empty string on success, error string on failure.
        """
        if not output.strip():
            return "Output is empty."
        if "json" in contract.lower():
            try:
                json.loads(re.sub(r"```(?:json)?|```", "", output).strip())
            except json.JSONDecodeError as exc:
                return f"JSON validation failed: {exc}\n\nOutput was:\n{output[:500]}"
        return ""

    @staticmethod
    def _execution_system_prompt() -> str:
        return textwrap.dedent("""\
            You are a precise execution agent. Complete the assigned subtask
            exactly as described. Produce only the requested output in the
            specified format — no preamble, no explanation unless asked.
        """)

    @staticmethod
    def _build_execution_prompt(description: str, contract: str,
                                last_error: str, context: str) -> str:
        parts = [f"Task: {description}"]
        if contract:
            parts.append(f"Output format: {contract}")
        if context:
            parts.append(f"Context:\n{context}")
        if last_error:
            parts.append(
                f"Your previous attempt failed validation. Fix ONLY the following issue:\n{last_error}"
            )
        return "\n\n".join(parts)

"""
tests.py — Unit tests for the multi-agent SWE orchestration library.

Covers:
  - BudgetTracker     (budget.py)
  - ModelRouter       (router.py)
  - State machine     (state.py)
  - All 6 agent personas  (agents.py)
  - Orchestrator validation + legacy helpers  (orchestrator.py)

No Vertex AI calls are made — all LLM interactions are mocked.

Run with:  python tests.py
"""

from __future__ import annotations
import json
import os
import sys
import types
import tempfile
import types
import unittest
from pathlib import Path

ORCH_DIR = Path(__file__).resolve().parent
META_DIR = ORCH_DIR.parent
for d in [str(META_DIR), str(ORCH_DIR)]:
    if d not in sys.path:
        sys.path.insert(0, d)
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Provide a lightweight vertexai stub so orchestrator.py can be imported
# without the real SDK being installed.
# ---------------------------------------------------------------------------
_vertexai_stub = types.ModuleType("vertexai")
_vertexai_stub.init = MagicMock()  # type: ignore[attr-defined]
_genai_stub = types.ModuleType("vertexai.generative_models")
_genai_stub.GenerativeModel = MagicMock()   # type: ignore[attr-defined]
_genai_stub.GenerationConfig = MagicMock()  # type: ignore[attr-defined]
sys.modules.setdefault("vertexai", _vertexai_stub)
sys.modules.setdefault("vertexai.generative_models", _genai_stub)


# ===========================================================================
# BudgetTracker tests
# ===========================================================================
class TestBudgetTracker(unittest.TestCase):

    def setUp(self):
        from orchestrator.budget import BudgetTracker
        self.tracker = BudgetTracker()

    def test_record_returns_nonzero_cost(self):
        cost = self.tracker.record("flash", input_tokens=1000, output_tokens=500)
        self.assertGreater(cost, 0)

    def test_session_cost_accumulates(self):
        self.tracker.record("flash", 500, 200)
        self.tracker.record("flash", 500, 200)
        self.assertEqual(len(self.tracker._session_records), 2)

    def test_task_reset(self):
        self.tracker.record("flash", 500, 200)
        self.tracker.reset_task()
        self.assertEqual(self.tracker.task_cost, 0.0)
        self.assertGreater(self.tracker.session_cost, 0)

    def test_session_hard_stop(self):
        from orchestrator.budget import BudgetExceeded
        from orchestrator.config import BUDGET
        with patch("orchestrator.budget.BUDGET", {**BUDGET, "session_hard_stop_usd": 0.000001,
                                                 "session_warn_usd": 0.0}):
            from orchestrator.budget import BudgetTracker
            t = BudgetTracker()
            t.record("flash", 1000, 1000)
            with self.assertRaises(BudgetExceeded):
                t.check_session()

    def test_task_hard_stop(self):
        from orchestrator.budget import BudgetExceeded
        from orchestrator.config import BUDGET
        with patch("orchestrator.budget.BUDGET", {**BUDGET, "task_hard_stop_usd": 0.000001}):
            from orchestrator.budget import BudgetTracker
            t = BudgetTracker()
            t.record("flash", 1000, 1000)
            with self.assertRaises(BudgetExceeded):
                t.check_task()

    def test_summary_contains_cost(self):
        self.tracker.record("pro", 100, 50)
        summary = self.tracker.summary()
        self.assertIn("Session cost", summary)
        self.assertIn("[pro]", summary)

    def test_persona_tier_recorded(self):
        """New persona tiers (e.g. 'coder') are recorded correctly."""
        from orchestrator.budget import BudgetTracker
        t = BudgetTracker()
        cost = t.record("coder", 500, 250)
        self.assertGreater(cost, 0)
        self.assertIn("[coder]", t.summary())


# ===========================================================================
# ModelRouter tests
# ===========================================================================
class TestModelRouter(unittest.TestCase):

    def setUp(self):
        from router.router import ModelRouter
        self.router = ModelRouter()

    def test_low_complexity_returns_flash(self):
        tier = self.router.select("Summarize this paragraph", prompt_token_estimate=100)
        self.assertEqual(tier, "flash")

    def test_high_token_count_escalates_to_pro(self):
        tier = self.router.select("Do something", prompt_token_estimate=10_000)
        self.assertEqual(tier, "pro")

    def test_reasoning_keyword_escalates_to_pro(self):
        tier = self.router.select("Explain why this fails", prompt_token_estimate=50)
        self.assertEqual(tier, "pro")

    def test_escalate(self):
        self.assertEqual(self.router.escalate("flash"), "pro")

    def test_escalate_at_max_stays(self):
        self.assertEqual(self.router.escalate("pro"), "pro")

    def test_downgrade(self):
        self.assertEqual(self.router.downgrade("pro"), "flash")

    def test_downgrade_at_min_stays(self):
        self.assertEqual(self.router.downgrade("flash"), "flash")

    def test_model_id_returns_string(self):
        from orchestrator.config import MODELS
        self.assertEqual(self.router.model_id("flash"), MODELS["flash"])

    def test_persona_routing_all_personas(self):
        """Every persona should resolve to a non-empty model string."""
        from orchestrator.config import PERSONAS
        for persona in PERSONAS:
            model = self.router.model_id_for_persona(persona)
            self.assertIsInstance(model, str)
            self.assertGreater(len(model), 0, f"Empty model ID for persona: {persona}")

    def test_unknown_persona_falls_back(self):
        """Unknown persona should not raise, just fall back."""
        model = self.router.model_id_for_persona("nonexistent_persona")
        self.assertIsInstance(model, str)

    def test_antigravity_backend(self):
        from router.router import ModelRouter
        router = ModelRouter(backend="antigravity")
        from orchestrator.config import MODELS_ANTIGRAVITY
        self.assertEqual(router.model_id_for_persona("orchestrator"),
                         MODELS_ANTIGRAVITY["orchestrator"])


# ===========================================================================
# State machine tests
# ===========================================================================
class TestWorkflowState(unittest.TestCase):

    def setUp(self):
        # Use a temp directory for state files
        self._tmpdir = tempfile.mkdtemp()
        # Patch config paths
        import orchestrator.config as config
        self._orig_state_dir  = config.STATE_DIR
        self._orig_state_file = config.STATE_FILE
        config.STATE_DIR  = os.path.join(self._tmpdir, ".orchestrator")
        config.STATE_FILE = os.path.join(config.STATE_DIR, "state.json")
        # Reload state module so patches take effect
        import importlib
        import orchestrator.state as state_mod
        importlib.reload(state_mod)
        self.state_mod = state_mod

    def tearDown(self):
        import config
        config.STATE_DIR  = self._orig_state_dir
        config.STATE_FILE = self._orig_state_file
        import importlib, state as state_mod
        importlib.reload(state_mod)

    def test_fresh_state_creates_file(self):
        state = self.state_mod.fresh_state("Build a rate limiter")
        self.assertTrue(os.path.exists(self.state_mod.STATE_FILE))
        self.assertEqual(state.status, self.state_mod.WorkflowStatus.INTAKE)

    def test_save_and_load_roundtrip(self):
        state = self.state_mod.fresh_state("Test roundtrip")
        state.architecture_summary = "Use Redis sliding window."
        self.state_mod.save_state(state)

        loaded = self.state_mod.load_state()
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.architecture_summary, "Use Redis sliding window.")
        self.assertEqual(loaded.task_id, state.task_id)

    def test_load_state_returns_none_when_missing(self):
        result = self.state_mod.load_state()
        self.assertIsNone(result)

    def test_log_event_appends(self):
        state = self.state_mod.fresh_state("Log test")
        state.log_event("Step 1 started")
        state.log_event("Step 2 started")
        self.assertEqual(len(state.event_log), 2)
        self.assertIn("Step 1 started", state.event_log[0])

    def test_subtask_serialization(self):
        from state import SubtaskSpec, WorkflowState, save_state, load_state
        state = self.state_mod.fresh_state("Subtask test")
        state.subtasks = [
            self.state_mod.SubtaskSpec(
                id="t01", name="Setup", description="Configure env",
                files_to_modify=["pyproject.toml"],
                acceptance_criteria="redis-py installed",
            )
        ]
        self.state_mod.save_state(state)
        loaded = self.state_mod.load_state()
        self.assertEqual(len(loaded.subtasks), 1)
        self.assertEqual(loaded.subtasks[0].id, "t01")
        self.assertEqual(loaded.subtasks[0].files_to_modify, ["pyproject.toml"])

    def test_current_subtask_property(self):
        state = self.state_mod.fresh_state("Prop test")
        self.assertIsNone(state.current_subtask)
        state.subtasks = [self.state_mod.SubtaskSpec(id="t01", name="X", description="Y")]
        state.current_subtask_idx = 0
        self.assertEqual(state.current_subtask.id, "t01")


# ===========================================================================
# Agent persona unit tests (LLM mocked)
# ===========================================================================

def _make_llm(response: str):
    """Return a simple mock LLM function that always returns `response`."""
    return MagicMock(return_value=response)


class TestPlannerAgent(unittest.TestCase):

    def test_valid_json_plan(self):
        from orchestrator.agents import PlannerAgent
        plan_json = json.dumps({
            "architecture_summary": "Redis sliding window",
            "tasks": [
                {
                    "id": "task_01",
                    "name": "Setup",
                    "description": "Install redis-py",
                    "files_to_modify": ["pyproject.toml"],
                    "acceptance_criteria": "redis-py >= 5.0.0 present",
                    "dependencies": [],
                }
            ]
        })
        agent = PlannerAgent(_make_llm(plan_json))
        result = agent.plan("Add rate-limiting")
        self.assertEqual(result.architecture_summary, "Redis sliding window")
        self.assertEqual(len(result.tasks), 1)
        self.assertEqual(result.tasks[0].id, "task_01")

    def test_invalid_json_fallback(self):
        from orchestrator.agents import PlannerAgent
        agent = PlannerAgent(_make_llm("Not valid JSON at all"))
        result = agent.plan("Do something")
        self.assertEqual(len(result.tasks), 1)
        self.assertEqual(result.tasks[0].id, "task_01")

    def test_plan_with_context(self):
        from orchestrator.agents import PlannerAgent
        plan_json = json.dumps({
            "architecture_summary": "Simple",
            "tasks": [{"id": "t1", "name": "N", "description": "D",
                        "files_to_modify": [], "acceptance_criteria": "", "dependencies": []}]
        })
        llm = _make_llm(plan_json)
        agent = PlannerAgent(llm)
        agent.plan("Goal", context="Some repo context")
        call_args = llm.call_args[0]  # positional: (persona, system, user)
        self.assertIn("Some repo context", call_args[2])


class TestCoderAgent(unittest.TestCase):

    def _make_subtask(self):
        from orchestrator.state import SubtaskSpec
        return SubtaskSpec(
            id="t01", name="Rate limiter", description="Implement token bucket",
            files_to_modify=["src/middleware/rate_limiter.py"],
            acceptance_criteria="429 on burst",
        )

    def test_returns_diff(self):
        from orchestrator.agents import CoderAgent
        agent = CoderAgent(_make_llm("--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n+rate_limit()"))
        diff = agent.implement(self._make_subtask())
        self.assertIn("rate_limit", diff)

    def test_includes_diagnosis_in_prompt(self):
        from orchestrator.agents import CoderAgent
        from orchestrator.state import DebugDiagnosis
        llm = _make_llm("diff output")
        agent = CoderAgent(llm)
        diagnosis = DebugDiagnosis(
            fault_location={"file": "src/middleware/rate_limiter.py", "line_number": 42},
            root_cause="TTL in seconds not ms",
            suggested_fix="Use pexpire(key, 60000)",
        )
        agent.implement(self._make_subtask(), diagnosis=diagnosis)
        call_args = llm.call_args[0]
        self.assertIn("TTL in seconds not ms", call_args[2])


class TestTesterAgent(unittest.TestCase):

    def _make_subtask(self):
        from orchestrator.state import SubtaskSpec
        return SubtaskSpec(id="t01", name="Test", description="Test rate limiter",
                            acceptance_criteria="429 on burst")

    def test_parses_passed_report(self):
        from orchestrator.agents import TesterAgent
        report_json = json.dumps({
            "test_run_status": "PASSED",
            "total_tests": 5,
            "passed": 5,
            "failed": 0,
            "failed_tests": [],
            "truncated_log": "All tests passed",
        })
        agent = TesterAgent(_make_llm(report_json))
        report = agent.test(self._make_subtask(), code_diff="some diff")
        self.assertEqual(report.test_run_status, "PASSED")
        self.assertEqual(report.passed, 5)

    def test_parses_failed_report(self):
        from orchestrator.agents import TesterAgent
        report_json = json.dumps({
            "test_run_status": "FAILED",
            "total_tests": 3,
            "passed": 2,
            "failed": 1,
            "failed_tests": [{"test_name": "test_burst", "error_type": "AssertionError",
                               "message": "Expected 429 got 200"}],
            "truncated_log": "FAILED",
        })
        agent = TesterAgent(_make_llm(report_json))
        report = agent.test(self._make_subtask(), code_diff="diff")
        self.assertEqual(report.test_run_status, "FAILED")
        self.assertEqual(report.failed, 1)
        self.assertEqual(report.failed_tests[0]["test_name"], "test_burst")

    def test_invalid_json_fallback(self):
        from orchestrator.agents import TesterAgent
        agent = TesterAgent(_make_llm("not json"))
        report = agent.test(self._make_subtask(), code_diff="diff")
        self.assertEqual(report.test_run_status, "FAILED")


class TestReviewerAgent(unittest.TestCase):

    def _make_subtask(self):
        from orchestrator.state import SubtaskSpec
        return SubtaskSpec(id="t01", name="Review", description="Review rate limiter",
                            acceptance_criteria="OWASP compliant")

    def test_approve_verdict(self):
        from orchestrator.agents import ReviewerAgent
        verdict_json = json.dumps({
            "verdict": "APPROVE",
            "feedback": ["Looks good"],
            "line_specific": [],
        })
        agent = ReviewerAgent(_make_llm(verdict_json))
        verdict = agent.review(self._make_subtask(), code_diff="diff")
        self.assertEqual(verdict.verdict, "APPROVE")

    def test_reject_verdict(self):
        from orchestrator.agents import ReviewerAgent
        verdict_json = json.dumps({
            "verdict": "REJECT",
            "feedback": ["Hardcoded secret on line 5"],
            "line_specific": [{"file": "app.py", "line": 5, "comment": "Hardcoded secret"}],
        })
        agent = ReviewerAgent(_make_llm(verdict_json))
        verdict = agent.review(self._make_subtask(), code_diff="diff")
        self.assertEqual(verdict.verdict, "REJECT")
        self.assertEqual(len(verdict.line_specific), 1)

    def test_invalid_json_defaults_to_comment(self):
        from orchestrator.agents import ReviewerAgent
        agent = ReviewerAgent(_make_llm("plain text not json"))
        verdict = agent.review(self._make_subtask(), code_diff="diff")
        self.assertEqual(verdict.verdict, "COMMENT")


class TestDebuggerAgent(unittest.TestCase):

    def _make_report(self):
        from orchestrator.state import TestReport
        return TestReport(
            test_run_status="FAILED",
            total_tests=3, passed=2, failed=1,
            failed_tests=[{"test_name": "test_burst", "error_type": "AssertionError",
                           "message": "Expected 429 got 200"}],
            truncated_log="FAILED test_burst",
        )

    def _make_subtask(self):
        from orchestrator.state import SubtaskSpec
        return SubtaskSpec(id="t01", name="Debug", description="Fix rate limiter",
                            acceptance_criteria="429 on burst")

    def test_parses_diagnosis(self):
        from orchestrator.agents import DebuggerAgent
        diag_json = json.dumps({
            "fault_location": {"file": "src/middleware/rate_limiter.py", "line_number": 42},
            "root_cause": "TTL set in seconds not ms",
            "suggested_fix": "Use pexpire(key, 60000)",
        })
        agent = DebuggerAgent(_make_llm(diag_json))
        diag = agent.diagnose(self._make_report(), "some diff", self._make_subtask())
        self.assertEqual(diag.fault_location["line_number"], 42)
        self.assertIn("seconds", diag.root_cause)

    def test_invalid_json_fallback(self):
        from orchestrator.agents import DebuggerAgent
        agent = DebuggerAgent(_make_llm("not json at all"))
        diag = agent.diagnose(self._make_report(), "diff", self._make_subtask())
        self.assertIsInstance(diag.root_cause, str)
        self.assertGreater(len(diag.root_cause), 0)


# ===========================================================================
# Orchestrator validation + legacy helper tests (no LLM, no state file)
# ===========================================================================
class TestOrchestratorValidation(unittest.TestCase):

    def _make_orch(self):
        from orchestrator import Orchestrator
        from router.router import ModelRouter
        from orchestrator.budget import BudgetTracker
        orch = Orchestrator.__new__(Orchestrator)
        orch.router = ModelRouter()
        orch.budget = BudgetTracker()
        orch._project  = "test-project"
        orch._location = "us-central1"
        return orch

    def test_validate_empty_output(self):
        orch = self._make_orch()
        err = orch._validate("", contract="any output")
        self.assertIn("empty", err.lower())

    def test_validate_valid_json_contract(self):
        orch = self._make_orch()
        err = orch._validate('{"key": "value"}', contract="return JSON")
        self.assertEqual(err, "")

    def test_validate_invalid_json_contract(self):
        orch = self._make_orch()
        err = orch._validate("not json at all", contract="return JSON")
        self.assertIn("JSON", err)

    def test_validate_non_json_contract_passes(self):
        orch = self._make_orch()
        err = orch._validate("some plain text", contract="plain text description")
        self.assertEqual(err, "")


# ===========================================================================
# Subtask parsing tests
# ===========================================================================
class TestParseSubtasks(unittest.TestCase):

    def test_valid_json_array(self):
        from orchestrator import _parse_subtasks
        raw = '[{"id":"t1","description":"do x","input_contract":"","output_contract":""}]'
        tasks = _parse_subtasks(raw)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["id"], "t1")

    def test_json_in_markdown_fence(self):
        from orchestrator import _parse_subtasks
        raw = '```json\n[{"id":"t1","description":"do x","input_contract":"","output_contract":""}]\n```'
        tasks = _parse_subtasks(raw)
        self.assertEqual(tasks[0]["id"], "t1")

    def test_fallback_on_invalid_json(self):
        from orchestrator import _parse_subtasks
        tasks = _parse_subtasks("just some text that is not json")
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["id"], "task_1")


# ===========================================================================
# Integration: repair loop guard (mocked LLM, mocked state)
# ===========================================================================
class TestRepairLoopGuard(unittest.TestCase):
    """
    Verify that the repair loop terminates after MAX_REFINEMENT_ITERATIONS
    and does not loop forever.
    """

    def _make_failing_test_report(self):
        from orchestrator.state import TestReport
        return TestReport(
            test_run_status="FAILED", total_tests=1, passed=0, failed=1,
            failed_tests=[{"test_name": "test_x", "error_type": "AssertionError",
                           "message": "fail"}],
            truncated_log="FAILED",
        )

    def _make_orchestrator_shell(self):
        """Build an Orchestrator without Vertex AI initialization."""
        from orchestrator import Orchestrator
        from orchestrator.agents import CoderAgent, TesterAgent, DebuggerAgent
        from router.router import ModelRouter
        from orchestrator.budget import BudgetTracker
        orch = Orchestrator.__new__(Orchestrator)
        orch.router = ModelRouter()
        orch.budget = BudgetTracker()
        orch._project  = "test"
        orch._location = "us-central1"
        orch._coder    = CoderAgent(_make_llm("diff output"))
        # Mock TesterAgent.test() directly so it returns a TestReport (not parsed from LLM text)
        failing_report = self._make_failing_test_report()
        tester = TesterAgent(_make_llm("unused"))
        tester.test = MagicMock(return_value=failing_report)
        orch._tester   = tester
        orch._debugger = DebuggerAgent(_make_llm(json.dumps({
            "fault_location": {"file": "f.py", "line_number": 1},
            "root_cause": "bug",
            "suggested_fix": "fix it",
        })))
        return orch

    def test_repair_loop_stops_at_max_iterations(self):
        import orchestrator.config as config
        from orchestrator.state import SubtaskSpec, WorkflowState, fresh_state
        from orchestrator import Orchestrator

        # Use a temp dir for state
        with tempfile.TemporaryDirectory() as tmpdir:
            orig_dir  = config.STATE_DIR
            orig_file = config.STATE_FILE
            config.STATE_DIR  = os.path.join(tmpdir, ".orchestrator")
            config.STATE_FILE = os.path.join(config.STATE_DIR, "state.json")

            import importlib
            import orchestrator.state as state_mod
            importlib.reload(state_mod)

            try:
                orch = self._make_orchestrator_shell()
                state = state_mod.fresh_state("Test loop guard")
                subtask = state_mod.SubtaskSpec(
                    id="t01", name="Test", description="Implement X",
                    acceptance_criteria="passes",
                )
                state.subtasks = [subtask]

                result = orch._repair_loop(state, subtask, "initial diff", context="")

                self.assertFalse(result, "Expected repair loop to return False after exhaustion")
                self.assertEqual(subtask.repair_iterations, config.MAX_REFINEMENT_ITERATIONS)
            finally:
                config.STATE_DIR  = orig_dir
                config.STATE_FILE = orig_file
                importlib.reload(state_mod)


class TestOrchestratorIntegration(unittest.TestCase):
    def test_successful_run(self):
        # Setup a lightweight orchestrator without real Vertex AI calls
        from orchestrator import Orchestrator
        from orchestrator.state import PlannerOutput, SubtaskSpec, TestReport, ReviewVerdict, WorkflowStatus
        from orchestrator.agents import OrchestratorAgent, PlannerAgent, CoderAgent, TesterAgent, ReviewerAgent, DebuggerAgent
        from router.router import ModelRouter
        from orchestrator.budget import BudgetTracker
        import types
        from unittest.mock import MagicMock

        # Instantiate orchestrator without calling __init__
        orch = Orchestrator.__new__(Orchestrator)
        orch.router = ModelRouter()
        orch.budget = BudgetTracker()
        orch._project = "test"
        orch._location = "us-central1"
        orch._resume = False
        orch._persona_model_map = {p: orch.router.model_id_for_persona(p) for p in ["orchestrator", "planner", "coder", "tester", "reviewer", "debugger"]}

        # Mock LLM call (not used directly because agents are mocked)
        orch._llm_call = lambda *args, **kwargs: ""

        # Wire up mocked agents
        orch._orchestrator_agent = OrchestratorAgent(orch._llm_call)
        orch._planner = PlannerAgent(orch._llm_call)
        orch._coder = CoderAgent(orch._llm_call)
        orch._tester = TesterAgent(orch._llm_call)
        orch._reviewer = ReviewerAgent(orch._llm_call)
        orch._debugger = DebuggerAgent(orch._llm_call)

        # Mock planner to return a simple plan with one subtask
        dummy_subtask = SubtaskSpec(
            id="t01",
            name="Dummy",
            description="Do something",
            files_to_modify=["dummy.py"],
            acceptance_criteria="pass",
        )
        orch._planner.plan = MagicMock(return_value=PlannerOutput(
            architecture_summary="dummy arch",
            tasks=[dummy_subtask]
        ))

        # Mock coder to return a diff string
        orch._coder.implement = MagicMock(return_value="diff --git a/dummy.py b/dummy.py\n+++ /dev/null")

        # Mock tester to return a passing test report
        orch._tester.test = MagicMock(return_value=TestReport(
            test_run_status="PASSED",
            total_tests=1,
            passed=1,
            failed=0,
            failed_tests=[],
            truncated_log=""
        ))

        # Mock reviewer to approve
        orch._reviewer.review = MagicMock(return_value=ReviewVerdict(
            verdict="APPROVE",
            feedback=["looks good"],
            line_specific=[]
        ))

        # Run orchestrator
        result = orch.run(goal="Test goal", context="", repository_path="")
        self.assertTrue(result["success"], "Orchestrator should report success")
        self.assertEqual(result["status"], WorkflowStatus.COMPLETE)
        # Verify that planner, coder, tester, reviewer were each called once
        orch._planner.plan.assert_called_once()
        orch._coder.implement.assert_called_once()
        orch._tester.test.assert_called_once()
        orch._reviewer.review.assert_called_once()


class TestPhase10Orchestrator(unittest.TestCase):
    def test_routing_manifest_parsing(self):
        from router.manifest import RoutingManifest
        manifest = RoutingManifest(
            intent="schema_registry",
            primary_target_symbols=["user.py::User"],
            repomap_token_budget=1024,
            task_instructions="Refactor database schema"
        )
        self.assertEqual(manifest.intent, "schema_registry")
        self.assertEqual(manifest.repomap_token_budget, 1024)

    def test_daily_budget_circuit_breaker(self):
        from orchestrator.budget import check_and_update_budget, get_quota_file_path
        import json
        import time

        quota_file = get_quota_file_path()
        # Backup original quota if exists
        original_content = None
        if quota_file.exists():
            original_content = quota_file.read_text(encoding="utf-8")

        try:
            today = time.strftime("%Y-%m-%d")
            quota_file.parent.mkdir(parents=True, exist_ok=True)
            with open(quota_file, "w", encoding="utf-8") as f:
                json.dump({"date": today, "tokens": 100, "cost": 0.40}, f)

            result = check_and_update_budget(input_tokens=100)
            self.assertFalse(result, "Circuit breaker should trip when budget ceiling is exceeded")
        finally:
            if original_content is not None:
                quota_file.write_text(original_content, encoding="utf-8")


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False)
    sys.exit(0 if result.result.wasSuccessful() else 1)

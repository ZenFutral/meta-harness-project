# Multi-Agent Software Engineering Orchestration Framework

A cost-optimized, hierarchical multi-agent Software Engineering (SWE) orchestration framework built on GCP Vertex AI and Antigravity model APIs.

The framework coordinates specialized agent personas through a structured Hub-and-Spoke workflow with explicit context boundaries, token budget circuit breakers, and state persistence.

---

## Architecture Overview

The system uses a **Hub-and-Spoke Topology** driven by an central state machine:

```
                  ┌─────────────────┐
                  │ Orchestrator /  │
                  │   Supervisor    │
                  └────────┬────────┘
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
      ┌────────────┐ ┌────────────┐ ┌────────────┐
      │  Planner   │ │   Coder    │ │   Tester   │
      └────────────┘ └────────────┘ └────────────┘
             │             │             │
             └─────────────┼─────────────┘
                           ▼
                  ┌─────────────────┐
                  │ Reviewer &      │
                  │ Debugger        │
                  └─────────────────┘
```

### State Machine Lifecycle

```
INTAKE ──► PLANNING ──► CODING ──► TESTING
                           ▲          │
                           │     FAILED
                        DEBUGGING ◄───┤
                           │          │
                           └─── (loop)│
                                      ▼
                                   PASSED ──► REVIEWING
                                                  │
                                              APPROVED
                                                  │
                                                  ▼
                                              COMPLETE
```

1. **INTAKE → PLANNING**: The [PlannerAgent](./meta-harness/orchestrator/agents.py#L113-L186) decomposes high-level goals into a Directed Acyclic Graph (DAG) of isolated subtasks.
2. **CODING**: The [CoderAgent](./meta-harness/orchestrator/agents.py#L192-L242) produces targeted code changes and unified diffs.
3. **TESTING & DEBUGGING**: The [TesterAgent](./meta-harness/orchestrator/agents.py#L247-L313) verifies code changes against acceptance criteria. Failures trigger the [DebuggerAgent](./meta-harness/orchestrator/agents.py#L382-L444) to localize fault locations and suggest root-cause fixes back to the Coder (up to 3 iterations).
4. **REVIEWING**: The [ReviewerAgent](./meta-harness/orchestrator/agents.py#L319-L376) inspects code diffs adversarially for security vulnerabilities, quality, and edge-case adherence.
5. **ESCALATION & RE-PLANNING**: Exhausted repair loops or reviewer rejections escalate to the Planner to re-architect remaining tasks.

---

## Key Modules

- [`orchestrator.py`](./meta-harness/orchestrator/orchestrator.py): Core pipeline engine managing state transitions, repair loops, escalations, and budget enforcement.
- [`agents.py`](./meta-harness/orchestrator/agents.py): Defines six persona classes (`OrchestratorAgent`, `PlannerAgent`, `CoderAgent`, `TesterAgent`, `ReviewerAgent`, `DebuggerAgent`).
- [`router.py`](./meta-harness/router/router.py): `ModelRouter` maps agent personas to cost-optimised Vertex AI or Antigravity model endpoints.
- [`budget.py`](./meta-harness/orchestrator/budget.py): `BudgetTracker` tracks session and task costs with hard-stop circuit breaker limits.
- [`state.py`](./meta-harness/orchestrator/state.py): Dataclasses and persistence functions (`.orchestrator/state.json`) for session pause/resume support.
- [`config.py`](./meta-harness/orchestrator/config.py): System configurations, model routing maps, cost tables, and execution limits.
- [`main.py`](./meta-harness/orchestrator/main.py): Command Line Interface (CLI) entry point.

---

## Installation & Requirements

Requires **Python 3.9+**.

Install dependencies:
```bash
pip install -r requirements.txt
```

*Note: Google Cloud authentication is required for Vertex AI backends (`gcloud auth application-default login`).*

---

## Usage

### CLI

Execute a software engineering task:

```bash
python main.py --project my-gcp-project --goal "Add rate-limiting to /api/v1/ingest"
```

#### CLI Flags & Options

| Flag | Description | Default |
| --- | --- | --- |
| `--project` | GCP project ID (Required) | - |
| `--goal` | Objective statement (Required) | - |
| `--context` | Extra repo context string or filepath | `""` |
| `--location` | GCP Vertex AI region | `us-central1` |
| `--backend` | Backend provider: `vertex` or `antigravity` | `vertex` |
| `--repo` | Target repository path | `""` |
| `--resume` | Resume session from `.orchestrator/state.json` | `False` |
| `--verbose` | Enable debug log output | `False` |

### Python API

```python
from orchestrator import Orchestrator

orchestrator = Orchestrator(
    project="my-gcp-project",
    location="us-central1",
    backend="vertex",
)

result = orchestrator.run(
    goal="Refactor user authentication module to support OAuth2",
    context="Auth logic resides in services/auth.py",
)

print(f"Workflow status: {result['status']}")
print(f"Total budget spent: {result['budget']}")
```

---

## Running Tests

Run the unit test suite:

```bash
python tests.py
```

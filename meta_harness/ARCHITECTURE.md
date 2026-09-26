# Multi-Agent Orchestration & Contextualization Architecture

This document presents the birds-eye architectural overview, state machine models, data flows, and design principles of the orchestration system.

---

## 1. System Topology & Ecosystem Overview

The ecosystem operates as a dual-engine architecture consisting of **Contextualization** and **Multi-Agent Orchestration**:

```
                       ┌──────────────────────────────────────┐
                       │           Local Workspace            │
                       └──────────────────┬───────────────────┘
                                          │
                                          ▼
                       ┌──────────────────────────────────────┐
                       │        Contextualize Engine          │
                       │  - File System Scraper & Watcher     │
                       │  - Git Diff & History Harvester      │
                       │  - Token Budget Truncator            │
                       └──────────────────┬───────────────────┘
                                          │ Context Bundle (JSON)
                                          ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             SWE Orchestrator System                              │
│                                                                                  │
│                        ┌─────────────────────────────┐                           │
│                        │   Orchestrator / Supervisor │                           │
│                        └──────────────┬──────────────┘                           │
│                                       │                                          │
│         ┌─────────────────────────────┼─────────────────────────────┐            │
│         ▼                             ▼                             ▼            │
│  ┌────────────┐                ┌────────────┐                ┌────────────┐      │
│  │  Planner   │                │   Coder    │                │   Tester   │      │
│  └────────────┘                └────────────┘                └────────────┘      │
│         │                             │                             │            │
│         └─────────────────────────────┼─────────────────────────────┘            │
│                                       ▼                                          │
│                        ┌─────────────────────────────┐                           │
│                        │     Reviewer & Debugger     │                           │
│                        └─────────────────────────────┘                           │
│                                       │                                          │
│  ┌────────────────────────────────────┴───────────────────────────────────────┐  │
│  │                        Cross-Cutting Infrastructure                       │  │
│  │  ┌──────────────────────┐ ┌──────────────────────┐ ┌─────────────────────────┐  │  │
│  │  │  ModelRouter (Tier)  │ │  BudgetTracker ($)   │ │ State Manager (Json)   │  │  │
│  │  └──────────────────────┘ └──────────────────────┘ └─────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Orchestrator Lifecycle & State Machine

The orchestration execution loop strictly enforces a state machine with automated repair loops, feedback iterations, and escalation paths.

```
       ┌─────────┐
       │ INTAKE  │
       └────┬────┘
            │
            ▼
       ┌──────────┐
       │ PLANNING │ ◄─────────────────────────────────────────────┐
       └────┬─────┘                                               │ (Re-plan Escalation)
            │                                                     │
            ▼                                                     │
       ┌──────────┐      (Failed Test)       ┌──────────┐         │
  ┌──► │  CODING  │ ───────────────────────► │ DEBUGGING│ ────────┤ (Max iterations exceeded)
  │    └────┬─────┘                          └────┬─────┘         │
  │         │                                     │               │
  │         ▼                                     │               │
  │    ┌──────────┐                               │               │
  └─── │ TESTING  │ ◄─────────────────────────────┘               │
 (Fix) └────┬─────┘                                               │
            │                                                     │
         (Passed)                                                 │
            │                                                     │
            ▼                                                     │
       ┌──────────┐          (Changes Requested)                  │
       │REVIEWING │ ──────────────────────────────────────────────┘
       └────┬─────┘
            │
        (Approved)
            │
            ▼
       ┌──────────┐
       │ COMPLETE │
       └──────────┘
```

### State Transitions & Rules

1. **INTAKE → PLANNING**: High-level task objective is ingested. The [`PlannerAgent`](./meta-harness/orchestrator/agents.py#L113-L186) parses constraints and builds a task DAG.
2. **PLANNING → CODING**: The subtasks are picked up sequentially or in topological order by the [`CoderAgent`](./meta-harness/orchestrator/agents.py#L192-L242).
3. **CODING → TESTING**: Code modifications produce diffs and updated code snippets, which are passed to the [`TesterAgent`](./meta-harness/orchestrator/agents.py#L247-L313).
4. **TESTING → DEBUGGING / REVIEWING**:
   - **On Test Failure**: Transition to [`DebuggerAgent`](./meta-harness/orchestrator/agents.py#L382-L444). The debugger performs root-cause analysis and feeds corrective feedback back to the Coder (up to 3 maximum attempts).
   - **On Test Pass**: Transition to [`ReviewerAgent`](./meta-harness/orchestrator/agents.py#L319-L376).
5. **REVIEWING → COMPLETE / RE-PLANNING**:
   - **Approved**: Task marked complete; next subtask in DAG is invoked.
   - **Rejected / Re-plan Needed**: Re-routes to the Planner for DAG adjustments.

---

## 3. Core Component Deep-Dive

### 3.1 Multi-Tier Routing & Manifest Generation (`router/`)

Model execution is dynamically routed based on agent capability demands and cost:

- **Tier 0 (Fast Triage)**: Hugging Face zero-shot classifier (`facebook/bart-large-mnli`) parses prompt intent with offline heuristic fallback.
- **Tier 1 (Cost-Optimized / Ambiguity Fallback)**: Google Vertex AI (`gemini-2.0-flash`, `gemini-2.0-flash-lite`, `gemini-2.5-flash`) with hard-stop daily budget guard.
- **Tier 2 (Deep Reasoning & Execution)**: Google Antigravity CLI harness (`antigravity-default`, `gemini-2.5-pro`, `deepseek-r1`).
- Generates typed [`RoutingManifest`](./meta-harness/router/manifest.py) standardizing target symbols, focus files, and token budgets.

### 3.2 Budget & Circuit Breaker System (`budget.py`)

- Tracks input tokens, output tokens, and estimated cost against configurable thresholds.
- Enforces session and per-task dollar hard-stops (`session_hard_stop_usd: $1.00`, `task_hard_stop_usd: $0.25`).
- Daily quota circuit-breaker: enforces a hard ceiling of `$0.33/day` recorded atomically in `.agent/cache/quota.json`.

### 3.3 Contextualization Engine (`contextualize/`)

- Scans file trees, gathers recent Git commits/diffs, environment variables, and Repomap skeletons.
- Truncates context dynamically using token encoding (`cl100k_base`) to guarantee inputs remain strictly within configured context windows (`max_tokens: 32000`).
- Produces structured bundles at `output/context_bundle.json` and metrics at `test_metrics.json`.

### 3.4 Repomap Code Intelligence (`.agent/repomap/`)

- High-performance SQLite-WAL database caching AST symbols, call graphs, and export registries.
- Implements Tarjan's SCC cycle detection, PageRank centrality ranking, and marginal density code packing.
- Exposes JSON-RPC tool endpoints and CLI commands (`summary`, `trace`, `schemas`, `cycles`).

### 3.5 System Monitoring GUI (`gui/`)

- Zero-dependency HTTP server (`ThreadingHTTPServer`) serving real-time telemetry HUD.
- Features quota gauges, feature status grid, vendor toggles, SQLite-WAL table inspection, and interactive RPC probe playgrounds.

---

## 4. State Persistence & Resilience

The orchestrator guarantees atomic state updates saved to `.orchestrator/state.json`:

- Full execution status (`INTAKE`, `PLANNING`, `CODING`, `TESTING`, `DEBUGGING`, `REVIEWING`, `COMPLETE`, `FAILED`).
- Active DAG subtask index and subtask outputs.
- Running token consumption and total accrued cost.
- Session resume capabilities via `--resume` CLI flag.

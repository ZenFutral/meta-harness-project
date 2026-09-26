# Multi-Agent Orchestration & Contextualization Ecosystem

An enterprise-grade, cost-optimized Multi-Agent Software Engineering (SWE) Orchestration Framework paired with an automated repository Contextualization Engine. 

This repository brings together two complementary subsystems to provide end-to-end automated software engineering execution with high-fidelity context bundling, token budget protection, model routing, and state persistence.

---

## 🚀 Key Subsystems

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Orchestration Ecosystem                                │
│                                                                                 │
│   ┌───────────────────────────┐                 ┌───────────────────────────┐   │
│   │     Contextualize Engine  │                 │    SWE Orchestrator       │   │
│   │                           │                 │                           │   │
│   │ • File System Watcher     │                 │ • Hub & Spoke State Engine│   │
│   │ • Git Diff & History      │ ──Context─────► │ • 6 Persona Multi-Agents  │   │
│   │ • Token Budget Truncator  │   Bundles       │ • Cost & Model Router     │   │
│   │ • Context JSON Bundler    │                 │ • Circuit Breakers & Fits │   │
│   └───────────────────────────┘                 └───────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

1. **[`orchestrator/`](./meta-harness/orchestrator)**: Multi-agent state engine managing 6 specialized persona agents (`Planner`, `Coder`, `Tester`, `Reviewer`, `Debugger`, `Orchestrator`), structured repair loops, model routing (Vertex AI / Antigravity), and session budget circuit breakers.
2. **[`contextualize/`](./meta-harness/contextualize)**: Intelligent repository context gatherer that monitors workspace changes, gathers git diffs/history, and builds token-budgeted context bundles to feed agent inputs.
3. **[`router/`](./meta-harness/router)**: Multi-tier routing engine supporting fast-path zero-shot intent triage (Hugging Face BART Large MNLI) and Gemini Flash fallback with daily spending guard.
4. **[`gui/`](./meta-harness/gui)**: Real-time telemetry HUD and web observatory monitoring daily quota, SQLite-WAL cache tables, persona states, and live probes.
5. **[`.agent/repomap/`](./.agent/repomap)**: Two-tier graph symbol indexer, PageRank centrality ranker, cycle detector, and marginal density code skeleton packer.

---

## 📁 Repository Structure

```
.
├── ARCHITECTURE.md          # Comprehensive architectural specification & design diagrams
├── README.md                # Birds-eye overview & project documentation
├── orchestrator/            # Hierarchical Multi-Agent SWE Execution System
│   ├── main.py              # CLI Entry Point
│   ├── orchestrator.py      # Core State Machine Engine & Repair Loops
│   ├── agents.py            # Agent Personas (Planner, Coder, Tester, etc.)
│   ├── router.py            # Model Routing Shim
│   ├── budget.py            # Token & Cost Circuit Breaker Tracker
│   ├── state.py             # State Models & Persistence (.orchestrator/state.json)
│   ├── config.py            # Framework System Configuration
│   └── tests.py             # Orchestrator Test Suite
├── contextualize/           # Automated Repository Context Generation Engine
│   ├── config.json          # Context Engine Configuration & Token Limits
│   ├── metrics.json         # Runtime Metrics Output
│   ├── log.json             # System Logs Output
│   ├── output/              # Context Bundles Output Directory
│   ├── run.ps1 / run.cmd    # Execution Scripts
│   └── src/                 # Context Engine Source Code
├── router/                  # Multi-Tier Intent Classifier & Routing Manifests
│   ├── zero_shot.py         # Stage 1 HF Zero-Shot Classifier
│   ├── flash_fallback.py    # Stage 2 Gemini Flash Fallback Router
│   ├── manifest.py          # RoutingManifest Schema
│   └── vendor_config.py     # Vendor Toggles & Configuration
├── gui/                     # Telemetry Dashboard & Feature Observatory
│   ├── server.py            # HTTP Server with REST API & Static Files
│   ├── telemetry.py         # Telemetry & Quota Aggregation Engine
│   ├── probes.py            # Diagnostic Probes
│   └── static/              # Web Frontend (HTML / CSS / JS)
└── .agent/repomap/          # Code Intelligence, Centrality & Graph Index
    ├── core/                # Storage, TwoTierGraph, Ranker, Packer
    ├── facets/              # Hierarchy, Schemas, Blast Radius
    ├── server.py            # JSON-RPC 2.0 Server
    └── cli.py               # Faceted CLI Commands
```

---

## ⚡ Quick Start

### 1. Requirements & Setup

Requires **Python 3.9+**.

```bash
# Set up orchestrator environment
cd meta-harness/orchestrator
pip install -r requirements.txt
```

*Note: GCP authentication is required for Vertex AI endpoints (`gcloud auth application-default login`).*

### 2. Running the Orchestrator CLI

Execute a software engineering task with budget controls and persona coordination:

```bash
python meta-harness/orchestrator/main.py --project my-gcp-project --goal "Add rate-limiting to /api/v1/ingest"
```

### 3. Launching the System Observatory GUI

Start the web monitoring dashboard:

```bash
python -m gui.cli --port 8087
```

### 4. Generating Context Bundles

To generate a context bundle for a target repository:

```powershell
cd meta-harness/contextualize
.\run.ps1
```

---

## 📊 Summary of Agent Personas

| Agent Persona | Role & Functionality | Default Model |
| --- | --- | --- |
| **Planner** | Decomposes high-level goals into isolated DAG subtasks | Gemini 2.5 Flash |
| **Coder** | Implements target features, code modifications, and diffs | Gemini 2.0 Flash |
| **Tester** | Executes unit/integration test suites and evaluates results | Gemini 2.0 Flash |
| **Debugger** | Analyzes test failures, localizes errors, and proposes fixes | Gemini 2.5 Flash |
| **Reviewer** | Performs security, quality, and edge-case code review | Gemini 2.5 Flash |
| **Supervisor** | Manages orchestration lifecycle, budget limits, and escalations | Gemini 2.0 Flash-Lite |

---

## 📜 Documentation

- For deep-dive architectural specifications, data flow diagrams, and state machines, see [ARCHITECTURE.md](./meta-harness/ARCHITECTURE.md).
- For orchestrator module details, refer to [orchestrator/README.md](./meta-harness/orchestrator/README.md).
- For context engine details, refer to [contextualize/README.md](./meta-harness/contextualize/README.md).
- For routing engine details, refer to [router/README.md](./meta-harness/router/README.md).
- For telemetry GUI details, refer to [gui/README.md](./meta-harness/gui/README.md).
- For Repomap code intelligence details, refer to [.agent/repomap/README.md](./.agent/repomap/README.md).

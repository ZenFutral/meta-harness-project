# Meta-Harness

An enterprise-grade, cost-optimized Multi-Agent Software Engineering (SWE) Orchestration Framework paired with an automated repository Contextualization Engine, Repomap Code Intelligence Graph, Multi-Tier Router, and Real-Time Monitoring Observatory.

---

## 🏛️ Ecosystem Overview

Meta-Harness is structured into modular subsystems:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Meta-Harness Ecosystem                                │
│                                                                                 │
│   ┌───────────────────────────┐                 ┌───────────────────────────┐   │
│   │     Contextualize Engine  │                 │    SWE Orchestrator       │   │
│   │                           │                 │                           │   │
│   │ • File System Watcher     │                 │ • Hub & Spoke State Engine│   │
│   │ • Git Diff & History      │ ──Context─────► │ • 6 Persona Multi-Agents  │   │
│   │ • Token Budget Truncator  │   Bundles       │ • Cost & Model Router     │   │
│   │ • Repomap AST Client      │                 │ • Circuit Breakers ($0.33)│   │
│   └─────────────┬─────────────┘                 └─────────────┬─────────────┘   │
│                 │                                             │                 │
│                 ▼                                             ▼                 │
│   ┌───────────────────────────┐                 ┌───────────────────────────┐   │
│   │   Repomap Graph & Index   │                 │ System Monitoring GUI HUD │   │
│   │ (.agent/repomap)          │                 │ (meta-harness/gui)        │   │
│   │ • SQLite-WAL Symbol DB    │                 │ • Live Quota Gauges       │   │
│   │ • Centrality PageRank     │                 │ • SQLite Cache Inspector  │   │
│   │ • SCC Cycle Detection     │                 │ • Interactive Probes      │   │
│   └───────────────────────────┘                 └───────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Repository Directory Structure

```
meta-harness-project/
├── meta_harness/                  # Core Meta-Harness Python framework package
│   ├── orchestrator/              # Hub & Spoke Multi-Agent State Machine & Execution Engine
│   │   ├── agents.py              # 6 Persona definitions (Planner, Coder, Tester, Reviewer, Debugger, Orchestrator)
│   │   ├── budget.py              # Multi-tier cost budget manager & daily circuit breakers ($0.33 limit)
│   │   ├── config.py              # Orchestrator parameters, retry limits & token allocations
│   │   ├── main.py                # Standalone orchestrator CLI runner
│   │   ├── orchestrator.py        # Central state machine loop, DAG subtask manager, & repair cycle launcher
│   │   ├── state.py               # Workflow state model, checkpointing, & task graph serialization
│   │   ├── sessions/              # Active workflow session logs & state snapshots
│   │   └── tests/                 # Unit & integration tests for orchestrator components
│   │
│   ├── contextualize/             # Automated Codebase Context Engine
│   │   ├── engine.py              # Token-budget context builder with cl100k_base encoding
│   │   ├── git_diff.py            # Git status & diff patch extraction
│   │   ├── repomap_client.py      # Client interface for Repomap RPC symbol index
│   │   ├── watcher.py             # Filesystem event listener & cache invalidator
│   │   └── tests/                 # Contextualization test suite
│   │
│   ├── router/                    # Two-Stage Intent & Vendor Routing System
│   │   ├── router.py              # Main multi-tier intent router entrypoint
│   │   ├── zero_shot.py           # Stage 1 Zero-Shot Classifier (BART-large MNLI fallback / heuristic rules)
│   │   ├── flash_fallback.py      # Stage 2 LLM Classifier (Gemini 1.5 Flash API fallback)
│   │   ├── vendor_config.py       # Vendor model pricing tables, quota caps, and tier mappings
│   │   ├── manifest.py            # Model registry & capabilities manifest
│   │   └── tests/                 # Routing evaluation and cost tests
│   │
│   ├── gui/                       # Telemetry Observatory & Web Management HUD
│   │   ├── server.py              # Zero-dependency ThreadingHTTPServer REST & SSE API server
│   │   ├── cli.py                 # Observatory CLI starter (--port options)
│   │   ├── telemetry.py           # Hardware, system metrics, & live quota data aggregator
│   │   ├── chat.py                # Router Agent Chat Hub handler & session manager
│   │   ├── agents_network.py      # Real-time state machine directed graph & intervention drawer API
│   │   ├── cache_metrics.py       # SQLite-backed cache hit/miss logger & metric tracker
│   │   ├── cache_ops.py           # File detail inspection, AST parser, and cache invalidation handlers
│   │   ├── probes.py              # Feature card probe execution handlers (RPC, AST, Router, Cycle)
│   │   ├── models.py              # GUI data transfer schemas and types
│   │   ├── static/                # Frontend SPA assets (Vanilla JS, CSS Tokens, Micro-animations)
│   │   └── tests/                 # GUI API & server unit test suite
│   │
│   ├── tests/                     # Package-level integration test suite
│   └── ARCHITECTURE.md            # Comprehensive technical blueprint and state machine diagram
│
├── .agent/                        # Agent runtime state, caches, tools, and symbol indexing
│   ├── repomap/                   # Code Intelligence Graph Engine
│   │   ├── server.py              # JSON-RPC 2.0 symbol index server
│   │   ├── parser.py              # Tree-sitter & AST Python/JS/TS source code parser
│   │   ├── ranker.py              # PageRank symbol importance ranker
│   │   ├── cycle_detector.py      # Tarjan's Strongly Connected Components (SCC) cycle detector
│   │   └── schema_registry.py     # Structural schema definition indexer
│   ├── cache/                     # Persisted local state (`repomap.db` SQLite-WAL, `quota.json`)
│   ├── config/                    # Vendor configurations (`vendors.json`)
│   ├── tools/                     # Tool schemas (`repomap_tools.json`)
│   └── bin/                       # Runtime executable helpers
│
├── .github/                       # GitHub repository configuration
│   └── workflows/                 # CI/CD Workflows (`ci.yml` multi-Python matrix testing)
│
├── start.bat                      # 1-Click launcher script for Windows Command Prompt
├── start.ps1                      # 1-Click launcher script for Windows PowerShell
├── start.sh                       # 1-Click launcher script for Linux / macOS
├── start.py                       # Cross-platform Python startup coordinator & browser auto-launcher
├── requirements.txt               # System Python dependencies
├── pytest.ini                     # Pytest testing configuration
├── Dockerfile                     # Containerization deployment definition
└── change_list.md                 # System implementation roadmap & audit log
```

---

## ⚡ Quick Start

### 🚀 1-Click All-in-One Startup (Recommended)

To start all functions, initialize the Repomap AST code intelligence index, initialize SWE orchestrator workflow state, boot the monitoring web server, and automatically launch the dashboard in your default browser:

- **Windows (Double-click or CMD)**:

  ```cmd
  start.bat
  ```

- **PowerShell**:

  ```powershell
  .\start.ps1
  ```

- **Linux / macOS**:

  ```bash
  chmod +x start.sh && ./start.sh
  ```

- **Cross-Platform Python**:

  ```bash
  python start.py
  ```

Your browser will automatically open to `http://127.0.0.1:8080/`.

---

### 1. Requirements

Requires **Python 3.9+** (tested on Python 3.13).

```bash
pip install -r requirements.txt
```

### 2. Run the Multi-Agent Orchestrator

```bash
python meta_harness/orchestrator/main.py --project <gcp-project-id> --goal "Add rate-limiting to /api/v1/ingest"
```

### 3. Launch the System Monitoring GUI Standalone

```bash
python -m meta_harness.gui.cli --port 8080
```

### 4. Run the Full Test Suite

```bash
pytest
---

## 🔑 Key Subsystems & Features

### 🤖 6-Persona SWE Orchestrator (`meta_harness/orchestrator`)
- **Hub & Spoke DAG State Engine**: Coordinates subtasks across six specialized personas (`Planner`, `Coder`, `Tester`, `Reviewer`, `Debugger`, `Orchestrator`).
- **Autonomous Repair Cycles**: Diagnoses failing tests, generates unified diff patches, and re-evaluates code dynamically.
- **Circuit Breaker Budgeting**: Implements strict daily spending limits ($0.33 limit) with multi-vendor quota fallback.

### 🧠 Repository Contextualization Engine (`meta_harness/contextualize`)
- **Token-Budget Builder**: Packs git diffs, file structures, and relevant symbol skeletons into strict `cl100k_base` context windows.
- **Dynamic File Watcher**: Listens for filesystem changes to invalidate cached AST tokens in real time.

### 🔀 Multi-Tier Intent Router (`meta_harness/router`)
- **Stage 1 Zero-Shot Classification**: Routes low-complexity prompts using local heuristic rules or Zero-Shot BART-large MNLI.
- **Stage 2 LLM Fallback**: Routes complex SWE tasks to high-capacity model providers with model registry fallback.

### 🌐 System Monitoring Observatory HUD (`meta_harness/gui`)
- **Zero-Dependency Web Server**: Built on Python standard library `ThreadingHTTPServer` supporting REST APIs and Server-Sent Events (SSE).
- **Interactive Feature Probes**: Embedded in-card probe widgets for AST symbol extraction, JSON-RPC queries, intent routing verification, and cycle detection.
- **Live Agent Network Graph**: SVG visual graph of agent state transitions with slide-out intervention drawers (Pause, Rerun, Edit Task, Model Override).
- **Cache Metric Observatory**: SQLite-backed file detail inspector and cache hit/miss tracking.

### 📊 Repomap Code Intelligence Graph (`.agent/repomap`)
- **AST Symbol Indexing**: Parses Python, JavaScript, and TypeScript files into SQLite-WAL backed tables.
- **PageRank & Cycle Detection**: Ranks code centrality and detects circular dependencies using Tarjan's SCC algorithm.
- **JSON-RPC Server**: Exposes code graph interfaces over lightweight RPC tools.

---

## 📜 Full Documentation

- Architectural Blueprint & State Machine: [ARCHITECTURE.md](./meta_harness/ARCHITECTURE.md)
- Subsystem Guides:
  - [SWE Orchestrator](./meta_harness/orchestrator/README.md)
  - [Contextualization Engine](./meta_harness/contextualize/README.md)
  - [Multi-Tier Router](./meta_harness/router/README.md)
  - [Monitoring GUI & Observatory](./meta_harness/gui/README.md)
  - [Repomap Code Intelligence Graph](./.agent/repomap/README.md)

## Contributing to Meta-Harness

Thank you for contributing to Meta-Harness! To maintain code quality, consistency, and stability across our multi-agent orchestration ecosystem, please review and follow these guidelines.

---

### 🏗️ Architecture & Philosophy

Meta-Harness is structured with modularity, low overhead, and deterministic execution in mind:

- **`meta-harness/orchestrator`**: Multi-agent hub-and-spoke state machine with persona isolation.
- **`meta-harness/contextualize`**: High-performance context gathering engine with strict token budgets.
- **`meta-harness/router`**: Two-stage intent classification with cost tracking and circuit breaker limits ($0.33/day cap).
- **`meta-harness/gui`**: Lightweight, zero-dependency telemetry HUD and probe dashboard.
- **`.agent/repomap`**: PageRank code intelligence graph engine, cycle detection, and SQLite-WAL state store.

Please review [ARCHITECTURE.md](./meta-harness/ARCHITECTURE.md) before designing architectural changes.

---

### 🛠️ Development Setup

1. **Python Requirement**: Python 3.9+ (Python 3.12+ recommended).
2. **Install Dependencies**:

   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

1. **Verify Environment**:

   ```bash
   pytest
   ```

---

### 🧪 Testing Guidelines

- All new features, bug fixes, and refactoring **must** include accompanying automated tests.
- Keep tests isolated; do not write persistent test artifacts into version-controlled paths (use `tempfile` or ensure outputs are ignored).
- Run the full suite locally before committing:

  ```bash
  pytest
  ```

---

## 📝 Commit & PR Conventions

- **Clear, imperative commit messages**: e.g., `feat(router): add adaptive temperature thresholding` or `fix(gui): sanitize probe rpc inputs`.
- Keep PRs focused on a single responsibility.
- Ensure all CI tests pass.

#    m e t a - h a r n e s s - p r o j e c t 

 
 

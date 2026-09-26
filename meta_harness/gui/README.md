# Meta-Harness System Monitoring & Feature Observatory GUI

High-performance, zero-dependency telemetry HUD, feature matrix catalog, and RPC playground for the Meta-Harness multi-agent framework.

---

## Overview

The `gui` package provides a standalone monitoring web dashboard powered by Python's built-in `ThreadingHTTPServer` and modern vanilla HTML/CSS/JS frontend. It offers real-time visibility into quota consumption, SQLite-WAL cache tables, agent personas, and interactive feature probes.

```
┌────────────────────────────────────────────────────────────────────────┐
│               System Monitoring GUI Architecture                       │
│                                                                        │
│   ┌────────────────────┐                   ┌───────────────────────┐   │
│   │ Vanilla Web Client │ ──REST / JSON──►  │ Python HTTP Server    │   │
│   │ (HUD, Grid, Probes)│                   │ (ThreadingHTTPServer) │   │
│   └────────────────────┘                   └───────────┬───────────┘   │
│                                                        │               │
│                        ┌───────────────────────────────┼──────────┐    │
│                        ▼                               ▼          ▼    │
│             ┌─────────────────────┐          ┌──────────────┐ ┌──────┐ │
│             │ Telemetry / Quotas  │          │ SQLite-WAL   │ │Probes│ │
│             │ (.agent/cache/quota)│          │ (repomap.db) │ │Engine│ │
│             └─────────────────────┘          └──────────────┘ └──────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Key Features

1. **Telemetry HUD**:
   - Real-time tracker for daily Vertex AI quota ($0.33/day ceiling).
   - Visual circuit-breaker status warning if spending reaches the cap.
   - Session tokens, database size, and test execution duration metrics.
2. **Feature Matrix & Status**:
   - Comprehensive grid tracking implementation status of all phases and subsystems.
   - Interactive vendor toggle controls for Hugging Face, Vertex AI, and Google Antigravity.
3. **SQLite-WAL Inspector**:
   - Browse tables (`parse_cache`, `symbol_references`, `export_registry`, `wildcard_dependencies`) in `.agent/cache/repomap.db`.
4. **RPC Playground & Probes**:
   - Test intent classification routing directly from the UI.
   - Run symbol blast-radius and skeleton extraction queries against local codebase.
5. **Agent Persona Activity**:
   - Live state of all 6 SWE personas (`Planner`, `Coder`, `Tester`, `Reviewer`, `Debugger`, `Orchestrator`).

---

## Directory Structure

```
gui/
├── cli.py            # CLI entrypoint for launching the server
├── server.py         # ThreadingHTTPServer implementation with REST API & static file serving
├── models.py         # Dataclasses defining telemetry snapshots and feature schemas
├── telemetry.py      # Telemetry aggregation engine reading quota and database state
├── probes.py         # Direct execution probes for router, schemas, and skeletons
├── static/           # Web frontend assets
│   ├── index.html    # Single-page web dashboard application
│   ├── css/          # Vanilla CSS stylesheets
│   └── js/           # Vanilla JS controller logic
└── tests/
    └── test_gui.py   # Unit and integration test suite for server endpoints and probes
```

---

## API Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/telemetry` | Returns system telemetry snapshot (quota, DB stats, test metrics). |
| `GET` | `/api/features` | Returns the complete catalog of system features and statuses. |
| `GET` | `/api/cache/tables?table=<name>&limit=<n>` | Samples rows from SQLite cache database. |
| `GET` | `/api/vendors` | Loads vendor toggle configurations. |
| `GET` | `/api/agent_activity` | Returns active states and task assignments for agent personas. |
| `GET` | `/api/probe/schemas` | Returns parsed schema registry definitions. |
| `GET` | `/api/probe/cycles` | Checks for circular imports in the codebase. |
| `POST` | `/api/vendors/toggle` | Toggles model vendor ON/OFF (`{"vendor": "huggingface", "enabled": false}`). |
| `POST` | `/api/probe/route` | Probes multi-tier router with prompt string. |
| `POST` | `/api/probe/skeleton` | Extracts skeleton code for target file path within token budget. |
| `POST` | `/api/probe/blast_radius` | Computes symbol call hierarchy and dependency blast radius. |

---

## Quick Start

### Launch GUI Server

Run the GUI module directly with Python:

```bash
python -m gui.cli --port 8087
```

Options:
- `--host`: Interface to bind (default: `127.0.0.1`).
- `--port`: Port number (default: `8080`).
- `--no-browser`: Disable automatic browser opening on launch.

---

## Testing

Run the GUI test suite:

```bash
pytest meta-harness/gui/tests/test_gui.py
```

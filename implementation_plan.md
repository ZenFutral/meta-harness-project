# Implementation Plan: Zero-Dependency Architecture & Resilient Multi-Agent Telemetry

## 1. Summary

The `meta_harness` project currently relies on heavy ML dependencies for Stage 1 intent routing (`BART Large MNLI`) and mismatched tokenizer specifications (`cl100k_base`), which compromise its zero-dependency philosophy[cite: 2, 4]. Furthermore, concurrent writes from the 6 persona multi-agents alongside JSON-RPC 2.0 telemetry probes via the `ThreadingHTTPServer` threaten to lock the `SQLite-WAL` database (`repomap.db`)[cite: 2, 3, 4]. This initiative strips external dependencies in favor of standard library implementations, secures `repomap.db` with a dedicated writer thread[cite: 2, 4], implements a strict 4-tier model provider fallback (Gemma E4B, Antigravity CLI, Vertex API, OpenRouter API), and transitions the $0.33/day circuit breaker[cite: 3, 4] into a dual-mode monitoring system for predictive quota tracking and budget capping.

## 2. Index & File Reference

- Phase 1: Contextualization Engine & Standard Library Tokenization
  - Target File: `meta_harness/contextualize/truncator.py` (Lines: ~1-85, Token estimation)
  - Target File: `meta_harness/contextualize/engine.py` (Context bundling integration)
- Phase 2: Heuristic Intent Routing & 4-Tier Model Cascade
  - Target File: `meta_harness/router/stage1.py` (Replace `BART Large MNLI` with deterministic heuristics)
  - Target File: `meta_harness/router/stage2.py` (Implement Gemma E4B to OpenRouter cascade)
  - Target File: `.agent/config/vendors.json` (Provider endpoint schemas)
- Phase 3: SQLite-WAL Concurrency Hardening
  - Target File: `.agent/repomap/db.py` (Implement single-writer queue and PRAGMAs)
  - Target File: `meta_harness/orchestrator/main.py` (Writer daemon initialization)
- Phase 4: Dual-Mode Telemetry & Antigravity Quota Early-Warning
  - Target File: `meta_harness/router/circuit_breaker.py` (Refactor daily circuit breaker to predictive velocity and monthly cap)
  - Target File: `meta_harness/gui/server.py` (Expose HUD telemetry via `ThreadingHTTPServer`)
  - Target File: `meta_harness/gui/static/app.js` (Render predictive alerts natively)
  - Target File: `.agent/cache/quota.json` (Atomic state storage for spend and RPM)
- Phase 5: Zero-Dependency CI/CD & PEP 621 Packaging
  - Target File: `pyproject.toml` (New File Creation)
  - Target File: `requirements.txt` (Strip production dependencies)
  - Target File: `.github/workflows/ci.yml` (Enforce zero-dependency audit gates)

## 3. Phases Outline

### Phase 1: Contextualization Engine & Standard Library Tokenization

- Goal: Eliminate the `cl100k_base` tokenizer mismatch by deploying a zero-dependency, pure-Python token estimator[cite: 2, 4].
- Implementation Steps:
  1. Remove `cl100k_base` and external tokenizer binaries from `meta_harness/contextualize/truncator.py`[cite: 2, 4].
  2. Implement a pure standard library token estimator using calibrated character-to-token ratios.
  3. Update `meta_harness/contextualize/engine.py` to utilize this local heuristic when assembling diffs and file system state.
- Phase Gotchas & Strategic Notes:
  - Slicing structural AST bundles mid-declaration will severely impair the downstream 6 persona multi-agents[cite: 3, 4].
  - Always truncate to the nearest complete statement to prevent parsing corruption.

### Phase 2: Heuristic Intent Routing & 4-Tier Model Cascade

- Goal: Eradicate the heavy `BART Large MNLI` machine learning footprint and institute a strict 4-stage provider failover sequence[cite: 2, 4].
- Implementation Steps:
  1. Purge deep learning dependencies from `meta_harness/router/stage1.py` and implement a deterministic AST and keyword heuristic router for the 6 persona multi-agents[cite: 3, 4].
  2. Refactor `meta_harness/router/stage2.py` to route generation tasks via standard library HTTP and subprocess modules, executing a strict cascade: Gemma E4B (local) -> Antigravity CLI -> Vertex API -> OpenRouter API.
  3. Validate timeout handling across each tier to ensure hanging local models seamlessly failover.
- Phase Gotchas & Strategic Notes:
  - Gemma E4B has a smaller context window.
  - The router must gracefully escalate to the Antigravity CLI if the repository context exceeds local limits.

### Phase 3: SQLite-WAL Concurrency Hardening

- Goal: Prevent `repomap.db` database lockups caused by simultaneous agent writes and JSON-RPC 2.0 telemetry probes[cite: 2, 3, 4].
- Implementation Steps:
  1. Refactor `.agent/repomap/db.py` to route all write operations into a thread-safe standard library queue consumed by a single dedicated writer daemon[cite: 2, 4].
  2. Enforce explicit Write-Ahead Logging PRAGMAs on all read connections to maximize read concurrency[cite: 3, 4].
  3. Update the orchestrator in `meta_harness/orchestrator/main.py` to start and safely join the writer daemon during execution lifecycles.
- Phase Gotchas & Strategic Notes:
  - Do not share the writer thread's database connection with the `ThreadingHTTPServer`[cite: 3, 4].
  - Probes must instantiate isolated, read-only cursors.

### Phase 4: Dual-Mode Telemetry & Antigravity Quota Early-Warning

- Goal: Refactor the $0.33/day circuit breaker to track a hard $9.50/month Vertex API limit and a predictive Antigravity Pro velocity monitor[cite: 3, 4].
- Implementation Steps:
  1. Modify `meta_harness/router/circuit_breaker.py` to monitor 60-second Requests-Per-Minute (RPM) velocity against Antigravity CLI invocations to anticipate 5-hour quota depletion[cite: 4].
  2. Configure a monthly cumulative spend tracker capping Vertex API calls at $9.50, persisting state via atomic file replacements in `.agent/cache/quota.json`[cite: 3, 4].
  3. Update the vanilla JavaScript in `meta_harness/gui/static/app.js` and JSON-RPC endpoints in `meta_harness/gui/server.py` to serve active tier status and an early-warning velocity banner[cite: 3, 4].
- Phase Gotchas & Strategic Notes:
  - Ensure the frontend implementation remains strictly zero-dependency, relying only on native DOM updates rather than heavy external frameworks[cite: 4].

### Phase 5: Zero-Dependency CI/CD & PEP 621 Packaging

- Goal: Align the repository with modern Python standards, isolating `pytest` and strictly enforcing zero-dependency deployments[cite: 2, 4].
- Implementation Steps:
  1. Introduce a standard `pyproject.toml` to define the package metadata and console entry points, deprecating direct `requirements.txt` reliance for runtime[cite: 2, 4].
  2. Strip all third-party libraries from `requirements.txt`[cite: 3, 4].
  3. Update `.github/workflows/ci.yml` to execute the `pytest` test suite alongside an audit gate verifying that the environment contains zero unauthorized dependencies[cite: 2, 3, 4].
- Phase Gotchas & Strategic Notes:
  - Verify that the CLI entry points do not introduce circular imports between the orchestrator state machine and the `ThreadingHTTPServer` GUI[cite: 3, 4].

## 4. Final Mission & Execution Checklist

- Mission Statement:
Solidify the framework into a resilient, strictly zero-dependency SWE orchestration hub[cite: 2, 4]. The initiative fully eradicates heavy machine learning dependencies by adopting standard library token estimators and heuristic intent routing[cite: 2, 4]. It guarantees simultaneous multi-agent stability by isolating SQLite-WAL database writes to a dedicated queue[cite: 2, 3, 4]. Finally, it protects workflow continuity with a 4-tier local-to-cloud model fallback, backed by telemetry that proactively warns of Antigravity quota depletion and enforces strict Vertex cloud budgets[cite: 4].

- Implementation Checklist:

  - [X] **Phase 1: Zero-Dependency Contextualizer & Model Token Synchronization**
    - [X] `meta_harness/contextualize/truncator.py`:
      - [X] Purge `tiktoken` imports, binary bindings, and references to `cl100k_base`[cite: 2, 4].
      - [X] Implement `StdlibTokenEstimator` using calibrated code-to-prose weighting (3.6 characters/token for source code and AST nodes; 4.0 characters/token for markdown/prose).
      - [X] Implement `truncate_to_budget(content, max_tokens, boundary_mode="ast_statement")` to ensure AST node, class, and function definitions are truncated strictly along statement boundaries rather than mid-identifier[cite: 2, 4].
      - [X] Implement safe line-based slicing fallback when structural delimiters are absent.
    - [X] `meta_harness/contextualize/engine.py`:
      - [X] Refactor `ContextEngine.build_context_bundle()` to consume `StdlibTokenEstimator`[cite: 2, 4].
      - [X] Implement strict context packaging prioritization: active file diffs > repomap symbol definitions > AST skeletons > git commit history[cite: 2, 4].
      - [X] Inject dynamic model context ceilings based on active provider tier (e.g., lower budget threshold for Gemma E4B vs. cloud endpoints).
    - [X] `meta_harness/tests/test_contextualize.py`:
      - [X] Author unit tests asserting zero external third-party dependencies during token calculation[cite: 2, 4].
      - [X] Verify AST structural integrity under exact token boundary constraints.
      - [X] Test context packaging across 2k, 4k, 8k, and 32k token limits without syntax fragmentation.

  - [X] **Phase 2: Deterministic Heuristic Intent Routing & 4-Tier Model Cascade**
    - [X] `meta_harness/router/stage1.py`:
      - [X] Remove `torch`, `transformers`, and local `BART Large MNLI` model download routines[cite: 2, 4].
      - [X] Implement `DeterministicIntentRouter` using standard library regular expressions and keyword weighting.
    - [X] `meta_harness/router/persona_rules.py` (New File Creation):
      - [X] Create scoring matrices mapping task goals to the 6 SWE personas: Planner, Coder, Tester, Reviewer, Debugger, Orchestrator[cite: 2, 4].
      - [X] Implement action-verb precedence rules (e.g., "test implementation" -> `Tester`; "diagnose stacktrace" -> `Debugger`).
    - [X] `meta_harness/router/stage2.py`:
      - [X] Remove Google GenAI and third-party vendor SDKs; refactor client communication to pure standard library `urllib.request` and `subprocess`[cite: 2, 4].
      - [X] Implement `ProviderCascadeExecutor` supporting sequential failover:
        - Tier 1: Local Gemma E4B (subprocess / local HTTP endpoint).
        - Tier 2: Google Antigravity CLI (subprocess invocation with structured JSON output parsing).
        - Tier 3: GCP Vertex AI API (`urllib.request` REST client).
        - Tier 4: OpenRouter API (`urllib.request` REST fallback).
      - [X] Add pre-routing context size checks: automatically bypass Tier 1 (Gemma E4B) if context bundle exceeds the model's edge context window.
      - [X] Configure isolated timeout guards: 5s connection timeout for local Gemma, 30s timeout for Antigravity CLI, 20s for Vertex/OpenRouter REST endpoints.
    - [X] `.agent/config/vendors.json`:
      - [X] Clean vendor schemas to restrict endpoints, CLI binary paths, environment variable keys, and timeouts exclusively to the 4 approved providers[cite: 2, 4].
    - [X] `meta_harness/tests/test_router.py`:
      - [X] Test Stage 1 heuristic accuracy against a matrix of 25+ varied engineering prompts with sub-millisecond execution times.
      - [X] Test full Stage 2 cascade failover: simulate Tier 1 unavailability -> verify Tier 2 escalation; simulate Tier 2 failure -> verify Tier 3, etc.

  - [X] **Phase 3: SQLite-WAL Concurrency Hardening & Writer Queue Daemon**
    - [X] `.agent/repomap/db.py`:
      - [X] Refactor connection factory to configure Write-Ahead Logging PRAGMAs:
        - `PRAGMA journal_mode = WAL;`[cite: 2, 4]
        - `PRAGMA busy_timeout = 5000;`[cite: 2, 4]
        - `PRAGMA synchronous = NORMAL;`
      - [X] Implement `DatabaseWriterQueue`: a background daemon `threading.Thread` consuming SQL write queries and parameters from a standard library `queue.Queue()`.
      - [X] Implement synchronous commit checkpoints using `threading.Event` for operations requiring read-after-write consistency.
      - [X] Configure all telemetry probes and read queries to use isolated, read-only cursor connections to fully leverage WAL concurrent read capabilities[cite: 2, 4].
    - [X] `meta_harness/orchestrator/main.py`:
      - [X] Initialize and start `DatabaseWriterQueue` on orchestrator startup[cite: 2, 4].
      - [X] Register shutdown hooks (`atexit` and `signal.signal`) to drain pending queue writes and cleanly close the database connection upon task completion or user interrupt [SIGINT/Ctrl+C](cite: 2, 4).
    - [X] `meta_harness/tests/test_repomap.py`:
      - [X] Build concurrent stress-test suite simulating 6 persona threads writing graph nodes simultaneously while GUI probes execute read queries[cite: 2, 4].
      - [X] Assert zero occurrences of `sqlite3.OperationalError: database is locked` across 100+ concurrent operations[cite: 2, 4].

  - [X] **Phase 4: Dual-Mode Telemetry & Antigravity Quota Early-Warning System**
    - [X] `meta_harness/router/circuit_breaker.py`:
      - [X] Deprecate the legacy $0.33/day budget circuit breaker[cite: 2, 4].
      - [X] Implement `VertexMonthlyBudgetBreaker`:
        - Track token usage and compute cumulative costs for Tier 3 Vertex API invocations.
        - Enforce calendar month detection with automatic budget reset on day 1 of each month.
        - Trigger immediate failover to Tier 4 (OpenRouter) when Vertex spend reaches $9.50.
      - [X] Implement `AntigravitySwarmRateMonitor`:
        - Record all Antigravity CLI invocations across the swarm in a 60-second sliding timestamp window[cite: 2, 4].
        - Calculate swarm-wide aggregate Requests-Per-Minute (RPM).
        - Implement predictive burn heuristic tracking concurrent persona session density against the 5-hour rolling Pro credit window.
        - Raise `ANTIGRAVITY_THROTTLE_WARNING` boolean flag when request acceleration indicates impending quota restrictions.
    - [X] `.agent/cache/quota.json`:
      - [X] Update JSON schema to persist: `vertex_month_spend`, `vertex_budget_ceiling` ($9.50), `antigravity_swarm_rpm`, `antigravity_warning_active`, and `last_updated_timestamp`[cite: 2, 4].
      - [X] Implement atomic file updates (write to temporary file + `os.replace`) to prevent corrupted cache reads during parallel persona execution[cite: 2, 4].
    - [X] `meta_harness/gui/server.py` & `meta_harness/gui/static/app.js`:
      - [X] Expose JSON-RPC endpoint `/rpc/telemetry` returning active provider tier, Vertex monthly budget progress, swarm RPM, and throttle warning flags[cite: 2, 4].
      - [X] Update telemetry dashboard using vanilla HTML, CSS, and JavaScript:
        - Active Provider Tier Badge (Gemma -> Antigravity -> Vertex -> OpenRouter).
        - Vertex AI Monthly Spend Progress Bar ($X.XX / $9.50).
        - Swarm RPM Gauge and visual early-warning banner indicating Antigravity throttle risk[cite: 2, 4].
    - [X] `meta_harness/tests/test_circuit_breaker.py`:
      - [X] Verify that reaching the $9.50 monthly Vertex threshold trips the breaker and routes directly to OpenRouter.
      - [X] Validate RPM velocity calculations and warning state triggers under simulated burst traffic.

  - [X] **Phase 5: Modern Zero-Dependency Packaging \& CI/CD Enforcement**
    - [X] `pyproject.toml` (New File Creation):
      - [X] Author PEP 517 / PEP 621 compliant configuration defining metadata, Python compatibility (`>=3.9`), and zero runtime dependencies[cite: 2, 4].
      - [X] Define console entry point scripts:
        - [X] `meta-harness = meta_harness.orchestrator.main:main`[cite: 2, 4]
        - [X] `meta-harness-gui = meta_harness.gui.cli:main`[cite: 2, 4]
      - [X] Configure development dependency group: `[project.optional-dependencies] dev = ["pytest"]`[cite: 2, 4].
    - [X] `requirements.txt`:
      - [X] Remove all third-party runtime dependencies (e.g., `torch`, `transformers`, `tiktoken`)[cite: 2, 4].
      - [X] Direct local installation to `-e .[dev]` or retain exclusively development test runners[cite: 2, 4].
    - [X] `.github/workflows/ci.yml`:
      - [X] Configure test matrix covering Python 3.9 through 3.13[cite: 2, 4].
      - [X] Add automated CI audit gate asserting `pip list` contains zero unauthorized runtime packages[cite: 2, 4].
      - [X] Mandate passing pytest execution for pull request merges into `main`[cite: 2, 4].
    - [X] Documentation & Final System Verification:
      - [X] Update `README.md` to reflect zero-dependency architecture, 4-tier fallback sequence, and dual telemetry HUD metrics[cite: 2, 4].
      - [X] Execute clean smoke tests:
        - [X] `python meta_harness/orchestrator/main.py --project . --goal "Test task"`[cite: 2, 4]
        - [X] `python -m meta_harness.gui.cli --port 8087`[cite: 2, 4]
        - [X] `pytest`[cite: 2, 4]

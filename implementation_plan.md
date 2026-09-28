# Implementation Plan: Zero-Toil Multi-Language Refactor & Hardened Terminal Operations

## 1. Summary & Architectural Assessment

This refactor transitions `meta-harness-project` from an over-engineered hybrid web/ML system into a durable, self-healing developer harness[cite: 1, 3]. We eliminate local neural network dependencies (BART-Large MNLI) and web assets [HTML/CSS/JS/ThreadingHTTPServer](cite: 1, 3). In their place, we implement a two-stage router with a strictly non-destructive offline executor, Gemini-native token budgeting, resilient multi-language AST extraction via pre-compiled grammars, and a decoupled terminal telemetry dashboard[cite: 1, 3].

- **Trade-offs & Maintenance Attack Surface**:
  - *Dynamic Binaries vs. Pre-Compiled Wheels*: On-demand binary downloading creates an unmaintainable matrix of libc versions (glibc vs. musl), architectures (x86_64, aarch64, arm64), and network availability risks. Standardizing on `tree-sitter-languages` adds ~30MB to the environment installation but completely eliminates runtime compilation, network requirements, and binary drift.
  - *Non-Destructive Offline Isolation*: When severed from network LLM routing, the framework executes diagnostic workspace checks (test runs, git status/diff inspections) without modifying user files, preventing unintended file mutations while maintaining operational visibility[cite: 1, 3].
  - *Terminal Telemetry vs. Browser HUD*: Purging the HTTP server eliminates port collisions, browser cache mismatches, and web asset maintenance, standardizing all monitoring on stdout/stderr streams[cite: 1, 3].
- **Upstream Dependency Vetting**:
  - `google-genai`: The official, supported Google SDK for Gemini Flash model routing and bundle token validation[cite: 1, 3].
  - `rich`: The established, cross-platform terminal rendering standard (maintained by Textualize) for live tables, gauges, and formatting.
  - `tree-sitter-languages`: Vetted, pre-built binary wheels bundling pre-compiled parsers for 30+ languages without local compiler dependencies.
  - `networkx`: Pure-Python graph library for Repomap PageRank centrality and SCC cycle detection[cite: 1, 3].
  - Python Standard Library (`sqlite3`, `subprocess`, `re`, `argparse`): Prioritized for concurrency management, process execution, and fallback parsing.
- **Hard Failure Modes & Non-Negotiable Boundaries**:
  - Zero dynamic binary downloads or runtime package installations (`pip` subprocesses are strictly banned).
  - Zero local PyTorch, Transformers, or ONNX runtimes[cite: 3].
  - Complete eradication of OpenAI's `cl100k_base` tokenizer[cite: 1, 3].
  - Offline fallback must remain strictly non-destructive; it cannot execute automated formatters, code mods, or disk writes unless explicit CLI authorization flags are passed.
  - Telemetry database reads must strictly use read-only URI mode (`file:repomap.db?mode=ro`) to eliminate lock contention against active agent write transactions[cite: 1, 3].
- **Explicit Omissions**:
  - No browser-based web servers (FastAPI, Flask, Starlette, or `ThreadingHTTPServer`)[cite: 1, 3].
  - No heavyweight multi-agent frameworks [LangChain, AutoGen, CrewAI](cite: 1).
  - No external vector databases (Chroma, FAISS); context retrieval relies entirely on Repomap graph topology and git diffs[cite: 1, 3].

## 2. Index & File Reference

- Phase 1: Packaging Modernization & Dependency Purge
  - Target File: `requirements.txt` [Deprecate/Convert to editable pointer](cite: 1, 3)
  - Target File: `pyproject.toml` (New File Creation: Standardized PEP 621 packaging and console scripts)
  - Target File: `.github/workflows/ci.yml` [Hardening CI test matrices](cite: 1, 3)
- Phase 2: Deterministic Router & Non-Destructive Offline Execution (Orchestration Engine)
  - Target File: `meta_harness/router/stage1_classifier.py` [Purged: BART-Large MNLI removed](cite: 1, 3)
  - Target File: `meta_harness/router/router.py` [Implement regex matching, Gemini Stage 2, and non-destructive offline fallback](cite: 1, 3)
  - Target File: `meta_harness/router/circuit_breaker.py` [Enforce daily $0.33 spend ceiling](cite: 1, 3)
- Phase 3: Token Harmonization & Defensive Multi-Language AST Parsing (Context Engine)
  - Target File: `meta_harness/contextualize/budget.py` (Evict `tiktoken`, implement character-ratio estimator & Gemini API verification)[cite: 1, 3]
  - Target File: `meta_harness/contextualize/bundler.py` [AST context truncation limits](cite: 1, 3)
  - Target File: `.agent/repomap/ast_parser.py` (New File Creation: Multi-language parsing via `tree-sitter-languages` with regex fallback)[cite: 1, 3]
- Phase 4: Thread-Safe Telemetry & Rich Terminal HUD (Tool & Interface Engines)
  - Target File: `meta_harness/gui/*` (Complete Directory Deletion: Remove HTML, CSS, JS, and `ThreadingHTTPServer`)[cite: 1, 3]
  - Target File: `meta_harness/cli/hud.py` [New File Creation: Rich terminal dashboard and read-only SQLite inspection](cite: 1, 3)
  - Target File: `meta_harness/cli/__main__.py` (New File Creation: Unified CLI entrypoint)
  - Target File: `.agent/repomap/storage.py` [Enforce WAL pragmas, connection pooling, and read-only URI isolation](cite: 1, 3)
- Phase 5: Verification & End-to-End Regression Harness
  - Target File: `meta_harness/tests/test_router.py` [Verify heuristics, Gemini fallback, and offline read-only isolation](cite: 1, 3)
  - Target File: `meta_harness/tests/test_context.py` [Validate token estimations and multi-language AST extraction](cite: 1, 3)
  - Target File: `meta_harness/tests/test_storage.py` [Concurrency stress test with 6 writing agents and active CLI reads](cite: 1, 3)
  - Target File: `meta_harness/tests/test_cli.py` (New File Creation: Headless terminal rendering test)

## 3. Phases Outline

### Phase 1: Packaging Modernization & Dependency Purge

- Goal: Establish a modern, zero-toil packaging baseline using PEP 621 and completely remove local ML framework bloat[cite: 1, 3].
- Implementation Steps:
  1. Author `pyproject.toml` specifying build backend (`setuptools>=68.0`), project metadata, console scripts (`meta-harness` and `meta-harness-hud`), and core dependencies: `google-genai`, `rich`, `tree-sitter-languages`, `networkx`, and `pytest`[cite: 1, 3].
  2. Permanently delete `torch`, `transformers`, `tiktoken`, and any build toolchain scripts from the environment[cite: 1, 3].
  3. Replace `requirements.txt` with a single `-e .` reference for legacy compatibility[cite: 1, 3].
  4. Update `.github/workflows/ci.yml` to run clean matrix tests on Python 3.9 through 3.13 without cached torch wheels[cite: 1, 3].
- Phase Gotchas & Strategic Notes:
  - Gotchas: Ensure subpackage imports across `meta_harness` and `.agent` resolve cleanly in editable mode without modifying `sys.path`.
  - Anti-patterns: Adding shell scripts that invoke `pip` at runtime to install missing dependencies dynamically.
  - Maintenance traps: Retaining stale ML configuration options or mock fixtures in `pytest.ini`[cite: 1, 3].

### Phase 2: Deterministic Router & Non-Destructive Offline Execution

- Goal: Replace BART-Large with a deterministic heuristic fast-path, backed by structured Gemini Flash Stage 2 routing and a non-destructive offline diagnostic runner[cite: 1, 3].
- Implementation Steps:
  1. Delete `meta_harness/router/stage1_classifier.py` and remove all Hugging Face model checkpoint loaders[cite: 1, 3].
  2. In `meta_harness/router/router.py`, construct a fast-path regex/keyword lookup table mapping standard engineering goals directly to personas:
     - `test`, `pytest`, `verify` -> `Tester`[cite: 1, 3]
     - `fix`, `bug`, `traceback`, `error` -> `Debugger`[cite: 1, 3]
     - `refactor`, `clean`, `style` -> `Reviewer`[cite: 1, 3]
     - `plan`, `spec`, `architect` -> `Planner`[cite: 1, 3]
  3. For complex queries, check `circuit_breaker.py` ($0.33/day ceiling); if budget permits and the network is live, query Gemini Flash using a structured JSON schema to assign the persona[cite: 1, 3].
  4. Implement the offline fallback handler: if network resolution fails, the API key is unset, or Gemini is unreachable, route to `Orchestrator`[cite: 1, 3]. The offline Orchestrator executes strictly non-destructive workspace diagnostics via `subprocess`:
     - Executes local tests (`pytest`) in isolated discovery/run mode without updating files[cite: 1, 3].
     - Inspects git working tree status and diffs via `git status --short` and `git diff`[cite: 1, 3].
     - Emits a structured diagnostic report to `.agent/cache/offline_report.json` without modifying code files[cite: 1, 3].
     - Explicitly voids and rejects write automations (e.g., auto-formatters, patch applications) unless an explicit `--allow-destructive` flag is passed.
- Phase Gotchas & Strategic Notes:
  - Gotchas: Subprocess execution during offline fallback must enforce strict timeouts (`timeout=30`) and handle non-zero exit codes gracefully so the CLI never hangs.
  - Anti-patterns: Permitting the offline fallback to modify source code files without an active LLM validation step.
  - Maintenance traps: Building a complex natural language parser into the heuristic table. Keep regex rules concise and hand off unhandled online tasks to Gemini[cite: 1, 3].

### Phase 3: Token Harmonization & Defensive Multi-Language AST Parsing

- Goal: Prevent token calculation drift using native Gemini accounting and implement unified multi-language AST extraction via pre-compiled grammars[cite: 1, 3].
- Implementation Steps:
  1. Purge `tiktoken` and the `cl100k_base` specification from `meta_harness/contextualize/budget.py`[cite: 1, 3].
  2. Implement an offline character-ratio estimator in `budget.py`: use a ratio of 3.5 characters per token with a conservative 15% safety buffer for intermediate file slicing and diff pruning[cite: 1, 3].
  3. In `meta_harness/contextualize/bundler.py`, validate final context bundles against the model limit using `client.models.count_tokens` from `google-genai` when online[cite: 1, 3].
  4. Implement `.agent/repomap/ast_parser.py` using `tree-sitter-languages` to extract structural code skeletons [classes, functions, method signatures, exports](cite: 1, 3):
     - Support Python, JavaScript, TypeScript, Go, Rust, Java, C, and C++ out of the box using pre-compiled grammar bindings.
     - Implement automatic language detection mapped from file extensions (`.py`, `.js`, `.ts`, `.go`, `.rs`, `.java`, `.cpp`, `.c`).
     - Universal Fallback: If a file extension is not supported by `tree-sitter-languages`, extract top-level declarations using standard regex indentation patterns rather than attempting to download external binaries.
- Phase Gotchas & Strategic Notes:
  - Gotchas: Ensure binary files, minified bundles, and large lockfiles (`package-lock.json`, `uv.lock`) are ignored before AST extraction to prevent parsing bottlenecks.
  - Anti-patterns: Fetching `.so`, `.dylib`, or `.wasm` files over the network during parsing; all language grammars must originate from the verified `tree-sitter-languages` wheel.
  - Maintenance traps: Storing duplicate symbol tables; ensure extracted AST nodes are normalized directly into the SQLite-WAL schema in `.agent/cache/repomap.db`[cite: 1, 3].

### Phase 4: Thread-Safe SQLite-WAL & Rich Terminal HUD

- Goal: Purge browser web assets and implement an intuitive, thread-safe terminal dashboard for live agent observability and quota tracking[cite: 1, 3].
- Implementation Steps:
  1. Completely delete the `meta_harness/gui/` directory, including its HTML, CSS, JavaScript files, and `ThreadingHTTPServer` implementation[cite: 1, 3].
  2. In `.agent/repomap/storage.py`, harden database operations by wrapping all connections in a context manager applying[cite: 1, 3]:
     - `PRAGMA journal_mode=WAL;`[cite: 1, 3]
     - `PRAGMA busy_timeout=5000;`[cite: 1, 3]
     - `PRAGMA synchronous=NORMAL;`[cite: 1, 3]
  3. Implement `meta_harness/cli/hud.py` using `rich.console.Console`, `rich.table.Table`, `rich.panel.Panel`, and `rich.live.Live`:
     - Render active agent persona, current execution state, and loop guard counter[cite: 1, 3].
     - Display daily spending gauges against the $0.33 limit[cite: 1, 3].
     - Display Repomap graph metrics [total indexed symbols, PageRank centrality leaders, detected SCC cycles](cite: 1, 3).
     - Render a scrolling live log of recent orchestration events[cite: 1].
  4. In `hud.py`, ensure all telemetry database connections connect using URI read-only mode (`file:.agent/cache/repomap.db?mode=ro`) to prevent dashboard monitoring from locking active multi-agent writes[cite: 1, 3].
  5. Implement `meta_harness/cli/__main__.py` to provide a clean CLI experience (`meta-harness run --goal "..."`, `meta-harness hud`, `meta-harness repomap index`).
- Phase Gotchas & Strategic Notes:
  - Gotchas: In `rich.live.Live`, set `auto_refresh=False` and refresh manually on discrete telemetry polling intervals to avoid screen flickering on constrained terminals.
  - Anti-patterns: Spawning an HTTP server or embedding a webview when standard terminal output meets all operational monitoring requirements[cite: 1, 3].
  - Maintenance traps: Writing telemetry metrics to raw JSON files and SQLite simultaneously; designate `repomap.db` as the sole operational source of truth[cite: 1, 3].

### Phase 5: Verification & End-to-End Regression Harness

- Goal: Validate intent routing, multi-language parsing, token management, and concurrency safety under automated test execution[cite: 1, 3].
- Implementation Steps:
  1. In `meta_harness/tests/test_router.py`, assert that[cite: 1, 3]:
     - Deterministic inputs match correct personas via heuristics[cite: 1, 3].
     - Complex queries hit mocked Gemini Flash schemas when online[cite: 1, 3].
     - Simulated network loss triggers the offline Orchestrator to execute local non-destructive rules (tests/git status) without crashing and without mutating files[cite: 1, 3].
  2. In `meta_harness/tests/test_context.py`, verify that[cite: 1, 3]:
     - Character-ratio estimations safely approximate tokens within a 15% margin[cite: 1, 3].
     - Multi-language code samples (Python, TypeScript, Go, Rust) generate valid AST symbol trees via `ast_parser.py`[cite: 1, 3].
     - Unsupported file types fall back gracefully to basic structural regex extraction without throwing exceptions.
  3. In `meta_harness/tests/test_storage.py`, write a concurrency stress test: spin up 6 worker threads writing simulated agent states to `repomap.db` while 2 CLI reader threads query the database every 20ms in `mode=ro`, asserting zero `sqlite3.OperationalError: database is locked` exceptions[cite: 1, 3].
  4. In `meta_harness/tests/test_cli.py`, initialize `hud.py` using `rich.console.Console(record=True)` to verify terminal layout rendering and ensure clean shutdown on `SIGINT`.
- Phase Gotchas & Strategic Notes:
  - Gotchas: Mock all external Google GenAI API calls in the automated test suite to prevent API billing during CI execution.
  - Anti-patterns: Committing generated SQLite test databases or coverage outputs into version control; enforce temporary directory (`tmp_path`) isolation.
  - Maintenance traps: Writing tests that assert exact visual character layouts in the terminal; assert underlying table data states instead.

## 4. Final Mission & Execution Checklist

- **Mission Statement**: This refactor transforms Meta-Harness into an enduring, low-maintenance orchestration engine by eliminating local neural network dependencies and web UI baggage[cite: 1, 3]. Multi-language AST indexing is standardized through pre-compiled upstream wheels, intent routing is backed by a strictly non-destructive offline diagnostic executor, and operational observability is unified in a responsive terminal interface[cite: 1, 3]. Every pillar adheres to strict decoupling contracts and boring, established technology to guarantee long-term operational resilience without maintenance drag[cite: 1, 3].
- **Implementation Checklist**:
  - [ ] Create `pyproject.toml` declaring dependencies (`google-genai`, `rich`, `tree-sitter-languages`, `networkx`) and CLI entrypoints[cite: 1, 3].
  - [ ] Purge `torch`, `transformers`, `tiktoken`, and legacy `requirements.txt`[cite: 1, 3].
  - [ ] Delete `stage1_classifier.py` and implement regex fast-path routing in `meta_harness/router/router.py`[cite: 1, 3].
  - [ ] Implement Gemini Flash Stage 2 routing with $0.33/day circuit breaker protection[cite: 1, 3].
  - [ ] Implement non-destructive offline fallback in `router.py` [executes read-only pytest/git status/diff](cite: 1, 3).
  - [ ] Purge `cl100k_base` and implement the 3.5 char/token estimator + native Gemini API token validation[cite: 1, 3].
  - [ ] Implement `.agent/repomap/ast_parser.py` using `tree-sitter-languages` with extension-based grammar mapping and regex fallback[cite: 1, 3].
  - [ ] Delete `meta_harness/gui/` and its HTML/CSS/JS assets[cite: 1, 3].
  - [ ] Implement `meta_harness/cli/hud.py` using `rich` with read-only SQLite access (`mode=ro`)[cite: 1, 3].
  - [ ] Enforce SQLite-WAL pragmas (`busy_timeout=5000`, `synchronous=NORMAL`) in `storage.py`[cite: 1, 3].
  - [ ] Pass all unit, integration, and concurrency stress tests via `pytest`[cite: 1, 3].

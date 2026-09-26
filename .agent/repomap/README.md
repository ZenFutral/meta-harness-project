# Repomap Subsystem

Structural code intelligence engine providing AST parsing, symbol indexing, centrality ranking, dependency cycle detection, and token-budgeted skeleton packing.

---

## Overview

The `repomap` subsystem operates within `.agent/repomap` and builds an in-depth two-tier graph representation of the repository. It indexes symbols (classes, functions, methods, imports), calculates graph centrality, and serves faceted queries to the context engine and agent orchestrator via JSON-RPC or CLI.

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Repomap Engine                                │
│                                                                        │
│   Source Files ──► Tree-sitter / AST Parser                            │
│                            │                                           │
│                            ▼                                           │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ SQLite-WAL Database (.agent/cache/repomap.db)                  │   │
│   │ • parse_cache          • symbol_references                     │   │
│   │ • export_registry      • wildcard_dependencies                 │   │
│   └────────────────────────────────┬───────────────────────────────┘   │
│                                    │                                   │
│            ┌───────────────────────┼───────────────────────┐           │
│            ▼                       ▼                       ▼           │
│   ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐   │
│   │ TwoTierGraph    │    │ CentralityRanker │    │ DensityPacker   │   │
│   │ (Imports & Call)│    │ (PageRank/Bi-Dir)│    │ (Budget Guard)  │   │
│   └────────┬────────┘    └─────────┬────────┘    └────────┬────────┘   │
│            └───────────────────────┼──────────────────────┘            │
│                                    ▼                                   │
│                        RepomapJSONRPCServer & CLI                      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Architecture & Components

1. **`core/storage.py` (`RepomapStorage`)**:
   - Manages SQLite database connection using **Write-Ahead Logging (WAL)** mode for concurrent readers.
   - Handles schema migrations and caching for AST symbol definitions and export registries.
   - Implements recursive Common Table Expression (CTE) transitive cache invalidation when files change.
2. **`core/graph.py` (`TwoTierGraph`)**:
   - Builds macro (module import level) and micro (symbol call level) dependency graphs.
   - Implements Tarjan's Strongly Connected Components (SCC) algorithm for import cycle detection (`find_cycles()`).
3. **`core/ranker.py` (`CentralityRanker`)**:
   - Computes weighted PageRank scores across symbols and files.
   - Biases scores toward focus files and active working targets.
4. **`core/packer.py` (`MarginalDensityPacker`)**:
   - Generates compact Python code skeletons representing top-ranked symbols.
   - Strictly enforces token budgets using line-by-line marginal utility packing.
5. **`facets/`**:
   - `hierarchy.py`: Traverses symbol type hierarchies and class inheritance trees.
   - `schemas.py`: Extracts Pydantic models, dataclasses, and DTO schemas into a central registry.
   - `blast_radius.py`: Computes upstream caller and downstream callee impact trees.
6. **`server.py` (`RepomapJSONRPCServer`)**:
   - Standalone JSON-RPC 2.0 tool server exposing indexing and querying methods to LLM tools and external callers.

---

## CLI Usage

The Repomap CLI can be executed directly:

```bash
python .agent/repomap/cli.py <command> [options]
```

### Available Commands

- **Index Repository**:
  ```bash
  python .agent/repomap/cli.py index --full
  # Or dirty index only modified files:
  python .agent/repomap/cli.py index --dirty
  ```
- **Generate Token-Budgeted Code Summary**:
  ```bash
  python .agent/repomap/cli.py summary --budget 2048 --focus "meta-harness/orchestrator/orchestrator.py"
  ```
- **Trace Symbol Hierarchy & Blast Radius**:
  ```bash
  python .agent/repomap/cli.py trace "Orchestrator" --direction both --depth 3
  ```
- **Extract Schema Registry**:
  ```bash
  python .agent/repomap/cli.py schemas
  ```
- **Detect Import Cycles**:
  ```bash
  python .agent/repomap/cli.py cycles
  ```
- **Start JSON-RPC Server**:
  ```bash
  python .agent/repomap/cli.py serve --rpc
  ```

---

## JSON-RPC Methods

| Method | Parameters | Description |
| --- | --- | --- |
| `repo_map_summary` | `budget_tokens` (int), `focus_files` (list[str]) | Returns packed code skeleton within token budget. |
| `get_symbol_hierarchy` | `symbol_name` (str), `direction` (str), `max_depth` (int) | Traces class inheritance and call relationships. |
| `get_schema_registry` | `{}` | Returns all registered Pydantic models and dataclasses. |
| `resolve_imports` | `source_file` (str), `target_file` (str) | Resolves dependency path between two source files. |

---

## Testing

Run unit tests for Repomap:

```bash
pytest .agent/repomap/tests
```

<div align="center">

# Fusion-Code-Modelization

**Legacy Code Modernization & Cross-Language Migration Platform**

Modernize, refactor, and migrate legacy codebases — entirely local, powered by fusion-mlx.

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-727+-success.svg)](tests/)

[Quick Start](#quick-start) · [CLI Reference](#cli-reference) · [Architecture](#architecture) · [Changelog](#changelog)

</div>

---

## Why Fusion-Code-Modelization?

| Feature | Fusion-Code-Modelization | Claude Code Modernization |
|---------|--------------------------|--------------------------|
| **Local offline** | ✅ 100% local | ❌ Cloud-only |
| **Data privacy** | ✅ Data never leaves device | ❌ Code uploaded to cloud |
| **China compliance** | ✅ Full compliance | ❌ Violates data security law |
| **Zero API cost** | ✅ | ❌ Enterprise subscription |
| **Cross-language migration** | ✅ COBOL→Java, VB6→C#, etc. | ✅ |
| **Safe incremental refactoring** | ✅ Test-first + dual-run verify | ✅ |
| **Security scanning** | ✅ Static + LLM-powered | ✅ |
| **Enterprise pipeline** | ✅ Git/CI-CD/PR/Audit logs | ✅ |
| **Streaming LLM output** | ✅ Real-time token streaming | ❌ |
| **Progress callbacks** | ✅ Composable callback system | ❌ |
| **Microservice decomposition** | ✅ | ✅ |
| **Git integration** | ✅ Gitee, GitHub, GitLab | ✅ GitHub only |
| **Parallel multi-agent sessions** | ✅ SessionEngine | ✅ |
| **Dynamic Workflow** | ✅ LLM task decomposition | ✅ |
| **Incremental snapshots** | ✅ FileDelta + SnapshotManager | ✅ |
| **Three-tier project memory** | ✅ FUSION.md (global/project/directory) | ✅ CLAUDE.md |
| **Security sandbox** | ✅ Three-tier (readonly/manual/auto) | ✅ |
| **Dual-stack model routing** | ✅ local/cloud + complexity routing | ✅ |
| **Enterprise audit** | ✅ JSONL + search/export/statistics | ✅ |
| **Cluster scheduling** | ✅ Node registration + auto-schedule | ✅ |
| **MCP plugin platform** | ✅ Registry + lifecycle management | ✅ |
| **Benchmark suites** | ✅ Code quality, performance, migration, security | ✅ |
| **Cluster load balancing** | ✅ 4 strategies (round-robin/least-loaded/weighted/affinity) | ✅ |
| **Offline deployment** | ✅ Full-offline/semi-offline/online with capability matrix | ✅ |
| **Full-chain traceability** | ✅ Artifact tracking with forward/backward BFS traversal | ✅ |
| **Agent cross-machine comm** | ✅ Channel-based collaboration with conflict resolution | ✅ |

---

## Quick Start

### Prerequisites

- macOS with Apple Silicon (M1–M5)
- Python 3.12+
- [fusion-gateway](https://github.com/dahai80/fusion-gateway) running on `localhost:11432` (the unified inference gateway), with [fusion-mlx](https://github.com/dahai80/fusion-mlx) as its upstream on `localhost:11434`

### Authentication & Model ID

All inference is routed through **fusion-gateway** (`localhost:11432/v1`); this package never connects to fusion-mlx (`localhost:11434`) directly. `MLXClient` authenticates to the gateway with a bearer token. The API key is resolved in priority order (first non-empty wins):

1. `FUSION_MLX_API_KEY` environment variable — the **gateway client key** (e.g. `fg-admin-key`)
2. `MLX_API_KEY` environment variable
3. `OPENAI_API_KEY` environment variable

> ⚠️ The key must be a gateway client key registered in fusion-gateway's `config.yaml` (`auth.api_keys`), **not** the fusion-mlx upstream key. If none is set, requests run unauthenticated and the gateway will reject them.

The default local model id is `Qwen3.5-9B-4bit` (must match a model loaded by the gateway's fusion-mlx upstream — check `~/claude-home/fusion-mlx/start.sh status`). Override per call with `MLXClient(...).chat(model=...)` or by constructing a custom `ModelConfig`.

```bash
export FUSION_MLX_API_KEY="<gateway-client-key>"   # e.g. fg-admin-key
```

### Install

```bash
git clone https://github.com/dahai80/fusion-code-modelization.git
cd fusion-code-modelization
pip install -e ".[test]"
```

### Analyze a Codebase

```bash
fusion-code-modelization analyze /path/to/codebase --output=report.md
```

### Transpile Code Between Languages

```bash
# Python → Java
fusion-code-modelization transpile input.py --from=python --to=java --output=output.java

# COBOL → Go (with real-time streaming)
fusion-code-modelization transpile legacy.cbl --from=cobol --to=go --stream

# COBOL → Go with Agent Loop self-heal (verify logic equivalence + auto-retry on failure)
fusion-code-modelization transpile legacy.cbl --from=cobol --to=go --loop --max-iter=5
```

### Refactor Code Safely

```bash
fusion-code-modelization refactor legacy_code.py --instructions="add type hints" --output=refactored.py

# With Agent Loop self-heal (dual-run equivalence verify + auto-retry)
fusion-code-modelization refactor legacy_code.py --instructions="add type hints" --loop --output=refactored.py
```

### Generate Tests

```bash
fusion-code-modelization test-gen source.py --output=tests.py
```

### Security Scan

```bash
fusion-code-modelization security legacy_code.py --output=security_report.json
```

### Generate Documentation

```bash
# Module docs
fusion-code-modelization doc-gen source.py --type=module --output=docs.md

# API docs (streaming)
fusion-code-modelization doc-gen api.py --type=api --stream
```

---

## CLI Reference

| Command | Description |
|---------|-------------|
| `analyze <path> [--output]` | Analyze codebase dependencies and generate report |
| `transpile <file> --from --to [--output] [--stream]` | Transpile code between languages |
| `refactor <file> [--instructions] [--output] [--stream]` | Refactor code incrementally |
| `test-gen <file> [--language] [--output] [--stream]` | Generate unit tests |
| `security <file> [--language] [--output] [--stream]` | Scan for security vulnerabilities |
| `doc-gen <file> [--type] [--language] [--output] [--stream]` | Documentation generation (module/class/api) |
| `session <action> [--id] [--name]` | Manage parallel sessions (create/list/start/pause/resume/complete/delete) |
| `snapshot <action> [--project-dir] [--id] [--label] [--steps]` | Incremental snapshots and rollback (create/list/restore/rewind/delete) |
| `workflow <action> [--description] [--template] [--max-parallel]` | Dynamic task decomposition and execution (decompose/run) |
| `memory <action> [--project-dir] [--query]` | Three-tier project memory (init/list/load/query) |
| `sandbox <action> [--path] [--mode]` | Security sandbox and audit (check/audit) |
| `decompose <path> [--method] [--output]` | Microservice boundary detection (static/llm) |
| `audit <action> [--actor] [--severity]` | Enterprise audit logging (log/search/export/stats/cleanup) |
| `cluster <action> [--node-id] [--session-id]` | Distributed cluster scheduling (discover/dispatch/status/schedule/migrate/register/tasks) |
| `plugin <action> [--plugin-id] [--query]` | MCP plugin platform (list/search/install/load/unload/execute/status) |
| `benchmark <action> [--suite] [--report-id]` | Run benchmark suites and compare reports (run/list/compare/history) |
| `loadbalancer <action> [--strategy]` | Cluster load balancing (overview/rebalance/predict/select) |
| `offline <action> [--mode] [--package-dir]` | Offline deployment management (detect/capabilities/prepare/validate/restore) |
| `trace <action> [--artifact-type] [--artifact-id]` | End-to-end traceability (create/link/forward/backward/report) |
| `agent-comm <action> [--agents] [--collab-id]` | Agent cross-machine communication (create/submit/conflict/resolve/complete/list/status) |
| `version` | Show version info |
| `serve [--host] [--port] [--mlx-url]` | Start the REST API server (default `127.0.0.1:11459`) |
| `--json` | Global flag: output results as JSON |
| `--verbose` / `-v` | Global flag: enable debug logging |
| `--quiet` / `-q` | Global flag: suppress non-error output |

### Streaming Mode

Commands that call the LLM support `--stream` for real-time token output:

```bash
fusion-code-modelization transpile src.py --from=python --to=java --stream
fusion-code-modelization refactor src.py --stream
fusion-code-modelization test-gen src.py --stream
fusion-code-modelization security src.py --stream
fusion-code-modelization doc-gen src.py --stream
```

### Agent Loop (Self-Heal)

`--loop` enables a bounded, fully-traced self-heal loop on `transpile`, `refactor`, and `test-gen`. The
model decides *how to fix* an output that fails verification — it does **not** pick which tool to run, so
the tool sequence stays fixed and auditable. Each iteration: build prompt → LLM → extract code → verify
tool → on failure, feed the error back and retry, up to `--max-iter` (default 5). A JSONL trace is written
per run.

```bash
# transpile with logic-equivalence verification
fusion-code-modelization transpile legacy.cbl --from=cobol --to=go --loop --max-iter=5

# refactor with dual-run equivalence verification
fusion-code-modelization refactor legacy_code.py --loop

# test-gen with syntax-check verification (python uses compile(); other langs use an LLM check)
fusion-code-modelization test-gen legacy_code.py --loop
```

| Flag | Scope | Description |
|------|-------|-------------|
| `--loop` | transpile / refactor / test-gen | Enable Agent Loop self-heal (takes precedence over `--stream`) |
| `--max-iter N` | transpile / refactor / test-gen | Max loop iterations (default 5) |

### Hook Interception Layer

A deterministic interception layer the model cannot bypass. A hook registry lets built-in guards
`allow`, `deny`, or `modify` payloads. Coverage is **event-scoped**, not universal:

| Event | Where emitted | Scope |
|-------|---------------|-------|
| `PRE_WRITE` | `SafeWriter` (all package write sites: snapshot, session, audit, CLI output) | every write through the unified writer |
| `POST_LLM` | `AgentLoop` (`--loop` paths only: transpile, refactor, test-gen) | only the self-heal loop |
| `PRE_EXEC` | `AgentLoop` verify-tool execution + `PipelineIntegrator` shell runs | loop tool exec + pipeline git/subprocess |
| `POST_EXEC` | `PipelineIntegrator` shell runs | pipeline git/subprocess |

**Non-loop LLM calls** (plain `transpile`, `refactor`, `scan`, `doc-gen`, `session`, `workflow`) do **not**
emit `POST_LLM` — they call `MLXClient.chat()` directly, bypassing the registry. To get hook coverage on
an LLM path, use `--loop`.

Built-in guards:
- `path_guard` (`PRE_WRITE`) — blocks path traversal / system dirs.
- `dangerous_cmd_guard` (`PRE_EXEC`) — blocks destructive shell commands (`rm -rf /`, fork bombs, `mkfs`, …), fail-closed allowlist.
- `secret_scrub` (`POST_LLM`) — redacts leaked secrets in LLM output (AWS keys, `sk-*`, `ghp_*`, private keys).
- `audit_log` (`POST_EXEC`) — records executed pipeline actions.
- `guard_evaluate` (`POST_LLM` + `PRE_WRITE`) — delegates to `fusion-core.guard_client` → fusion-guard
  (UDS JSON-RPC) when available, with a regex fallback + `WARNING` log when the guard is unreachable.

```bash
# Hooks are on by default when --loop is used; disable with the global flag:
fusion-code-modelization --no-hooks transpile src.py --from=python --to=go --loop
```

### REST API Server

Issue #3 — a FastAPI server exposing sessions, workflows, and cluster operations over HTTP/WebSocket:

```bash
# Install server extras (fastapi + uvicorn)
pip install -e ".[server]"

# Start the server (default 127.0.0.1:11459)
fusion-code-modelization serve --port 11459

# Or via the module
python -m fusion_code_modelization.server.runner
```

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/health` | Health check |
| `GET` / `POST` | `/api/sessions` | List / create sessions |
| `GET` | `/api/sessions/{id}` | Get session snapshot |
| `POST` | `/api/sessions/{id}/{action}` | start / pause / resume / complete / fail / delete / clone |
| `POST` | `/api/sessions/{id}/chat` | Send a chat message |
| `POST` | `/api/sessions/{id}/distribute` | Distribute session to cluster nodes (Issue #4) |
| `GET` | `/api/sessions/{id}/cluster-status` | Query cluster distribution status |
| `POST` | `/api/sessions/{id}/merge` | Merge completed cluster results |
| `POST` | `/api/workflows/run` | Decompose + execute a workflow |
| `GET` | `/api/workflows/{plan_id}` | Fetch a stored workflow result |
| `WS` | `/ws/chat` | Streaming chat over WebSocket |

Interactive API docs are auto-served at `/docs` (Swagger) and `/redoc`.

### Supported Languages

| Language | Analysis | Transpile | Test Gen | Security |
|----------|----------|-----------|----------|----------|
| Python | ✅ | ✅ | ✅ | ✅ |
| Java | ✅ | ✅ | ✅ | ✅ |
| Go | ✅ | ✅ | ❌ | ✅ |
| JavaScript/TypeScript | ✅ | ✅ | ❌ | ✅ |
| C/C++ | ✅ | ❌ | ❌ | ✅ |
| C# | ✅ | ✅ | ❌ | ✅ |
| COBOL | ✅ | ✅ | ❌ | ❌ |
| VB6 | ✅ | ✅ | ❌ | ❌ |
| Ruby | ✅ | ❌ | ❌ | ❌ |
| Swift | ✅ | ❌ | ❌ | ❌ |
| Rust | ✅ | ❌ | ❌ | ❌ |
| PHP | ✅ | ❌ | ❌ | ❌ |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Fusion-Code-Modelization CLI                  │
│  analyze · transpile · refactor · test-gen · security · session  │
│  snapshot · workflow · memory · sandbox · decompose · doc-gen    │
│  audit · cluster · plugin · benchmark · loadbalancer · offline   │
│  trace · agent-comm                                              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                     Core Engine                                  │
│                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │ DependencyAnaly│  │ CodeTranspiler │  │ Incremental      │  │
│  │ zer            │  │ (COBOL→Java,   │  │ Refactorer       │  │
│  │ (dead code,    │  │  VB6→C#, etc.) │  │ (test-first,     │  │
│  │  tech debt)    │  │  + streaming   │  │  dual-run verify, │  │
│  └────────────────┘  └────────────────┘  │  + streaming)    │  │
│                                          └──────────────────┘  │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │ TestGenerator  │  │ SecurityScanner│  │ PipelineIntegrat │  │
│  │ (unit/integrat │  │ (secrets,      │  │ or               │  │
│  │  ion tests,    │  │  injections,   │  │ (Git/CI-CD/PR)   │  │
│  │  + streaming)  │  │  + streaming)  │  └──────────────────┘  │
│  └────────────────┘  └────────────────┘                        │
│                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │ PRGenerator    │  │ DocGenerator   │  │ Microservice     │  │
│  │ (PR descriptions│  │ (migration     │  │ Decomposer       │  │
│  │  & changelogs) │  │  reports, API, │  │ (boundary analysis│ │
│  └────────────────┘  │  + streaming)  │  └──────────────────┘  │
│                       └────────────────┘                        │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              Platform Layer                                 │  │
│  │                                                            │  │
│  │  ┌─────────────┐ ┌──────────────┐ ┌────────────────────┐  │  │
│  │  │ Session     │ │ Snapshot     │ │ Security Sandbox   │  │  │
│  │  │ Engine      │ │ Manager      │ │ (readonly/manual/  │  │  │
│  │  │ (parallel   │ │ (incremental │ │  auto)             │  │  │
│  │  │  sessions)  │ │  file deltas)│ │                    │  │  │
│  │  └─────────────┘ └──────────────┘ └────────────────────┘  │  │
│  │                                                            │  │
│  │  ┌─────────────┐ ┌──────────────┐ ┌────────────────────┐  │  │
│  │  │ Dynamic     │ │ Project      │ │ MLXClient          │  │  │
│  │  │ Workflow    │ │ Memory       │ │ (unified HTTP      │  │  │
│  │  │ (LLM task   │ │ (FUSION.md   │ │  + streaming)      │  │  │
│  │  │  decompose) │ │  3-tier)     │ │                    │  │  │
│  │  └─────────────┘ └──────────────┘ └────────────────────┘  │  │
│  │                                                            │  │
│  │  ┌─────────────┐ ┌──────────────┐ ┌────────────────────┐  │  │
│  │  │ Progress    │ │ DualStack    │ │ Enterprise         │  │  │
│  │  │ Callbacks   │ │ Client       │ │ Audit Logger       │  │  │
│  │  │ (composable │ │ (local/cloud │ │ (JSONL store       │  │  │
│  │  │  events)    │ │  routing)    │ │  + export)         │  │  │
│  │  └─────────────┘ └──────────────┘ └────────────────────┘  │  │
│  │                                                            │  │
│  │  ┌─────────────┐ ┌──────────────┐ ┌────────────────────┐  │  │
│  │  │ Cluster     │ │ Plugin       │ │ Snapshot           │  │  │
│  │  │ Scheduler   │ │ Platform     │ │ Optimizer          │  │  │
│  │  │ (auto-sched)│ │ (registry +  │ │ (compress +        │  │  │
│  │  │             │ │  lifecycle)  │ │  verify)           │  │  │
│  │  └─────────────┘ └──────────────┘ └────────────────────┘  │  │
│  │                                                            │  │
│  │  ┌──────────────────── V2.0 ────────────────────────────┐│  │
│  │  │ Benchmark │ LoadBalancer │ Offline    │ Trace │AgentComm││
│  │  │ Suites &  │ 4-strategy  │ Deploy     │ Full- │Channel ││
│  │  │ Reports   │ scheduling  │ packages   │ chain │Coord.  ││
│  │  └───────────┴─────────────┴────────────┴───────┴────────┘│  │
│  └────────────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP API (all model calls)
┌───────────────────────────▼─────────────────────────────────────┐
│                    fusion-mlx (/v1/chat/completions)              │
│                    Apple Silicon MLX Runtime                     │
└─────────────────────────────────────────────────────────────────┘
```

### Key Modules

| Module | File | Description |
|--------|------|-------------|
| **Dependency Analyzer** | `analyzer/dependency.py` | Code dependency graph, dead code detection, tech debt estimation |
| **Code Transpiler** | `migration/transpiler.py` | Cross-language migration + streaming (`transpile_stream()`) |
| **Incremental Refactorer** | `refactor/refactorer.py` | Test-first refactoring with dual-run verification + streaming |
| **Test Generator** | `test_gen/generator.py` | Unit and integration test generation + streaming |
| **Security Scanner** | `security/scanner.py` | Multi-mode scanning: static-only, static+LLM, static+fusion-security + streaming |
| **Doc Generator** | `doc_gen/generator.py` | Module/class/API doc generation + streaming |
| **Progress Callbacks** | `core/progress.py` | ProgressEvent, LoggingProgressCallback, CompositeProgressCallback |
| **Pipeline Integrator** | `pipeline/integrator.py` | Git/CI-CD integration, PR creation, audit logging |
| **PR Generator** | `pr_gen/pr_generator.py` | PR description and changelog generation |
| **Microservice Decomposer** | `pr_gen/decomposer.py` | Monolith boundary analysis with multi-granularity |
| **MLXClient** | `core/client.py` | Unified HTTP client for fusion-mlx API, code extraction, streaming |
| **ModelConfig** | `core/config.py` | Model configuration with presets + dual-stack routing |
| **Session Engine** | `session/engine.py` | Parallel multi-agent sessions with state machine lifecycle |
| **Snapshot Manager** | `snapshot/manager.py` | Incremental file snapshots with create/restore/rewind |
| **Security Sandbox** | `sandbox/guard.py` | Three-tier (readonly/manual/auto) file and command guard |
| **Task Decomposer** | `workflow/decomposer.py` | LLM-powered task decomposition with dependency resolution |
| **Workflow Executor** | `workflow/executor.py` | Parallel sub-agent execution with progress callbacks |
| **Memory Tier Manager** | `memory/tier.py` | Three-tier FUSION.md (global/project/directory) |
| **Boundary Detector** | `decompose/detector.py` | Coupling analysis + LLM-powered microservice boundary detection |
| **AuditLogger** | `audit/logger.py` | Enterprise audit: log, search, export (JSON/CSV/Markdown), statistics |
| **ClusterScheduler** | `cluster/scheduler.py` | Node registration, task dispatch, auto-scheduling by load |
| **PluginManager** | `plugin/manager.py` | Plugin lifecycle: load/unload/execute with action validation |
| **BenchmarkRunner** | `benchmark/runner.py` | Benchmark suite execution, report generation, trend comparison |
| **LoadBalancer** | `loadbalancer/balancer.py` | 4-strategy cluster load balancing with capacity prediction |
| **OfflineManager** | `offline/manager.py` | Offline mode detection, package prepare/validate/restore |
| **TraceTracker** | `trace/tracker.py` | BFS forward/backward artifact tracing, coverage reports |
| **CollaborationCoordinator** | `agent_comm/coordinator.py` | Multi-agent collaboration with conflict detection/resolution |

---

## Development

```bash
# Install dev dependencies
pip install -e ".[test]"

# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=fusion_code_modelization

# Lint
ruff check .
ruff format --check .
```

### Test Stats
- **727+ tests**, 0 failures
- **Integration tests** covering cross-module workflows
- **Streaming tests** for all 5 LLM modules
- **Python 3.12+** compatible

---

## Changelog

### v0.7.1 — Enterprise Production-Readiness Audit Fix (P0-P3)
- **77 audit findings resolved** (9 CRITICAL / 24 HIGH / 25 MEDIUM / 19 LOW) across Architecture, Security, Performance, Enterprise-readiness, and Operations dimensions
- **Security**: hook layer hardened to fail-closed (unknown action → DENY); symlink traversal blocked in snapshot/scan; WebSocket + REST body-size limits; CORS/Host guard; secret scrubbing widened; non-loopback node http flagged; LLM JSON schema-validated before CLI/API return
- **Correctness**: `MemoryContext.summarize/query` now returns `str` per `chat()` contract (was returning raw dict); stream path gets empty-content guard (issue #14 extended); agent loop fail-fast on unknown tool; retry total_deadline cap
- **Performance**: snapshot scan size cap + ignore list (build/dist/target); dead-code cache; scheduler state incremental save
- **Type safety**: mypy 18 → 0 errors; bandit CI gating enforced (no `|| true`); ruff clean
- **Operations**: single-source `__version__` via importlib.metadata; CLI log timestamp + logger name; live-gateway probe test (`@pytest.mark.live`, skipped by default); README_CN synced 1:1 with README.md; `.[server]` install CI job; production operations guide expanded with **deployment runbook**, **secret rotation procedure**, and **monitoring dashboard** (scrape config + alert thresholds) in [`docs/operations.md`](docs/operations.md)
- **Version**: 0.7.0 → 0.7.1

### v0.6.5 — Server Port Fix (closes #16)
- **Issue #16**: moved the REST API server default port from `11441` to **`11459`** to resolve the collision with `fusion-code` (which owns `11441` per the monorepo port registry); `11459` allocated from the verified-free pool across all 40 repos
- **Centralized**: new `DEFAULT_SERVER_PORT = 11459` constant in `core/config.py`; `server/runner.py:run_server` and the `serve` CLI subcommand both reference it (single source of truth)
- **Docs**: README serve table + REST API section updated to `11459`
- 727 tests passing, lint + format clean

### v0.6.4 — Gateway Routing (no direct fusion-mlx)
- **Mandatory gateway routing**: all inference now goes through **fusion-gateway** on `localhost:11432/v1`; the package no longer connects to fusion-mlx (`localhost:11434`) directly
- **New defaults**: `ModelConfig.base_url` → `http://localhost:11432/v1` (`DEFAULT_GATEWAY_URL`); cluster node port + offline health-check → `11432` (`GATEWAY_PORT`); CLI `--mlx-url` and `serve`/`cluster` defaults aligned
- **Env-only key resolution**: `_resolve_api_key()` now resolves `FUSION_MLX_API_KEY` / `MLX_API_KEY` / `OPENAI_API_KEY` from env only (removed `~/.fusion-mlx/settings.json` fallback); the key must be a **gateway client key** (e.g. `fg-admin-key`), not the fusion-mlx upstream key
- **Touched 16 source files** (core + 14 feature modules + cli + server + offline + cluster) so every `mlx_url` default points at the gateway; `NodeClient` sends auth headers
- **Real-model acceptance verified through gateway**: chat, chat_stream, transpile, refactor, test-gen, security scan, doc-gen — every HTTP call to `localhost:11432/v1`, none to 11434
- 727 tests passing, lint + format clean

### v0.6.3 — Production Integration Fixes (auth + model id)
- **Auth header**: `MLXClient.chat()` / `chat_stream()` now send `Authorization: Bearer <api_key>` to fusion-mlx — previously sent no auth header and would be rejected with 401 on secured instances
- **Model id alignment**: default `ModelConfig.model` corrected from `qwen3.5-9b` to `Qwen3.5-9B-4bit` (the actually-loaded model id); `MODEL_PRESETS`, `SessionConfig`, `SessionEngine.create_session`, `NodeClient`, and `OfflineConfig` defaults updated consistently via a shared `DEFAULT_LOCAL_MODEL` constant
- **API key resolution**: new `_resolve_api_key()` resolves from `FUSION_MLX_API_KEY` / `MLX_API_KEY` / `OPENAI_API_KEY` env vars, falling back to `auth.api_key` in `~/.fusion-mlx/settings.json`; no secrets hardcoded in source
- **Real-model acceptance verified**: chat, chat_stream, transpile, refactor, test-gen, security scan (static+llm), doc-gen, session chat, PR/report/decomposer generation, cluster dispatch, REST server, and CLI all confirmed end-to-end against a running fusion-mlx
- 727 tests passing, coverage 83%, lint + format clean

### v0.6.2 — Project Naming Alignment
- **Issue #6**: aligned `pyproject.toml` `[project] name` to `fusion-code-modelization`, matching the GitHub repo, the CLI entry point, and the importable package (`fusion_code_modelization/`); removed the stale `fusion-code-modernization` dist registration
- 727 tests passing, lint + format clean

### v0.6.1 — REST API + Multi-node Cluster Sessions
- **Issue #3 — REST API server**: new `server/` module (FastAPI + uvicorn) exposing session CRUD/actions, chat (HTTP + WebSocket), workflow run/status, and cluster operations; `serve` CLI subcommand; `[server]` optional extra
- **Issue #4 — Multi-node cluster sessions**: `CLUSTER_RUNNING` session state + transitions, `cluster_nodes` config field (persisted), `distribute_session()` / `cluster_status()` / `merge_cluster_results()` on `SessionEngine`
- **Bugfix**: CLI `session` command used non-existent `session.id` (now `session.session_id`)
- **727 tests passing**, coverage 83%, lint + format clean

### v0.6.0 — Runtime Maturity + Streaming UX
- **Streaming LLM support**: `transpile_stream()`, `refactor_stream()`, `generate_unit_tests_stream()`, `scan_stream()`, `generate_docs_stream()` — real-time token output via SSE
- **CLI `--stream` flag**: Added to transpile, refactor, test-gen, security, doc-gen subcommands
- **Progress callback system**: `ProgressEvent`, `LoggingProgressCallback`, `CompositeProgressCallback` with composable emit helpers
- **Progress wired into**: session/engine, workflow/executor, decompose/detector
- **SecurityScanner fix**: `_check_hardcoded_secrets` regex corrected; `static_only` backward-compatible default
- **704 tests passing**, lint clean

### v0.5.0 — Architecture Compliance & Module Split
- Architecture compliance fixes across all modules
- `__init__.py` monoliths split into proper module files
- Dedicated test files for 8 uncovered modules
- Cross-module integration tests
- CLI hardening and CI enhancement
- 674 tests passing

### v0.3.0 — Enterprise Platform
- Enterprise audit system (JSONL + search/export/statistics)
- Cluster scheduling (node discovery + auto-schedule)
- MCP plugin platform (registry + lifecycle)
- Snapshot optimization (compress/verify/auto-cleanup)
- CLI extensions for all new modules

### v0.2.0 — Platform Expansion
- 6 new modules: benchmark, loadbalancer, offline, trace, agent_comm, dual-stack routing
- CLI subcommands for all new modules
- Ruff lint + GitHub Actions CI

### v0.1.0 — Initial Release
- Core engine: dependency analysis, transpiler, refactorer, test generator, security scanner
- Pipeline integrator, PR generator, doc generator, microservice decomposer
- Session engine, snapshot manager, sandbox guard
- Dynamic workflow, project memory, boundary detector

---

## License

[Apache License 2.0](LICENSE)

## Acknowledgments

- [fusion-mlx](https://github.com/dahai80/fusion-mlx) — Apple Silicon model serving
- [Claude Code Modernization](https://docs.anthropic.com/en/docs/claude-code) — Reference architecture

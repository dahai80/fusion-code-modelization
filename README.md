<div align="center">

# Fusion-Code-Modelization

**Legacy Code Modernization & Cross-Language Migration Platform**

Modernize, refactor, and migrate legacy codebases — entirely local, powered by fusion-mlx.

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-327-success.svg)](tests/)

[Quick Start](#quick-start) · [CLI Reference](#cli-reference) · [Architecture](#architecture) · [Documentation](docs/)

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
| **Snapshot optimization** | ✅ compress/verify/auto-cleanup | ✅ |

**One sentence:** Fusion-Code-Modelization is the local-first, privacy-compliant alternative to Claude Code Modernization — powered by fusion-mlx on Apple Silicon.

---

## Quick Start

### Prerequisites

- macOS with Apple Silicon (M1–M5)
- Python 3.12+
- [fusion-mlx](https://github.com/dahai80/fusion-mlx) running on `localhost:11434`

### Install

```bash
git clone https://github.com/dahai80/fusion-code-modelization.git
cd fusion-code-modelization
pip install -e ".[test]"
```

### Analyze a Codebase

```bash
# Analyze dependencies and generate report
fusion-code-modelization analyze /path/to/codebase --output=report.md

# View report
cat report.md
```

### Transpile Code Between Languages

```bash
# Convert Python to Java
fusion-code-modelization transpile input.py --from=python --to=java --output=output.java

# Convert COBOL to Go
fusion-code-modelization transpile legacy.cbl --from=cobol --to=go --output=modern.go
```

### Refactor Code Safely

```bash
# Refactor with test-first approach
fusion-code-modelization refactor legacy_code.py --output=refactored.py

# With specific instructions
fusion-code-modelization refactor messy_code.py --instructions="Extract helper functions, add type hints"
```

### Generate Tests

```bash
fusion-code-modelization test-gen source.py --output=tests.py
```

### Security Scan

```bash
fusion-code-modelization security legacy_code.py --output=security_report.json
```

---

## CLI Reference

| Command | Description |
|---------|-------------|
| `analyze <path> [--output]` | Analyze codebase dependencies and generate report |
| `transpile <file> --from --to [--output]` | Transpile code between languages |
| `refactor <file> [--instructions] [--output]` | Refactor code incrementally |
| `test-gen <file> [--language] [--output]` | Generate unit tests |
| `security <file> [--language] [--output]` | Scan for security vulnerabilities |
| `session <action> [--id] [--name]` | Manage parallel sessions (create/list/start/pause/resume/complete/delete) |
| `snapshot <action> [--project-dir] [--id] [--label] [--steps]` | Incremental snapshots and rollback (create/list/restore/rewind/delete) |
| `workflow <action> [--description] [--template] [--max-parallel]` | Dynamic task decomposition and execution (decompose/run) |
| `memory <action> [--project-dir] [--query]` | Three-tier project memory (init/list/load/query) |
| `sandbox <action> [--path] [--mode]` | Security sandbox and audit (check/audit) |
| `decompose <path> [--method] [--output]` | Microservice boundary detection (static/llm) |
| `doc-gen <file> [--type] [--language] [--output]` | Documentation generation (module/class/api) |
| `audit <action> [--actor] [--severity]` | Enterprise audit logging (log/search/export/stats/cleanup) |
| `cluster <action> [--node-id] [--session-id]` | Distributed cluster scheduling (discover/dispatch/status/schedule/migrate/register/tasks) |
| `plugin <action> [--plugin-id] [--query]` | MCP plugin platform (list/search/install/load/unload/execute/status) |
| `version` | Show version info |

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
│  audit · cluster · plugin                                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                     Core Engine                                  │
│                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │ DependencyAnaly│  │ CodeTranspiler │  │ Incremental      │  │
│  │ zer            │  │ (COBOL→Java,   │  │ Refactorer       │  │
│  │ (dead code,    │  │  VB6→C#, etc.) │  │ (test-first,     │  │
│  │  tech debt)    │  └────────────────┘  │  dual-run verify) │  │
│  └────────────────┘                      └──────────────────┘  │
│                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │ TestGenerator  │  │ SecurityScanner│  │ PipelineIntegrat │  │
│  │ (unit/integrat │  │ (secrets,      │  │ or               │  │
│  │  ion tests)    │  │  injections)   │  │ (Git/CI-CD/PR)   │  │
│  └────────────────┘  └────────────────┘  └──────────────────┘  │
│                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │ PRGenerator    │  │ DocGenerator   │  │ Microservice     │  │
│  │ (PR descriptions│  │ (migration     │  │ Decomposer       │  │
│  │  & changelogs) │  │  reports, API) │  │ (boundary analysis│ │
│  └────────────────┘  └────────────────┘  └──────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              Platform Layer (NEW)                          │  │
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
│  │  │ (LLM task   │ │ (FUSION.md   │ │  client)           │  │  │
│  │  │  decompose) │ │  3-tier)     │ │                    │  │  │
│  │  └─────────────┘ └──────────────┘ └────────────────────┘  │  │
│  │                                                            │  │
│  │  ┌─────────────┐ ┌──────────────┐ ┌────────────────────┐  │  │
│  │  │ DualStack   │ │ Enterprise   │ │ Cluster            │  │  │
│  │  │ Client      │ │ Audit Logger │ │ Scheduler          │  │  │
│  │  │ (local/cloud│ │ (JSONL store │ │ (node discovery,   │  │  │
│  │  │  routing)   │ │  + export)   │ │  auto-schedule)    │  │  │
│  │  └─────────────┘ └──────────────┘ └────────────────────┘  │  │
│  │                                                            │  │
│  │  ┌─────────────┐ ┌──────────────┐                         │  │
│  │  │ Plugin      │ │ Snapshot     │                         │  │
│  │  │ Platform    │ │ Optimizer    │                         │  │
│  │  │ (registry + │ │ (compress +  │                         │  │
│  │  │  lifecycle) │ │  verify)     │                         │  │
│  │  └─────────────┘ └──────────────┘                         │  │
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
| **Code Transpiler** | `migration/transpiler.py` | Cross-language migration (COBOL→Java, VB6→C#, etc.) |
| **Incremental Refactorer** | `refactor/refactorer.py` | Test-first refactoring with dual-run verification |
| **Test Generator** | `test_gen/generator.py` | Unit and integration test generation (UnitTestGenerator) |
| **Security Scanner** | `security/scanner.py` | Hardcoded secrets, injection vulnerabilities, CVE detection |
| **Pipeline Integrator** | `pipeline/__init__.py` | Git/CI-CD integration, PR creation, audit logging |
| **Priority Scorer** | `pipeline/__init__.py` | Migration priority scoring (business + tech debt) |
| **PR Generator** | `pr_gen/__init__.py` | PR description and changelog generation |
| **Doc Generator** | `pr_gen/__init__.py` | Migration reports and API documentation |
| **Microservice Decomposer** | `pr_gen/__init__.py` | Monolith boundary analysis and microservice suggestions |
| **MLXClient** | `core/client.py` | Unified HTTP client for fusion-mlx API, code extraction |
| **ModelConfig** | `core/config.py` | Model configuration with presets (default/code/analysis/creative/fast) |
| **Session Engine** | `session/engine.py` | Parallel multi-agent sessions with state machine lifecycle |
| **Session Store** | `session/store.py` | JSON file persistence for session state |
| **Snapshot Manager** | `snapshot/manager.py` | Incremental file snapshots with create/restore/rewind |
| **File Delta** | `snapshot/delta.py` | difflib-based file diff computation and application |
| **Security Sandbox** | `sandbox/guard.py` | Three-tier (readonly/manual/auto) file and command guard |
| **Sandbox Policy** | `sandbox/policy.py` | Path boundaries, dangerous command blocking, sensitive file protection |
| **Sandbox Audit** | `sandbox/audit.py` | Operation logging with JSON-line persistence |
| **Task Decomposer** | `workflow/decomposer.py` | LLM-powered task decomposition with dependency resolution |
| **Workflow Executor** | `workflow/executor.py` | Parallel sub-agent execution with merge/converge |
| **Workflow Templates** | `workflow/decomposer.py` | Pre-built templates (legacy_migration, security_scan, batch_api) |
| **Memory Tier Manager** | `memory/tier.py` | Three-tier FUSION.md (global/project/directory) |
| **Memory Context** | `memory/context.py` | LLM-enhanced memory summarization and query |
| **Boundary Detector** | `decompose/__init__.py` | Coupling analysis + LLM-powered microservice boundary detection |
| **Documentation Generator** | `doc_gen/__init__.py` | Module/class/API doc generation + README builder |
| **DualStackClient** | `core/client.py` | Local/cloud dual-stack with automatic routing and fallback |
| **ModelRouter** | `core/config.py` | Complexity-based routing (LOCAL_FIRST/CLOUD_FIRST/COMPLEXITY_BASED) |
| **DualModelConfig** | `core/config.py` | Dual model stack configuration with routing strategy |
| **AuditLogger** | `audit/logger.py` | Enterprise audit: log, search, export (JSON/CSV/Markdown), statistics |
| **AuditStore** | `audit/store.py` | JSONL-based audit persistence with rotation and cleanup |
| **AuditEntry/Filter/Report** | `audit/models.py` | Audit data models with 18 action types, 3 severity levels |
| **ClusterScheduler** | `cluster/scheduler.py` | Node registration, task dispatch, auto-scheduling by load |
| **NodeClient** | `cluster/node_client.py` | HTTP client for cluster node health check and task submission |
| **NodeInfo/TaskDispatch** | `cluster/models.py` | Cluster data models with load_score property |
| **PluginManager** | `plugin/manager.py` | Plugin lifecycle: load/unload/execute with action validation |
| **PluginRegistry** | `plugin/registry.py` | JSON-based plugin registry with install/update/disable |
| **PluginManifest** | `plugin/models.py` | Plugin manifest with 9 categories, 5 statuses, action schemas |

---

## Comparison with Claude Code Modernization

| Capability | Claude Code | Fusion-Code-Modelization |
|------------|-------------|--------------------------|
| Code dependency analysis | ✅ | ✅ |
| Dead code detection | ✅ | ✅ |
| Tech debt estimation | ✅ | ✅ |
| Cross-language migration | ✅ COBOL→Java, etc. | ✅ COBOL→Java, VB6→C#, etc. |
| Test-first refactoring | ✅ | ✅ |
| Dual-run verification | ✅ | ✅ |
| Unit test generation | ✅ | ✅ |
| Security vulnerability scanning | ✅ | ✅ |
| Enterprise pipeline (Git/CI-CD) | ✅ | ✅ |
| Migration priority scoring | ✅ | ✅ |
| Microservice decomposition | ✅ | ✅ |
| Audit logging | ✅ | ✅ |
| Parallel multi-agent sessions | ✅ | ✅ SessionEngine |
| Dynamic Workflow | ✅ | ✅ TaskDecomposer + WorkflowExecutor |
| Incremental snapshots | ✅ | ✅ SnapshotManager + FileDelta |
| Three-tier project memory | ✅ CLAUDE.md | ✅ FUSION.md |
| Security sandbox | ✅ | ✅ three-tier (readonly/manual/auto) |
| **Local offline** | ❌ Cloud-only | ✅ **100% local** |
| **Data privacy** | ❌ Code uploaded to cloud | ✅ **Data never leaves device** |
| **China compliance** | ❌ Violates data security law | ✅ **Full compliance** |
| **Zero API cost** | ❌ Enterprise subscription | ✅ **Free** |
| **Gitee/GitLab support** | ❌ GitHub only | ✅ **All platforms** |
| **Dual-stack model routing** | ✅ | ✅ **local/cloud + fallback** |
| **Enterprise audit system** | ✅ | ✅ **JSONL + export** |
| **Cluster scheduling** | ✅ | ✅ **auto-schedule by load** |
| **MCP plugin platform** | ✅ | ✅ **registry + lifecycle** |
| **Snapshot optimization** | ✅ | ✅ **compress/verify/cleanup** |

---

## Development

```bash
# Install dev dependencies
pip install -e ".[test]"

# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=fusion_code_modelization
```

### Test Stats
- **327 tests**, 0 failures
- **96%+ statement coverage**
- **Python 3.12+** compatible

### Lint

```bash
pip install -e ".[lint]"
ruff check .
ruff format --check .
```

---

## License

MIT

## Acknowledgments

- [fusion-mlx](https://github.com/dahai80/fusion-mlx) — Apple Silicon model serving
- [Claude Code Modernization](https://docs.anthropic.com/en/docs/claude-code) — Reference architecture